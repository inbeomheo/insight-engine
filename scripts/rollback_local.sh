#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.deploy.yml}"
IMAGE_TAG="${IMAGE_TAG:-insight-engine:local}"
ROLLBACK_IMAGE_TAG="${ROLLBACK_IMAGE_TAG:-insight-engine:rollback}"
ROLLBACK_SKIP_CLEANUP="${ROLLBACK_SKIP_CLEANUP:-false}"

_truthy() {
  case "${1:-}" in
    1|true|TRUE|True|yes|YES|Yes|on|ON|On) return 0 ;;
    *) return 1 ;;
  esac
}

_image_label() {
  docker image inspect --format "{{ index .Config.Labels \"$1\" }}" "$ROLLBACK_IMAGE_TAG" 2>/dev/null || true
}

_usable_metadata() {
  case "${1:-}" in
    ""|"<no value>"|local|unknown|dev|development|test|none|null) return 1 ;;
    *) return 0 ;;
  esac
}

if ! docker image inspect "$ROLLBACK_IMAGE_TAG" >/dev/null 2>&1; then
  printf 'ERROR: rollback image %s not found. Run deploy:local after a healthy deployment to seed it.\n' "$ROLLBACK_IMAGE_TAG" >&2
  exit 2
fi

rollback_version="$(_image_label org.opencontainers.image.version)"
rollback_revision="$(_image_label org.opencontainers.image.revision)"
rollback_build_time="$(_image_label org.opencontainers.image.created)"

if ! _usable_metadata "$rollback_version"; then
  printf 'ERROR: rollback image %s has no usable org.opencontainers.image.version label.\n' "$ROLLBACK_IMAGE_TAG" >&2
  exit 2
fi
if ! _usable_metadata "$rollback_revision"; then
  printf 'ERROR: rollback image %s has no usable org.opencontainers.image.revision label.\n' "$ROLLBACK_IMAGE_TAG" >&2
  exit 2
fi
if ! _usable_metadata "$rollback_build_time"; then
  printf 'ERROR: rollback image %s has no usable org.opencontainers.image.created label.\n' "$ROLLBACK_IMAGE_TAG" >&2
  exit 2
fi

export APP_VERSION="${APP_VERSION:-$rollback_version}"
export GIT_SHA="${GIT_SHA:-$rollback_revision}"
export APP_RELEASE="${APP_RELEASE:-$rollback_revision}"
export BUILD_TIME="${BUILD_TIME:-$rollback_build_time}"

printf '== retag rollback image ==\n'
printf 'source=%s\ntarget=%s\nrelease=%s\ngit_sha=%s\nbuild_time=%s\n' \
  "$ROLLBACK_IMAGE_TAG" "$IMAGE_TAG" "$APP_RELEASE" "$GIT_SHA" "$BUILD_TIME"
docker tag "$ROLLBACK_IMAGE_TAG" "$IMAGE_TAG"

printf '\n== recreate app services from rollback image ==\n'
docker compose -f "$COMPOSE_FILE" up -d --no-build --force-recreate --wait --wait-timeout 180 --remove-orphans backend frontend
docker compose -f "$COMPOSE_FILE" up -d --force-recreate --no-deps --wait --wait-timeout 60 --remove-orphans edge

printf '\n== verify rollback readiness ==\n'
INSIGHT_EXPECTED_RELEASE="$APP_RELEASE" INSIGHT_EXPECTED_GIT_SHA="$GIT_SHA" npm run ops:monitor

if _truthy "$ROLLBACK_SKIP_CLEANUP"; then
  printf '\n== skip cleanup after rollback ==\n'
else
  npm run docker:cleanup
fi
