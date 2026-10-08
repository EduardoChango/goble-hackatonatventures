"""Saldo real de medicación: cuánto le queda al paciente y cuándo se acaba.

Reglas (las mismas de la vista SQL v_saldo_medicacion en db/init/006_abastecimiento.sql):
    unidades_obtenidas = entregado por el IESS + comprado          (receta vigente)
    fecha_agotamiento  = inicio de la receta + unidades_obtenidas // tomas por día
    dias_restantes     = fecha_agotamiento - hoy                   (mínimo 0)
    saldo_unidades     = unidades_obtenidas - tomas por día * días transcurridos   (mínimo 0)
Supuestos de la demo: 1 tableta por toma y adherencia completa desde la fecha de la receta.
"""
from dataclasses import asdict, dataclass
from datetime import date, timedelta

import logic

UMBRAL_DIAS = 7  # avisar con una semana de anticipación (por defecto; cada paciente puede tener otro)

ESTADOS = ("ok", "por_agotarse", "agotado", "sin_respuesta_iess")


@dataclass(frozen=True)
class Saldo:
    nombre: str
    dosis_mg: int
    tomas_por_dia: int
    inicio: date
    fin_tratamiento: date
    unidades_obtenidas: int
    saldo_unidades: int
    fecha_agotamiento: date
    dias_restantes: int
    estado: str

    def a_dict(self):
        d = asdict(self)
        for k in ("inicio", "fin_tratamiento", "fecha_agotamiento"):
            d[k] = d[k].isoformat()
        return d


def calcular_saldo(*, nombre, dosis_mg, tomas_por_dia, dias_receta, inicio, unidades_obtenidas, hoy,
                   umbral_dias=UMBRAL_DIAS, sin_respuesta_iess=False):
    if tomas_por_dia <= 0:
        raise ValueError("tomas_por_dia debe ser mayor que 0")
    transcurridos = max((hoy - inicio).days, 0)
    fecha_agotamiento = inicio + timedelta(days=unidades_obtenidas // tomas_por_dia)
    dias_restantes = max((fecha_agotamiento - hoy).days, 0)
    if sin_respuesta_iess:
        estado = "sin_respuesta_iess"
    elif dias_restantes <= 0:
        estado = "agotado"
    elif dias_restantes <= umbral_dias:
        estado = "por_agotarse"
    else:
        estado = "ok"
    return Saldo(
        nombre=nombre, dosis_mg=dosis_mg, tomas_por_dia=tomas_por_dia, inicio=inicio,
        fin_tratamiento=inicio + timedelta(days=dias_receta),
        unidades_obtenidas=unidades_obtenidas,
        saldo_unidades=max(unidades_obtenidas - tomas_por_dia * transcurridos, 0),
        fecha_agotamiento=fecha_agotamiento, dias_restantes=dias_restantes, estado=estado,
    )


def saldos_desde_estado(s, hoy, umbral_dias=UMBRAL_DIAS):
    """Saldos de la receta vigente a partir del dict de estado de la app (modo JSON o BD)."""
    v = logic.visita_actual(s)
    if not v:
        return []
    sin_respuesta = logic.falta_respuesta_iess(s)
    return [calcular_saldo(nombre=m["nombre"], dosis_mg=m["dosis_mg"], tomas_por_dia=logic.tomas_por_dia(m),
                           dias_receta=int(m["dias"]), inicio=date.fromisoformat(v["fecha"]),
                           unidades_obtenidas=logic.inventario(s, m, v["fecha"]), hoy=hoy,
                           umbral_dias=umbral_dias, sin_respuesta_iess=sin_respuesta)
            for m in v["meds"]]


def estado_paciente(saldos):
    """Semáforo del paciente: el peor estado entre sus medicamentos."""
    if not saldos:
        return "ok"
    prioridad = {"agotado": 3, "sin_respuesta_iess": 2, "por_agotarse": 1, "ok": 0}
    return max((x.estado if isinstance(x, Saldo) else x["estado"] for x in saldos), key=prioridad.__getitem__)
