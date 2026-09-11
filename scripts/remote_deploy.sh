#!/usr/bin/env bash
# Runs on the app box with DATABASE_URL set: build the image, create the tables, restart the app.
set -euo pipefail
cd "$(dirname "$0")/.."
DOCKER=docker
if ! $DOCKER info >/dev/null 2>&1; then DOCKER="sudo docker"; fi
$DOCKER build -t pmus-kalshi-mapper .
$DOCKER run --rm -e DATABASE_URL pmus-kalshi-mapper python -m mapper init-db ${INIT_DB_ARGS:-}
$DOCKER rm -f pmus-kalshi-mapper >/dev/null 2>&1 || true
$DOCKER run -d --restart always -p 80:8000 -e DATABASE_URL \
    -v "$HOME/pmus-kalshi-mapper/keys:/app/keys:ro" \
    --name pmus-kalshi-mapper pmus-kalshi-mapper
$DOCKER image prune -f
