#!/usr/bin/env bash
# Empaqueta, sube los zips a S3 y despliega infra/template.yaml con CloudFormation.
#
# Uso (desde cualquier carpeta, con credenciales AWS en el entorno):
#   ENV_NAME=dev USE_MOCKS=true bash infra/deploy.sh
#
# Variables opcionales:
#   ENV_NAME          dev | prod                       (default: dev)
#   USE_MOCKS         true | false                     (default: true)
#   PROVIDER_API_URL  URL de la API externa real       (default: vacío)
#   AWS_REGION        región                           (default: la del perfil o us-east-1)
#   ARTIFACTS_BUCKET  bucket para los zips             (default: goble-artifacts-<account>-<region>)
set -euo pipefail

cd "$(dirname "$0")/.."

ENV_NAME="${ENV_NAME:-dev}"
USE_MOCKS="${USE_MOCKS:-true}"
PROVIDER_API_URL="${PROVIDER_API_URL:-}"
REGION="${AWS_REGION:-$(aws configure get region 2>/dev/null || true)}"
REGION="${REGION:-us-east-1}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
BUCKET="${ARTIFACTS_BUCKET:-goble-artifacts-${ACCOUNT}-${REGION}}"
PREFIX="goble/${ENV_NAME}"
STACK="goble-${ENV_NAME}"
PYTHON="$(command -v python3 || command -v python || command -v py)"

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
for zip in "$LAYER_ZIP" "$PROCESS_JOB_ZIP" "$GET_JOB_ZIP"; do
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
    UseMocks="$USE_MOCKS" \
    ProviderApiUrl="$PROVIDER_API_URL" \
    ArtifactsBucket="$BUCKET" \
    LayerKey="${PREFIX}/${LAYER_ZIP}" \
    ProcessJobKey="${PREFIX}/${PROCESS_JOB_ZIP}" \
    GetJobKey="${PREFIX}/${GET_JOB_ZIP}"

aws cloudformation describe-stacks --region "$REGION" --stack-name "$STACK" \
  --query "Stacks[0].Outputs" --output table
