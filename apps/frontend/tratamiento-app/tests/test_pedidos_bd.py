"""Fase 4: pedidos a Farmaenlace (mock), callback firmado y suscripción de abastecimiento automático.

Requiere DATABASE_URL con la base recién inicializada. Todo en modo local (sin AWS).
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import data  # noqa: E402

pytestmark = pytest.mark.skipif(not data.USAR_BD, reason="requiere DATABASE_URL")

if data.USAR_BD:
    import db
    from abastecimiento import evaluador, firma, pedidos, suscripcion
    from abastecimiento import repositorio as repo
    from farmaenlace_mock import servicio
    from farmaenlace_mock.app import app as app_mock

LEVODOPA = "FE-00082"   # Jorge (12): 3 al día. Hay stock en la farmacia 5 (no en la 1)
TRAMADOL = "FE-00150"   # Mercedes (15): controlado


@pytest.fixture(autouse=True)
def limpio(monkeypatch):
    monkeypatch.delenv("EVENT_BUS_NAME", raising=False)
    monkeypatch.delenv("MODULO_WEBHOOK_URL", raising=False)
    yield
    repo.fijar_fecha_referencia(None)
    for pid in (12, 14):           # deshace pedidos, compras y stock reservado
        db.usar_paciente(pid)
        db.reset()
    db._c().execute("TRUNCATE alerta, evento_log, farmaenlace.demanda, farmaenlace.pedido")
    db.cerrar()


def stock(farmacia, uid):
    return db._uno("SELECT cantidad FROM stock WHERE uid_farmacia = %s AND uid_medicina = %s", farmacia, uid)["cantidad"]


def emails(evento="PedidoActualizado"):
    return [f["detail"] for f in db._todos("""SELECT detail FROM evento_log WHERE detail_type = 'NotificacionEnviada'
                                               AND detail->>'evento' = %s ORDER BY id""", evento)]


def test_pedido_manual_confirmado_avanza_y_se_registra_como_compra():
    antes = stock(5, LEVODOPA)
    p = pedidos.crear(12, 5, "delivery", [{"uid_medicina": LEVODOPA, "cantidad": 90}])
    assert p["estado"] == "confirmado" and p["ref_farmaenlace"].startswith("FE-PED-") and p["eta"]
    assert p["direccion_entrega"] == "Calle Manuel Burbano y 24 de Mayo, Puembo"
    assert stock(5, LEVODOPA) == antes - 90                     # Farmaenlace reservó
    assert "fue confirmado" in emails()[-1]["asunto"]

    assert servicio.avanzar(p["ref_farmaenlace"])["estado"] == "en_camino"
    assert servicio.avanzar(p["ref_farmaenlace"])["estado"] == "entregado"
    assert pedidos.obtener(p["id"])["estado"] == "entregado"
    levodopa = {r["nombre"]: r for r in repo.saldos(12)}["Levodopa + carbidopa"]
    assert levodopa["comprado"] == 90 and levodopa["estado"] == "ok"   # el saldo se recalculó
    assert stock(5, LEVODOPA) == antes - 90                     # la entrega no descuenta dos veces
    assert [e["asunto"].split(": ", 1)[1] for e in emails()] == [
        "tu pedido fue confirmado", "tu pedido está en camino", "tu pedido fue entregado"]
    with pytest.raises(servicio.MockError):
        servicio.avanzar(p["ref_farmaenlace"])                  # ya está entregado


def test_retiro_pasa_por_listo_para_retirar():
    p = pedidos.crear(12, 5, "retiro", [{"uid_medicina": LEVODOPA, "cantidad": 30}])
    assert p["direccion_entrega"] is None
    assert servicio.avanzar(p["ref_farmaenlace"])["estado"] == "listo_para_retiro"
    assert "Retíralo en" in emails()[-1]["texto"]


def test_rechazo_por_falta_de_stock_no_reserva():
    antes = stock(5, LEVODOPA)
    p = pedidos.crear(12, 5, "delivery", [{"uid_medicina": LEVODOPA, "cantidad": antes + 1}])
    assert p["estado"] == "rechazado" and "Sin stock suficiente" in p["motivo"]
    assert stock(5, LEVODOPA) == antes
    assert "no pudo prepararse" in emails()[-1]["asunto"]


def test_validaciones_al_crear():
    with pytest.raises(pedidos.PedidoInvalido, match="retiro presencial"):
        pedidos.crear(15, 1, "delivery", [{"uid_medicina": TRAMADOL, "cantidad": 10}])
    assert pedidos.crear(15, 9, "retiro", [{"uid_medicina": TRAMADOL, "cantidad": 10}])["modo"] == "retiro"
    with pytest.raises(pedidos.PedidoInvalido, match="no autorizó"):
        pedidos.crear(10, 1, "retiro", [{"uid_medicina": LEVODOPA, "cantidad": 1}])   # sin consentimiento
    with pytest.raises(pedidos.PedidoInvalido):
        pedidos.crear(12, 5, "avion", [{"uid_medicina": LEVODOPA, "cantidad": 1}])


def test_pedido_solicitado_lleva_datos_de_entrega_y_demanda_no():
    pedidos.crear(12, 5, "delivery", [{"uid_medicina": LEVODOPA, "cantidad": 30}])
    (sol,) = [f["detail"] for f in db._todos(
        "SELECT detail FROM evento_log WHERE direccion = 'publicado' AND detail_type = 'PedidoSolicitado'")]
    assert sol["cliente"]["nombre"] == "Jorge Quishpe (ejemplo)" and sol["cliente"]["contacto"] == "Ana Quishpe (ejemplo)"
    evaluador.evaluar()
    assert servicio.listar_demanda()                            # la demanda llegó al mock
    filas = db._todos("SELECT * FROM farmaenlace.demanda")
    assert filas and all("paciente" not in json.dumps(f, default=str) for f in filas)


def test_suscripcion_genera_pedidos_a_domicilio_repartidos():
    assert evaluador.evaluar()["pedidos_automaticos"] == []      # hoy Patricio está ok
    repo.avanzar_dias(20)
    r = evaluador.evaluar()
    auto = [p for p in r["pedidos_automaticos"] if p["paciente_id"] == 14]
    assert {p["farmacia"] for p in auto} == {"Medicity Puembo", "Farmacias Económicas Pifo Chaupimolino"}
    items = {i["nombre"]: i["cantidad"] for p in pedidos.de_paciente(14) for i in p["items"]}
    assert items == {"Gabapentina": 90, "Omeprazol": 30, "Oxibutinina": 56}   # ninguna tenía 60 de oxibutinina
    assert all(p["modo"] == "delivery" and p["origen"] == "suscripcion" and p["estado"] == "confirmado"
               for p in pedidos.de_paciente(14))
    parcial = db._uno("SELECT detail FROM evento_log WHERE detail_type = 'SuscripcionParcial'")["detail"]
    assert parcial["items"][0]["pedido"] == 56 and parcial["items"][0]["necesario"] == 60
    assert any("pedido automático" in e["asunto"] for e in emails())
    # el Scheduler vuelve a correr: no se duplica (hay pedidos abiertos)
    assert evaluador.evaluar()["pedidos_automaticos"] == []


def test_suscripcion_inactiva_o_sin_suscripcion_no_pide():
    suscripcion.desactivar(14)
    repo.avanzar_dias(20)
    assert evaluador.evaluar()["pedidos_automaticos"] == []
    assert suscripcion.obtener(12) is None                      # Jorge no tiene suscripción: solo alertas


def test_no_reintenta_el_mismo_dia_lo_rechazado():
    p = pedidos.crear(12, 5, "delivery", [{"uid_medicina": LEVODOPA, "cantidad": 99999}])
    assert p["estado"] == "rechazado"
    suscripcion.activar(12)
    assert suscripcion.procesar(12, repo.saldos(12)) == []      # levodopa se rechazó hoy
    repo.avanzar_dias(1)
    nuevos = suscripcion.procesar(12, repo.saldos(12))          # al día siguiente sí reintenta
    assert nuevos and nuevos[0]["items"][0]["uid_medicina"] == LEVODOPA


def test_webhook_del_modulo_exige_firma():
    import app as app_modulo
    c = app_modulo.app.test_client()
    p = pedidos.crear(12, 5, "retiro", [{"uid_medicina": LEVODOPA, "cantidad": 10}])
    cuerpo = json.dumps({"pedido_id": p["id"], "estado": "listo_para_retiro", "ref": p["ref_farmaenlace"]}).encode()
    url = "/api/v1/webhooks/farmaenlace"
    assert c.post(url, data=cuerpo).status_code == 401
    assert c.post(url, data=cuerpo, headers={firma.HEADER: "falsa"}).status_code == 401
    r = c.post(url, data=cuerpo, headers={firma.HEADER: firma.firmar(cuerpo)})
    assert r.status_code == 200 and r.get_json()["estado"] == "listo_para_retiro"
    malo = json.dumps({"pedido_id": p["id"], "estado": "en_camino"}).encode()   # retiro no va "en camino"
    assert c.post(url, data=malo, headers={firma.HEADER: firma.firmar(malo)}).status_code == 409
    nada = json.dumps({"pedido_id": 999999, "estado": "confirmado"}).encode()
    assert c.post(url, data=nada, headers={firma.HEADER: firma.firmar(nada)}).status_code == 404


def test_api_del_mock_exige_api_key():
    c = app_mock.test_client()
    assert c.get("/salud").status_code == 200
    assert c.get("/pedidos").status_code == 401
    key = {"x-api-key": "solo-para-desarrollo-local"}
    pedidos.crear(12, 5, "delivery", [{"uid_medicina": LEVODOPA, "cantidad": 30}])
    lista = c.get("/pedidos", headers=key).get_json()["pedidos"]
    assert lista and lista[0]["estado"] == "confirmado"
    r = c.post(f"/pedidos/{lista[0]['ref']}/avanzar", headers=key)
    assert r.status_code == 200 and r.get_json()["estado"] == "en_camino"
    assert c.post("/pedidos/NO-EXISTE/avanzar", headers=key).status_code == 404


def test_reset_restaura_la_suscripcion():
    suscripcion.desactivar(14)
    db.usar_paciente(14)
    db.reset()
    assert suscripcion.obtener(14)["activa"] is True and suscripcion.obtener(14)["uid_farmacia_preferida"] == 1
