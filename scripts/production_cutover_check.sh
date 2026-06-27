#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

PY="${PYTHON:-python3}"
if [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  detected_git_sha="$(git rev-parse HEAD)"
else
  detected_git_sha=""
fi

export APP_VERSION="${APP_VERSION:-v2.0}"
export GIT_SHA="${GIT_SHA:-$detected_git_sha}"
export APP_RELEASE="${APP_RELEASE:-$GIT_SHA}"
export BUILD_TIME="${BUILD_TIME:-$(date -u +'%Y-%m-%dT%H:%M:%SZ')}"
export ERROR_TRACKING_REQUIRED="${ERROR_TRACKING_REQUIRED:-true}"
export ALERT_WEBHOOK_REQUIRED="${ALERT_WEBHOOK_REQUIRED:-true}"

base_url="${INSIGHT_BASE_URL:-${APP_BASE_URL:-}}"
if [ -z "$base_url" ]; then
  printf 'ERROR: INSIGHT_BASE_URL or APP_BASE_URL is required for production cutover checks.\n' >&2
  exit 2
fi

tls_min_days="${MONITOR_TLS_MIN_DAYS:-21}"
image_ref="${IMAGE_REF:-insight-engine:local}"

printf '== release source state ==\n'
"$PY" scripts/check_release_source_state.py --require-clean

printf '== release verification ==\n'
npm run verify:release

printf '== production readiness ==\n'
"$PY" scripts/check_production_readiness.py

printf '\n== production image hygiene ==\n'
EXPECTED_GIT_SHA="$GIT_SHA" bash scripts/verify_docker_image_hygiene.sh "$image_ref"

printf '\n== strict host prerequisites ==\n'
"$PY" scripts/check_host_prereqs.py \
  --require-overcommit \
  --require-persistent-overcommit \
  --require-external-backups \
  --require-backup-mounts

printf '\n== latest backup restore drill ==\n'
"$PY" scripts/backup_app_data.py drill-latest --summary

printf '\n== public deployment monitor ==\n'
"$PY" scripts/monitor_readiness.py \
  --base-url "$base_url" \
  --require-public-host \
  --require-https \
  --tls-min-days "$tls_min_days" \
  --require-release-metadata \
  --expected-release "$APP_RELEASE" \
  --expected-git-sha "$GIT_SHA" \
  --require-webhook \
  --send-test-alert
