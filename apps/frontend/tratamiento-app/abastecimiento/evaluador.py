"""Evaluador del abastecimiento: revisa el saldo de cada paciente y emite los eventos.

Lo disparan el Scheduler (todos los pacientes), "Evaluar ahora" (EvaluacionSolicitada) y cada
cambio de un paciente (PacienteActualizado). Es idempotente: la tabla `alerta` impide avisar dos
veces lo mismo en el mismo día de referencia, así que puede correr cada pocos minutos.

Por paciente con alertas nuevas publica:
  MedicacionPorAgotarse  medicamentos por agotarse o agotados + farmacias + productos sugeridos
  EntregaIessIncompleta  el IESS entregó parcial, nada, o aún no responde
  DemandaPrevista        a la mejor farmacia sugerida, SIN datos del paciente
"""
import uuid
from collections import defaultdict

import db
from abastecimiento import eventos, farmacias
from abastecimiento import repositorio as repo

CRITICOS = ("por_agotarse", "agotado")


def _crear_alerta(paciente_id, receta_item_id, tipo, fecha, dias_restantes=None, detalle=None):
    """True si la alerta es nueva (no existía para ese día de referencia)."""
    return db._uno("""
        INSERT INTO alerta (paciente_id, receta_item_id, tipo, fecha_referencia, dias_restantes, detalle)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (paciente_id, receta_item_id, tipo, fecha_referencia) DO NOTHING
        RETURNING id""", paciente_id, receta_item_id, tipo, fecha, dias_restantes, detalle) is not None


def _entregas_pendientes(paciente_id):
    """Medicamentos de la receta vigente que el IESS no entregó completos (o no respondió) y que
    todavía faltan: si el cuidador ya compró la diferencia, no hay nada que avisar."""
    return db._todos("""
        SELECT ri.id AS receta_item_id, m.uid AS uid_medicina, m.nombre, m.concentracion, va.fecha AS inicio,
               i.total, i.tomas_por_dia, e.estado::text AS estado_iess,
               COALESCE(e.unidades_recibidas, 0) AS recibido, i.comprado,
               GREATEST(i.total - i.inventario, 0) AS falta
        FROM v_visita_actual va
        JOIN paciente p            ON p.id = va.paciente_id AND p.tiene_iess
        JOIN receta_item ri        ON ri.visita_id = va.id
        JOIN medicinas m           ON m.uid = ri.uid_medicina
        JOIN v_inventario i        ON i.receta_item_id = ri.id
        LEFT JOIN entrega_iess e   ON e.receta_item_id = ri.id
        WHERE va.paciente_id = %s
          AND (e.estado IS NULL OR (e.estado <> 'completo' AND i.total - i.inventario > 0))
        ORDER BY m.nombre""", paciente_id)


def _paciente(paciente_id):
    return db._uno("""SELECT id, nombre, lat::float AS lat, lng::float AS lng, direccion_entrega,
                             movilidad_reducida FROM paciente WHERE id = %s""", paciente_id)


def evaluar(paciente_id=None, origen="programado"):
    """Evalúa a un paciente o a todos. Devuelve un resumen de lo que hizo."""
    hoy = repo.fecha_referencia()
    por_paciente = defaultdict(list)
    for fila in repo.saldos(paciente_id):
        por_paciente[fila["paciente_id"]].append(fila)
    resumen = {"origen": origen, "fecha_referencia": hoy.isoformat(), "pacientes_evaluados": len(por_paciente),
               "alertas_nuevas": 0, "eventos": []}

    for pid, filas in por_paciente.items():
        criticos = [f for f in filas if f["estado"] in CRITICOS
                    and _crear_alerta(pid, f["receta_item_id"], f["estado"], hoy, f["dias_restantes"])]
        iess = []
        for e in _entregas_pendientes(pid):
            sin_respuesta = e["estado_iess"] is None
            tipo, fecha = ("iess_sin_respuesta", hoy) if sin_respuesta else ("entrega_iess_incompleta", e["inicio"])
            if _crear_alerta(pid, e["receta_item_id"], tipo, fecha, detalle=e["estado_iess"] or "sin respuesta"):
                iess.append(e)
        if not criticos and not iess:
            continue
        resumen["alertas_nuevas"] += len(criticos) + len(iess)
        resumen["eventos"] += _publicar_paciente(pid, hoy, criticos, iess)

    eventos.registrar(str(uuid.uuid4()), "interno", "EvaluacionEjecutada",
                      {**resumen, "paciente_id": paciente_id})
    return resumen


