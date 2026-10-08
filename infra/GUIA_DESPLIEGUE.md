# Guía: desplegar y probar "Mi tratamiento" en AWS (PowerShell)

Paso a paso para subir la app a una cuenta de **AWS Workshop Studio** desde Windows y probarla.
Todos los comandos se ejecutan en **PowerShell** (no hace falta abrirlo como administrador), desde la raíz del repo.

```
Navegador ──HTTPS──► API Gateway HTTP ──► Lambda Flask ─┬─► RDS PostgreSQL 17 (red privada)
                                                        └─► NAT ─► Claude en Bedrock (recetas)
Lambda db-init ──► crea el esquema y carga el catálogo de Farmaenlace y los 11 pacientes de prueba
```

> **Costo:** mientras el stack existe, el NAT Gateway cuesta unos USD 1,10 al día y RDS unos USD 0,40 al día, aunque nadie use la app.
> **Borra el stack al terminar** (Paso 8).

---

## Paso 0: Tener el código actualizado

```powershell
cd $HOME\OneDrive\Desktop\goble-hackatonatventures
git switch main
git pull origin main
git status            # debe decir "nothing to commit, working tree clean"
```

Si `git status` muestra archivos con `deleted:` que tú no borraste, fue OneDrive. Recupéralos con `git restore .`.
Para evitarlo, conviene clonar el repo **fuera de OneDrive**, por ejemplo en `C:\dev\`.

## Paso 1: Herramientas (una sola vez)

**AWS CLI:**

```powershell
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

Espera a que el instalador **termine**, **cierra todas las terminales** (incluida la de VSCode) y abre PowerShell de nuevo:

```powershell
aws --version         # aws-cli/2.x
```

Si dice que `aws` no se reconoce, agrégalo en esa sesión: `$Env:Path += ";C:\Program Files\Amazon\AWSCLIV2"`.

**Entorno de Python del proyecto** (el script lo usa para empaquetar):

```powershell
if (-not (Test-Path .venv\Scripts\python.exe)) { py -m venv .venv }
```

## Paso 2: Credenciales de Workshop Studio

1. En la página del evento, abre **Get AWS CLI credentials** y copia el bloque de la pestaña **Windows PowerShell** (líneas `$Env:AWS_... = "..."`).
2. Pégalo en PowerShell y define la región del evento:

```powershell
$Env:AWS_ACCESS_KEY_ID = "..."
$Env:AWS_SECRET_ACCESS_KEY = "..."
$Env:AWS_SESSION_TOKEN = "..."
$Env:AWS_REGION = "us-east-1"      # la región que indique el workshop

aws sts get-caller-identity        # debe mostrar el Account del workshop
```

- **Credenciales vencidas:** expiran. Si aparece `ExpiredToken`, vuelve a copiarlas y pegarlas.
- **Terminal nueva:** cada ventana nueva de PowerShell necesita las credenciales otra vez.

## Paso 3: Habilitar Claude en Bedrock (consola web)

AWS retiró la página *Model access*: los modelos se habilitan solos la primera vez que se usan. En los modelos
de Anthropic, la primera vez puede pedir un formulario de caso de uso, que la Lambda no puede llenar.
Por eso conviene activarlo a mano antes de desplegar, **en la misma región** de tus credenciales:

1. **Amazon Bedrock → Model catalog** → busca **Claude Sonnet 5** (Anthropic), el modelo que usa la app, y ábrelo.
2. **Open in playground** y envía un mensaje cualquiera (por ejemplo, "hola").
3. Si aparece el formulario de caso de uso, llénalo (por ejemplo: *"Hackathon demo: lectura de recetas médicas de ejemplo"*) y vuelve a probar.
4. Si Claude responde en el playground, el modelo ya está activo para toda la cuenta.

**Si aparece `AccessDeniedException ... private marketplace eligibility`:** la cuenta del workshop solo permite
los modelos que aprobaron los organizadores. Prueba en el playground otros Claude y despliega con el que responda:

| Modelo en el playground | Opción para `deploy.ps1` |
|---|---|
| Claude Sonnet 5 | `-ClaudeModel anthropic.claude-sonnet-5` |
| Claude Opus 4.8 | `-ClaudeModel anthropic.claude-opus-4-8` |
| Claude Fable 5.1 | `-ClaudeModel anthropic.claude-fable-5-1` |
| Claude Haiku 4.5 | `-ClaudeModel anthropic.claude-haiku-4-5` |

Si ninguno funciona, pregunta a los organizadores qué modelos están habilitados. La app funciona igual sin IA:
la lectura de recetas devuelve la receta de ejemplo.

