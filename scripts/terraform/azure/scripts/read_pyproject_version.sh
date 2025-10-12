#!/usr/bin/env bash
set -euo pipefail

INPUT=$(cat)
PYPROJECT_PATH=$(jq -r '.path // empty' <<<"$INPUT")
PREFIX=$(jq -r '.prefix // empty' <<<"$INPUT")

if [[ -z "$PYPROJECT_PATH" || ! -f "$PYPROJECT_PATH" ]]; then
  printf '{"error":"pyproject_not_found"}'
  exit 0
fi

# Extract version from [project] or [tool.poetry] tables
VERSION=$(awk '
  BEGIN{sec=""}
  /^[[:space:]]*\[project\][[:space:]]*$/ {sec="project"}
  /^[[:space:]]*\[tool\.poetry\][[:space:]]*$/ {sec="poetry"}
  sec!="" && $0 ~ /^[[:space:]]*version[[:space:]]*=/ {
    if (match($0, /version[[:space:]]*=[[:space:]]*"([^"]+)"/, m)) { print m[1]; exit }
  }
' "$PYPROJECT_PATH")

if [[ -z "$VERSION" ]]; then
  printf '{"error":"version_not_found"}'
  exit 0
fi

# Sanitize for docker tag: allowed [A-Za-z0-9_.-]
IMAGE_TAG=$(printf '%s' "${PREFIX}${VERSION}" | sed -E 's/[^A-Za-z0-9_.-]+/-/g')

jq -n --arg version "$VERSION" --arg image_tag "$IMAGE_TAG" '{version:$version, image_tag:$image_tag}'
