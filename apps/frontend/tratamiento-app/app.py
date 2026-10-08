"""App de continuidad de tratamiento (demo del hackatón).

Correr:  python app.py   y abrir http://localhost:5000
"""
import os
import time

# Las fechas ("hoy") y horas de las tomas son de Ecuador, también en la Lambda (que trae TZ=UTC).
# "<-05>5" = UTC-5 sin horario de verano; formato POSIX que no necesita la base de zonas horarias.
if hasattr(time, "tzset"):
    os.environ["TZ"] = os.getenv("APP_TZ", "<-05>5")
    time.tzset()

from flask import (Flask, g, jsonify, redirect, render_template, request,  # noqa: E402
                   send_from_directory, session)

import ai  # noqa: E402
import data  # noqa: E402
import logic  # noqa: E402

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "solo-para-desarrollo-local")
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  SESSION_COOKIE_SECURE=os.getenv("SESSION_COOKIE_SECURE") == "1")
app.jinja_env.globals.update(
    fecha_corta=logic.fecha_corta, fecha_larga=logic.fecha_larga, ETIQUETAS=logic.ETIQUETAS,
    hoy_iso=logic.hoy_iso,
)

if data.USAR_BD:  # API del módulo de abastecimiento (necesita PostgreSQL)
    from api_v1 import bp as api_v1  # noqa: E402
    app.register_blueprint(api_v1)

PUBLICAS = {"login", "static", "service_worker"}


# ---------- Login de la demo: cada usuario ve solo la data de su paciente ----------
@app.before_request
def exigir_login():
    if request.endpoint in PUBLICAS or request.path.startswith("/api/v1/"):  # /api/v1 tiene su propia auth
        return None
    pid = session.get("pid")
    if pid is None:
        if request.path.startswith("/api/"):
            return jsonify(error="no autenticado"), 401
        return redirect("/login")
    data.usar_paciente(pid)
    return None


@app.teardown_request
def cerrar_bd(_exc):
    data.cerrar()


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        pid = data.autenticar(request.form.get("email", ""), request.form.get("password", ""))
        if pid is not None:
            session.clear()
            session["pid"] = pid
            return redirect("/")
        error = "Correo o contraseña incorrectos."
    return render_template("login.html", error=error, usuarios=data.usuarios_demo(),
                           password_demo=data.DEMO_PASSWORD)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


def estado():
    # Se carga una vez por request (pagina() vuelve a pedirlo)
    if "estado" not in g:
        g.estado = data.load()
        g.estado["sim_hora"] = session.get("sim_hora")
    return g.estado


def pagina(plantilla, activa=None, **ctx):
    s = estado()
    return render_template(plantilla, s=s, perfil=s["perfil"], activa=activa,
                           msg=request.args.get("msg"), **ctx)


# ---------- Hoy ----------
@app.route("/")
def hoy():
    s = estado()
    v = logic.visita_actual(s)
    cita = s["perfil"].get("cita")
    return pagina("hoy.html", "hoy", dia=logic.resumen_dia(s), faltantes=logic.faltantes(s),
                  pendiente_iess=logic.falta_respuesta_iess(s), compras=logic.aviso_compras(s),
                  cita=cita, visita=v)


# ---------- Perfil ----------
@app.route("/perfil", methods=["GET", "POST"])
def perfil():
    s = estado()
    if request.method == "POST":
        f = request.form
        p = s["perfil"]
        p["nombre"] = f.get("nombre", p["nombre"]).strip() or p["nombre"]
        p["edad"] = int(f.get("edad") or p["edad"])
        p["cuidador"] = f.get("cuidador", "").strip()
        p["condiciones"] = [c.strip() for c in f.get("condiciones", "").split(",") if c.strip()]
        p["iess"] = f.get("iess") == "si"
        p["consentimiento"] = f.get("consentimiento") == "on"
        p["cita"] = f.get("cita") or p.get("cita")
        if f.get("lat") and f.get("lng"):
            p["lat"], p["lng"] = float(f["lat"]), float(f["lng"])
        data.guardar_perfil(p)
        return redirect("/?msg=Perfil guardado")
    return pagina("perfil.html")


