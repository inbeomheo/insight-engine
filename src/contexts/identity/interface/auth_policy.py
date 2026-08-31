"""인증 우회(bypass) 정책 — production은 항상 fail-closed."""
from __future__ import annotations

import os

_TRUTHY = {"1", "true", "yes", "on"}
_BYPASS_ENVS = {"development", "testing"}


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
