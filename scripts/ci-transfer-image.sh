#!/usr/bin/env bash
# Run on the GitHub Actions runner after build/push and SSH setup.
set -euo pipefail

: "${APP_IMAGE:?APP_IMAGE is required}"
: "${SSH_HOST:?SSH_HOST is required}"
: "${SSH_PORT:?SSH_PORT is required}"
: "${SSH_USER:?SSH_USER is required}"

SSH_OPTS=(
  -4
  -i ~/.ssh/id_rsa
  -p "$SSH_PORT"
  -o BatchMode=yes
  -o ConnectTimeout=20
)

echo "--- pulling image on runner: $APP_IMAGE ---"
docker pull "$APP_IMAGE"

echo "--- streaming image to $SSH_USER@$SSH_HOST ---"
docker save "$APP_IMAGE" | gzip -1 | ssh "${SSH_OPTS[@]}" "$SSH_USER@$SSH_HOST" 'gunzip -c | docker load'

echo "--- verifying image on server ---"
ssh "${SSH_OPTS[@]}" "$SSH_USER@$SSH_HOST" \
  "docker image inspect $(printf %q "$APP_IMAGE") >/dev/null"

echo "--- image transfer complete ---"