# ---------- Receta ----------
@app.route("/receta")
def receta():
    s = estado()
    if request.args.get("nueva"):
        return pagina("receta.html", "receta", modo="nueva")
    fechas = sorted(v["fecha"] for v in s["visitas"])
    elegida = request.args.get("fecha") or (fechas[-1] if fechas else None)
    visita = next((v for v in s["visitas"] if v["fecha"] == elegida), None)
    filas = logic.comparar(visita, logic.visita_previa(s, visita["fecha"])) if visita else []
    return pagina("receta.html", "receta", modo="ver", fechas=fechas, elegida=elegida,
                  filas=filas, es_ultima=bool(fechas) and elegida == fechas[-1])


@app.route("/receta/leer", methods=["POST"])
def receta_leer():
    foto = request.files.get("foto")
    imagen = foto.read() if foto and foto.filename else None
    mime = foto.mimetype if foto and foto.filename else "image/jpeg"
    resultado = ai.extraer_receta(imagen, mime)
    session["borrador"] = resultado  # al confirmar se guarda lo que leyó la IA (visita.extraccion_ia)
    return pagina("receta.html", "receta", modo="borrador", borrador=resultado)


@app.route("/receta/confirmar", methods=["POST"])
def receta_confirmar():
    s = estado()
    f = request.form
    meds = []
    for i, nombre in enumerate(f.getlist("nombre")):
        if not nombre.strip():
            continue
        meds.append({"nombre": nombre.strip(), "dosis_mg": int(f.getlist("dosis_mg")[i] or 0),
                     "cada_horas": int(f.getlist("cada_horas")[i] or 24), "dias": int(f.getlist("dias")[i] or 30)})
    borrador = session.pop("borrador", None)
    if meds:
        hoy = logic.hoy_iso()
        s["visitas"] = [v for v in s["visitas"] if v["fecha"] != hoy] + [{"fecha": hoy, "meds": meds}]
        if borrador and borrador.get("origen") == "ia":
            data.guardar_receta(hoy, meds, "ia", borrador)
        else:
            data.guardar_receta(hoy, meds)
    return redirect("/receta?msg=Receta guardada")


# ---------- Entrega del IESS ----------
@app.route("/entrega", methods=["GET", "POST"])
def entrega():
    s = estado()
    v = logic.visita_actual(s)
    if request.method == "POST" and v:
        registro = {}
        for i, m in enumerate(v["meds"]):
            est = request.form.get(f"estado_{i}", "no")
            total = logic.total_recetado(m)
            if est == "completo":
                recibido = total
            elif est == "parcial":
                recibido = max(0, min(total, int(request.form.get(f"recibido_{i}") or 0)))
            else:
                recibido = 0
            registro[m["nombre"]] = {"estado": est, "recibido": recibido}
        s["entregas"][v["fecha"]] = registro
        data.registrar_entrega(v["fecha"], registro)
        return redirect("/farmacias" if logic.faltantes(s) else "/?msg=Todo entregado")
    meds = []
    for m in (v["meds"] if v else []):
        e = logic.entrega_de(s, v["fecha"], m["nombre"]) or {"estado": "completo", "recibido": logic.total_recetado(m)}
        meds.append({**m, "total": logic.total_recetado(m), "e": e})
    return pagina("entrega.html", None, visita=v, meds=meds)


# ---------- Plan ----------
@app.route("/plan")
def plan():
    s = estado()
    return pagina("plan.html", "plan", dia=logic.resumen_dia(s), compras=logic.aviso_compras(s),
                  faltantes=logic.faltantes(s), hora=logic.ahora(s))


@app.route("/plan/tomar", methods=["POST"])
def plan_tomar():
    s = estado()
    did = request.form["id"]
    hoy = logic.hoy_iso()
    tomas = s["tomas"].setdefault(hoy, [])
    if did not in tomas:
        tomas.append(did)
        data.registrar_toma(did)
    return redirect(request.form.get("volver") or "/plan")


# ---------- Farmacias ----------
@app.route("/farmacias")
def farmacias():
    s = estado()
    f = logic.faltantes(s)
    lat, lng = s["perfil"]["lat"], s["perfil"]["lng"]
    lista = logic.farmacias_cercanas(s, f, lat, lng) if f else []
    puntos = logic.mapa(lat, lng, lista) if lista else []
    v = logic.visita_actual(s)
    mios = {m["nombre"] for m in (v["meds"] if v else [])}
    promos = sorted(({**x, "tuyo": x["med"] in mios} for x in data.PROMOS), key=lambda x: not x["tuyo"])
    pedido = logic.pedido_mensual(s, lat, lng)
    return pagina("farmacias.html", "farmacias", faltantes=f, lista=lista, puntos=puntos, promos=promos,
                  pedido=pedido)


