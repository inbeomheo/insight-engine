#!/usr/bin/env bash
set -euo pipefail

# Safe Docker cleanup for Insight Engine deploys.
# - Keeps running containers and named volumes.
# - Retags the currently running backend image as insight-engine:local so compose
#   does not point at an unused image after failed/partial deploys.
# - Removes dangling images and BuildKit cache that accumulate after repeated
#   `docker compose up -d --build` runs.

IMAGE_TAG="${IMAGE_TAG:-insight-engine:local}"
BACKEND_CONTAINER="${BACKEND_CONTAINER:-insight-backend}"
PRUNE_BUILD_CACHE="${PRUNE_BUILD_CACHE:-1}"

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

if [ "$PRUNE_BUILD_CACHE" = "1" ]; then
  printf '\n== prune build cache ==\n'
  docker builder prune -f
else
  printf '\n== skip build cache prune ==\n'
fi

printf '\n== docker disk after cleanup ==\n'
docker system df || true

printf '\n== remaining insight images ==\n'
docker images --format '{{.ID}}\t{{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedSince}}' \
  | awk '$2 ~ /^insight-engine:/ || $2 ~ /^<none>:<none>$/ {print}' \
  | sort || true
