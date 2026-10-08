"""Publicación de eventos del módulo de abastecimiento.

- AWS (EVENT_BUS_NAME definido): PutEvents al bus de EventBridge; las reglas del template
  llevan cada evento a sus destinos (fase 3).
- Local (sin bus): despacho en proceso siguiendo la MISMA tabla de RUTAS, para ver y probar
  todo el flujo sin AWS. Cada entrega queda en evento_log.

Todos los eventos usan source="goble.abastecimiento".
"""
import json
import logging
import os
import uuid

import db

SOURCE = "goble.abastecimiento"
log = logging.getLogger(__name__)

# detail-type -> destinos. Es el contrato de las reglas de EventBridge (fase 3):
#   evaluador            Lambda evaluador (reevalúa al paciente o a todos)
#   notificador          Lambda notificador (email por SES al cuidador y al paciente)
#   webhook-app-principal API Destination hacia la app principal
#   farmaenlace          API Destination hacia Farmaenlace (mock en el MVP)
RUTAS = {
    "PacienteActualizado":   ["evaluador"],
    "EvaluacionSolicitada":  ["evaluador"],
    "MedicacionPorAgotarse": ["notificador", "webhook-app-principal"],
    "EntregaIessIncompleta": ["notificador", "webhook-app-principal"],
    "DemandaPrevista":       ["farmaenlace"],
    "PedidoSolicitado":      ["farmaenlace"],
    "PedidoActualizado":     ["notificador", "webhook-app-principal"],
}


def bus():
    return os.getenv("EVENT_BUS_NAME", "")


def modo():
    return "eventbridge" if bus() else "local"


def registrar(evento_id, direccion, detail_type, detail, destino=None):
    db._c().execute(
        """INSERT INTO evento_log (evento_id, direccion, detail_type, destino, paciente_id, detail)
           VALUES (%s, %s, %s, %s, %s, %s::jsonb)""",
        (evento_id, direccion, detail_type, destino, detail.get("paciente_id"),
         json.dumps(detail, ensure_ascii=False, default=str)))


def publicar(detail_type, detail):
    """Publica un evento y devuelve su id."""
    if detail_type not in RUTAS:
        raise ValueError(f"Evento desconocido: {detail_type}")
    evento_id = str(uuid.uuid4())
    detail = {**detail, "evento_id": evento_id}
    registrar(evento_id, "publicado", detail_type, detail)
    if modo() == "eventbridge":
        import boto3  # incluido en el runtime de Lambda
        r = boto3.client("events").put_events(Entries=[{
            "Source": SOURCE, "DetailType": detail_type, "EventBusName": bus(),
            "Detail": json.dumps(detail, ensure_ascii=False, default=str)}])
        if r.get("FailedEntryCount"):
            raise RuntimeError(f"EventBridge rechazó {detail_type}: {r['Entries']}")
    else:
        _despachar_local(detail_type, detail)
    return evento_id


def _despachar_local(detail_type, detail):
    """Imita las reglas de EventBridge en proceso. Un destino que falla no corta a los demás."""
    for destino in RUTAS[detail_type]:
        try:
            _DESTINOS_LOCALES[destino](detail_type, detail)
            registrar(detail["evento_id"], "entregado", detail_type, detail, destino)
        except Exception:  # noqa: BLE001 - como una DLQ: se registra y se sigue
            log.exception("Destino %s falló con %s", destino, detail_type)


def _al_evaluador(detail_type, detail):
    from abastecimiento import evaluador  # import diferido: el evaluador también publica
    evaluador.evaluar(paciente_id=detail.get("paciente_id"), origen=detail_type)


def _al_notificador(detail_type, detail):
    from abastecimiento import notificador
    notificador.notificar(detail_type, detail)


def _a_farmaenlace(detail_type, detail):
    """En AWS es una API Destination hacia la API del mock; en local, la misma lógica en proceso."""
    from farmaenlace_mock import servicio
    if detail_type == "DemandaPrevista":
        servicio.recibir_demanda(detail)
    elif detail_type == "PedidoSolicitado":
        servicio.recibir_pedido(detail)


def _sin_efecto(detail_type, detail):
    """Destinos externos que llegan en fases siguientes: en local basta con registrar la entrega."""


_DESTINOS_LOCALES = {
    "evaluador": _al_evaluador,
    "notificador": _al_notificador,         # email por SES (o simulado si no hay remitente)
    "webhook-app-principal": _sin_efecto,   # fase 5: receptor de webhooks de demo
    "farmaenlace": _a_farmaenlace,          # mock de Farmaenlace
}


def ultimos(limite=50, paciente_id=None):
    """Últimas filas de evento_log (para la consola de demo)."""
    filtro, params = ("WHERE paciente_id = %s", (paciente_id, limite)) if paciente_id else ("", (limite,))
    return db._todos(f"""SELECT id, evento_id, direccion, detail_type, destino, paciente_id, detail, creado_en
                         FROM evento_log {filtro} ORDER BY id DESC LIMIT %s""", *params)