## Paso 4: Desplegar

```powershell
powershell -ExecutionPolicy Bypass -File infra\deploy.ps1
```

`-ExecutionPolicy Bypass` permite ejecutar el script sin cambiar la configuración de seguridad de Windows.

| Etapa | Qué pasa |
|---|---|
| Empaquetar | Genera los zips en `build\artifacts\`. La primera vez descarga las dependencias para Linux (1-2 min) |
| Subir | Crea el bucket `goble-artifacts-<cuenta>-<región>` y sube los zips |
| CloudFormation | Crea el stack `goble-dev`: VPC, NAT, RDS, Lambdas y API. **Unos 15 minutos la primera vez** |
| Base de datos | Invoca la Lambda `goble-dev-db-init`, que carga el catálogo de Farmaenlace (farmacias, medicinas y stock) y los 11 pacientes |

Opciones útiles:

```powershell
powershell -ExecutionPolicy Bypass -File infra\deploy.ps1 -ClaudeModel anthropic.claude-opus-4-8    # otro modelo
powershell -ExecutionPolicy Bypass -File infra\deploy.ps1 -DbReset                                  # recarga la data fake
```

Para ver el progreso, abre **otra** ventana de PowerShell, pega las credenciales y ejecuta:

```powershell
aws cloudformation describe-stack-events --stack-name goble-dev --max-items 8 `
  --query "StackEvents[].[ResourceStatus,LogicalResourceId,ResourceStatusReason]" --output table
```

Al terminar deberías ver algo así:

```
{"estado": "inicializada", "archivos": [...], "pacientes": 11}
|  FrontendUrl  |  https://xxxx.execute-api.us-east-1.amazonaws.com  |
>> Abre FrontendUrl e ingresa con luis.mora@demo.ec / demo1234
```

## Paso 5: Probar

Guarda la URL de la app. En PowerShell se usa `curl.exe`, no `curl`, porque `curl` es un alias de otro comando:

```powershell
$URL = aws cloudformation describe-stacks --stack-name goble-dev `
  --query "Stacks[0].Outputs[?OutputKey=='FrontendUrl'].OutputValue" --output text
$URL
```

**1. Sin sesión, la app redirige al login.** Esperado: `302 .../login`.

```powershell
curl.exe -s -o NUL -w "%{http_code} %{redirect_url}`n" "$URL/"
```

**2. El login funciona.** Esperado: `302`.

```powershell
curl.exe -s -c "$Env:TEMP\ck.txt" -o NUL -w "%{http_code}`n" -d "email=luis.mora@demo.ec&password=demo1234" "$URL/login"
```

**3. La sesión lee su paciente desde RDS.** Esperado: `Hoy · Luis Mora (ejemplo)` y `2 de 4`.

```powershell
curl.exe -s -b "$Env:TEMP\ck.txt" "$URL/" | Select-String -Pattern "Hoy · [^<]*|\d de \d" -AllMatches |
  ForEach-Object { $_.Matches.Value } | Select-Object -First 2
```

**4. Cada usuario ve solo su paciente.** Esperado: `Hoy · Carmen Pazmiño (ejemplo)`.

```powershell
curl.exe -s -c "$Env:TEMP\ck2.txt" -o NUL -d "email=carmen.pazmino@demo.ec&password=demo1234" "$URL/login"
curl.exe -s -b "$Env:TEMP\ck2.txt" "$URL/" | Select-String -Pattern "Hoy · [^<]*" | ForEach-Object { $_.Matches.Value }
```

**5. Lectura de receta con Claude en Bedrock.** Necesitas una foto de receta en JPG o PNG de menos de 5 MB.

```powershell
curl.exe -s -b "$Env:TEMP\ck.txt" -F "foto=@$HOME\Desktop\receta.jpg;type=image/jpeg" "$URL/receta/leer" |
  Select-String -Pattern "Leída por IA|Lectura simulada de ejemplo" | ForEach-Object { $_.Matches.Value }
