#!/usr/bin/env bash
# Empaqueta, sube los zips a S3, despliega infra/template.yaml con CloudFormation y
# carga la base de datos (Lambda db-init) la primera vez.
#
# Uso (desde cualquier carpeta, con credenciales AWS en el entorno):
#   ENV_NAME=dev bash infra/deploy.sh
#
# El primer despliegue tarda ~15 min (RDS + NAT). Los siguientes, 1-3 min.
#
# Variables opcionales:
#   ENV_NAME          dev | prod                       (default: dev)
#   AWS_REGION        región                           (default: la del perfil o us-east-1)
#   ARTIFACTS_BUCKET  bucket para los zips             (default: goble-artifacts-<account>-<region>)
#   CLAUDE_MODEL      modelo de Bedrock                (default: anthropic.claude-sonnet-5)
#   DB_RESET          1 = borra la BD y vuelve a cargar la data fake (default: 0)
#   DB_INSTANCE_CLASS tamaño de RDS                    (default: db.t3.micro)
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_NAME="${ENV_NAME:-dev}"
REGION="${AWS_REGION:-$(aws configure get region 2>/dev/null || true)}"
REGION="${REGION:-us-east-1}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${ARTIFACTS_BUCKET:-goble-artifacts-${ACCOUNT}-${REGION}}"
PREFIX="goble/${ENV_NAME}"
STACK="goble-${ENV_NAME}"
CLAUDE_MODEL="${CLAUDE_MODEL:-anthropic.claude-sonnet-5}"
DB_RESET="${DB_RESET:-0}"
DB_INSTANCE_CLASS="${DB_INSTANCE_CLASS:-db.t3.micro}"
# .venv del repo si existe; en Windows "python3" suele ser el atajo de la Microsoft Store
if [ -x .venv/Scripts/python ]; then PYTHON=.venv/Scripts/python
elif [ -x .venv/bin/python ]; then PYTHON=.venv/bin/python
else PYTHON="$(command -v py || command -v python3 || command -v python)"; fi

echo ">> Cuenta ${ACCOUNT} | región ${REGION} | stack ${STACK}"

echo ">> Empaquetando"
"$PYTHON" scripts/package.py
# shellcheck disable=SC1091
source build/artifacts/keys.env

if ! aws s3api head-bucket --bucket "$BUCKET" --region "$REGION" 2>/dev/null; then
  echo ">> Creando bucket s3://${BUCKET}"
  aws s3 mb "s3://${BUCKET}" --region "$REGION"
fi

echo ">> Subiendo artefactos a s3://${BUCKET}/${PREFIX}/"
for zip in "$FRONTEND_ZIP"; do
  aws s3 cp "build/artifacts/${zip}" "s3://${BUCKET}/${PREFIX}/${zip}" --region "$REGION" --only-show-errors
done

echo ">> Desplegando CloudFormation"
aws cloudformation deploy \
  --region "$REGION" \
  --stack-name "$STACK" \
  --template-file infra/template.yaml \
  --capabilities CAPABILITY_IAM \
  --no-fail-on-empty-changeset \
  --parameter-overrides \
    EnvName="$ENV_NAME" \
    ArtifactsBucket="$BUCKET" \
    FrontendKey="${PREFIX}/${FRONTEND_ZIP}" \
    ClaudeModel="$CLAUDE_MODEL" \
    DbInstanceClass="$DB_INSTANCE_CLASS"

echo ">> Base de datos (Lambda db-init)"
if [ "$DB_RESET" = "1" ]; then PAYLOAD='{"forzar": true}'; else PAYLOAD='{}'; fi
aws lambda invoke --region "$REGION" --function-name "goble-${ENV_NAME}-db-init" \
  --cli-binary-format raw-in-base64-out --payload "$PAYLOAD" build/db-init.json >/dev/null
cat build/db-init.json; echo

aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs" --output table
echo ">> Abre FrontendUrl e ingresa con luis.mora@demo.ec / demo1234"
