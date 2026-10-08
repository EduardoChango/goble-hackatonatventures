"""Fase 3: notificador (simulado y SES con un cliente falso), modo EventBridge y handlers de Lambda.

Requiere DATABASE_URL con la base recién inicializada. No llama a AWS: boto3 se reemplaza por stubs.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import data  # noqa: E402

pytestmark = pytest.mark.skipif(not data.USAR_BD, reason="requiere DATABASE_URL")

if data.USAR_BD:
    import boto3

    import db
    from abastecimiento import evaluador, eventos, notificador
    from abastecimiento import repositorio as repo
    from handlers import evaluador as h_evaluador
    from handlers import notificador as h_notificador


class ClienteFalso:
    """Reemplaza a boto3.client('sesv2' | 'events') y guarda las llamadas."""
    def __init__(self, falla=None):
        self.llamadas, self.falla = [], falla

    def send_email(self, **kw):
        if self.falla:
            raise self.falla
        self.llamadas.append(("send_email", kw))
        return {"MessageId": "msg-123"}

    def put_events(self, **kw):
        self.llamadas.append(("put_events", kw))
        return {"FailedEntryCount": 0, "Entries": [{"EventId": "e-1"}]}


@pytest.fixture(autouse=True)
def limpio(monkeypatch):
    for v in ("EVENT_BUS_NAME", "EMAIL_REMITENTE", "EMAIL_DESTINO_DEMO", "APP_URL"):
        monkeypatch.delenv(v, raising=False)
    db._c().execute("TRUNCATE alerta, evento_log")
    yield
    repo.fijar_fecha_referencia(None)
    db._c().execute("TRUNCATE alerta, evento_log")
    db.cerrar()


def internos(detail_type):
    return [f["detail"] for f in db._todos(
        "SELECT detail FROM evento_log WHERE detail_type = %s ORDER BY id", detail_type)]


def test_simulado_deja_el_email_en_el_log():
    evaluador.evaluar(paciente_id=12)
    (email,) = [n for n in internos("NotificacionEnviada") if n["evento"] == "MedicacionPorAgotarse"]
    assert email["modo"] == "simulado"
    assert email["para"] == ["ana.quishpe@demo.ec", "jorge.quishpe@demo.ec"]   # cuidadora + paciente
    assert email["asunto"].startswith("Jorge Quishpe (ejemplo): Levodopa + carbidopa se acaba en 6 días")
    assert "Farmacias de Farmaenlace con stock" in email["texto"]
    assert "Pastillero semanal con alarma" in email["texto"]
    assert "no reemplaza la indicación médica" in email["texto"]


def test_email_de_entrega_iess_y_medicamento_controlado():
    asunto, texto, _ = notificador.armar("EntregaIessIncompleta", {
        "paciente": "Rosa", "medicamentos": [{"nombre": "Memantina", "concentracion": "10 mg",
                                              "estado_iess": "parcial", "falta": 40, "total": 60}]})
    assert "el IESS no completó" in asunto and "entregó solo una parte (faltan 40 de 60)" in texto
    _, texto, _ = notificador.armar("MedicacionPorAgotarse", {
        "paciente": "Mercedes", "medicamentos": [{
            "nombre": "Tramadol", "concentracion": "50 mg", "estado": "por_agotarse", "dias_restantes": 3,
            "fecha_agotamiento": "2026-10-11", "cantidad_sugerida": 90, "solo_retiro": True}]})
    assert "retiro presencial con receta especial" in texto
    assert notificador.armar("DemandaPrevista", {}) is None      # a Farmaenlace no se le manda email


def test_destino_demo_redirige_todo(monkeypatch):
    monkeypatch.setenv("EMAIL_DESTINO_DEMO", "jurado@ejemplo.com")
    evaluador.evaluar(paciente_id=12)
    (email,) = [n for n in internos("NotificacionEnviada") if n["evento"] == "MedicacionPorAgotarse"]
    assert email["para"] == ["jurado@ejemplo.com"]
    assert "iba para: ana.quishpe@demo.ec, jorge.quishpe@demo.ec" in email["texto"]


def test_ses_envia_con_remitente(monkeypatch):
    ses = ClienteFalso()
    monkeypatch.setattr(boto3, "client", lambda servicio, **kw: ses)
    monkeypatch.setenv("EMAIL_REMITENTE", "avisos@ejemplo.com")
    monkeypatch.setenv("APP_URL", "https://app.ejemplo.com")
    r = notificador.notificar("MedicacionPorAgotarse", {
        "paciente_id": 12, "paciente": "Jorge", "cuidadores": [{"email": "ana.quishpe@demo.ec"}],
        "medicamentos": [{"nombre": "Levodopa", "concentracion": "250 mg", "estado": "agotado",
                          "dias_restantes": 0, "fecha_agotamiento": "2026-10-08", "cantidad_sugerida": 90}]})
    assert r["enviado"] and r["message_id"] == "msg-123"
    (_, kw), = ses.llamadas
    assert kw["FromEmailAddress"] == "avisos@ejemplo.com"
    assert kw["Destination"]["ToAddresses"] == ["ana.quishpe@demo.ec", "jorge.quishpe@demo.ec"]
    assert "Abrir la app: https://app.ejemplo.com" in kw["Content"]["Simple"]["Body"]["Text"]["Data"]


def test_ses_falla_sin_cortar_el_flujo(monkeypatch):
    monkeypatch.setattr(boto3, "client", lambda servicio, **kw: ClienteFalso(falla=RuntimeError("sandbox")))
    monkeypatch.setenv("EMAIL_REMITENTE", "avisos@ejemplo.com")
    r = notificador.notificar("EntregaIessIncompleta", {
        "paciente_id": 13, "paciente": "Rosa", "cuidadores": [],
        "medicamentos": [{"nombre": "Memantina", "concentracion": "10 mg", "estado_iess": "no",
                          "falta": 60, "total": 60}]})
    assert r["enviado"] is False and "sandbox" in r["error"]
    assert internos("NotificacionFallida") and not internos("NotificacionEnviada")


def test_modo_eventbridge_publica_en_el_bus_y_no_despacha_local(monkeypatch):
    events = ClienteFalso()
    monkeypatch.setattr(boto3, "client", lambda servicio, **kw: events)
    monkeypatch.setenv("EVENT_BUS_NAME", "goble-dev-abastecimiento")
    evento_id = eventos.publicar("EvaluacionSolicitada", {"solicitado_por": "prueba"})
    (_, kw), = events.llamadas
    (entrada,) = kw["Entries"]
    assert entrada["EventBusName"] == "goble-dev-abastecimiento" and entrada["Source"] == "goble.abastecimiento"
    assert entrada["DetailType"] == "EvaluacionSolicitada" and evento_id in entrada["Detail"]
    # en AWS el evaluador lo ejecuta la regla, no este proceso
    assert not internos("EvaluacionEjecutada")
    assert not db._todos("SELECT 1 FROM evento_log WHERE direccion = 'entregado'")


def test_handler_evaluador_mueve_el_reloj_para_la_demo():
    hoy = repo.fecha_referencia()
    r = h_evaluador.handler({"origen": "manual", "avanzar_dias": 20})
    assert (repo.fecha_referencia() - hoy).days == 20
    assert r["fecha_referencia"] == repo.fecha_referencia().isoformat()
    assert any(e["paciente_id"] == 14 for e in r["eventos"])          # Patricio aparece con +20 días
    r = h_evaluador.handler({"origen": "manual", "reloj": "hoy"})
    assert repo.fecha_referencia() == hoy and r["fecha_referencia"] == hoy.isoformat()


def test_handlers_lambda_con_eventos_de_eventbridge():
    r = h_evaluador.handler({"version": "0", "id": "eb-1", "detail-type": "PacienteActualizado",
                             "source": "goble.abastecimiento", "detail": {"paciente_id": 12, "evento_id": "ev-1"}})
    assert r["pacientes_evaluados"] == 1
    r = h_notificador.handler({"version": "0", "id": "eb-2", "detail-type": "MedicacionPorAgotarse",
                               "source": "goble.abastecimiento", "detail": {
                                   "evento_id": "ev-2", "paciente_id": 12, "paciente": "Jorge",
                                   "cuidadores": [{"email": "ana.quishpe@demo.ec"}],
                                   "medicamentos": [{"nombre": "Levodopa", "concentracion": "250 mg",
                                                     "estado": "por_agotarse", "dias_restantes": 6,
                                                     "fecha_agotamiento": "2026-10-14",
                                                     "cantidad_sugerida": 90}]}})
    assert r["modo"] == "simulado"
    entregas = {(f["evento_id"], f["destino"]) for f in db._todos(
        "SELECT evento_id, destino FROM evento_log WHERE direccion = 'entregado'")}
    assert ("ev-1", "evaluador") in entregas and ("ev-2", "notificador") in entregas
