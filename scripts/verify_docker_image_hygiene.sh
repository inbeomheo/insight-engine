#!/usr/bin/env bash
set -euo pipefail

IMAGE_REF="${1:-${IMAGE_REF:-insight-engine:local}}"

docker image inspect "$IMAGE_REF" >/dev/null

image_label() {
  docker image inspect --format "{{ index .Config.Labels \"$1\" }}" "$IMAGE_REF" 2>/dev/null || true
}

usable_metadata() {
  case "${1:-}" in
    ""|"<no value>"|local|unknown|dev|development|test|none|null) return 1 ;;
    *) return 0 ;;
  esac
}

image_version="$(image_label org.opencontainers.image.version)"
image_revision="$(image_label org.opencontainers.image.revision)"
image_created="$(image_label org.opencontainers.image.created)"

if ! usable_metadata "$image_version"; then
  printf 'ERROR: image %s has no usable org.opencontainers.image.version label.\n' "$IMAGE_REF" >&2
  exit 1
fi
if ! usable_metadata "$image_revision"; then
  printf 'ERROR: image %s has no usable org.opencontainers.image.revision label.\n' "$IMAGE_REF" >&2
  exit 1
fi
if ! usable_metadata "$image_created"; then
  printf 'ERROR: image %s has no usable org.opencontainers.image.created label.\n' "$IMAGE_REF" >&2
  exit 1
fi

expected_git_sha="${EXPECTED_GIT_SHA:-${INSIGHT_EXPECTED_GIT_SHA:-}}"
if [ -n "$expected_git_sha" ] && [ "$image_revision" != "$expected_git_sha" ]; then
  printf 'ERROR: image %s revision label %s does not match expected git SHA %s.\n' \
    "$IMAGE_REF" "$image_revision" "$expected_git_sha" >&2
  exit 1
fi

expected_app_version="${EXPECTED_APP_VERSION:-}"
if [ -n "$expected_app_version" ] && [ "$image_version" != "$expected_app_version" ]; then
  printf 'ERROR: image %s version label %s does not match expected version %s.\n' \
    "$IMAGE_REF" "$image_version" "$expected_app_version" >&2
  exit 1
fi

docker run --rm --entrypoint sh "$IMAGE_REF" -eu -c '
  for path in \
    /app/.env \
    /app/.env.local \
    /app/tests \
    /app/test-results \
    /app/playwright-report \
    /app/.agent \
    /app/.agents \
    /app/.claude \
    /app/.cmux \
    /app/.understand-anything \
    /app/.worktrees \
    /app/downloads \
    /app/publish_queue.json \
    /app/skills-lock.json \
    /app/package-lock.json
  do
    if [ -e "$path" ]; then
      echo "unexpected image artifact: $path" >&2
      exit 1
    fi
  done

  test -f /app/README.md
  test -f /app/frontend/package-lock.json
  test -d /app/frontend/.next
  test -d /app/frontend/node_modules
'

printf 'docker image hygiene passed: %s\n' "$IMAGE_REF"
