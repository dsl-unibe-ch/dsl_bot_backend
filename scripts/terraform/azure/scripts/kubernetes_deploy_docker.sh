#!/usr/bin/env bash

# This script is used to deploy the docker image to the kubernetes cluster


set -euo pipefail

usage() {
  cat <<'EOF'
Usage: kubernetes_deploy_docker.sh [-e dev|prod]

Reads AZURE_CONTAINER_REGISTRY_LOGIN_SERVER from .env.<ENV> at the repo root
and exports it for subsequent commands. Defaults ENV=dev if not provided.

Examples:
  ./kubernetes_deploy_docker.sh -e dev
  ENV=prod ./kubernetes_deploy_docker.sh
EOF
}

ENV_NAME="${ENV:-dev}"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -e|--env)
      shift
      ENV_NAME="${1:-}"
      [[ -z "$ENV_NAME" ]] && { echo "ERROR: missing value for -e|--env" >&2; exit 1; }
      ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
  shift || true
done

# Locate repository root (relative to this script path)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../" && pwd)"

ENV_FILE="$REPO_ROOT/.env.$ENV_NAME"
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: Environment file not found: $ENV_FILE" >&2
  echo "Create it based on .env.$ENV_NAME.example at the repo root." >&2
  exit 1
fi

# Load variables from the .env file safely
set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

if [[ -z "${AZURE_CONTAINER_REGISTRY_LOGIN_SERVER:-}" ]]; then
  echo "ERROR: AZURE_CONTAINER_REGISTRY_LOGIN_SERVER is not set in $ENV_FILE" >&2
  exit 1
fi

ACR_LOGIN_SERVER="$AZURE_CONTAINER_REGISTRY_LOGIN_SERVER"
ACR_NAME="${ACR_LOGIN_SERVER%%.*}"
AZ_SUBSCRIPTION_ID=$(az account show --query id -o tsv)

export AZURE_CONTAINER_REGISTRY_LOGIN_SERVER="$ACR_LOGIN_SERVER"

echo "ENV:            $ENV_NAME"
echo "Repo root:      $REPO_ROOT"
echo "Subscription ID: $AZ_SUBSCRIPTION_ID"
echo "Using ACR:      $ACR_NAME ($ACR_LOGIN_SERVER)"


kubectl apply -f kubernetes_deploy_docker.yaml
