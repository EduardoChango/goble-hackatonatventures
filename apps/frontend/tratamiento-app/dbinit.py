"""Crea el esquema y carga la data fake (db/init/*.sql) en la base de datos.

- En AWS es la Lambda `goble-<env>-db-init`; infra/deploy.sh la invoca después de desplegar.
  Evento: {} (solo si la base está vacía) o {"forzar": true} (borra todo y vuelve a cargar).
- En local:  python dbinit.py [--forzar]   (usa DATABASE_URL)
"""
import json
import sys

import db


def handler(event, _context):
    return db.inicializar(forzar=bool((event or {}).get("forzar")))


if __name__ == "__main__":
    print(json.dumps(db.inicializar(forzar="--forzar" in sys.argv), ensure_ascii=False, indent=2))
