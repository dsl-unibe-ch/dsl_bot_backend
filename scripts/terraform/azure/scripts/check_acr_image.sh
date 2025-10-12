#!/usr/bin/env bash
set -euo pipefail

INPUT="$(cat)"
REGISTRY="$(jq -r '.registry // empty' <<<"$INPUT")"
REPO="$(jq -r '.repository // empty' <<<"$INPUT")"
TAG="$(jq -r '.tag // empty' <<<"$INPUT")"

if [[ -z "$REGISTRY" || -z "$REPO" || -z "$TAG" ]]; then
  printf '{"exists":"false"}'
  exit 0
fi

if TAGS="$(az acr repository show-tags --name "$REGISTRY" --repository "$REPO" --output tsv 2>/dev/null)"; then
  if grep -Fxq "$TAG" <<<"$TAGS"; then
    printf '{"exists":"true"}'
  else
    printf '{"exists":"false"}'
  fi
else
  printf '{"exists":"false"}'
fi