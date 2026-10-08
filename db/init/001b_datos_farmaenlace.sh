#!/bin/bash
# Solo para docker compose (la Lambda ignora los .sh y carga db/datos_farmaenlace desde db.py).
# Corre justo después de 001_schema.sql y antes de 002: farmacias -> medicinas -> stock.
set -e
for f in farmacias medicinas stock; do
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "/datos_farmaenlace/$f.sql"
done
