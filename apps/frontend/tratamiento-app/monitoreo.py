"""Centro de monitoreo (consola de la demo): semáforo de todos los pacientes, reloj, pedidos y eventos."""
from collections import defaultdict

from flask import Blueprint, redirect, render_template, request

import db
from abastecimiento import eventos
from abastecimiento import repositorio as repo
from abastecimiento.calculo import estado_paciente

bp = Blueprint("monitoreo", __name__, url_prefix="/monitoreo")


@bp.get("")
def ver():
    por_paciente = defaultdict(list)
    for f in repo.saldos():
        por_paciente[f["paciente_id"]].append(f)
    nombres = {r["id"]: r["nombre"] for r in db._todos("SELECT id, nombre FROM paciente")}
    pacientes = sorted(({"id": pid, "nombre": nombres.get(pid, pid), "estado": estado_paciente(filas),
                         "meds": filas} for pid, filas in por_paciente.items()),
                       key=lambda p: ({"agotado": 0, "sin_respuesta_iess": 1, "por_agotarse": 2}.get(p["estado"], 3),
                                      p["nombre"]))
    pedidos = db._todos("""
        SELECT p.id, p.estado, p.modo, p.origen, p.ref_farmaenlace, pa.nombre AS paciente, f.nombre AS farmacia,
               (SELECT string_agg(m.nombre || ' x' || pi.cantidad, ', ') FROM pedido_item pi
                JOIN medicinas m ON m.uid = pi.uid_medicina WHERE pi.pedido_id = p.id) AS items
        FROM pedido p JOIN paciente pa ON pa.id = p.paciente_id JOIN farmacias f ON f.uid = p.uid_farmacia
        ORDER BY p.id DESC LIMIT 15""")
    return render_template("monitoreo.html", pacientes=pacientes, pedidos=pedidos,
                           eventos=eventos.ultimos(40), hoy=repo.fecha_referencia(),
                           simulado=repo.reloj_simulado(), modo=eventos.modo(), msg=request.args.get("msg"))


@bp.post("/evaluar")
def evaluar():
    eventos.publicar("EvaluacionSolicitada", {"solicitado_por": "centro de monitoreo"})
    return redirect("/monitoreo?msg=Evaluación solicitada")


@bp.post("/simular")
def simular():
    dias = int(request.form.get("dias") or 7)
    repo.avanzar_dias(dias)
    eventos.publicar("EvaluacionSolicitada", {"solicitado_por": f"simular +{dias} días"})
    return redirect(f"/monitoreo?msg=Reloj adelantado {dias} días")


@bp.post("/hoy")
def hoy():
    repo.fijar_fecha_referencia(None)
    return redirect("/monitoreo?msg=Reloj en la fecha real")


@bp.post("/avanzar/<ref>")
def avanzar(ref):
    from farmaenlace_mock import servicio  # la demo hace de Farmaenlace
    r = servicio.avanzar(ref)
    return redirect(f"/monitoreo?msg=Pedido {ref}: {r['estado']}")
