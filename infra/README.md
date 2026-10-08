# Infra: CloudFormation

> **Paso a paso para desplegar y probar desde Windows:** [GUIA_DESPLIEGUE.md](GUIA_DESPLIEGUE.md)

| Archivo | Qué es |
|---|---|
| `template.yaml` | El stack de la app **Mi tratamiento**: VPC, RDS, Lambdas, API HTTP y permisos de Bedrock |
| `deploy.ps1` / `deploy.sh` | Empaqueta, sube los zips a S3, despliega el stack y carga la base de datos (PowerShell / bash) |
| `../scripts/package.py` | Genera los zips en `build/artifacts/`. Las dependencias de la app se descargan para Linux |

## App "Mi tratamiento"

```
Navegador ──HTTPS──► API Gateway HTTP ──► Lambda goble-<env>-tratamiento-app (Flask)
                                             │  subredes privadas
                                             ├──► RDS PostgreSQL 17 goble-<env>   (solo desde las Lambdas)
                                             └──► NAT ──► Claude en Bedrock (lectura de recetas)

Lambda goble-<env>-db-init ──► crea el esquema y carga los datos: catálogo de Farmaenlace
                               (db/datos_farmaenlace/) y pacientes de prueba (db/init/*.sql)
```

| Recurso | Detalle |
|---|---|
| VPC | 1 subred pública (NAT) + 2 privadas (RDS exige 2 zonas) |
| RDS | `db.t3.micro` (cambiable con `-DbInstanceClass`), 20 GB gp3 cifrado, sin acceso público |
| Secrets Manager | `goble-<env>/db` (usuario y contraseña de RDS) y `goble-<env>/flask-secret-key` (firma las cookies del login) |
| Lambda Flask | Misma app que en local, vía `apig-wsgi`. `AI_PROVIDER=bedrock` |
| API Gateway HTTP | Da la URL HTTPS que necesita la PWA (notificaciones y ubicación) |
| IAM | `bedrock-mantle:CreateInference` para Claude en Bedrock |

**Costo aproximado mientras el stack existe:** el NAT Gateway cuesta unos USD 1,10 al día y RDS unos USD 0,40 al día. Lambda, API Gateway y Bedrock se cobran por uso. **Borra el stack al terminar la demo.**

## Antes del primer deploy: acceso a Claude en Bedrock

Los modelos de Bedrock se habilitan solos al primer uso, pero los de Anthropic pueden pedir un formulario de caso de uso la primera vez. En la misma región del stack, abre **Bedrock → Model catalog → Claude Sonnet 5 → Open in playground** y envía un mensaje (detalle en [GUIA_DESPLIEGUE.md](GUIA_DESPLIEGUE.md), Paso 3). Sin ese acceso la app funciona igual, pero la lectura de recetas devuelve la receta de ejemplo. Para usar otro modelo: `CLAUDE_MODEL=anthropic.claude-opus-4-8 bash infra/deploy.sh`.

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
2. En S3, crea un bucket y sube el zip `frontend-<hash>.zip`.
3. En CloudFormation, ve a **Create stack → Upload a template file** y elige `infra/template.yaml`.
4. Completa los parámetros: `ArtifactsBucket`, y en `FrontendKey` el nombre exacto del zip (más la carpeta, si lo subiste dentro de una).
5. Marca *"I acknowledge that AWS CloudFormation might create IAM resources"* y crea el stack.
6. Cuando termine, en Lambda abre `goble-dev-db-init` y ejecuta un **Test** con el evento `{}` para cargar la base.

## Eliminar

```bash
aws cloudformation delete-stack --stack-name goble-dev
```

- **Se borra:** RDS se elimina sin snapshot final y los secretos quedan programados para borrarse en 7 días.
- **Se queda:** el bucket de artefactos no forma parte del stack; hay que vaciarlo y borrarlo a mano.

## Notas

- **Contraseña de la base:** las Lambdas reciben la contraseña de RDS como variable de entorno (resuelta desde Secrets Manager al desplegar), así que es visible en la consola de Lambda. Para producción, léela de Secrets Manager en tiempo de ejecución.
- **Tamaño de las fotos:** API Gateway con Lambda acepta peticiones de hasta 6 MB. Una foto de receta muy pesada falla y la app cae a la receta de ejemplo; conviene reducirla en el navegador antes de subirla.
