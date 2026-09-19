#!/usr/bin/env sh
set -eu

failed=0

check_command() {
  command_name="$1"
  label="$2"
  if command -v "$command_name" >/dev/null 2>&1; then
    version="$($command_name --version 2>/dev/null | head -n 1 || true)"
    echo "OK   $label ${version}"
  else
    echo "MISS $label"
    failed=1
  fi
}

check_command git Git
check_command docker Docker

if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    echo "OK   Docker Compose $(docker compose version --short 2>/dev/null || true)"
  else
    echo "MISS Docker Compose v2"
    failed=1
  fi
fi

if [ "$failed" -ne 0 ]; then
  echo "Install missing prerequisites, then run make doctor again."
  exit 1
fi

echo "Development prerequisites are available."
