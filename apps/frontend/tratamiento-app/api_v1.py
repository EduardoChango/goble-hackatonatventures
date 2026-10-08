"""API del módulo de abastecimiento (/api/v1). Fuera del login de la app: cada ruta trae su propia
autenticación. La fase 5 agrega las rutas para la app principal (x-api-key)."""
import json

from flask import Blueprint, jsonify, request

from abastecimiento import eventos, firma, pedidos

bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@bp.post("/webhooks/farmaenlace")
def webhook_farmaenlace():
    """Callback de Farmaenlace con el nuevo estado de un pedido. Firmado con HMAC-SHA256."""
    cuerpo = request.get_data()
    if not firma.verificar(cuerpo, request.headers.get(firma.HEADER)):
        return jsonify(error="firma inválida"), 401
    datos = json.loads(cuerpo)
    eventos.registrar(datos.get("ref") or "", "recibido", "CallbackFarmaenlace", datos, "modulo")
    try:
        p = pedidos.aplicar_actualizacion(datos)
    except LookupError as e:
        return jsonify(error=str(e)), 404
    except pedidos.PedidoInvalido as e:
        return jsonify(error=str(e)), 409
    return jsonify(pedido_id=p["id"], estado=p["estado"])
