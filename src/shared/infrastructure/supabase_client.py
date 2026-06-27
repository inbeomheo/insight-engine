"""Supabase 인프라 헬퍼 — cross-cutting 클라이언트 + 암호화 헬퍼.

Issue #17 (소PR A) — `services/data/supabase_service.py`에 있던 인프라 계층 헬퍼를
도메인 코드와 분리하기 위해 본 모듈로 이전.

제공 헬퍼:
- `get_supabase()` — anon-key 기반 클라이언트 싱글톤
- `is_supabase_enabled()` — 환경변수 기반 활성화 여부
- `_get_admin_client()` — service_role-key 기반 admin 클라이언트
- `encrypt_api_key()` / `decrypt_api_key()` — Fernet 암호화/복호화

기존 `services.data.supabase_service`는 본 모듈에서 재익스포트하는 shim으로 유지되어
호출처 호환성을 보장한다. 신규 호출처는 본 모듈을 직접 import할 것.
"""
from __future__ import annotations

import base64
import hashlib
import os

from cryptography.fernet import Fernet

from services.core.logging_config import supabase_logger as logger
from services.exceptions import ConfigurationError


# ---------------------------------------------------------------------------
# 모듈 레벨 싱글톤 상태
# ---------------------------------------------------------------------------
_supabase_client = None
_supabase_admin = None
_fernet_instance: Fernet | None = None
_encryption_enabled: bool | None = None


def _is_production_env() -> bool:
    return (os.getenv('FLASK_ENV') or '').strip().lower() == 'production'


def _missing_encryption_secret_error() -> ConfigurationError:
    return ConfigurationError(
        "ENCRYPTION_SECRET 환경변수가 필요합니다. "
        "production에서는 API 키를 평문으로 저장할 수 없습니다.",
        config_key='ENCRYPTION_SECRET',
    )


def _lazy_create_client(url: str, key: str):
    """supabase.create_client를 지연 로딩 (cold start ~1.5초 절감)."""
    from supabase import create_client
    return create_client(url, key)


def get_supabase():
    """Supabase 클라이언트 싱글톤 (anon key)."""
    global _supabase_client

    if _supabase_client is None:
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')

        if not url or not key:
            return None

        _supabase_client = _lazy_create_client(url, key)

    return _supabase_client


def is_supabase_enabled() -> bool:
    """Supabase 활성화 여부 (환경변수 기반)."""
    return bool(os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'))


def _get_admin_client():
    """Supabase Admin 클라이언트 (service_role key — 계정 삭제 등)."""
    global _supabase_admin

    if _supabase_admin is None:
        url = os.getenv('SUPABASE_URL')
        service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not url or not service_role_key:
            logger.warning("SUPABASE_SERVICE_ROLE_KEY 미설정 - admin 기능 비활성화")
            return None

        _supabase_admin = _lazy_create_client(url, service_role_key)

    return _supabase_admin


def _is_encryption_enabled() -> bool:
    """암호화 활성화 여부 확인."""
    global _encryption_enabled
    if _encryption_enabled is None:
        secret = os.getenv('ENCRYPTION_SECRET')
        _encryption_enabled = bool(secret and secret.strip())
        if not _encryption_enabled:
            logger.warning(
                "ENCRYPTION_SECRET이 설정되지 않았습니다. API 키 암호화가 비활성화됩니다."
            )
    return _encryption_enabled


def _get_fernet() -> Fernet:
    """Fernet 인스턴스 싱글톤.

    Raises:
        ConfigurationError: ENCRYPTION_SECRET 환경변수 미설정.
    """
    global _fernet_instance

    if _fernet_instance is None:
        secret = os.getenv('ENCRYPTION_SECRET')

        if not secret or not secret.strip():
            raise _missing_encryption_secret_error()

        key = hashlib.sha256(secret.encode()).digest()
        _fernet_instance = Fernet(base64.urlsafe_b64encode(key))

    return _fernet_instance


def encrypt_api_key(api_key: str) -> str:
    """API 키 암호화. 개발 비활성화 시 원본 반환, production에서는 fail-closed."""
    if not api_key:
        return None
    if not _is_encryption_enabled():
        if _is_production_env():
            raise _missing_encryption_secret_error()
        logger.debug("암호화 비활성화 상태, 원본 저장")
        return api_key
    try:
        return _get_fernet().encrypt(api_key.encode()).decode()
    except ConfigurationError:
        if _is_production_env():
            raise
        logger.warning("암호화 설정 오류, 원본 저장")
        return api_key


def decrypt_api_key(encrypted_key: str) -> str:
    """API 키 복호화. 개발 비활성화 시 원본 반환, production에서는 fail-closed."""
    if not encrypted_key:
        return None
    if not _is_encryption_enabled():
        if _is_production_env():
            raise _missing_encryption_secret_error()
        return encrypted_key
    try:
        return _get_fernet().decrypt(encrypted_key.encode()).decode()
    except ConfigurationError:
        if _is_production_env():
            raise
        return encrypted_key
    except Exception as e:
        logger.warning(f"API 키 복호화 실패: {e}")
        return None


def reset_clients_for_test() -> None:
    """테스트용: 싱글톤 캐시 초기화.

    프로덕션 코드에서는 호출하지 말 것 — supabase-py 클라이언트가 내부적으로
    유지하는 connection 핸들이 GC 타이밍에 따라 닫히므로 동일 프로세스에서
    바로 새 인스턴스를 만들면 충돌 가능.
    """
    global _supabase_client, _supabase_admin, _fernet_instance, _encryption_enabled
    _supabase_client = None
    _supabase_admin = None
    _fernet_instance = None
    _encryption_enabled = None


__all__ = [
    "get_supabase",
    "is_supabase_enabled",
    "_get_admin_client",
    "_lazy_create_client",
    "encrypt_api_key",
    "decrypt_api_key",
    "_is_encryption_enabled",
    "_get_fernet",
    "reset_clients_for_test",
]
