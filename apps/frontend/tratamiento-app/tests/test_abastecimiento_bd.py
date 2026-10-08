"""Módulo de abastecimiento contra PostgreSQL: vista v_saldo_medicacion, reloj de la demo,
cuidadores, productos relacionados y reset de los pacientes nuevos (12-15).

Requiere DATABASE_URL (db/docker-compose.yml) con la base recién inicializada.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import data  # noqa: E402

pytestmark = pytest.mark.skipif(not data.USAR_BD, reason="requiere DATABASE_URL")

if data.USAR_BD:
    import db
    from abastecimiento import repositorio as repo
    from abastecimiento.calculo import calcular_saldo


@pytest.fixture(autouse=True)
def conexion():
    yield
    repo.fijar_fecha_referencia(None)   # nunca dejar el reloj movido
    db.cerrar()


def por_nombre(paciente_id):
    return {r["nombre"]: r for r in repo.saldos(paciente_id)}


def test_vista_sql_igual_al_calculo_en_python():
    """La vista y abastecimiento/calculo.py aplican las mismas reglas, para todos los pacientes."""
    filas = repo.saldos()
    assert len(filas) > 30
    for r in filas:
        py = calcular_saldo(nombre=r["nombre"], dosis_mg=r["dosis_mg"], tomas_por_dia=r["tomas_por_dia"],
                            dias_receta=r["dias_receta"], inicio=r["inicio"],
                            unidades_obtenidas=r["unidades_obtenidas"], hoy=r["fecha_referencia"],
                            umbral_dias=r["umbral_dias"], sin_respuesta_iess=r["estado"] == "sin_respuesta_iess")
        assert (py.fecha_agotamiento, py.dias_restantes, py.saldo_unidades, py.estado) == (
            r["fecha_agotamiento"], r["dias_restantes"], r["saldo_unidades"], r["estado"]), r


def test_estados_de_los_pacientes_nuevos_con_la_fecha_real():
    jorge = por_nombre(12)   # Parkinson: 90 tabletas de levodopa, 3 al día, receta de hace 24 días
    assert (jorge["Levodopa + carbidopa"]["dias_restantes"], jorge["Levodopa + carbidopa"]["estado"]) == (6, "por_agotarse")
    assert jorge["Pramipexol"]["estado"] == "ok"                       # IESS 30 + compra 30
    rosa = por_nombre(13)    # Alzheimer: el IESS entregó 20 de 60 de memantina hace 10 días
    assert rosa["Memantina"]["estado"] == "agotado" and rosa["Donepezilo"]["estado"] == "ok"
    assert {r["estado"] for r in repo.saldos(14)} == {"ok"}            # cuadriplejia: todo entregado
    assert {r["estado"] for r in repo.saldos(15)} == {"sin_respuesta_iess"}  # paliativos: IESS sin responder


def test_reloj_de_la_demo_cambia_el_estado():
    hoy = repo.fecha_referencia()
    assert hoy == date.today()
    assert repo.avanzar_dias(20) == hoy + timedelta(days=20)
    assert repo.reloj_simulado()
    patricio = por_nombre(14)
    assert patricio["Gabapentina"]["dias_restantes"] == 5 and patricio["Gabapentina"]["estado"] == "por_agotarse"
    assert repo.fijar_fecha_referencia(None) == hoy and not repo.reloj_simulado()


def test_medicamento_controlado_marcado():
    mercedes = por_nombre(15)
    assert mercedes["Tramadol"]["controlado"] is True and mercedes["Paracetamol"]["controlado"] is False


def test_cuidadores():
    assert [p["id"] for p in repo.pacientes_de(1)] == [12, 13]          # Ana cuida a sus dos padres
    roles = {c["nombre"]: c["rol"] for c in repo.cuidadores_de(14)}
    assert roles == {"Diego Andrade (ejemplo)": "principal", "Sofía Paredes (ejemplo)": "apoyo"}


def test_sugerencias_por_condicion_y_por_grupo():
    patricio = {p["nombre"] for p in repo.sugerencias(14)}
    assert {"Cojín antiescaras", "Pañales para adulto"} <= patricio      # por cuadriplejia
    assert "Bolsa recolectora de orina" in patricio                      # por oxibutinina (grupo Urología)
    assert "Pastillero semanal con alarma" in {p["nombre"] for p in repo.sugerencias(12)}  # Parkinson
    assert repo.sugerencias(3) == [] or all(p["motivo"] for p in repo.sugerencias(3))


def test_reset_restaura_un_paciente_nuevo():
    db.usar_paciente(12)
    db.registrar_compra(1, "envio", {"Levodopa + carbidopa": 90})
    assert por_nombre(12)["Levodopa + carbidopa"]["estado"] == "ok"
    db.reset()
    assert por_nombre(12)["Levodopa + carbidopa"]["estado"] == "por_agotarse"
    assert [p["id"] for p in repo.pacientes_de(1)] == [12, 13]          # el vínculo con la cuidadora vuelve
    assert db.autenticar("jorge.quishpe@demo.ec", "demo1234") == 12
