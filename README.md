# Mi tratamiento · hackatón

App web (PWA) para que a nadie se le acabe la medicina a mitad del tratamiento: lee la receta con IA,
registra lo que entregó el IESS, avisa las tomas y encuentra la farmacia de Farmaenlace más cercana
con stock de lo que falta.

```
.
├── apps/frontend/tratamiento-app/   # La app: Flask + HTML/JS (PWA), login, IA con Claude
│   ├── app.py                       #   Rutas
│   ├── logic.py                     #   Reglas: faltantes, dosis, avisos, farmacias cercanas
│   ├── data.py / db.py              #   Datos: data/state.json (sin BD) o PostgreSQL
│   ├── ai.py                        #   Lectura de recetas con Claude (Bedrock o API de Anthropic)
│   ├── lambda_handler.py, dbinit.py #   Entradas de AWS Lambda
│   └── tests/                       #   Pruebas de punta a punta
│
├── db/                              # PostgreSQL 17 (ver db/README.md)
│   ├── init/                        #   Esquema, pacientes y usuarios de prueba
│   ├── datos_farmaenlace/           #   Catálogo real: farmacias, medicinas y stock
│   └── docker-compose.yml           #   Base local
│
├── infra/                           # AWS con CloudFormation (ver infra/README.md)
│   ├── template.yaml                #   VPC + RDS + Lambda Flask + API HTTP + Bedrock
│   ├── deploy.ps1 / deploy.sh       #   Empaquetan, suben a S3, despliegan y cargan la BD
│   └── GUIA_DESPLIEGUE.md           #   Paso a paso para desplegar y probar
│
└── scripts/package.py               # Arma el zip de la Lambda (dependencias para Linux)
```

## Empezar

| Quiero... | Ver |
|---|---|
| Correr la app en mi computador | [apps/frontend/tratamiento-app/README.md](apps/frontend/tratamiento-app/README.md) |
| Desplegar en AWS y probar | [infra/GUIA_DESPLIEGUE.md](infra/GUIA_DESPLIEGUE.md) |
| Entender la base de datos y los usuarios de prueba | [db/README.md](db/README.md) |

## Desarrollo

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt

pytest                                   # pruebas de la app en modo JSON
docker compose -f db/docker-compose.yml up -d
$Env:DATABASE_URL = "postgresql://goble:goble@localhost:5432/tratamiento"
pytest                                   # además: login, aislamiento entre usuarios y escrituras en la BD
cfn-lint infra/template.yaml             # valida la infraestructura
```

Las variables que usa la app en local están en [.env.example](.env.example).

## Hosting

Amplify Hosting **no ejecuta servidores Python**, así que la app Flask corre en **AWS Lambda detrás de
API Gateway HTTP** (que da el HTTPS que necesita la PWA), con RDS PostgreSQL y Claude en Bedrock.
