#!/usr/bin/env bash
set -euo pipefail

# Push key=value pairs from a .env file into an Azure Web App's App Settings
# Usage:
#   ./scripts/push_env_to_webapp.sh -e .env.dev -g rg-kb-dev-001 -n kioskbot-backend-web
# Optional slot:
#   ./scripts/push_env_to_webapp.sh -e .env.prod -g rg-kb-prod-001 -n kioskbot-backend-web -s staging

ENV_FILE=""
RESOURCE_GROUP=""
WEBAPP_NAME=""
SLOT_NAME=""

while getopts ":e:g:n:s:h" opt; do
  case $opt in
    e) ENV_FILE=${OPTARG} ;;
    g) RESOURCE_GROUP=${OPTARG} ;;
    n) WEBAPP_NAME=${OPTARG} ;;
    s) SLOT_NAME=${OPTARG} ;;
    h)
      echo "Usage: $0 -e <env_file> -g <resource_group> -n <webapp_name> [-s <slot>]" ; exit 0 ;;
    *) echo "Invalid option: -$OPTARG" ; exit 2 ;;
  esac
done

if [[ -z "${ENV_FILE}" || -z "${RESOURCE_GROUP}" || -z "${WEBAPP_NAME}" ]]; then
  echo "ERROR: -e, -g and -n are required. Run with -h for help." >&2
  exit 2
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  echo "ERROR: Env file not found: ${ENV_FILE}" >&2
  exit 1
fi

# Build settings array: preserve values (including spaces) and strip surrounding quotes
declare -a SETTINGS
while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
  line="${raw_line%$'\r'}"          # strip CR for Windows line endings
  [[ -z "$line" ]] && continue       # skip empty
  [[ "$line" =~ ^[[:space:]]*# ]] && continue  # skip comments
  if [[ "$line" != *"="* ]]; then
    continue
  fi
  key=${line%%=*}
  val=${line#*=}
  key=$(echo "$key" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
  val=$(echo "$val" | sed -E 's/^[[:space:]]+|[[:space:]]+$//g')
  # remove surrounding quotes if present
  if [[ "$val" =~ ^\".*\"$ ]]; then val=${val:1:${#val}-2}; fi
  if [[ "$val" =~ ^\'.*\'$ ]]; then val=${val:1:${#val}-2}; fi
  # skip export prefix in keys if present
  key=${key#export }
  [[ -z "$key" ]] && continue
  SETTINGS+=("${key}=${val}")
done < "${ENV_FILE}"

if [[ ${#SETTINGS[@]} -eq 0 ]]; then
  echo "No settings parsed from ${ENV_FILE}. Nothing to do." >&2
  exit 0
fi

cmd=(az webapp config appsettings set --resource-group "${RESOURCE_GROUP}" --name "${WEBAPP_NAME}" --only-show-errors --output table --settings)
if [[ -n "${SLOT_NAME}" ]]; then
  cmd+=(--slot "${SLOT_NAME}")
fi

cmd+=("${SETTINGS[@]}")

echo "Applying $((${#SETTINGS[@]})) settings from ${ENV_FILE} to ${WEBAPP_NAME}${SLOT_NAME:+ (slot: ${SLOT_NAME})} in RG ${RESOURCE_GROUP}..."
"${cmd[@]}"
echo "Done."


