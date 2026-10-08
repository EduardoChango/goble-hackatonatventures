"""Genera los seeds de pacientes fake y de usuarios de la demo:

    db/init/004_pacientes_fake.sql   10 pacientes fake (ids 2-11), uno por cada caso de la app
    db/init/005_usuarios.sql         un usuario de login por paciente (ids 1-11)

Uso:  py db/gen_pacientes_fake.py

Es determinista (semilla fija): regenerarlo produce el mismo SQL.
Las fechas de visitas, tomas y citas son relativas a CURRENT_DATE para que la data
siempre se vea "actual" sin importar cuándo se levante la base.
Cada paciente va en un bloque "-- @paciente N": "Restablecer datos" re-ejecuta solo ese bloque.
"""

import hashlib
import json
import random
import re
import unicodedata
from datetime import date
from pathlib import Path

INIT = Path(__file__).resolve().parent / "init"
OUT = INIT / "004_pacientes_fake.sql"
OUT_USUARIOS = INIT / "005_usuarios.sql"
PASSWORD_DEMO = "demo1234"
rng = random.Random(2026)

MED = {"Losartán": 1, "Metformina": 2, "Atorvastatina": 3, "Amlodipino": 4,
       "Enalapril": 5, "Glibenclamida": 6, "Levotiroxina": 7, "Omeprazol": 8}


def uid_medicina(nombre, dosis):
    """uid FE-xxxxx de la presentación (nombre + concentración) en db/datos_farmaenlace/medicinas.sql."""
    texto = (INIT.parent / "datos_farmaenlace" / "medicinas.sql").read_text(encoding="utf-8")
    for unidad in ("mg", "mcg"):
        m = re.search(r"\('(FE-\d+)', '" + re.escape(nombre) + f"', '{dosis} {unidad}'", texto)
        if m:
            return m.group(1)
    raise SystemExit(f"No hay {nombre} {dosis} en medicinas.sql")
COND = {"Hipertensión": 1, "Diabetes tipo 2": 2, "Dislipidemia": 3,
        "Hipotiroidismo": 4, "Gastritis crónica": 5}
HORARIOS = {24: ["08:00"], 12: ["08:00", "20:00"], 8: ["06:00", "14:00", "22:00"]}
HORARIO_NOCHE = {"Atorvastatina": ["21:00"], "Levotiroxina": ["06:00"]}

NOMBRES = ["Rosa", "Jorge", "Carmen", "Segundo", "Blanca", "Washington", "Gloria",
           "Héctor", "Marlene", "Fausto", "Teresa", "Galo"]
APELLIDOS = ["Guamán", "Paredes", "Villacís", "Naranjo", "Chicaiza", "Lozada",
             "Pazmiño", "Altamirano", "Toapanta", "Sánchez", "Cevallos", "Masaquiza"]
CUIDADORES = ["Hijo/a", "Esposo/a", "Nieto/a", "Hermano/a", None]

# Puembo: La Palma Polo Club, sede del hackatón (igual que data.CENTRO)
LAT, LNG = -0.1588, -78.3665


def item(nombre, dosis, cada=24, dias=30):
    return {"nombre": nombre, "dosis_mg": dosis, "cada_horas": cada, "dias": dias,
            "horarios": HORARIO_NOCHE.get(nombre) if cada == 24 and nombre in HORARIO_NOCHE
            else HORARIOS[cada]}


def total(it):
    return len(it["horarios"]) * it["dias"]


