#!/usr/bin/env bash
# Run on the staging server after git reset (called by GitHub Actions).
set -euo pipefail

: "${APP_IMAGE:?APP_IMAGE is required}"
: "${EXPECTED_GIT_COMMIT:?EXPECTED_GIT_COMMIT is required}"
: "${GIT_BRANCH:?GIT_BRANCH is required}"
: "${GIT_COMMIT_DATE:?GIT_COMMIT_DATE is required}"

DEPLOY_DIR="${DEPLOY_DIR:-/home/mgask-staging}"
cd "$DEPLOY_DIR"

COMPOSE=(docker compose --project-name mgask-staging --env-file .env -f docker-compose.staging.yml)
export APP_IMAGE

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

running_container_id="$("${COMPOSE[@]}" ps -q web | head -n1)"
running_image_id="$(docker inspect --format='{{.Image}}' "$running_container_id")"
if [ "$running_image_id" != "$pulled_image_id" ]; then
  echo "::error::web container is not running the pulled image"
  exit 1
fi

echo "--- collectstatic ---"
"${COMPOSE[@]}" exec -T web python manage.py collectstatic --noinput

"${COMPOSE[@]}" ps
echo "--- deploy complete ---"