@app.route("/farmacias/comprar", methods=["POST"])
def farmacias_comprar():
    s = estado()
    v = logic.visita_actual(s)
    fid = int(request.form["farmacia"])
    modo = request.form.get("modo", "recoger")
    farm = next((x for x in data.FARMACIAS if x["id"] == fid), None)
    if v and farm:
        compras = s["compras"].setdefault(v["fecha"], {})
        vendido = s.setdefault("vendido", {}).setdefault(str(farm["id"]), {})
        comprado = {}
        for x in logic.faltantes(s):
            u = min(logic.stock_de(s, farm, x["nombre"]), x["falta"])
            if u > 0:
                compras[x["nombre"]] = compras.get(x["nombre"], 0) + u
                vendido[x["nombre"]] = vendido.get(x["nombre"], 0) + u
                comprado[x["nombre"]] = u
        data.registrar_compra(farm["id"], modo, comprado)
    accion = "enviarán a tu casa" if modo == "envio" else "reservamos para que recojas"
    return redirect(f"/?msg=Listo: te {accion} desde {farm['nombre'] if farm else 'la farmacia'}")


@app.route("/farmacias/repetir", methods=["POST"])
def farmacias_repetir():
    """Repetir el pedido del mes: compra de un mes de cada medicina en la mejor farmacia."""
    s = estado()
    lat, lng = s["perfil"]["lat"], s["perfil"]["lng"]
    pedido = logic.pedido_mensual(s, lat, lng)
    modo = request.form.get("modo", "envio")
    if pedido:
        v = logic.visita_actual(s)
        farm = pedido["farmacia"]
        compras = s["compras"].setdefault(v["fecha"], {})
        vendido = s.setdefault("vendido", {}).setdefault(str(farm["id"]), {})
        comprado = {}
        for i in pedido["items"]:
            u = min(logic.stock_de(s, farm, i["nombre"]), i["unidades"])
            if u > 0:
                compras[i["nombre"]] = compras.get(i["nombre"], 0) + u
                vendido[i["nombre"]] = vendido.get(i["nombre"], 0) + u
                comprado[i["nombre"]] = u
        data.registrar_compra(farm["id"], modo, comprado)
        accion = "enviarán a tu casa" if modo == "envio" else "reservamos para que recojas"
        return redirect(f"/?msg=Pedido del mes listo: te {accion} desde {farm['nombre']}")
    return redirect("/farmacias")


# ---------- Resumen para el médico ----------
@app.route("/resumen")
def resumen():
    s = estado()
    return pagina("resumen.html", "receta", r=logic.resumen_medico(s))


@app.route("/api/ubicacion", methods=["POST"])
def api_ubicacion():
    s = estado()
    j = request.get_json(force=True)
    s["perfil"]["lat"], s["perfil"]["lng"] = float(j["lat"]), float(j["lng"])
    data.guardar_ubicacion(s["perfil"]["lat"], s["perfil"]["lng"])
    return jsonify(ok=True)


# ---------- Avisos y panel de demo ----------
@app.route("/api/avisos")
def api_avisos():
    s = estado()
    antes = len(s["enviados"])
    avisos = logic.generar_avisos(s)
    if avisos:
        data.guardar_avisos(avisos, s["enviados"][antes:])
    return jsonify(avisos=avisos)


@app.route("/api/simular", methods=["POST"])
def api_simular():
    s = estado()
    j = request.get_json(force=True)
    if j.get("accion") == "hora":
        # la hora simulada vive en la sesión de cada usuario
        session["sim_hora"] = s["sim_hora"] = j.get("hora") or None
    elif j.get("accion") == "aviso":
        a = logic.aviso_manual(j.get("tipo"), s)
        if a:
            s["cola"].append(a)
            data.encolar_aviso(a)
    elif j.get("accion") == "reset":
        session.pop("sim_hora", None)
        data.reset()
        return jsonify(ok=True)
    return jsonify(ok=True, sim_hora=s.get("sim_hora"))


# ---------- PWA ----------
@app.route("/sw.js")
def service_worker():
    resp = send_from_directory(os.path.join(app.root_path, "static"), "sw.js",
                               mimetype="application/javascript")
    resp.headers["Service-Worker-Allowed"] = "/"
    resp.headers["Cache-Control"] = "no-cache"
    return resp


if __name__ == "__main__":
    # Solo en este computador (127.0.0.1). Para el celular se usa ngrok, ver README.
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", 5000)), debug=True)
