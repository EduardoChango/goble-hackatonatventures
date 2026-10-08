"""Saldo real de medicación (abastecimiento/calculo.py) con fechas fijas. No necesita base de datos."""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import data  # noqa: E402
from abastecimiento.calculo import calcular_saldo, estado_paciente, saldos_desde_estado  # noqa: E402

INICIO = date(2026, 10, 1)


def saldo(unidades, hoy, tomas=3, **kw):
    return calcular_saldo(nombre="Levodopa", dosis_mg=250, tomas_por_dia=tomas, dias_receta=30,
                          inicio=INICIO, unidades_obtenidas=unidades, hoy=hoy, **kw)


def test_por_agotarse_descuenta_lo_consumido():
    s = saldo(90, date(2026, 10, 25))          # 90 tabletas, 3 al día -> alcanzan 30 días
    assert s.fecha_agotamiento == date(2026, 10, 31)
    assert s.dias_restantes == 6
    assert s.saldo_unidades == 90 - 3 * 24     # 24 días consumidos
    assert s.estado == "por_agotarse"
    assert s.fin_tratamiento == date(2026, 10, 31)


def test_ok_con_margen():
    s = saldo(90, date(2026, 10, 6))
    assert (s.dias_restantes, s.estado) == (25, "ok")


def test_agotado_nunca_negativo():
    s = saldo(30, date(2026, 10, 20))          # alcanzaba 10 días
    assert s.fecha_agotamiento == date(2026, 10, 11)
    assert (s.dias_restantes, s.saldo_unidades, s.estado) == (0, 0, "agotado")


def test_sin_medicacion_es_agotado():
    assert saldo(0, date(2026, 10, 1)).estado == "agotado"


def test_sin_respuesta_iess_tiene_prioridad():
    assert saldo(90, date(2026, 10, 2), sin_respuesta_iess=True).estado == "sin_respuesta_iess"


def test_umbral_por_paciente():
    hoy = date(2026, 10, 21)                   # quedan 10 días
    assert saldo(90, hoy).estado == "ok"
    assert saldo(90, hoy, umbral_dias=10).estado == "por_agotarse"


def test_hoy_antes_del_inicio_no_consume():
    s = saldo(90, date(2026, 9, 28))
    assert s.saldo_unidades == 90 and s.dias_restantes == 33


def test_unidades_que_no_completan_un_dia():
    s = saldo(5, date(2026, 10, 1), tomas=3)   # 5 tabletas = 1 día completo
    assert s.fecha_agotamiento == date(2026, 10, 2) and s.dias_restantes == 1


def test_tomas_invalidas():
    with pytest.raises(ValueError):
        saldo(10, date(2026, 10, 1), tomas=0)


def test_semaforo_del_paciente():
    ok, poco, sin = saldo(90, date(2026, 10, 6)), saldo(90, date(2026, 10, 25)), saldo(0, date(2026, 10, 2))
    assert estado_paciente([ok, poco]) == "por_agotarse"
    assert estado_paciente([ok, poco, sin]) == "agotado"
    assert estado_paciente([]) == "ok"


def test_saldos_del_paciente_demo_en_modo_json():
    """Luis Mora (data.seed): receta del 2026-10-03, IESS completo/parcial/no."""
    s = data.seed()
    por_nombre = {x.nombre: x for x in saldos_desde_estado(s, hoy=date(2026, 10, 8))}
    assert por_nombre["Losartán"].fecha_agotamiento == date(2026, 11, 2)      # 30 tabletas, 1 al día
    assert por_nombre["Losartán"].estado == "ok"
    assert por_nombre["Metformina"].fecha_agotamiento == date(2026, 10, 17)   # 28 tabletas, 2 al día
    assert (por_nombre["Metformina"].dias_restantes, por_nombre["Metformina"].estado) == (9, "ok")
    assert por_nombre["Atorvastatina"].estado == "agotado"                    # el IESS no entregó
