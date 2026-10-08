"""Evaluador + eventos en modo local (sin AWS) contra PostgreSQL.

Requiere DATABASE_URL con la base recién inicializada. Cada prueba parte sin alertas ni eventos.
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
    from abastecimiento import eventos, evaluador
    from abastecimiento import repositorio as repo
    from handlers import evaluador as handler_evaluador


@pytest.fixture(autouse=True)
def limpio(monkeypatch):
    monkeypatch.delenv("EVENT_BUS_NAME", raising=False)   # despacho local
    db._c().execute("TRUNCATE alerta, evento_log")
    yield
    repo.fijar_fecha_referencia(None)
    db._c().execute("TRUNCATE alerta, evento_log")
    db.cerrar()


def publicados(detail_type, paciente_id=None):
    filas = db._todos("""SELECT detail FROM evento_log WHERE direccion = 'publicado' AND detail_type = %s
                         ORDER BY id""", detail_type)
    return [f["detail"] for f in filas if paciente_id is None or f["detail"].get("paciente_id") == paciente_id]


def test_eventos_de_la_evaluacion_con_la_fecha_real():
    r = evaluador.evaluar()
    assert r["pacientes_evaluados"] == 15 and r["alertas_nuevas"] > 0

    (jorge,) = publicados("MedicacionPorAgotarse", 12)
    assert [m["nombre"] for m in jorge["medicamentos"]] == ["Levodopa + carbidopa"]
    assert jorge["medicamentos"][0]["dias_restantes"] == 6
    assert jorge["cuidadores"] == [{"nombre": "Ana Quishpe (ejemplo)", "email": "ana.quishpe@demo.ec",
                                    "rol": "principal"}]
    assert jorge["farmacias_sugeridas"] and jorge["farmacias_sugeridas"][0]["completa"]
    assert "Pastillero semanal con alarma" in {p["nombre"] for p in jorge["productos_sugeridos"]}

    (rosa,) = publicados("MedicacionPorAgotarse", 13)
    assert rosa["medicamentos"][0]["nombre"] == "Memantina" and rosa["medicamentos"][0]["estado"] == "agotado"
    (rosa_iess,) = publicados("EntregaIessIncompleta", 13)
    assert rosa_iess["medicamentos"][0] == {"nombre": "Memantina", "concentracion": "10 mg",
                                            "estado_iess": "parcial", "recibido": 20, "comprado": 0,
                                            "total": 60, "falta": 40}

    (mercedes,) = publicados("EntregaIessIncompleta", 15)
    assert {m["estado_iess"] for m in mercedes["medicamentos"]} == {"sin_respuesta"}
    assert publicados("MedicacionPorAgotarse", 15) == []      # sin respuesta del IESS: no es "agotado"
    assert publicados("MedicacionPorAgotarse", 14) == []      # Patricio está ok


def test_iess_incompleto_pero_ya_comprado_no_se_avisa():
    """Paciente 9: el IESS entregó 15 de 30 de Losartán, pero el cuidador compró los 15 que faltaban."""
    evaluador.evaluar()
    assert publicados("EntregaIessIncompleta", 9) == []
    demandas = [i for d in publicados("DemandaPrevista") for i in d["items"]]
    assert all(i["cantidad"] > 0 for i in demandas)


def test_demanda_prevista_sin_datos_personales():
    evaluador.evaluar()
    demandas = publicados("DemandaPrevista")
    assert demandas
    for d in demandas:
        texto = json.dumps(d, ensure_ascii=False)
        assert "paciente" not in texto and "@" not in texto and "direccion_entrega" not in texto
        assert d["farmacia_id"] and d["items"] and all(i["cantidad"] > 0 for i in d["items"])
    levodopa = [i for d in demandas for i in d["items"] if i["nombre"] == "Levodopa + carbidopa"]
    assert levodopa and levodopa[0]["cantidad"] == 90                  # un mes: 3 al día x 30 días


def test_idempotente_mismo_dia():
    primera = evaluador.evaluar()
    segunda = evaluador.evaluar()
    assert primera["alertas_nuevas"] > 0
    assert segunda["alertas_nuevas"] == 0 and segunda["eventos"] == []


def test_reloj_de_la_demo_dispara_alertas_nuevas():
    evaluador.evaluar()
    assert publicados("MedicacionPorAgotarse", 14) == []
    repo.avanzar_dias(20)
    r = evaluador.evaluar()
    (patricio,) = publicados("MedicacionPorAgotarse", 14)
    assert {m["nombre"] for m in patricio["medicamentos"]} == {"Gabapentina", "Oxibutinina", "Omeprazol"}
    assert patricio["fecha_referencia"] == r["fecha_referencia"]
    # Diego (principal) y Sofía (apoyo) reciben el aviso
    assert {c["nombre"] for c in patricio["cuidadores"]} == {"Diego Andrade (ejemplo)", "Sofía Paredes (ejemplo)"}


def test_rutas_locales_entregan_a_los_destinos():
    evaluador.evaluar(paciente_id=12)
    entregas = db._todos("""SELECT detail_type, destino FROM evento_log WHERE direccion = 'entregado'
                            ORDER BY id""")
    destinos = {(e["detail_type"], e["destino"]) for e in entregas}
    assert ("MedicacionPorAgotarse", "notificador") in destinos
    assert ("MedicacionPorAgotarse", "webhook-app-principal") in destinos
    assert ("DemandaPrevista", "farmaenlace") in destinos
    assert db._uno("SELECT count(*) AS n FROM evento_log WHERE detail_type = 'EvaluacionEjecutada'")["n"] == 1


def test_compra_reevalua_al_paciente_al_instante():
    db.usar_paciente(12)
    try:
        data.registrar_compra(1, "envio", {"Levodopa + carbidopa": 90})   # vía data: publica PacienteActualizado
        (evento,) = publicados("PacienteActualizado", 12)
        assert evento["motivo"] == "registrar_compra"
        ejec = db._uno("""SELECT detail FROM evento_log WHERE detail_type = 'EvaluacionEjecutada'
                          ORDER BY id DESC LIMIT 1""")["detail"]
        assert ejec["origen"] == "PacienteActualizado" and ejec["paciente_id"] == 12
        assert repo.saldos(12)[0]["estado"] == "ok"                          # ya no le falta levodopa
    finally:
        db.reset()


def test_evaluar_ahora_por_evento():
    eventos.publicar("EvaluacionSolicitada", {"solicitado_por": "prueba"})
    ejec = db._uno("SELECT detail FROM evento_log WHERE detail_type = 'EvaluacionEjecutada'")["detail"]
    assert ejec["origen"] == "EvaluacionSolicitada" and ejec["pacientes_evaluados"] == 15


def test_handler_lambda_programado_y_por_evento():
    r = handler_evaluador.handler({"origen": "programado"})
    assert r["origen"] == "programado" and r["pacientes_evaluados"] == 15
    r = handler_evaluador.handler({"detail-type": "PacienteActualizado", "detail": {"paciente_id": 13}})
    assert r["origen"] == "PacienteActualizado" and r["pacientes_evaluados"] == 1


def test_evento_desconocido():
    with pytest.raises(ValueError):
        eventos.publicar("NoExiste", {})
