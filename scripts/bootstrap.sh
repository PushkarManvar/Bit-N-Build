#!/usr/bin/env sh
set -eu

project_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"

./scripts/doctor.sh

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
else
  echo "Keeping existing .env"
fi

docker compose config >/dev/null
docker compose build

echo "Setup complete. Run: make up"
