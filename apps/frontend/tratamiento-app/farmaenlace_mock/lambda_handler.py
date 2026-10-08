"""Lambda goble-<env>-farmaenlace-mock.

- Por API Gateway (API Destinations de EventBridge y la demo): la app Flask de app.py.
- Invocación directa para la demo desde la CLI:
    {"accion": "avanzar", "ref": "FE-PED-000001"}
    {"accion": "pedidos"}     {"accion": "demanda"}
"""
import os
import time

if hasattr(time, "tzset"):
    os.environ["TZ"] = os.getenv("APP_TZ", "<-05>5")
    time.tzset()

from apig_wsgi import make_lambda_handler  # noqa: E402

import db  # noqa: E402
from farmaenlace_mock import servicio  # noqa: E402
from farmaenlace_mock.app import app  # noqa: E402

_http = make_lambda_handler(app, binary_support=True)


def handler(event, context):
    accion = (event or {}).get("accion")
    if not accion:
        return _http(event, context)
    try:
        if accion == "avanzar":
            return servicio.avanzar(event["ref"])
        if accion == "pedidos":
            return {"pedidos": servicio.listar_pedidos()}
        if accion == "demanda":
            return {"demanda": [{**d, "desde": d["desde"].isoformat() if d["desde"] else None}
                                for d in servicio.listar_demanda()]}
        raise ValueError(f"acción desconocida: {accion}")
    finally:
        db.cerrar()
