# Infra: CloudFormation

> **Paso a paso para desplegar y probar desde Windows:** [GUIA_DESPLIEGUE.md](GUIA_DESPLIEGUE.md)

| Archivo | Qué es |
|---|---|
| `template.yaml` | Un solo stack: la app **Mi tratamiento** (VPC, RDS, Lambdas, API HTTP) y el backend `goble` (DynamoDB, Layer, Lambdas, API REST) |
| `deploy.ps1` / `deploy.sh` | Empaqueta, sube los zips a S3, despliega el stack y carga la base de datos (PowerShell / bash) |
| `../scripts/package.py` | Genera los zips en `build/artifacts/`. Las dependencias de la app se descargan para Linux |

## App "Mi tratamiento"

```
Navegador ──HTTPS──► API Gateway HTTP ──► Lambda goble-<env>-tratamiento-app (Flask)
                                             │  subredes privadas
                                             ├──► RDS PostgreSQL 17 goble-<env>   (solo desde las Lambdas)
                                             └──► NAT ──► Claude en Bedrock (lectura de recetas)

Lambda goble-<env>-db-init ──► crea el esquema y carga la data fake (db/init/*.sql)
```

| Recurso | Detalle |
|---|---|
| VPC | 1 subred pública (NAT) + 2 privadas (RDS exige 2 zonas) |
| RDS | `db.t4g.micro`, 20 GB gp3 cifrado, sin acceso público |
| Secrets Manager | `goble-<env>/db` (usuario y contraseña de RDS) y `goble-<env>/flask-secret-key` (firma las cookies del login) |
| Lambda Flask | Misma app que en local, vía `apig-wsgi`. `AI_PROVIDER=bedrock` |
| API Gateway HTTP | Da la URL HTTPS que necesita la PWA (notificaciones y ubicación) |
| IAM | `bedrock-mantle:CreateInference` para Claude en Bedrock |

**Costo aproximado mientras el stack existe:** el NAT Gateway cuesta unos USD 1,10 al día y RDS unos USD 0,40 al día. Lambda, API Gateway y Bedrock se cobran por uso. **Borra el stack al terminar la demo.**

## Antes del primer deploy: acceso a Claude en Bedrock

En la consola de AWS ve a **Bedrock → Model access** y habilita **Claude Opus 5.5**, en la misma región del stack. Sin ese acceso la app funciona igual, pero la lectura de recetas devuelve la receta de ejemplo. Para usar otro modelo: `CLAUDE_MODEL=anthropic.claude-sonnet-5-5 bash infra/deploy.sh`.

## Opción A: desde la terminal (recomendada)

Requisitos: AWS CLI v2, Python 3.12+ y bash (en Windows, Git Bash). También funciona en **AWS CloudShell**.

1. En Workshop Studio, abre **Get AWS CLI credentials** y exporta `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN` y `AWS_REGION`.
2. Ejecuta:
   ```bash
   ENV_NAME=dev bash infra/deploy.sh
   ```
   El primer despliegue tarda unos 15 minutos (RDS y NAT); los siguientes, 1 a 3 minutos. Al terminar, el script invoca `db-init` y muestra los outputs.
3. Abre `FrontendUrl` e ingresa con `luis.mora@demo.ec` / `demo1234`. La pantalla de login lista los demás usuarios de prueba.

Puedes volver a ejecutar el mismo comando para actualizar el stack. `db-init` no toca una base que ya tiene datos. Para borrarla y volver a cargar la data fake: `DB_RESET=1 bash infra/deploy.sh`.

## Opción B: subir el YAML desde la consola

1. Ejecuta `py scripts/package.py` para generar los zips en `build/artifacts/`.
2. En S3, crea un bucket y sube los 4 zips.
3. En CloudFormation, ve a **Create stack → Upload a template file** y elige `infra/template.yaml`.
4. Completa los parámetros: `ArtifactsBucket`, y en `LayerKey`, `ProcessJobKey`, `GetJobKey` y `FrontendKey` el nombre exacto de cada zip (más la carpeta, si los subiste dentro de una).
5. Marca *"I acknowledge that AWS CloudFormation might create IAM resources"* y crea el stack.
6. Cuando termine, en Lambda abre `goble-dev-db-init` y ejecuta un **Test** con el evento `{}` para cargar la base.

## Eliminar

```bash
aws cloudformation delete-stack --stack-name goble-dev
```

- **Se borra:** RDS se elimina sin snapshot final y los secretos quedan programados para borrarse en 7 días.
- **Se queda:** el bucket de artefactos no forma parte del stack; hay que vaciarlo y borrarlo a mano.

## Backend `goble` (jobs)

```
API Gateway  POST /jobs          ──► goble-<env>-process-job ──┐
             GET  /jobs/{job_id} ──► goble-<env>-get-job     ──┼──► DynamoDB goble-<env>-jobs
                                     (Layer: goble + mocks)    │
                                                               └──► API externa (o mocks si UseMocks=true)
```

## Notas

- **Contraseña de la base:** las Lambdas reciben la contraseña de RDS como variable de entorno (resuelta desde Secrets Manager al desplegar), así que es visible en la consola de Lambda. Para producción, léela de Secrets Manager en tiempo de ejecución.
- **Tamaño de las fotos:** API Gateway con Lambda acepta peticiones de hasta 6 MB. Una foto de receta muy pesada falla y la app cae a la receta de ejemplo; conviene reducirla en el navegador antes de subirla.
- **Cambios en la API REST de jobs:** si agregas o modificas métodos, renombra `ApiDeployment` (por ejemplo, `ApiDeploymentV2`) para que API Gateway publique los cambios.
