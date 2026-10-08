# Goble: hackathon workspace

Monorepo con **arquitectura hexagonal (ports & adapters)**. Toda la lógica de negocio vive en un
único hexágono, `packages/goble`. Las lambdas, el frontend y la IaC son piezas externas que se
conectan a él.

```
.
├── packages/goble/src/goble/        # HEXÁGONO (compartido por lambdas y frontend)
│   ├── domain/                      #   Entidades y reglas puras (sin AWS, sin frameworks)
│   ├── application/
│   │   ├── ports/inbound.py         #   Qué ofrece el sistema (casos de uso)
│   │   ├── ports/outbound.py        #   Qué necesita del exterior (repos, APIs externas)
│   │   └── use_cases/               #   Orquestación del dominio a través de los puertos
│   ├── adapters/
│   │   ├── inbound/                 #   Helpers para adapters de entrada (API Gateway)
│   │   └── outbound/                #   Implementaciones de los puertos de salida
│   │       ├── persistence/         #     DynamoDB | InMemory
│   │       └── external_api/        #     HTTP real | Mock (lee /mocks)
│   └── bootstrap/                   #   Settings + container (composition root)
│
├── apps/                            # ADAPTERS DE ENTRADA (driving)
│   ├── lambdas/
│   │   ├── process_job/handler.py   #   POST /jobs
│   │   └── get_job/handler.py       #   GET  /jobs/{job_id}
│   └── frontend/
│       ├── tratamiento-app/         #   App de la demo: Flask + PWA, login, PostgreSQL, IA (Bedrock)
│       ├── bff/                     #   Flask (backend-for-frontend) del scaffold inicial
│       └── ui/                      #   Streamlit (solo habla con el BFF)
│
├── infra/                           # IaC: CloudFormation
│   ├── template.yaml                #   VPC + RDS + Lambda Flask + API HTTP, y DynamoDB + Lambdas de jobs
│   └── deploy.sh                    #   empaqueta, sube a S3 y despliega
│
├── db/                              # PostgreSQL: esquema, vistas y data fake (ver db/README.md)
│   ├── docker-compose.yml
│   └── init/                        #   001_schema … 004_pacientes_fake (corren al crear el volumen)
│
├── mocks/                           # DATA MOCKEADA
│   ├── entrypoint/                  #   payloads de entrada + eventos de API Gateway
│   └── external_apis/<api>/         #   respuestas simuladas de las APIs externas
│
├── scripts/                         # package.py (zips para S3), invoke_local.py
└── tests/                           # pytest (usa adapters in-memory + mocks)
```

## Regla de dependencias

```
apps/* (entrada) ──► application (ports + use_cases) ──► domain
                                 ▲
adapters/outbound ───────────────┘   (implementan los ports de salida)
```

- `domain` no importa nada del proyecto.
- `application` solo importa `domain` y sus propios `ports`.
- Solo `bootstrap/container.py` decide qué adapter implementa cada puerto, según las variables de entorno.

## Setup local

```bash
python -m venv .venv
source .venv/Scripts/activate      # Windows (Git Bash). En PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env
```

## Comandos

| Qué | Comando |
|---|---|
| Tests | `pytest` |
| Invocar una lambda con un evento mock | `python scripts/invoke_local.py process_job mocks/entrypoint/events/process_job.json` |
| Flask BFF (puerto 5000) | `cd apps/frontend && flask --app bff.app run --port 5000` |
| Streamlit UI | `cd apps/frontend && streamlit run ui/app.py` |
| Empaquetar layer y lambdas | `python scripts/package.py` |
| Deploy a AWS | `ENV_NAME=dev USE_MOCKS=true bash infra/deploy.sh` (ver [infra/README.md](infra/README.md)) |

Con `BACKEND_MODE=local` (valor por defecto), el BFF ejecuta los casos de uso en proceso, así que
el frontend funciona completo sin AWS. Con `BACKEND_MODE=http` y `API_BASE_URL` apunta al API Gateway desplegado.

## Mocks vs real

| Variable | `true` / vacío | real |
|---|---|---|
| `USE_MOCKS` | `MockExternalDataProvider` (lee `mocks/external_apis`) | `HttpExternalDataProvider` |
| `JOBS_TABLE_NAME` | vacío: `InMemoryJobRepository` | `DynamoDBJobRepository` |

Ver [mocks/README.md](mocks/README.md) para agregar escenarios o nuevas APIs.

## Agregar una lambda nueva

1. Caso de uso en `application/use_cases/` y, si hace falta, un puerto nuevo en `ports/`.
2. Fábrica en `bootstrap/container.py`.
3. `apps/lambdas/<nombre>/handler.py`: solo traduce el evento al caso de uso y la respuesta a HTTP.
4. Evento de ejemplo en `mocks/entrypoint/events/`.
5. En `infra/template.yaml`: agregar su rol, función, log group, método, permiso y parámetro `<Nombre>Key`. Luego agrégala a `LAMBDAS` en `scripts/package.py` y a `infra/deploy.sh`.

## Hosting del frontend

Amplify Hosting **no ejecuta servidores Python**, así que la app Flask `apps/frontend/tratamiento-app`
corre en **AWS Lambda detrás de API Gateway HTTP** (que da el HTTPS), con RDS PostgreSQL y Claude en Bedrock.
Ver [infra/README.md](infra/README.md).

> `Job` es una entidad placeholder: renómbrala al concepto real del negocio.