```

- **`Leída por IA`:** Bedrock funciona.
- **`Lectura simulada de ejemplo`:** algo falló; revisa los logs (Paso 6).

**6. En el navegador y el celular.** Abre la URL con `Start-Process $URL` o desde el celular.

- **Login:** con `luis.mora@demo.ec` / `demo1234`. La pantalla lista los demás usuarios de prueba; todos usan `demo1234`.
- **Instalarla:** como la URL es HTTPS, Chrome permite instalarla como app (menú → *Instalar aplicación*) y activar notificaciones.
- **Guion de la demo:** está en `apps\frontend\tratamiento-app\README.md`. El botón **Demo → Restablecer datos** devuelve al paciente de la sesión a su estado inicial.

## Paso 6: Ver logs

```powershell
aws logs tail /aws/lambda/goble-dev-tratamiento-app --since 15m --follow   # la app
aws logs tail /aws/lambda/goble-dev-db-init --since 1h                     # carga de la BD
```

Los errores de la IA aparecen como `[ai.py] No se pudo leer la receta con IA: ...`.

## Paso 7: Actualizar después de cambiar código

```powershell
powershell -ExecutionPolicy Bypass -File infra\deploy.ps1            # 1 a 3 minutos; solo se actualiza lo que cambió
powershell -ExecutionPolicy Bypass -File infra\deploy.ps1 -DbReset   # además borra la BD y recarga la data fake
```

`db-init` no toca una base que ya tiene datos, salvo con `-DbReset`.

## Paso 8: Borrar todo al terminar

```powershell
aws cloudformation delete-stack --stack-name goble-dev
aws cloudformation wait stack-delete-complete --stack-name goble-dev
$Account = aws sts get-caller-identity --query Account --output text
aws s3 rb "s3://goble-artifacts-$Account-$Env:AWS_REGION" --force
```

RDS se borra sin snapshot final y los secretos quedan programados para borrarse en 7 días.

---

## Si algo falla

| Síntoma | Causa probable y solución |
|---|---|
| `aws` no se reconoce | Cierra y abre la terminal, o usa el `$Env:Path += ...` del Paso 1 |
| `No hay credenciales válidas de AWS` (del script) | Faltan las credenciales en esta ventana, o expiraron. Repite el Paso 2 |
| `ExpiredToken` o `Unable to locate credentials` | Lo mismo: vuelve a pegar las credenciales del Paso 2 |
| `SignatureDoesNotMatch` | La clave secreta llegó alterada. En PowerShell, cópiala de la pestaña **Windows PowerShell**. En Git Bash, ver el anexo |
| "la ejecución de scripts está deshabilitada" | Ejecuta el script con `powershell -ExecutionPolicy Bypass -File ...`, como en el Paso 4 |
| Falla al empaquetar (`pip`) | Recrea el entorno: `Remove-Item -Recurse -Force .venv; py -m venv .venv` |
| El stack queda en `ROLLBACK_COMPLETE` | Busca el primer `CREATE_FAILED` con el comando del Paso 4. Borra el stack (Paso 8) antes de reintentar |
| `CREATE_FAILED` con `not authorized` o `explicit deny` | La cuenta del workshop prohíbe ese recurso (por ejemplo NAT, EIP o RDS). Anota el recurso y el mensaje para buscar una alternativa |
| `db-init` responde con error o timeout | `aws logs tail /aws/lambda/goble-dev-db-init`. La Lambda debe estar en la VPC y llegar a RDS por el puerto 5432 |
| La URL responde `Internal Server Error` | `aws logs tail /aws/lambda/goble-dev-tratamiento-app` |
| `AccessDeniedException ... private marketplace eligibility` en Bedrock | El workshop no aprobó ese modelo. Usa otro Claude con `-ClaudeModel` (Paso 3) |
| La receta siempre sale "simulada" | El modelo no está activo: pruébalo en el playground de Bedrock (Paso 3). También puede ser que la región no lo soporte o que la foto pese más de unos 5 MB |
| Archivos `deleted:` en `git status` que no borraste | OneDrive. `git restore .` los recupera |

---

## Anexo: Git Bash, Mac, Linux o CloudShell

`infra/deploy.sh` hace lo mismo que `deploy.ps1`:

```bash
export AWS_ACCESS_KEY_ID=... AWS_SECRET_ACCESS_KEY=... AWS_SESSION_TOKEN=... AWS_REGION=us-east-1
ENV_NAME=dev bash infra/deploy.sh          # DB_RESET=1 para recargar la data fake
```

**Si usas Git Bash en Windows**, ejecuta antes `export MSYS2_ENV_CONV_EXCL='AWS_'`.
Git Bash convierte a ruta de Windows las variables que empiezan con `/` al pasarlas a `aws.exe`. Si tu clave secreta empieza con `/`, AWS la recibe alterada y responde `SignatureDoesNotMatch`.

## Referencias

- Detalle de la infraestructura: [README.md](README.md) de esta carpeta
- Base de datos, pacientes y usuarios de prueba: [db/README.md](../db/README.md)
- App, login y modo local: [apps/frontend/tratamiento-app/README.md](../apps/frontend/tratamiento-app/README.md)
