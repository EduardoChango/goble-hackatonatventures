"""API HTTP del mock de Farmaenlace (Lambda + API Gateway propios, como un sistema externo).

Todas las rutas exigen el header x-api-key (las API Destinations de EventBridge lo envían).
    POST /demanda               demanda prevista (cuerpo = detail de DemandaPrevista)
    POST /pedidos               pedido nuevo (cuerpo = detail de PedidoSolicitado)
    POST /pedidos/<ref>/avanzar  demo: confirmado -> en camino / listo -> entregado
    GET  /pedidos, GET /demanda  lo que ve Farmaenlace
"""
import hmac
import os

from flask import Flask, jsonify, request

import db
from farmaenlace_mock import servicio

app = Flask(__name__)


def _api_key():
    return os.getenv("FARMAENLACE_API_KEY", "solo-para-desarrollo-local")


@app.before_request
def autenticar():
    if request.path == "/salud":
        return None
    if not hmac.compare_digest(request.headers.get("x-api-key", ""), _api_key()):
        return jsonify(error="x-api-key inválida"), 401
    return None


@app.teardown_request
def cerrar(_exc):
    db.cerrar()


@app.errorhandler(LookupError)
def no_existe(e):
    return jsonify(error=str(e)), 404


@app.errorhandler(servicio.MockError)
def invalido(e):
    return jsonify(error=str(e)), 409


@app.get("/salud")
def salud():
    return {"ok": True, "sistema": "farmaenlace-mock"}


@app.post("/demanda")
def demanda():
    return jsonify(servicio.recibir_demanda(request.get_json(force=True))), 202


@app.post("/pedidos")
def crear_pedido():
    return jsonify(servicio.recibir_pedido(request.get_json(force=True))), 201


@app.post("/pedidos/<ref>/avanzar")
def avanzar(ref):
    return jsonify(servicio.avanzar(ref))


@app.get("/pedidos")
def pedidos():
    return jsonify(pedidos=servicio.listar_pedidos())


@app.get("/demanda")
def ver_demanda():
    return jsonify(demanda=servicio.listar_demanda())