# Cada caso: visitas = [(días atrás, [items], origen)], la última es la receta actual.
# entrega: "todo" | None (IESS no responde) | {nombre: (estado, recibido)}; solo receta actual.
# compras: [(farmacia_id, modo, {nombre: unidades})] sobre la receta actual.
CASOS = [
    dict(caso="Sin IESS: compra todo", iess=False, condiciones=["Hipertensión", "Dislipidemia"],
         visitas=[(12, [item("Enalapril", 10, 12), item("Atorvastatina", 20)], "manual")],
         entrega=None),
    dict(caso="IESS entregó todo (todo al día)", iess=True, condiciones=["Hipertensión"],
         visitas=[(40, [item("Losartán", 50)], "manual"),
                  (8, [item("Losartán", 50), item("Amlodipino", 5)], "manual")],
         entrega="todo"),
    dict(caso="IESS aún no responde", iess=True, condiciones=["Diabetes tipo 2"],
         visitas=[(35, [item("Metformina", 850, 12)], "manual"),
                  (1, [item("Metformina", 850, 12), item("Glibenclamida", 5)], "manual")],
         entrega=None),
    dict(caso="Primera visita", iess=True, condiciones=["Dislipidemia"],
         visitas=[(5, [item("Atorvastatina", 40), item("Omeprazol", 20)], "manual")],
         entrega={"Atorvastatina": ("no", 0), "Omeprazol": ("completo", 30)}),
    dict(caso="Medicamento suspendido", iess=True, condiciones=["Hipertensión"],
         visitas=[(33, [item("Losartán", 50), item("Amlodipino", 10)], "manual"),
                  (3, [item("Losartán", 100), item("Enalapril", 10)], "manual")],
         entrega="todo"),
    dict(caso="Dosis reducida", iess=True, condiciones=["Diabetes tipo 2"],
         visitas=[(30, [item("Metformina", 1000, 12)], "manual"),
                  (6, [item("Metformina", 500, 12)], "manual")],
         entrega={"Metformina": ("parcial", 40)}),
    dict(caso="Cambio de frecuencia (24 h -> 12 h)", iess=True,
         condiciones=["Diabetes tipo 2", "Hipertensión"],
         visitas=[(31, [item("Metformina", 850, 24), item("Losartán", 50)], "manual"),
                  (4, [item("Metformina", 850, 12), item("Losartán", 50)], "manual")],
         entrega="todo"),
    dict(caso="Compró en farmacia lo que faltaba", iess=True, condiciones=["Hipertensión"],
         visitas=[(10, [item("Losartán", 100), item("Amlodipino", 5)], "manual")],
         entrega={"Losartán": ("parcial", 15), "Amlodipino": ("completo", 30)},
         compras=[(7, "envio", {"Losartán": 15})]),
    dict(caso="Sin consentimiento (perfil incompleto)", iess=True, condiciones=[],
         consentimiento=False, cuidador=None,
         visitas=[(9, [item("Levotiroxina", 50)], "manual")],
         entrega="todo"),
    dict(caso="Caso cargado: 5 medicamentos, receta leída con IA", iess=True,
         condiciones=["Hipertensión", "Diabetes tipo 2", "Dislipidemia", "Gastritis crónica"],
         visitas=[(36, [item("Losartán", 50), item("Metformina", 850, 12)], "manual"),
                  (2, [item("Losartán", 100), item("Metformina", 1000, 12),
                       item("Atorvastatina", 20), item("Glibenclamida", 5),
                       item("Omeprazol", 20)], "ia")],
         entrega={"Losartán": ("completo", 30), "Metformina": ("parcial", 30),
                  "Atorvastatina": ("no", 0), "Glibenclamida": ("completo", 30),
                  "Omeprazol": ("no", 0)},
         aviso_cola=True),
]


def q(s):
    return "NULL" if s is None else "'" + str(s).replace("'", "''") + "'"


def dias_atras(n):
    return "CURRENT_DATE" if n == 0 else f"CURRENT_DATE - {n}"


def password_hash(password, salt):
    """Mismo formato que werkzeug.security.generate_password_hash(method="pbkdf2")."""
    iteraciones = 600_000
    h = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iteraciones).hex()
    return f"pbkdf2:sha256:{iteraciones}${salt}${h}"


def email_de(nombre):
    """'Luis Mora (ejemplo)' -> 'luis.mora@demo.ec'"""
    base = unicodedata.normalize("NFKD", nombre.replace(" (ejemplo)", "")).encode("ascii", "ignore").decode()
    return ".".join(base.lower().split()) + "@demo.ec"


