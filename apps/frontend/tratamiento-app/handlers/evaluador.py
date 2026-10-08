"""Lambda goble-<env>-evaluador y comando local.

AWS: la invocan el Scheduler ({"origen": "programado"}) y las reglas de EventBridge para
PacienteActualizado / EvaluacionSolicitada (evento con "detail-type" y "detail").

Local (con DATABASE_URL):
    python -m handlers.evaluador                  # evalúa a todos con el reloj actual
    python -m handlers.evaluador --avanzar 10     # simula +10 días y evalúa
    python -m handlers.evaluador --hoy            # vuelve el reloj a la fecha real
    python -m handlers.evaluador --paciente 12    # solo un paciente
"""
import argparse
import json
import os
import sys
import time

if hasattr(time, "tzset"):  # fechas de Ecuador también en la Lambda (TZ=UTC)
    os.environ["TZ"] = os.getenv("APP_TZ", "<-05>5")
    time.tzset()

import db  # noqa: E402
from abastecimiento import evaluador  # noqa: E402
from abastecimiento import repositorio as repo  # noqa: E402


def handler(event, _context=None):
    event = event or {}
    detail = event.get("detail") or {}
    origen = event.get("detail-type") or event.get("origen") or "programado"
    try:
        return evaluador.evaluar(paciente_id=detail.get("paciente_id"), origen=origen)
    finally:
        db.cerrar()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--avanzar", type=int, help="simular N días más antes de evaluar")
    p.add_argument("--hoy", action="store_true", help="volver el reloj de la demo a la fecha real")
    p.add_argument("--paciente", type=int, help="evaluar solo a este paciente")
    a = p.parse_args(argv)
    try:
        if a.hoy:
            repo.fijar_fecha_referencia(None)
        if a.avanzar:
            repo.avanzar_dias(a.avanzar)
        resumen = evaluador.evaluar(paciente_id=a.paciente, origen="cli")
    finally:
        db.cerrar()
    print(json.dumps(resumen, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())
