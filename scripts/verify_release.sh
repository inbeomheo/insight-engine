#!/usr/bin/env bash
set -euo pipefail

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
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

PY="${PYTHON:-python3}"
if [ -x .venv/bin/python ]; then
  PY=.venv/bin/python
fi

npm run verify:audit
npm run verify:secrets
"$PY" scripts/check_production_readiness.py
"$PY" scripts/check_host_prereqs.py
"$PY" scripts/backup_app_data.py rehearse --summary
"$PY" scripts/backup_app_data.py drill-latest --summary
docker compose -f docker-compose.deploy.yml config --quiet
npm run verify:caddy
npm run verify:k8s
npm run verify:ci
npm run verify:maintenance
