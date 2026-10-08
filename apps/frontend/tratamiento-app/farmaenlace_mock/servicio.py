"""Lógica del mock de Farmaenlace (esquema `farmaenlace` en la misma base de la demo).

- recibir_demanda: guarda la demanda prevista (anónima) por sucursal.
- recibir_pedido: revisa el stock de la sucursal; si alcanza lo reserva y confirma, si no rechaza.
  Responde al módulo por callback (firmado con HMAC).
- avanzar: confirmado -> en_camino (delivery) | listo_para_retiro (retiro) -> entregado.
"""
import json
import os
import urllib.request
from datetime import datetime, timedelta, timezone

import db
from abastecimiento import eventos, firma

ETA = {"delivery": timedelta(hours=2), "retiro": timedelta(minutes=30)}
SIGUIENTE = {
    ("delivery", "confirmado"): "en_camino", ("delivery", "en_camino"): "entregado",
    ("retiro", "confirmado"): "listo_para_retiro", ("retiro", "listo_para_retiro"): "entregado",
}


class MockError(ValueError):
    pass


def recibir_demanda(detail):
    for i in detail.get("items", []):
        db._c().execute("""
            INSERT INTO farmaenlace.demanda (evento_id, farmacia_id, uid_medicina, nombre, cantidad, fecha_necesidad)
            VALUES (%s, %s, %s, %s, %s, %s)""",
            (detail.get("evento_id"), detail["farmacia_id"], i["uid_medicina"], i["nombre"], i["cantidad"],
             i.get("fecha_necesidad")))
    eventos.registrar(detail.get("evento_id", ""), "recibido", "DemandaPrevista", detail, "farmaenlace")
    return {"recibidos": len(detail.get("items", []))}


def recibir_pedido(detail):
    """Reserva el stock en la sucursal y confirma, o rechaza si no alcanza."""
    eventos.registrar(detail.get("evento_id", ""), "recibido", "PedidoSolicitado", detail, "farmaenlace")
    existente = db._uno("SELECT * FROM farmaenlace.pedido WHERE pedido_origen = %s", detail["pedido_id"])
    if existente:  # el bus puede reintentar: responder lo mismo
        return _respuesta(existente)
    ref = "FE-PED-%06d" % db._uno("SELECT nextval('farmaenlace.pedido_ref_seq') AS n")["n"]
    farmacia = detail["farmacia_id"]
    with db._c().transaction():
        faltan = []
        for i in detail["items"]:
            fila = db._uno("""SELECT cantidad FROM stock WHERE uid_farmacia = %s AND uid_medicina = %s
                              FOR UPDATE""", farmacia, i["uid_medicina"])
            if not fila or fila["cantidad"] < i["cantidad"]:
                faltan.append(f"{i['nombre']} (hay {fila['cantidad'] if fila else 0} de {i['cantidad']})")
        if faltan:
            estado, eta, motivo = "rechazado", None, "Sin stock suficiente en la sucursal: " + ", ".join(faltan)
        else:
            for i in detail["items"]:   # reserva
                db._c().execute("""UPDATE stock SET cantidad = cantidad - %s
                                   WHERE uid_farmacia = %s AND uid_medicina = %s""",
                                (i["cantidad"], farmacia, i["uid_medicina"]))
            estado, eta, motivo = "confirmado", datetime.now(timezone.utc) + ETA[detail["modo"]], None
        p = db._uno("""
            INSERT INTO farmaenlace.pedido (ref, pedido_origen, farmacia_id, modo, estado, items, cliente, eta, motivo)
            VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s) RETURNING *""",
            ref, detail["pedido_id"], farmacia, detail["modo"], estado,
            json.dumps(detail["items"], ensure_ascii=False), json.dumps(detail.get("cliente") or {}, ensure_ascii=False),
            eta, motivo)
    notificar_modulo(p)
    return _respuesta(p)


def avanzar(ref):
    p = db._uno("SELECT * FROM farmaenlace.pedido WHERE ref = %s", ref)
    if not p:
        raise LookupError(f"pedido {ref} no existe")
    siguiente = SIGUIENTE.get((p["modo"], p["estado"]))
    if not siguiente:
        raise MockError(f"el pedido {ref} está {p['estado']} y no puede avanzar")
    eta = datetime.now(timezone.utc) + timedelta(minutes=40) if siguiente == "en_camino" else p["eta"]
    p = db._uno("""UPDATE farmaenlace.pedido SET estado = %s, eta = %s, actualizado_en = now()
                   WHERE ref = %s RETURNING *""", siguiente, eta, ref)
    notificar_modulo(p)
    return _respuesta(p)


def listar_pedidos(limite=50):
    return [_respuesta(p) for p in db._todos(
        "SELECT * FROM farmaenlace.pedido ORDER BY creado_en DESC LIMIT %s", limite)]


def listar_demanda():
    """Demanda prevista agregada por sucursal y medicina: lo que Farmaenlace debería ubicar."""
    return db._todos("""
        SELECT d.farmacia_id, f.nombre AS farmacia, d.uid_medicina, d.nombre, sum(d.cantidad)::int AS cantidad,
               min(d.fecha_necesidad) AS desde, count(*)::int AS solicitudes
        FROM farmaenlace.demanda d JOIN farmacias f ON f.uid = d.farmacia_id
        GROUP BY 1, 2, 3, 4 ORDER BY min(d.fecha_necesidad), 2""")


def _respuesta(p):
    return {"ref": p["ref"], "pedido_id": p["pedido_origen"], "farmacia_id": p["farmacia_id"], "modo": p["modo"],
            "estado": p["estado"], "eta": p["eta"].isoformat() if p["eta"] else None, "motivo": p["motivo"],
            "items": p["items"]}


def notificar_modulo(p):
    """Callback al módulo. Con MODULO_WEBHOOK_URL hace el POST firmado (AWS); si no, en proceso (local)."""
    datos = {"pedido_id": p["pedido_origen"], "ref": p["ref"], "estado": p["estado"],
             "eta": p["eta"].isoformat() if p["eta"] else None, "motivo": p["motivo"]}
    url = os.getenv("MODULO_WEBHOOK_URL", "")
    if not url:
        from abastecimiento import pedidos
        return pedidos.aplicar_actualizacion(datos)
    cuerpo = json.dumps(datos).encode()
    req = urllib.request.Request(url, data=cuerpo, method="POST", headers={
        "Content-Type": "application/json", firma.HEADER: firma.firmar(cuerpo)})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read() or b"{}")
