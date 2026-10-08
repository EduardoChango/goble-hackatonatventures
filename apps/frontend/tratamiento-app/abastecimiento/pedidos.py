"""Pedidos a Farmaenlace (delivery o retiro): crear, recibir la confirmación y el avance de estado.

Flujo: crear() -> PedidoSolicitado -> Farmaenlace confirma o rechaza -> callback firmado
-> aplicar_actualizacion() -> PedidoActualizado (email + webhook). Al entregarse se registra como
compra (sin volver a descontar stock: Farmaenlace ya lo reservó al confirmar) y se reevalúa al paciente.
"""
import db
from abastecimiento import eventos
from abastecimiento import repositorio as repo

ABIERTOS = ("solicitado", "confirmado", "en_camino", "listo_para_retiro")
TRANSICIONES = {
    "solicitado": {"confirmado", "rechazado", "cancelado"},
    "confirmado": {"en_camino", "listo_para_retiro", "entregado", "cancelado"},
    "en_camino": {"entregado", "cancelado"},
    "listo_para_retiro": {"entregado", "cancelado"},
}


class PedidoInvalido(ValueError):
    """El pedido no se puede crear o el cambio de estado no es válido."""


def obtener(pedido_id):
    p = db._uno("""
        SELECT p.*, f.nombre AS farmacia, f.direccion AS direccion_farmacia, pa.nombre AS paciente
        FROM pedido p JOIN farmacias f ON f.uid = p.uid_farmacia JOIN paciente pa ON pa.id = p.paciente_id
        WHERE p.id = %s""", pedido_id)
    if p:
        p["items"] = db._todos("""
            SELECT pi.uid_medicina, m.nombre, m.concentracion, pi.cantidad, pi.receta_item_id
            FROM pedido_item pi JOIN medicinas m ON m.uid = pi.uid_medicina
            WHERE pi.pedido_id = %s ORDER BY m.nombre""", pedido_id)
    return p


def de_paciente(paciente_id):
    return [obtener(r["id"]) for r in db._todos(
        "SELECT id FROM pedido WHERE paciente_id = %s ORDER BY id DESC", paciente_id)]


def uids_abiertos(paciente_id):
    return {r["uid_medicina"] for r in db._todos(
        "SELECT uid_medicina FROM v_pedido_abierto WHERE paciente_id = %s", paciente_id)}


def uids_rechazados(paciente_id, fecha):
    """Medicinas con un pedido rechazado en ese día de referencia (para no reintentar cada 2 minutos)."""
    return {r["uid_medicina"] for r in db._todos("""
        SELECT pi.uid_medicina FROM pedido p JOIN pedido_item pi ON pi.pedido_id = p.id
        WHERE p.paciente_id = %s AND p.estado = 'rechazado' AND p.fecha_referencia = %s""", paciente_id, fecha)}


def crear(paciente_id, uid_farmacia, modo, items, origen="manual"):
    """items: [{"uid_medicina", "cantidad", "receta_item_id"?}]. Publica PedidoSolicitado."""
    if modo not in ("delivery", "retiro"):
        raise PedidoInvalido(f"modo inválido: {modo}")
    if not items:
        raise PedidoInvalido("el pedido no tiene medicamentos")
    pac = db._uno("""SELECT id, nombre, consentimiento, direccion_entrega FROM paciente WHERE id = %s""", paciente_id)
    if not pac:
        raise PedidoInvalido(f"paciente {paciente_id} no existe")
    if not pac["consentimiento"]:
        raise PedidoInvalido("el paciente no autorizó compartir sus datos con la farmacia")
    meds = {r["uid"]: r for r in db._todos(
        "SELECT uid, nombre, concentracion, controlado FROM medicinas WHERE uid = ANY(%s::text[])",
        [i["uid_medicina"] for i in items])}
    if len(meds) != len({i["uid_medicina"] for i in items}):
        raise PedidoInvalido("hay medicinas que no están en el catálogo")
    controlados = [meds[i["uid_medicina"]]["nombre"] for i in items if meds[i["uid_medicina"]]["controlado"]]
    if modo == "delivery" and controlados:
        raise PedidoInvalido(f"{', '.join(controlados)} requiere retiro presencial con receta especial")
    if modo == "delivery" and not pac["direccion_entrega"]:
        raise PedidoInvalido("el paciente no tiene dirección de entrega")

    with db._c().transaction():
        pid = db._uno("""
            INSERT INTO pedido (paciente_id, uid_farmacia, modo, origen, direccion_entrega, fecha_referencia)
            VALUES (%s, %s, %s, %s, %s, fecha_referencia()) RETURNING id""",
            paciente_id, uid_farmacia, modo, origen,
            pac["direccion_entrega"] if modo == "delivery" else None)["id"]
        for i in items:
            db._c().execute("""INSERT INTO pedido_item (pedido_id, uid_medicina, receta_item_id, cantidad)
                               VALUES (%s, %s, %s, %s)""",
                            (pid, i["uid_medicina"], i.get("receta_item_id"), int(i["cantidad"])))
    principal = next(iter(repo.cuidadores_de(paciente_id)), None)
    eventos.publicar("PedidoSolicitado", {
        "pedido_id": pid, "paciente_id": paciente_id, "farmacia_id": uid_farmacia, "modo": modo, "origen": origen,
        "items": [{"uid_medicina": i["uid_medicina"], "nombre": meds[i["uid_medicina"]]["nombre"],
                   "concentracion": meds[i["uid_medicina"]]["concentracion"], "cantidad": int(i["cantidad"])}
                  for i in items],
        # datos para la entrega: solo porque el paciente dio su consentimiento
        "cliente": {"nombre": pac["nombre"], "direccion": pac["direccion_entrega"] if modo == "delivery" else None,
                    "contacto": principal["nombre"] if principal else None,
                    "telefono": principal["telefono"] if principal else None},
    })
    return obtener(pid)


