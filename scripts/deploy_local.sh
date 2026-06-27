#!/usr/bin/env bash
set -euo pipefail

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  detected_git_sha="$(git rev-parse HEAD)"
else
  detected_git_sha=""
fi

export APP_VERSION="${APP_VERSION:-v2.0}"
export GIT_SHA="${GIT_SHA:-$detected_git_sha}"
export APP_RELEASE="${APP_RELEASE:-$GIT_SHA}"
export BUILD_TIME="${BUILD_TIME:-$(date -u +'%Y-%m-%dT%H:%M:%SZ')}"

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.deploy.yml}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-insight-backend}"
ROLLBACK_IMAGE_TAG="${ROLLBACK_IMAGE_TAG:-insight-engine:rollback}"
AUTO_ROLLBACK_ON_DEPLOY_FAILURE="${AUTO_ROLLBACK_ON_DEPLOY_FAILURE:-true}"

_truthy() {
  case "${1:-}" in
    1|true|TRUE|True|yes|YES|Yes|on|ON|On) return 0 ;;
    *) return 1 ;;
  esac
}

preserve_rollback_image() {
  if docker container inspect "$BACKEND_CONTAINER" >/dev/null 2>&1; then
    previous_image_id="$(docker inspect -f '{{.Image}}' "$BACKEND_CONTAINER")"
    if [ -n "$previous_image_id" ]; then
      printf '== preserve rollback image ==\n'
      printf 'container=%s\nimage=%s\ntag=%s\n' "$BACKEND_CONTAINER" "$previous_image_id" "$ROLLBACK_IMAGE_TAG"
      docker tag "$previous_image_id" "$ROLLBACK_IMAGE_TAG"
      return 0
    fi
  fi

  printf 'WARN: backend container %s not found; no rollback image preserved.\n' "$BACKEND_CONTAINER" >&2
  return 1
}

rollback_on_deploy_error() {
  status=$?
  trap - ERR
  if _truthy "$AUTO_ROLLBACK_ON_DEPLOY_FAILURE" && docker image inspect "$ROLLBACK_IMAGE_TAG" >/dev/null 2>&1; then
    printf '\nERROR: deploy failed; rolling back to %s.\n' "$ROLLBACK_IMAGE_TAG" >&2
    ROLLBACK_SKIP_CLEANUP=1 bash scripts/rollback_local.sh || true
  fi
  exit "$status"
}

preserve_rollback_image || true
trap rollback_on_deploy_error ERR

docker compose -f "$COMPOSE_FILE" up -d --build --wait --wait-timeout 180 --remove-orphans backend frontend
docker compose -f "$COMPOSE_FILE" up -d --force-recreate --no-deps --wait --wait-timeout 60 --remove-orphans edge

docker compose -f "$COMPOSE_FILE" exec -T backend python3 scripts/backup_app_data.py backup --summary
INSIGHT_EXPECTED_RELEASE="$APP_RELEASE" INSIGHT_EXPECTED_GIT_SHA="$GIT_SHA" npm run ops:monitor

trap - ERR
npm run docker:cleanup
