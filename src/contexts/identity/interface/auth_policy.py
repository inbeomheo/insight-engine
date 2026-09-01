"""인증 우회(bypass) 정책 — production은 항상 fail-closed."""
from __future__ import annotations

import hmac
import os
import re

_TRUTHY = {"1", "true", "yes", "on"}
_BYPASS_ENVS = {"development", "testing"}
_PROXY_USER_RE = re.compile(r"[A-Za-z0-9_.@-]{1,96}")


def flask_runtime_env() -> str:
    return (os.getenv("FLASK_ENV") or "").strip().lower()


def is_production_env() -> bool:
    return flask_runtime_env() == "production"


def is_auth_bypass_flag_set() -> bool:
    return (os.getenv("AUTH_BYPASS") or "").strip().lower() in _TRUTHY


def is_auth_bypass_allowed() -> bool:
    """개발/테스트에서만 AUTH_BYPASS=true 허용. production은 절대 불가."""
    if is_production_env():
        return False
    if flask_runtime_env() not in _BYPASS_ENVS:
        return False
    return is_auth_bypass_flag_set()


def trusted_proxy_user(headers) -> str | None:
    """Caddy가 공유 비밀로 서명한 요청의 로컬 사용자 ID를 반환한다."""
    if (os.getenv("AUTH_MODE") or "").strip().lower() != "trusted_proxy":
        return None

    expected = os.getenv("AUTH_PROXY_SECRET") or ""
    presented = headers.get("X-Insight-Proxy-Secret", "")
    if len(expected) < 32 or not presented:
        return None
    if not hmac.compare_digest(expected, presented):
        return None

    raw_user = (headers.get("X-Insight-Proxy-User") or "").strip()
    if not _PROXY_USER_RE.fullmatch(raw_user):
        return None
    return f"proxy_{raw_user}"