def aplicar_actualizacion(datos):
    """Callback de Farmaenlace: {"pedido_id", "estado", "ref"?, "eta"?, "motivo"?}. Idempotente."""
    p = obtener(int(datos["pedido_id"]))
    if not p:
        raise LookupError(f"pedido {datos['pedido_id']} no existe")
    estado = datos["estado"]
    if estado == p["estado"]:
        return p
    if estado not in TRANSICIONES.get(p["estado"], set()):
        raise PedidoInvalido(f"el pedido está {p['estado']}: no puede pasar a {estado}")
    with db._c().transaction():
        db._c().execute("""
            UPDATE pedido SET estado = %s, ref_farmaenlace = COALESCE(%s, ref_farmaenlace),
                              eta = COALESCE(%s, eta), motivo = COALESCE(%s, motivo), actualizado_en = now()
            WHERE id = %s""", (estado, datos.get("ref"), datos.get("eta"), datos.get("motivo"), p["id"]))
        if estado == "entregado":
            _registrar_como_compra(p)
    p = obtener(p["id"])
    cuidadores = repo.cuidadores_de(p["paciente_id"])
    eventos.publicar("PedidoActualizado", {
        "pedido_id": p["id"], "paciente_id": p["paciente_id"], "paciente": p["paciente"],
        "cuidadores": [{"nombre": c["nombre"], "email": c["email"], "rol": c["rol"]} for c in cuidadores],
        "farmacia": p["farmacia"], "direccion_farmacia": p["direccion_farmacia"], "modo": p["modo"],
        "origen": p["origen"], "estado": p["estado"], "ref": p["ref_farmaenlace"],
        "eta": p["eta"].isoformat() if p["eta"] else None, "motivo": p["motivo"],
        "items": [{"nombre": i["nombre"], "concentracion": i["concentracion"], "cantidad": i["cantidad"]}
                  for i in p["items"]],
    })
    if estado == "entregado":  # la medicación del paciente cambió: reevaluar al instante
        eventos.publicar("PacienteActualizado", {"paciente_id": p["paciente_id"], "motivo": "pedido_entregado"})
    return p


def _registrar_como_compra(p):
    """La entrega cuenta como compra de la receta vigente (el stock ya lo descontó Farmaenlace)."""
    visita = db._uno("SELECT id FROM v_visita_actual WHERE paciente_id = %s", p["paciente_id"])
    if not visita:
        return
    cid = db._uno("""INSERT INTO compra (paciente_id, visita_id, uid_farmacia, modo)
                     VALUES (%s, %s, %s, %s) RETURNING id""",
                  p["paciente_id"], visita["id"], p["uid_farmacia"],
                  "envio" if p["modo"] == "delivery" else "recoger")["id"]
    for i in p["items"]:
        item = db._uno("SELECT id FROM receta_item WHERE visita_id = %s AND uid_medicina = %s",
                       visita["id"], i["uid_medicina"])
        if item:
            db._c().execute("""
                INSERT INTO compra_item (compra_id, receta_item_id, unidades) VALUES (%s, %s, %s)
                ON CONFLICT (compra_id, receta_item_id) DO UPDATE SET unidades = compra_item.unidades + EXCLUDED.unidades
            """, (cid, item["id"], i["cantidad"]))
