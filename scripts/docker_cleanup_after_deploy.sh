#!/usr/bin/env bash
set -euo pipefail

# Safe Docker cleanup for Insight Engine deploys.
# - Keeps running containers and named volumes.
# - Retags the currently running backend image as insight-engine:local so compose
#   does not point at an unused image after failed/partial deploys.
# - Removes dangling images and prunes stale BuildKit cache while keeping recent
#   layers hot for repeated deploys.

IMAGE_TAG="${IMAGE_TAG:-insight-engine:local}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-insight-backend}"
BUILD_CACHE_PRUNE_UNTIL="${BUILD_CACHE_PRUNE_UNTIL:-168h}"
PRUNE_BUILD_CACHE="${PRUNE_BUILD_CACHE:-until=$BUILD_CACHE_PRUNE_UNTIL}"

printf '== docker disk before cleanup ==\n'
docker system df || true

if docker container inspect "$BACKEND_CONTAINER" >/dev/null 2>&1; then
  running_image_id="$(docker inspect -f '{{.Image}}' "$BACKEND_CONTAINER")"
  if [ -n "$running_image_id" ]; then
    printf '\n== retag running backend image ==\n'
    printf 'container=%s\nimage=%s\ntag=%s\n' "$BACKEND_CONTAINER" "$running_image_id" "$IMAGE_TAG"
    docker tag "$running_image_id" "$IMAGE_TAG"
  fi
else
  printf '\nWARN: backend container %s not found; skipping retag.\n' "$BACKEND_CONTAINER" >&2
fi

printf '\n== prune dangling images ==\n'
docker image prune -f

case "$PRUNE_BUILD_CACHE" in
  0|false|False|no|No|skip|off)
    printf '\n== skip build cache prune ==\n'
    ;;
  1|true|True|yes|Yes|all)
    printf '\n== prune all build cache ==\n'
    docker builder prune -f
    ;;
  until=*)
    printf '\n== prune stale build cache ==\n'
    printf 'filter=%s\n' "$PRUNE_BUILD_CACHE"
    docker builder prune -f --filter "$PRUNE_BUILD_CACHE"
    ;;
  *)
    printf '\nERROR: unsupported PRUNE_BUILD_CACHE value: %s\n' "$PRUNE_BUILD_CACHE" >&2
    printf 'Use 0, all, or until=<duration> such as until=168h.\n' >&2
    exit 2
    ;;
esac

printf '\n== docker disk after cleanup ==\n'
docker system df || true

printf '\n== remaining insight images ==\n'
docker images --format '{{.ID}}\t{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}' \
  | awk '$2 ~ /^insight-engine:/ || $2 ~ /^<none>:<none>$/ {print}' \
  | sort || true
