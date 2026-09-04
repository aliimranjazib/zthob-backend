#!/usr/bin/env bash
# Run on the production server after git reset (called by GitHub Actions).
set -euo pipefail

: "${APP_IMAGE:?APP_IMAGE is required}"
: "${EXPECTED_GIT_COMMIT:?EXPECTED_GIT_COMMIT is required}"
: "${GIT_BRANCH:?GIT_BRANCH is required}"
: "${GIT_COMMIT_DATE:?GIT_COMMIT_DATE is required}"

DEPLOY_DIR="${DEPLOY_DIR:-/home/mgask-production}"
cd "$DEPLOY_DIR"

if [ -f .env ]; then
  grep -v -E '^(GIT_COMMIT|GIT_BRANCH|GIT_COMMIT_DATE|APP_IMAGE)=' .env > .env.tmp || true
  mv .env.tmp .env
fi

export GIT_COMMIT="$EXPECTED_GIT_COMMIT"
printf 'GIT_COMMIT=%s\nGIT_BRANCH=%s\nGIT_COMMIT_DATE=%s\nAPP_IMAGE=%s\n' \
  "$GIT_COMMIT" "$GIT_BRANCH" "$GIT_COMMIT_DATE" "$APP_IMAGE" > deployment.env

COMPOSE=(docker compose --project-name mgask-production --env-file .env --env-file deployment.env -f docker-compose.production.yml)
export APP_IMAGE

echo "--- deployment.env ---"
cat deployment.env

if [ "${IMAGE_PRELOADED:-}" = "true" ]; then
  echo "--- using CI-preloaded image (skipping GHCR login/pull) ---"
  PULL_POLICY="never"
else
  : "${GHCR_USERNAME:?GHCR_USERNAME is required when IMAGE_PRELOADED is not true}"
  : "${GHCR_TOKEN:?GHCR_TOKEN is required when IMAGE_PRELOADED is not true}"
  printf '%s' "$GHCR_TOKEN" | docker login ghcr.io -u "$GHCR_USERNAME" --password-stdin
  echo "--- pulling images ---"
  "${COMPOSE[@]}" pull web celery_worker
  PULL_POLICY="always"
fi

if ! docker image inspect "$APP_IMAGE" >/dev/null 2>&1; then
  echo "::error::Image not found locally: $APP_IMAGE"
  exit 1
fi

pulled_image_id="$(docker image inspect --format='{{.Id}}' "$APP_IMAGE")"
image_git_commit="$(docker image inspect --format='{{range .Config.Env}}{{println .}}{{end}}' "$APP_IMAGE" | sed -n 's/^GIT_COMMIT=//p' | head -n1)"
echo "pulled_image_id=$pulled_image_id"
echo "image_git_commit=$image_git_commit"

if [ "$image_git_commit" != "$EXPECTED_GIT_COMMIT" ]; then
  echo "::error::Pulled image GIT_COMMIT=$image_git_commit expected $EXPECTED_GIT_COMMIT"
  exit 1
fi

mkdir -p backups
echo "--- database backup ---"
"${COMPOSE[@]}" exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB"' > "backups/backup_$(date +%F_%H-%M).sql"

echo "--- migration plan ---"
"${COMPOSE[@]}" run --rm web python manage.py migrate --plan

echo "--- running migrations ---"
"${COMPOSE[@]}" run --rm web python manage.py migrate --noinput

echo "--- removing old app containers ---"
for service in web celery_worker; do
  container_id="$("${COMPOSE[@]}" ps -q "$service" 2>/dev/null || true)"
  if [ -n "$container_id" ]; then
    echo "removing $service container $container_id"
    docker rm -f "$container_id"
  fi
done

echo "--- starting app containers ---"
"${COMPOSE[@]}" up -d --no-deps --force-recreate --pull "$PULL_POLICY" web celery_worker

"${COMPOSE[@]}" ps

running_container_id="$("${COMPOSE[@]}" ps -q web | head -n1)"
if [ -z "$running_container_id" ]; then
  echo "::error::web container is not running after deploy"
  exit 1
fi

running_image_id="$(docker inspect --format='{{.Image}}' "$running_container_id")"
running_created="$(docker inspect --format='{{.Created}}' "$running_container_id")"
running_config_image="$(docker inspect --format='{{.Config.Image}}' "$running_container_id")"
echo "running_image_id=$running_image_id"
echo "running_config_image=$running_config_image"
echo "running_created=$running_created"

if [ "$running_image_id" != "$pulled_image_id" ]; then
  echo "::error::web container is not running the pulled image"
  exit 1
fi

echo "--- collectstatic ---"
"${COMPOSE[@]}" exec -T web python manage.py collectstatic --noinput

echo "--- container GIT_* env ---"
"${COMPOSE[@]}" exec -T web /bin/sh -c 'env | grep -E "^GIT_" || true'

echo "--- version check ---"
"${COMPOSE[@]}" exec -T -e EXPECTED_GIT_COMMIT="$EXPECTED_GIT_COMMIT" web python manage.py shell -c "
import os
from apps.core.version import get_git_info
info = get_git_info()
print(info)
raise SystemExit(0 if info.get('full_commit_hash') == os.environ['EXPECTED_GIT_COMMIT'] else 1)
"

echo "--- deploy complete ---"
