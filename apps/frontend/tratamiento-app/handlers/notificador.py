"""Lambda goble-<env>-notificador: la invocan las reglas de EventBridge para
MedicacionPorAgotarse, EntregaIessIncompleta y PedidoActualizado."""
import os
import time

if hasattr(time, "tzset"):
    os.environ["TZ"] = os.getenv("APP_TZ", "<-05>5")
    time.tzset()

import db  # noqa: E402
from abastecimiento import eventos, notificador  # noqa: E402


def handler(event, _context=None):
    detail_type, detail = event["detail-type"], event.get("detail") or {}
    try:
        eventos.registrar(detail.get("evento_id", event.get("id", "")), "entregado", detail_type, detail,
                          "notificador")
        return notificador.notificar(detail_type, detail)
    finally:
        db.cerrar()
