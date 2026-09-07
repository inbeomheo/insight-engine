"""Supabase 인프라 헬퍼 — cross-cutting 클라이언트 + 암호화 헬퍼.

Issue #17 (소PR A) — `services/data/supabase_service.py`에 있던 인프라 계층 헬퍼를
도메인 코드와 분리하기 위해 본 모듈로 이전.

제공 헬퍼:
- `get_supabase()` — publishable/legacy anon key 기반 클라이언트 싱글톤
- `get_user_supabase()` — 검증된 사용자 JWT가 연결된 요청별 클라이언트
- `get_service_supabase()` — 명시적인 secret/legacy service_role 클라이언트
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


def _lazy_create_client(url: str, key: str, options=None):
    """supabase.create_client를 지연 로딩 (cold start ~1.5초 절감)."""
    from supabase import create_client
    if options is None:
        return create_client(url, key)
    return create_client(url, key, options)


def _first_configured_env(*names: str) -> str | None:
    """Return the first non-empty configured value without ever logging it."""
    for name in names:
        value = os.getenv(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _get_publishable_key() -> str | None:
    """Prefer the current publishable key and retain legacy anon compatibility."""
    return _first_configured_env('SUPABASE_PUBLISHABLE_KEY', 'SUPABASE_ANON_KEY')


def _get_secret_key() -> str | None:
    """Prefer the current secret key and retain legacy service_role compatibility."""
    return _first_configured_env('SUPABASE_SECRET_KEY', 'SUPABASE_SERVICE_ROLE_KEY')


def get_supabase(
    *,
    fresh: bool = False,
    auth_storage=None,
    access_token: str | None = None,
):
    """Supabase 저권한 publishable/anon 클라이언트를 반환한다.

    이 함수의 싱글톤은 Auth 토큰 검증·로그인 같은 비-RLS 기반 작업과 명시적인
    공개 데이터에만 사용한다. 사용자 소유 RLS 데이터는 반드시
    ``get_user_supabase()``를 사용해야 한다. 인증 세션을 변경하는 작업은
    ``fresh=True``로 요청별 클라이언트를 사용해야 하며, 전역 인스턴스의 인증
    상태나 headers를 변경해서는 안 된다.
    """
    global _supabase_client

    url = os.getenv('SUPABASE_URL')
    key = _get_publishable_key()

    if not url or not key:
        return None

    if access_token is not None and not fresh:
        raise ValueError('access_token requires a fresh Supabase client')

    if auth_storage is not None:
        if not fresh:
            raise ValueError('auth_storage requires a fresh Supabase client')
        if access_token is not None:
            raise ValueError('auth_storage and access_token cannot be combined')
        from supabase import ClientOptions
        return _lazy_create_client(
            url,
            key,
            ClientOptions(
                auto_refresh_token=False,
                persist_session=True,
                flow_type='pkce',
                storage=auth_storage,
            ),
        )

    if fresh:
        # 요청이 끝난 뒤 supabase-py의 자동 refresh timer가 브라우저와 같은
        # 일회용 refresh token을 계속 회전하지 않게 세션 보존을 끈다.
        from supabase import ClientOptions
        options = ClientOptions(
            auto_refresh_token=False,
            persist_session=False,
        )
        if access_token is not None:
            if not isinstance(access_token, str) or not access_token.strip():
                raise ValueError('access_token must be a non-empty string')
            # 이 options 객체와 생성될 fresh client는 요청 하나에만 속한다.
            # 프로세스 전역 싱글톤의 headers/auth session은 절대 변경하지 않는다.
            options.headers = {
                **options.headers,
                'Authorization': f'Bearer {access_token}',
            }
        return _lazy_create_client(url, key, options)

    if _supabase_client is None:
        _supabase_client = _lazy_create_client(url, key)

    return _supabase_client


def get_validated_request_access_token() -> str | None:
    """검증 완료된 Flask 요청에서만 사용자 JWT를 반환한다.

    ``require_auth``가 토큰을 Supabase Auth로 검증한 뒤 ``g.user_id``와
    ``g.access_token``을 함께 설정한다. 두 값 중 하나라도 없으면 검증된 요청으로
    보지 않는다. 함수 밖으로 반환된 토큰을 로깅하거나 영속화해서는 안 된다.
    """
    from flask import g, has_request_context

    if not has_request_context():
        return None

    user_id = g.get('user_id')
    access_token = g.get('access_token')
    if not user_id or not isinstance(access_token, str) or not access_token.strip():
        return None
    return access_token


def get_user_supabase(*, validated_access_token: str | None = None):
    """RLS 사용자 데이터용 요청별 Supabase 클라이언트를 반환한다.

    Supabase가 활성화된 환경에서는 검증된 JWT 없이 anon 클라이언트로 폴백하지
    않는다. Flask 요청 안에서는 ``require_auth``가 설정한 토큰을 사용한다.
    요청 컨텍스트 밖의 작업은 호출자가 이미 검증한 토큰을
    ``validated_access_token``으로 명시적으로 넘겨야 한다.

    Supabase가 비활성화된 로컬/테스트 모드에서는 기존 동작처럼 ``None``을
    반환한다.
    """
    if not is_supabase_enabled():
        return None

    access_token = validated_access_token
    if access_token is None:
        access_token = get_validated_request_access_token()

    if not isinstance(access_token, str) or not access_token.strip():
        raise ConfigurationError(
            'RLS 데이터 접근에는 검증된 사용자 인증 토큰이 필요합니다.',
            config_key='SUPABASE_USER_JWT',
        )

    client = get_supabase(fresh=True, access_token=access_token)
    if client is None:
        raise ConfigurationError(
            'Supabase 사용자 클라이언트를 생성할 수 없습니다.',
            config_key='SUPABASE_URL',
        )
    return client


def get_service_supabase():
    """명시적인 백그라운드/관리 작업용 secret/service_role 클라이언트.

    사용자 JWT가 없는 작업이 anon 권한으로 실행되는 것을 막는다. 이 함수 호출은
    RLS 우회가 필요한 서버 전용 작업임을 코드에서 명시하며, service_role 설정이
    불완전하면 실패-폐쇄한다.
    """
    url = os.getenv('SUPABASE_URL')
    service_role_key = _get_secret_key()

    if not url and not service_role_key:
        return None
    if not url or not service_role_key:
        raise ConfigurationError(
            'Supabase secret/service_role 설정이 필요합니다.',
            config_key='SUPABASE_SECRET_KEY|SUPABASE_SERVICE_ROLE_KEY',
        )

    client = _get_admin_client()
    if client is None:
        raise ConfigurationError(
            'Supabase secret/service_role 클라이언트를 생성할 수 없습니다.',
            config_key='SUPABASE_SECRET_KEY|SUPABASE_SERVICE_ROLE_KEY',
        )
    return client


def is_supabase_enabled() -> bool:
    """Supabase 활성화 여부 (환경변수 기반)."""
    return bool(os.getenv('SUPABASE_URL') and _get_publishable_key())


def _get_admin_client():
    """Supabase Admin 클라이언트 (secret/service_role key)."""
    global _supabase_admin

    if _supabase_admin is None:
        url = os.getenv('SUPABASE_URL')
        service_role_key = _get_secret_key()

        if not url or not service_role_key:
            logger.warning(
                "SUPABASE_SECRET_KEY/SUPABASE_SERVICE_ROLE_KEY 미설정 - "
                "admin 기능 비활성화"
            )
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
            raise ConfigurationError(
                "ENCRYPTION_SECRET 환경변수가 필요합니다. "
                "API 키 암호화를 위해 설정해주세요.",
                config_key='ENCRYPTION_SECRET',
            )

        key = hashlib.sha256(secret.encode()).digest()
        _fernet_instance = Fernet(base64.urlsafe_b64encode(key))

    return _fernet_instance


def encrypt_api_key(api_key: str) -> str:
    """API 키 암호화. 비활성화 시 원본 반환."""
    if not api_key:
        return None
    if not _is_encryption_enabled():
        logger.debug("암호화 비활성화 상태, 원본 저장")
        return api_key
    try:
        return _get_fernet().encrypt(api_key.encode()).decode()
    except ConfigurationError:
        logger.warning("암호화 설정 오류, 원본 저장")
        return api_key


def decrypt_api_key(encrypted_key: str) -> str:
    """API 키 복호화. 비활성화 시 원본 반환."""
    if not encrypted_key:
        return None
    if not _is_encryption_enabled():
        return encrypted_key
    try:
        return _get_fernet().decrypt(encrypted_key.encode()).decode()
    except ConfigurationError:
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
    "get_user_supabase",
    "get_service_supabase",
    "get_validated_request_access_token",
    "is_supabase_enabled",
    "_get_admin_client",
    "_lazy_create_client",
    "encrypt_api_key",
    "decrypt_api_key",
    "_is_encryption_enabled",
    "_get_fernet",
    "reset_clients_for_test",
]