def _publicar_paciente(pid, hoy, criticos, iess):
    paciente, cuidadores = _paciente(pid), repo.cuidadores_de(pid)
    # Lo que conviene comprar: un tratamiento completo de lo crítico + lo que el IESS no entregó
    pedidos = {f["uid_medicina"]: {"uid_medicina": f["uid_medicina"], "nombre": f["nombre"],
                                   "concentracion": f["concentracion"],
                                   "cantidad": f["tomas_por_dia"] * f["dias_receta"],
                                   "fecha_necesidad": f["fecha_agotamiento"].isoformat()} for f in criticos}
    for e in iess:
        pedidos.setdefault(e["uid_medicina"], {"uid_medicina": e["uid_medicina"], "nombre": e["nombre"],
                                               "concentracion": e["concentracion"],
                                               "cantidad": e["falta"],
                                               "fecha_necesidad": hoy.isoformat()})
    sugeridas = farmacias.sugerir(paciente, cuidadores, list(pedidos.values()))
    base = {
        "paciente_id": pid, "paciente": paciente["nombre"], "direccion_entrega": paciente["direccion_entrega"],
        "cuidadores": [{"nombre": c["nombre"], "email": c["email"], "rol": c["rol"]} for c in cuidadores],
        "fecha_referencia": hoy.isoformat(),
        "farmacias_sugeridas": [{k: f[k] for k in ("id", "nombre", "direccion", "km", "mas_cerca_de", "completa")}
                                for f in sugeridas],
    }
    publicados = []
    if criticos:
        publicados.append(("MedicacionPorAgotarse", eventos.publicar("MedicacionPorAgotarse", {
            **base,
            "medicamentos": [{
                "nombre": f["nombre"], "concentracion": f["concentracion"], "estado": f["estado"],
                "dias_restantes": f["dias_restantes"], "fecha_agotamiento": f["fecha_agotamiento"].isoformat(),
                "cantidad_sugerida": f["tomas_por_dia"] * f["dias_receta"],
                # psicotrópicos / estupefacientes: retiro presencial con receta especial
                "solo_retiro": f["controlado"]} for f in criticos],
            "productos_sugeridos": [{"nombre": p["nombre"], "motivo": p["motivo"]} for p in repo.sugerencias(pid)],
        })))
    if iess:
        publicados.append(("EntregaIessIncompleta", eventos.publicar("EntregaIessIncompleta", {
            **base,
            "medicamentos": [{"nombre": e["nombre"], "concentracion": e["concentracion"],
                              "estado_iess": e["estado_iess"] or "sin_respuesta",
                              "recibido": e["recibido"], "comprado": e["comprado"], "total": e["total"],
                              "falta": e["falta"]} for e in iess],
        })))
    if sugeridas:
        # Demanda prevista para que Farmaenlace ubique stock: agregada y anónima (sin paciente ni dirección)
        mejor = sugeridas[0]
        publicados.append(("DemandaPrevista", eventos.publicar("DemandaPrevista", {
            "farmacia_id": mejor["id"], "farmacia": mejor["nombre"], "fecha_referencia": hoy.isoformat(),
            "items": list(pedidos.values()),
        })))
    return [{"tipo": t, "evento_id": i, "paciente_id": pid} for t, i in publicados]