def usuarios_sql(pacientes):
    sql = ["-- GENERADO por db/gen_pacientes_fake.py. No editar a mano: edita el script y regenera.",
           f"-- Un usuario por paciente. Contraseña de todos: {PASSWORD_DEMO}", ""]
    for pid, nombre in pacientes:
        salt = "".join(rng.choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789") for _ in range(16))
        sql += [f"-- @paciente {pid}",
                "INSERT INTO usuario (id, paciente_id, email, password_hash) VALUES "
                f"({pid}, {pid}, {q(email_de(nombre))}, {q(password_hash(PASSWORD_DEMO, salt))});", ""]
    return "\n".join(sql)


def extraccion_ia(items):
    """Simula la salida cruda de ai.extraer_receta(): nombres sin normalizar y algún null."""
    crudo = []
    for i, it in enumerate(items):
        crudo.append({"nombre": it["nombre"].upper() + (" TABLETAS" if i % 2 == 0 else ""),
                      "dosis_mg": it["dosis_mg"],
                      "cada_horas": it["cada_horas"],
                      "dias": None if i == 3 else it["dias"]})
    return {"origen": "ia", "modelo": "anthropic.claude-sonnet-5", "medicamentos": crudo}


def main():
    sql = ["-- GENERADO por db/gen_pacientes_fake.py. No editar a mano: edita el script y regenera.",
           "-- 10 pacientes fake (ids 2-11), uno por cada caso de la app.", ""]
    visita_id, item_id, compra_id = 100, 1000, 1
    nombres = rng.sample([f"{n} {a}" for n in NOMBRES for a in APELLIDOS], len(CASOS))

    for pid, (caso, nombre) in enumerate(zip(CASOS, nombres), start=2):
        nacimiento = date(rng.randint(1941, 1980), rng.randint(1, 12), rng.randint(1, 28))
        lat = round(LAT + rng.uniform(-0.03, 0.03), 4)
        lng = round(LNG + rng.uniform(-0.03, 0.03), 4)
        consentimiento = caso.get("consentimiento", True)
        cuidador = caso["cuidador"] if "cuidador" in caso else rng.choice(CUIDADORES)

        sql.append(f"-- @paciente {pid}")
        sql.append(f"-- ---------- Paciente {pid}: {caso['caso']} ----------")
        sql.append(
            "INSERT INTO paciente (id, nombre, fecha_nacimiento, cuidador, tiene_iess, "
            "consentimiento, consentimiento_en, lat, lng) VALUES "
            f"({pid}, {q(nombre + ' (ejemplo)')}, '{nacimiento}', {q(cuidador)}, "
            f"{str(caso['iess']).upper()}, {str(consentimiento).upper()}, "
            f"{'now()' if consentimiento else 'NULL'}, {lat}, {lng});")

        if caso["condiciones"]:
            valores = ", ".join(f"({pid}, {COND[c]})" for c in caso["condiciones"])
            sql.append(f"INSERT INTO paciente_condicion (paciente_id, condicion_id) VALUES {valores};")

        sql.append(
            "INSERT INTO cita (paciente_id, fecha_hora, motivo) VALUES "
            f"({pid}, CURRENT_DATE + {rng.randint(3, 25)} + TIME '{rng.choice(['08:30', '09:00', '10:00', '11:30', '15:00'])}', "
            "'Control médico');")

        actuales = {}
        for n, (atras, items, origen) in enumerate(caso["visitas"]):
            es_actual = n == len(caso["visitas"]) - 1
            extra = q(json.dumps(extraccion_ia(items), ensure_ascii=False)) + "::jsonb" if origen == "ia" else "NULL"
            sql.append(
                "INSERT INTO visita (id, paciente_id, fecha, origen, extraccion_ia) VALUES "
                f"({visita_id}, {pid}, {dias_atras(atras)}, '{origen}', {extra});")
            for it in items:
                horarios = "{" + ",".join(it["horarios"]) + "}"
                sql.append(
                    "INSERT INTO receta_item (id, visita_id, uid_medicina, dosis_mg, cada_horas, dias, horarios) "
                    f"VALUES ({item_id}, {visita_id}, '{uid_medicina(it['nombre'], it['dosis_mg'])}', {it['dosis_mg']}, "
                    f"{it['cada_horas']}, {it['dias']}, '{horarios}');")
                if es_actual:
                    actuales[it["nombre"]] = (item_id, it)
                item_id += 1
            if es_actual:
                visita_actual = visita_id
            visita_id += 1

        entrega = caso["entrega"]
        if caso["iess"] and entrega:
            filas = []
            for nombre_med, (rid, it) in actuales.items():
                estado, recibido = ("completo", total(it)) if entrega == "todo" else entrega[nombre_med]
                filas.append(f"({rid}, '{estado}', {recibido})")
            sql.append("INSERT INTO entrega_iess (receta_item_id, estado, unidades_recibidas) VALUES "
                       + ", ".join(filas) + ";")

        for farmacia_id, modo, unidades in caso.get("compras", []):
            sql.append("INSERT INTO compra (id, paciente_id, visita_id, uid_farmacia, modo) VALUES "
                       f"({compra_id}, {pid}, {visita_actual}, {farmacia_id}, '{modo}');")
            filas = ", ".join(f"({compra_id}, {actuales[m][0]}, {u})" for m, u in unidades.items())
            sql.append(f"INSERT INTO compra_item (compra_id, receta_item_id, unidades) VALUES {filas};")
            compra_id += 1

        # Tomas de hoy: dosis de la mañana tomadas (si hay medicina), la noche pendiente
        tomas = []
        for rid, it in actuales.values():
            for h in it["horarios"]:
                if h < "12:00" and rng.random() < 0.8:
                    tomas.append(f"({rid}, CURRENT_DATE, '{h}', CURRENT_DATE + TIME '{h}' + INTERVAL '{rng.randint(0, 40)} minutes')")
        if tomas:
            sql.append("INSERT INTO toma (receta_item_id, fecha, hora, tomada_en) VALUES " + ", ".join(tomas) + ";")

        # Aviso de la toma de la mañana ya mostrado (dedupe por clave)
        rid, it = next(iter(actuales.values()))
        h = it["horarios"][0]
        cuerpo = f"{h} · {it['nombre']} {it['dosis_mg']} mg"
        corto = f"Es hora de tu medicina de las {h}."
        clave = f"|{it['nombre']}@{h}|toma"
        sql.append(
            "INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url, clave, creado_en, mostrado_en) VALUES "
            f"({pid}, 'toma', 'Es hora de tu medicina', {q(cuerpo)}, {q(corto)}, '/plan', "
            f"to_char(CURRENT_DATE, 'YYYY-MM-DD') || {q(clave)}, "
            f"CURRENT_DATE + TIME '{h}', CURRENT_DATE + TIME '{h}');")
        if caso.get("aviso_cola"):
            sql.append(
                "INSERT INTO aviso (paciente_id, tipo, titulo, cuerpo, corto, url) VALUES "
                f"({pid}, 'compra', 'Falta comprar medicinas', 'Te falta: Atorvastatina, Omeprazol.', "
                "'Tienes medicinas pendientes por comprar.', '/farmacias');")
        sql.append("")

    OUT.write_text("\n".join(sql), encoding="utf-8")
    print(f"Generado {OUT}")

    pacientes = [(1, "Luis Mora (ejemplo)")] + [(pid, n + " (ejemplo)") for pid, n in enumerate(nombres, start=2)]
    OUT_USUARIOS.write_text(usuarios_sql(pacientes), encoding="utf-8")
    print(f"Generado {OUT_USUARIOS}")


if __name__ == "__main__":
    main()
