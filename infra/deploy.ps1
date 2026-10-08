<#
.SYNOPSIS
  Versión PowerShell de infra/deploy.sh: empaqueta, sube los zips a S3, despliega
  infra/template.yaml con CloudFormation y carga la base de datos (Lambda db-init).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File infra\deploy.ps1
  powershell -ExecutionPolicy Bypass -File infra\deploy.ps1 -DbReset
  powershell -ExecutionPolicy Bypass -File infra\deploy.ps1 -ClaudeModel anthropic.claude-opus-4-8
  powershell -ExecutionPolicy Bypass -File infra\deploy.ps1 -DbInstanceClass db.t3.small
  powershell -ExecutionPolicy Bypass -File infra\deploy.ps1 -EmailRemitente yo@correo.com -EmailDestinoDemo yo@correo.com
  powershell -ExecutionPolicy Bypass -File infra\deploy.ps1 -FrecuenciaEvaluacion "cron(0 7 * * ? *)"

.NOTES
  Requiere AWS CLI v2 y credenciales en el entorno ($Env:AWS_ACCESS_KEY_ID, etc.).
  El primer despliegue tarda ~15 min (RDS + NAT). Los siguientes, 1-3 min.
#>
param(
    [string]$EnvName = "dev",
    [string]$Region = $Env:AWS_REGION,
    [string]$ArtifactsBucket = "",
    [string]$ClaudeModel = "anthropic.claude-sonnet-5",
    [string]$FrecuenciaEvaluacion = "rate(2 minutes)",  # producción: "cron(0 7 * * ? *)"
    [switch]$SinScheduler,      # si la cuenta no permite EventBridge Scheduler
    [string]$EmailRemitente = "",    # vacío = emails simulados (quedan en evento_log)
    [string]$EmailDestinoDemo = "",  # todos los emails a esta casilla (SES en sandbox)
    [string]$DbInstanceClass = "db.t3.micro",  # si no hay capacidad en la región: db.t4g.micro, db.t3.small
    [switch]$DbReset  # borra la BD y vuelve a cargar la data fake
)

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

# Ejecuta un comando nativo y corta el script si falla
function Invoke-Native {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Falló: $Exe $($Arguments -join ' ') (código $LASTEXITCODE)" }
}

if (-not $Region) { $Region = (aws configure get region) }
if (-not $Region) { $Region = "us-east-1" }
$Account = (aws sts get-caller-identity --query Account --output text)
if ($LASTEXITCODE -ne 0) { throw "No hay credenciales válidas de AWS. Revisa el Paso 2 de infra/GUIA_DESPLIEGUE.md" }
if (-not $ArtifactsBucket) { $ArtifactsBucket = "goble-artifacts-$Account-$Region" }
$Prefix = "goble/$EnvName"
$Stack = "goble-$EnvName"

if (Test-Path ".venv\Scripts\python.exe") { $Python = ".venv\Scripts\python.exe" } else { $Python = "py" }

Write-Host ">> Cuenta $Account | región $Region | stack $Stack" -ForegroundColor Cyan

Write-Host ">> Empaquetando" -ForegroundColor Cyan
Invoke-Native $Python @("scripts/package.py")
$Keys = @{}
Get-Content "build/artifacts/keys.env" | ForEach-Object {
    $k, $v = $_ -split "=", 2
    if ($k) { $Keys[$k.Trim()] = $v.Trim() }
}

# head-bucket escribe en stderr si el bucket no existe: no debe cortar el script
$ErrorActionPreference = "Continue"
aws s3api head-bucket --bucket $ArtifactsBucket --region $Region *> $null
$BucketExiste = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = "Stop"
if (-not $BucketExiste) {
    Write-Host ">> Creando bucket s3://$ArtifactsBucket" -ForegroundColor Cyan
    Invoke-Native aws @("s3", "mb", "s3://$ArtifactsBucket", "--region", $Region)
}

Write-Host ">> Subiendo artefactos a s3://$ArtifactsBucket/$Prefix/" -ForegroundColor Cyan
foreach ($zip in @($Keys.FRONTEND_ZIP)) {
    Invoke-Native aws @("s3", "cp", "build/artifacts/$zip", "s3://$ArtifactsBucket/$Prefix/$zip",
                        "--region", $Region, "--only-show-errors")
}

Write-Host ">> Desplegando CloudFormation (la primera vez tarda ~15 min)" -ForegroundColor Cyan
$Params = @(
    "EnvName=$EnvName",
    "ArtifactsBucket=$ArtifactsBucket",
    "FrontendKey=$Prefix/$($Keys.FRONTEND_ZIP)",
    "ClaudeModel=$ClaudeModel",
    "DbInstanceClass=$DbInstanceClass",
    "FrecuenciaEvaluacion=$FrecuenciaEvaluacion",
    "HabilitarScheduler=$(if ($SinScheduler) { 'false' } else { 'true' })",
    "EmailRemitente=$EmailRemitente",
    "EmailDestinoDemo=$EmailDestinoDemo"
)
Invoke-Native aws (@("cloudformation", "deploy", "--region", $Region, "--stack-name", $Stack,
                     "--template-file", "infra/template.yaml", "--capabilities", "CAPABILITY_IAM",
                     "--no-fail-on-empty-changeset", "--parameter-overrides") + $Params)

Write-Host ">> Base de datos (Lambda db-init)" -ForegroundColor Cyan
# El payload va en un archivo: Windows PowerShell 5.1 pierde las comillas del JSON al pasarlo como argumento
if ($DbReset) { $Payload = '{"forzar": true}' } else { $Payload = '{}' }
[System.IO.File]::WriteAllText("$PWD\build\db-init-payload.json", $Payload)  # sin BOM
Invoke-Native aws @("lambda", "invoke", "--region", $Region, "--function-name", "goble-$EnvName-db-init",
                    "--payload", "fileb://build/db-init-payload.json", "build/db-init.json") | Out-Null
Get-Content "build/db-init.json"
Write-Host ""

Invoke-Native aws @("cloudformation", "describe-stacks", "--region", $Region, "--stack-name", $Stack,
                    "--query", "Stacks[0].Outputs", "--output", "table")
Write-Host ">> Abre FrontendUrl e ingresa con luis.mora@demo.ec / demo1234" -ForegroundColor Green
