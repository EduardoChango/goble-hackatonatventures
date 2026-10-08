"""Almacenamiento en PostgreSQL (esquema en db/init/).

data.py lo usa cuando existe DATABASE_URL (o DB_HOST en AWS). Arma el MISMO dict de estado
que data.seed() para el paciente de la sesión, así logic.py y las plantillas no cambian.
Las escrituras son funciones explícitas (guardar_perfil, registrar_compra, ...).
"""
import contextvars
import os
import re
from datetime import date
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from werkzeug.security import check_password_hash

ZONA = "America/Guayaquil"
_paciente = contextvars.ContextVar("paciente", default=None)
_conexion = contextvars.ContextVar("conexion", default=None)

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
HORARIOS_POR_DEFECTO = {24: ["08:00"], 12: ["08:00", "20:00"], 8: ["06:00", "14:00", "22:00"],
                        6: ["06:00", "12:00", "18:00", "00:00"]}


# ---------- conexión ----------
def _dsn():
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    # AWS: la Lambda recibe las piezas por separado (la contraseña viene de Secrets Manager)
    return psycopg.conninfo.make_conninfo(
        host=os.environ["DB_HOST"], port=os.getenv("DB_PORT", "5432"), dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"], password=os.environ["DB_PASSWORD"], sslmode="require")


def conectar():
    return psycopg.connect(_dsn(), autocommit=True, row_factory=dict_row, connect_timeout=10,
                           options=f"-c TimeZone={ZONA}")


def _c():
    """Una conexión por request (app.py la cierra en teardown_request)."""
    c = _conexion.get()
    if c is None or c.closed:
        c = conectar()
        _conexion.set(c)
    return c


def cerrar():
    c = _conexion.get()
    if c is not None and not c.closed:
        c.close()
    _conexion.set(None)


def usar_paciente(pid):
    _paciente.set(pid)


def _pid():
    pid = _paciente.get()
    if pid is None:
        raise RuntimeError("No hay paciente en la sesión (falta login)")
    return pid


def _uno(sql, *params):
    return _c().execute(sql, params).fetchone()


def _todos(sql, *params):
    return _c().execute(sql, params).fetchall()


# ---------- login ----------
def autenticar(email, password):
    u = _uno("SELECT id, paciente_id, password_hash FROM usuario WHERE lower(email) = lower(%s)", email.strip())
    if not u or not check_password_hash(u["password_hash"], password):
        return None
    _c().execute("UPDATE usuario SET ultimo_login = now() WHERE id = %s", (u["id"],))
    return u["paciente_id"]


def usuarios_demo():
    return [(r["email"], r["nombre"]) for r in _todos(
        "SELECT u.email, p.nombre FROM usuario u JOIN paciente p ON p.id = u.paciente_id ORDER BY p.id")]


# ---------- lectura: estado del paciente + catálogos ----------
def _vence(d):
    hoy = date.today()
    if d <= hoy:
        return "Hoy"
    if (d - hoy).days < 7:
        return f"Hasta el {DIAS[d.weekday()]}"
    return f"Hasta el {d.day}/{d.month}"


def cargar():
    """Devuelve (estado, farmacias, promos) con la misma forma que data.seed() / data.FARMACIAS / PROMOS."""
    pid = _pid()
    hoy = date.today()
    p = _uno("""
        SELECT nombre, cuidador, tiene_iess, consentimiento, lat::float AS lat, lng::float AS lng,
               date_part('year', age(CURRENT_DATE, fecha_nacimiento))::int AS edad
        FROM paciente WHERE id = %s""", pid)
    if p is None:
        raise LookupError(f"Paciente {pid} no existe")
    condiciones = [r["nombre"] for r in _todos("""
        SELECT c.nombre FROM paciente_condicion pc JOIN condicion c ON c.id = pc.condicion_id
        WHERE pc.paciente_id = %s ORDER BY c.nombre""", pid)]
    cita = _uno("""
        SELECT to_char(fecha_hora, 'YYYY-MM-DD"T"HH24:MI') AS cita FROM cita WHERE paciente_id = %s
        ORDER BY (fecha_hora < now()), abs(extract(epoch FROM fecha_hora - now())) LIMIT 1""", pid)

    visitas = {}
    for r in _todos("""
            SELECT to_char(v.fecha, 'YYYY-MM-DD') AS fecha, m.nombre_generico AS nombre, ri.dosis_mg,
                   ri.cada_horas, ri.dias,
                   ARRAY(SELECT to_char(h, 'HH24:MI') FROM unnest(ri.horarios) h ORDER BY h) AS horarios
            FROM visita v JOIN receta_item ri ON ri.visita_id = v.id
            JOIN medicamento m ON m.id = ri.medicamento_id
            WHERE v.paciente_id = %s ORDER BY v.fecha, ri.id""", pid):
        fecha = r.pop("fecha")
        visitas.setdefault(fecha, []).append(r)

    entregas = {}
    for r in _todos("""
            SELECT to_char(v.fecha, 'YYYY-MM-DD') AS fecha, m.nombre_generico AS nombre,
                   e.estado::text AS estado, e.unidades_recibidas AS recibido
            FROM entrega_iess e JOIN receta_item ri ON ri.id = e.receta_item_id
            JOIN visita v ON v.id = ri.visita_id JOIN medicamento m ON m.id = ri.medicamento_id
            WHERE v.paciente_id = %s""", pid):
        entregas.setdefault(r["fecha"], {})[r["nombre"]] = {"estado": r["estado"], "recibido": r["recibido"]}

    compras = {}
    for r in _todos("""
            SELECT to_char(v.fecha, 'YYYY-MM-DD') AS fecha, m.nombre_generico AS nombre, sum(ci.unidades)::int AS u
            FROM compra_item ci JOIN receta_item ri ON ri.id = ci.receta_item_id
            JOIN visita v ON v.id = ri.visita_id JOIN medicamento m ON m.id = ri.medicamento_id
            WHERE v.paciente_id = %s GROUP BY 1, 2""", pid):
        compras.setdefault(r["fecha"], {})[r["nombre"]] = r["u"]

    tomas = [r["id"] for r in _todos("""
        SELECT m.nombre_generico || '@' || to_char(t.hora, 'HH24:MI') AS id
        FROM toma t JOIN receta_item ri ON ri.id = t.receta_item_id
        JOIN visita v ON v.id = ri.visita_id JOIN medicamento m ON m.id = ri.medicamento_id
        WHERE v.paciente_id = %s AND t.fecha = %s""", pid, hoy)]
    enviados = [r["clave"] for r in _todos(
        "SELECT clave FROM aviso WHERE paciente_id = %s AND clave LIKE %s", pid, hoy.isoformat() + "|%")]
    cola = [{"_id": r["id"], "tipo": r["tipo"], "titulo": r["titulo"], "cuerpo": r["cuerpo"],
             "corto": r["corto"] or r["titulo"], "url": r["url"]}
            for r in _todos("""
                SELECT id, tipo::text AS tipo, titulo, cuerpo, corto, url FROM aviso
                WHERE paciente_id = %s AND mostrado_en IS NULL ORDER BY creado_en""", pid)]

    estado = {
        "perfil": {"nombre": p["nombre"], "edad": p["edad"], "cuidador": p["cuidador"] or "",
                   "condiciones": condiciones, "iess": p["tiene_iess"], "consentimiento": p["consentimiento"],
                   "lat": p["lat"], "lng": p["lng"], "cita": cita["cita"] if cita else None},
        "visitas": [{"fecha": f, "meds": meds} for f, meds in visitas.items()],
        "entregas": entregas,
        "compras": compras,
        "vendido": {},  # en BD comprar descuenta farmacia_stock directamente
        "tomas": {hoy.isoformat(): tomas},
        "enviados": enviados,
        "cola": cola,
        "sim_hora": None,
    }

    farmacias = [{**r, "stock": r["stock"] or {}} for r in _todos("""
        SELECT f.id, c.nombre || ' · ' || f.sucursal AS nombre, f.parroquia, f.direccion,
               f.lat::float AS lat, f.lng::float AS lng,
               'Abierta hasta las ' || to_char(f.hora_cierre, 'HH24:MI') AS horario,
               (SELECT jsonb_object_agg(m.nombre_generico, s.unidades)
                FROM farmacia_stock s JOIN medicamento m ON m.id = s.medicamento_id
                WHERE s.farmacia_id = f.id) AS stock
        FROM farmacia f JOIN cadena c ON c.id = f.cadena_id ORDER BY f.id""")]
    promos = [{"titulo": r["titulo"], "detalle": r["detalle"], "med": r["med"], "vence": _vence(r["vigente_hasta"])}
              for r in _todos("""
                SELECT pr.titulo, pr.detalle, m.nombre_generico AS med, pr.vigente_hasta
                FROM promocion pr LEFT JOIN medicamento m ON m.id = pr.medicamento_id ORDER BY pr.id""")]
    return estado, farmacias, promos


# ---------- escrituras ----------
def _visita_actual_id(pid):
    r = _uno("SELECT id FROM visita WHERE paciente_id = %s ORDER BY fecha DESC LIMIT 1", pid)
    return r["id"] if r else None


def _medicamento_id(nombre):
    r = _uno("SELECT id FROM medicamento WHERE lower(nombre_generico) = lower(%s)", nombre)
    if r:
        return r["id"]
    return _uno("INSERT INTO medicamento (nombre_generico) VALUES (%s) RETURNING id", nombre)["id"]


def guardar_perfil(perfil):
    pid = _pid()
    with _c().transaction():
        _c().execute("""
            UPDATE paciente SET
                nombre = %(nombre)s,
                cuidador = NULLIF(%(cuidador)s, ''),
                tiene_iess = %(iess)s,
                consentimiento = %(consentimiento)s,
                consentimiento_en = CASE WHEN NOT %(consentimiento)s THEN NULL
                                         ELSE COALESCE(consentimiento_en, now()) END,
                -- el formulario envía la edad: solo se mueve la fecha de nacimiento si la edad cambió
                fecha_nacimiento = (fecha_nacimiento + make_interval(
                    years => date_part('year', age(CURRENT_DATE, fecha_nacimiento))::int - %(edad)s))::date,
                lat = %(lat)s, lng = %(lng)s
            WHERE id = %(pid)s""", {**perfil, "pid": pid, "cuidador": perfil.get("cuidador") or ""})
        nombres = perfil.get("condiciones") or []
        _c().execute("INSERT INTO condicion (nombre) SELECT unnest(%s::text[]) ON CONFLICT DO NOTHING", (nombres,))
        _c().execute("DELETE FROM paciente_condicion WHERE paciente_id = %s", (pid,))
        _c().execute("""INSERT INTO paciente_condicion (paciente_id, condicion_id)
                        SELECT %s, id FROM condicion WHERE nombre = ANY(%s::text[])""", (pid, nombres))
        if perfil.get("cita"):
            _c().execute("""DELETE FROM cita WHERE paciente_id = %s
                            AND (fecha_hora > now() OR fecha_hora = %s::timestamptz)""", (pid, perfil["cita"]))
            _c().execute("INSERT INTO cita (paciente_id, fecha_hora) VALUES (%s, %s::timestamptz)",
                         (pid, perfil["cita"]))


def guardar_ubicacion(lat, lng):
    _c().execute("UPDATE paciente SET lat = %s, lng = %s WHERE id = %s", (lat, lng, _pid()))


def guardar_receta(fecha, meds, origen="manual", extraccion=None):
    """Reemplaza la receta de esa fecha (app.py solo deja una por día)."""
    pid = _pid()
    with _c().transaction():
        _c().execute("DELETE FROM visita WHERE paciente_id = %s AND fecha = %s", (pid, fecha))
        vid = _uno("""INSERT INTO visita (paciente_id, fecha, origen, extraccion_ia)
                      VALUES (%s, %s, %s, %s) RETURNING id""",
                   pid, fecha, origen, Jsonb(extraccion) if extraccion else None)["id"]
        vistos = set()
        for m in meds:
            mid = _medicamento_id(m["nombre"])
            if mid in vistos:  # el mismo medicamento dos veces en el formulario
                continue
            vistos.add(mid)
            horarios = m.get("horarios") or HORARIOS_POR_DEFECTO.get(int(m["cada_horas"]), ["08:00"])
            _c().execute("""INSERT INTO receta_item (visita_id, medicamento_id, dosis_mg, cada_horas, dias, horarios)
                            VALUES (%s, %s, %s, %s, %s, %s::time[])""",
                         (vid, mid, m["dosis_mg"], m["cada_horas"], m["dias"], horarios))


def registrar_entrega(fecha, registro):
    pid = _pid()
    with _c().transaction():
        for nombre, e in registro.items():
            _c().execute("""
                INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas)
                SELECT ri.id, %s, %s FROM receta_item ri
                JOIN visita v ON v.id = ri.visita_id JOIN medicamento m ON m.id = ri.medicamento_id
                WHERE v.paciente_id = %s AND v.fecha = %s AND m.nombre_generico = %s
                ON CONFLICT (receta_item_id) DO UPDATE
                SET estado = EXCLUDED.estado, unidades_recibidas = EXCLUDED.unidades_recibidas, registrado_en = now()
            """, (e["estado"], int(e["recibido"]), pid, fecha, nombre))


def registrar_compra(farmacia_id, modo, unidades):
    """unidades = {nombre_medicamento: unidades}. Descuenta el stock de la farmacia."""
    pid = _pid()
    unidades = {n: int(u) for n, u in unidades.items() if int(u) > 0}
    vid = _visita_actual_id(pid)
    if not unidades or vid is None:
        return
    with _c().transaction():
        cid = _uno("""INSERT INTO compra (paciente_id, visita_id, farmacia_id, modo)
                      VALUES (%s, %s, %s, %s) RETURNING id""",
                   pid, vid, farmacia_id, modo if modo in ("recoger", "envio") else "recoger")["id"]
        for nombre, u in unidades.items():
            _c().execute("""
                INSERT INTO compra_item (compra_id, receta_item_id, unidades)
                SELECT %s, ri.id, %s FROM receta_item ri JOIN medicamento m ON m.id = ri.medicamento_id
                WHERE ri.visita_id = %s AND m.nombre_generico = %s
                ON CONFLICT (compra_id, receta_item_id) DO UPDATE SET unidades = compra_item.unidades + EXCLUDED.unidades
            """, (cid, u, vid, nombre))
            _c().execute("""
                UPDATE farmacia_stock SET unidades = GREATEST(unidades - %s, 0)
                WHERE farmacia_id = %s AND medicamento_id = (SELECT id FROM medicamento WHERE nombre_generico = %s)
            """, (u, farmacia_id, nombre))


def registrar_toma(did):
    """did = 'Losartán@08:00', una dosis de la receta actual tomada hoy."""
    nombre, _, hora = did.rpartition("@")
    pid = _pid()
    _c().execute("""
        INSERT INTO toma (receta_item_id, fecha, hora)
        SELECT ri.id, %s, %s FROM receta_item ri JOIN medicamento m ON m.id = ri.medicamento_id
        WHERE ri.visita_id = %s AND m.nombre_generico = %s
        ON CONFLICT (receta_item_id, fecha, hora) DO NOTHING
    """, (date.today(), hora, _visita_actual_id(pid), nombre))


def guardar_avisos(avisos, claves_nuevas):
    """Marca como mostrados los avisos de la cola y registra los automáticos (con su clave, para no repetir)."""
    pid = _pid()
    ids = [a["_id"] for a in avisos if "_id" in a]
    nuevos = [a for a in avisos if "_id" not in a]
    with _c().transaction():
        if ids:
            _c().execute("UPDATE aviso SET mostrado_en = now() WHERE paciente_id = %s AND id = ANY(%s)", (pid, ids))
        # logic.generar_avisos agrega una clave a s["enviados"] por cada aviso automático, en el mismo orden
        for a, clave in zip(nuevos, claves_nuevas):
            _c().execute("""
                INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url, clave, mostrado_en)
                VALUES (%s, %s, %s, %s, %s, %s, %s, now()) ON CONFLICT (paciente_id, clave) DO NOTHING
            """, (pid, a["tipo"], a["titulo"], a["cuerpo"], a.get("corto"), a.get("url", "/"), clave))


def encolar_aviso(a):
    _c().execute("""INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url)
                    VALUES (%s, %s, %s, %s, %s, %s)""",
                 (_pid(), a["tipo"], a["titulo"], a["cuerpo"], a.get("corto"), a.get("url", "/")))


# ---------- semillas: inicializar la BD y "Restablecer datos" ----------
def dir_semillas():
    """db/init del repo en local; en la Lambda se empaqueta como db_init/ junto a la app."""
    aqui = Path(__file__).resolve().parent
    candidatos = [os.getenv("DB_INIT_DIR"), aqui / "db_init"]
    if len(aqui.parents) > 2:  # repo: apps/frontend/tratamiento-app -> db/init
        candidatos.append(aqui.parents[2] / "db" / "init")
    for d in candidatos:
        if d and Path(d).is_dir():
            return Path(d)
    raise FileNotFoundError("No encuentro los .sql de db/init (define DB_INIT_DIR)")


def _bloques(texto):
    """Separa un .sql en bloques marcados con '-- @etiqueta' (hasta el siguiente marcador o '-- @fin')."""
    bloques, actual = {}, None
    for linea in texto.splitlines():
        m = re.match(r"^-- @(.+?)\s*$", linea)
        if m:
            actual = None if m.group(1) == "fin" else m.group(1)
            continue
        if actual:
            bloques.setdefault(actual, []).append(linea)
    return {k: "\n".join(v) for k, v in bloques.items()}


def reset():
    """Vuelve el paciente de la sesión a su estado de ejemplo y repone el stock simulado."""
    pid = _pid()
    with _c().transaction():
        _c().execute("DELETE FROM paciente WHERE id = %s", (pid,))  # en cascada: recetas, tomas, avisos, usuario...
        for archivo in sorted(dir_semillas().glob("*.sql")):
            bloques = _bloques(archivo.read_text(encoding="utf-8"))
            for etiqueta in (f"paciente {pid}", "stock"):
                if etiqueta in bloques:
                    _c().execute(bloques[etiqueta])


def inicializar(forzar=False):
    """Crea el esquema y carga la data fake (db/init/*.sql en orden). Lo usa dbinit.py."""
    archivos = sorted(dir_semillas().glob("*.sql"))  # antes de tocar la BD
    if not archivos:
        raise FileNotFoundError("No hay archivos .sql en " + str(dir_semillas()))
    c = conectar()
    try:
        existe = c.execute("SELECT to_regclass('public.paciente') IS NOT NULL AS e").fetchone()["e"]
        if existe and not forzar:
            return {"estado": "ya inicializada"}
        with c.transaction():  # todo o nada: si un .sql falla, la BD queda como estaba
            if existe:
                c.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
            for archivo in archivos:
                c.execute(archivo.read_text(encoding="utf-8"))
        pacientes = c.execute("SELECT count(*) AS n FROM paciente").fetchone()["n"]
        return {"estado": "inicializada", "archivos": [a.name for a in archivos], "pacientes": pacientes}
    finally:
        c.close()
