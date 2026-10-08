# Mocks

## `entrypoint/`
Datos de **entrada** al sistema.

- `payloads/`: los cuerpos JSON que envía el usuario o cliente. Los usan la UI de Streamlit y los tests.
- `events/`: eventos completos de API Gateway (proxy) para invocar las lambdas en local:
  `python scripts/invoke_local.py <lambda> mocks/entrypoint/events/<evento>.json`

## `external_apis/`
Respuestas **simuladas** de las APIs a las que nos conectamos, con una carpeta por API.
`MockExternalDataProvider` las lee cuando `USE_MOCKS=true`.

Formato de cada fixture:

```json
{ "status_code": 200, "body": { "...": "..." } }
```

- El archivo se elige por `payload.reference`: se busca `<reference>.json` y, si no existe, se usa `default.json`.
- Un `status_code >= 400` simula un error de la API y el job termina en `FAILED`.

Para agregar una API nueva:
1. Crea `external_apis/<api_name>/`.
2. Define su puerto en `goble/application/ports/outbound.py`.
3. Crea su adapter real y su adapter mock en `goble/adapters/outbound/`.
4. Conéctalos en `goble/bootstrap/container.py`.
