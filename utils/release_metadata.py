"""Non-secret release metadata helpers for health checks and observability."""
from __future__ import annotations

import os
import re
from typing import Mapping


DEFAULT_APP_VERSION = 'v2.0'
UNKNOWN = 'unknown'
METADATA_PATTERN = re.compile(r'^[A-Za-z0-9._:/@+-]{1,160}$')


def _safe_metadata_value(value: str | None, default: str = UNKNOWN) -> str:
    candidate = (value or '').strip()
    if candidate and METADATA_PATTERN.fullmatch(candidate):
        return candidate
    return default


def release_metadata(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return release/build identifiers that are safe to expose publicly."""
    snapshot = os.environ if env is None else env
    version = _safe_metadata_value(snapshot.get('APP_VERSION'), DEFAULT_APP_VERSION)
    git_sha = _safe_metadata_value(
        snapshot.get('GIT_SHA')
        or snapshot.get('BUILD_SHA')
        or snapshot.get('SOURCE_COMMIT'),
    )
    release = _safe_metadata_value(
        snapshot.get('APP_RELEASE')
        or snapshot.get('SENTRY_RELEASE')
        or git_sha,
        git_sha,
    )
    build_time = _safe_metadata_value(snapshot.get('BUILD_TIME') or snapshot.get('BUILD_DATE'))
    return {
        'version': version,
        'release': release,
        'gitSha': git_sha,
        'buildTime': build_time,
    }
