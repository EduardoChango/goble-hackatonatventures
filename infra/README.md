# Infra: CloudFormation

| Archivo | Qué es |
|---|---|
| `template.yaml` | Stack del backend: DynamoDB, Lambda Layer (core `goble` + mocks), 2 Lambdas, roles IAM y API Gateway REST |
| `deploy.sh` | Empaqueta, sube los zips a S3 y despliega el stack (`aws cloudformation deploy`) |
| `../scripts/package.py` | Genera los zips en `build/artifacts/` |

```
API Gateway  POST /jobs          ──► goble-<env>-process-job ──┐
             GET  /jobs/{job_id} ──► goble-<env>-get-job     ──┼──► DynamoDB goble-<env>-jobs
                                     (Layer: goble + mocks)    │
                                                               └──► API externa (o mocks si UseMocks=true)
```

## Opción A: desde la terminal (recomendada)

Requisitos: AWS CLI v2, Python 3.12+ y bash (en Windows, Git Bash).

1. En Workshop Studio, abre **Get AWS CLI credentials** y exporta `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` y `AWS_REGION`.
2. Ejecuta:
   ```bash
   ENV_NAME=dev USE_MOCKS=true bash infra/deploy.sh
   ```
3. El output `ApiUrl` es el `API_BASE_URL` del frontend.

Puedes volver a ejecutar el mismo comando para actualizar el stack. Solo se actualizan las lambdas cuyo código cambió.

## Opción B: subir el YAML desde la consola

1. Ejecuta `py scripts/package.py` para generar los zips en `build/artifacts/`.
2. En S3, crea un bucket y sube los 3 zips.
3. En CloudFormation, ve a **Create stack → Upload a template file** y elige `infra/template.yaml`.
4. Completa los parámetros: `ArtifactsBucket`, y en `LayerKey`, `ProcessJobKey` y `GetJobKey` el nombre exacto de cada zip (más la carpeta, si los subiste dentro de una).
5. Marca *"I acknowledge that AWS CloudFormation might create IAM resources"* y crea el stack.

## Eliminar

```bash
aws cloudformation delete-stack --stack-name goble-dev
```

El bucket de artefactos no forma parte del stack: hay que vaciarlo y borrarlo a mano.

## Notas

- **CORS:** el frontend llama a la API desde el Flask BFF (servidor a servidor), así que no hace falta CORS en API Gateway. Si alguna vez el navegador llama directo, agrega métodos `OPTIONS`.
- **Cambios en la API:** si agregas o modificas métodos, renombra `ApiDeployment` (por ejemplo, `ApiDeploymentV2`) para que API Gateway publique los cambios.
- **Frontend:** todavía no está en este stack. Amplify Hosting no ejecuta Flask ni Streamlit, así que falta decidir entre App Runner/ECS y Amplify con una UI estática.
