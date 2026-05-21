"""
API 키 발급/관리 서비스
사용자별 API 키 CRUD + 사용량 추적

Phase 2-f: 내부 구현을 `SupabaseApiKeyVault`(Identity & Access BC) 어댑터로 위임.
외부 API 시그니처/반환 형식/예외 동작은 100% 호환 유지.

기존 책임:
- IE 자체 발급 API 키 (`ie_xxx`) 의 해시 기반 CRUD/검증
- Supabase 활성 시 `ie_user_api_keys` 사용, 비활성 시 로컬 JSON 폴백

Vault 위임 정책:
- `create_key`/`revoke_key` 의 부수 효과 (마스킹된 ApiKey 도메인 객체 생성) 를
  SupabaseApiKeyVault 의 `store`/`revoke` 로 best-effort 위임 (예외는 격리).
- `key_hash` 기반 검증/조회 (`validate_key`, `list_keys`) 는 Vault 가 지원하지
  않는 도메인이므로 본 파일에서 직접 Supabase 호출 유지.
- 환경변수 폴백은 두 곳에 독립적으로 유지 (Vault 비활성 ↔ 본 서비스 폴백).
"""
import json
import os
import secrets
import hashlib
from datetime import datetime, timezone

from services.data.supabase_service import is_supabase_enabled, get_supabase
from services.core.logging_config import ServiceLogger
import logging

logger = ServiceLogger('ApiKeyService')

_LOCAL_API_KEYS_FILE = os.path.join(
    os.path.dirname(__file__), '..', 'data', 'user_api_keys.json'
)


def _load_local() -> dict:
    if os.path.exists(_LOCAL_API_KEYS_FILE):
        with open(_LOCAL_API_KEYS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def _save_local(data: dict):
    os.makedirs(os.path.dirname(_LOCAL_API_KEYS_FILE), exist_ok=True)
    with open(_LOCAL_API_KEYS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _generate_api_key() -> str:
    """ie_ 접두사 API 키 생성"""
    return f"ie_{secrets.token_urlsafe(32)}"


def _hash_key(key: str) -> str:
    """API 키 해시 (저장용)"""
    return hashlib.sha256(key.encode()).hexdigest()


def _mask_key(key: str) -> str:
    """API 키 마스킹 (조회용)"""
    if len(key) <= 10:
        return '****'
    return f"{key[:7]}...{key[-4:]}"


# ---------------------------------------------------------------------------
# Vault 위임 헬퍼 (Identity & Access BC 어댑터)
# ---------------------------------------------------------------------------

def _get_vault():
    """SupabaseApiKeyVault 인스턴스를 lazy 로 생성.

    Vault 모듈 import 실패 또는 인스턴스화 실패 시 None 반환 → 기존 로컬 로직 유지.
    예외는 본 서비스의 외부 계약에 영향이 없어야 하므로 격리한다.
    """
    try:
        from src.contexts.identity.infrastructure.supabase_api_key_vault import (
            SupabaseApiKeyVault,
        )
        return SupabaseApiKeyVault()
    except Exception as e:  # noqa: BLE001 — Vault 가용성은 best-effort
        logger.debug("Vault 인스턴스화 실패 (격리): %s", e)
        return None


def _vault_store_safe(user_id: str, name: str, raw_key: str) -> None:
    """Vault.store 호출을 best-effort 로 수행.

    반환값(ApiKey 도메인 객체)은 외부 계약에서 노출되지 않으므로 무시한다.
    외부 시그니처/응답은 본 모듈의 기존 dict 그대로 유지된다.
    """
    vault = _get_vault()
    if vault is None:
        return
    try:
        # 본 서비스는 IE 자체 발급 키이므로 provider="ie", label=사용자 지정 name.
        vault.store(
            account_id=user_id,
            provider='ie',
            plaintext_key=raw_key,
            label=name or 'default',
        )
    except Exception as e:  # noqa: BLE001 — 외부 계약 보호
        logger.debug("Vault.store 위임 실패 (격리): %s", e)


def _vault_revoke_safe(user_id: str, name: str) -> None:
    """Vault.revoke 호출을 best-effort 로 수행."""
    vault = _get_vault()
    if vault is None:
        return
    try:
        vault.revoke(
            account_id=user_id,
            provider='ie',
            label=name or 'default',
        )
    except Exception as e:  # noqa: BLE001 — 외부 계약 보호
        logger.debug("Vault.revoke 위임 실패 (격리): %s", e)


class ApiKeyService:
    """사용자 API 키 관리"""

    @staticmethod
    def create_key(user_id: str, name: str = 'default') -> dict:
        """
        새 API 키 발급

        Returns:
            {'key': str, 'key_id': str, 'name': str}
            키는 생성 시에만 전체 값 반환 (이후 마스킹)
        """
        try:
            raw_key = _generate_api_key()
            key_hash = _hash_key(raw_key)
            now = datetime.now(timezone.utc).isoformat()

            key_data = {
                'user_id': user_id,
                'name': name,
                'key_hash': key_hash,
                'key_prefix': raw_key[:7],
                'usage_count': 0,
                'created_at': now,
                'last_used_at': None,
                'is_active': True,
            }

            if is_supabase_enabled():
                try:
                    client = get_supabase()
                    result = client.table('ie_user_api_keys').insert(key_data).execute()
                    key_id = result.data[0]['id'] if result.data else key_hash[:12]
                    # Vault 어댑터에 동등한 마스킹 객체 등록 (best-effort)
                    _vault_store_safe(user_id, name, raw_key)
                    return {'key': raw_key, 'key_id': key_id, 'name': name}
                except Exception as e:
                    logger.error(f"API 키 생성 실패: {e}")
                    return {'error': str(e)}

            # 로컬 폴백
            data = _load_local()
            user_keys = data.get(user_id, [])
            key_id = key_hash[:12]
            key_data['id'] = key_id
            user_keys.append(key_data)
            data[user_id] = user_keys
            _save_local(data)
            # 로컬 모드에서도 Vault 위임 (Supabase 비활성 시 Vault 도 메모리 no-op)
            _vault_store_safe(user_id, name, raw_key)
            return {'key': raw_key, 'key_id': key_id, 'name': name}
        except Exception as e:
            logger.error("create_key 실패: %s", e, exc_info=True)
            return {}

    @staticmethod
    def list_keys(user_id: str) -> list:
        """
        사용자 API 키 목록 (마스킹됨)

        Returns:
            [{'key_id': str, 'name': str, 'key_preview': str, 'usage_count': int, ...}]

        Note:
            Vault 어댑터는 단일 키 (provider, label) 단위 reveal/store/revoke 만 지원하므로
            목록 조회는 본 파일에서 직접 Supabase 를 호출한다. (작업 지시에 따른 의도된 분리)
        """
        try:
            if is_supabase_enabled():
                try:
                    client = get_supabase()
                    result = client.table('ie_user_api_keys').select(
                        'id, name, key_prefix, usage_count, created_at, last_used_at, is_active'
                    ).eq('user_id', user_id).eq('is_active', True).execute()
                    return [
                        {
                            'key_id': k['id'],
                            'name': k.get('name', 'default'),
                            'key_preview': f"{k['key_prefix']}...****",
                            'usage_count': k.get('usage_count', 0),
                            'created_at': k.get('created_at', ''),
                            'last_used_at': k.get('last_used_at'),
                        }
                        for k in (result.data or [])
                    ]
                except Exception as e:
                    logger.error(f"API 키 목록 조회 실패: {e}")

            # 로컬 폴백
            data = _load_local()
            user_keys = data.get(user_id, [])
            return [
                {
                    'key_id': k.get('id', ''),
                    'name': k.get('name', 'default'),
                    'key_preview': f"{k.get('key_prefix', '???')}...****",
                    'usage_count': k.get('usage_count', 0),
                    'created_at': k.get('created_at', ''),
                    'last_used_at': k.get('last_used_at'),
                }
                for k in user_keys if k.get('is_active', True)
            ]
        except Exception as e:
            logger.error("list_keys 실패: %s", e, exc_info=True)
            return []

    @staticmethod
    def revoke_key(user_id: str, key_id: str) -> bool:
        """API 키 비활성화"""
        try:
            if is_supabase_enabled():
                try:
                    client = get_supabase()
                    # Vault 위임을 위해 비활성화 대상의 name(label) 조회
                    try:
                        target = client.table('ie_user_api_keys').select('name') \
                            .eq('id', key_id).eq('user_id', user_id).maybe_single().execute()
                        target_name = (target.data or {}).get('name', 'default')
                    except Exception:
                        target_name = 'default'

                    client.table('ie_user_api_keys').update({'is_active': False}) \
                        .eq('id', key_id).eq('user_id', user_id).execute()
                    _vault_revoke_safe(user_id, target_name)
                    return True
                except Exception as e:
                    logger.error(f"API 키 삭제 실패: {e}")
                    return False

            # 로컬 폴백
            data = _load_local()
            user_keys = data.get(user_id, [])
            for k in user_keys:
                if k.get('id') == key_id:
                    k['is_active'] = False
                    _save_local(data)
                    _vault_revoke_safe(user_id, k.get('name', 'default'))
                    return True
            return False
        except Exception as e:
            logger.error("revoke_key 실패: %s", e, exc_info=True)
            return False

    @staticmethod
    def validate_key(raw_key: str) -> dict | None:
        """
        API 키 검증 — 유효하면 사용자 정보 반환

        Returns:
            {'user_id': str, 'name': str} 또는 None

        Note:
            검증은 key_hash 기반 역조회가 필요한데 Vault 어댑터는 (account_id, provider, label)
            기반 reveal 만 제공하므로 위임 불가능 — 본 파일에서 기존 로직 유지.
        """
        try:
            key_hash = _hash_key(raw_key)

            if is_supabase_enabled():
                try:
                    client = get_supabase()
                    result = client.table('ie_user_api_keys').select('user_id, name') \
                        .eq('key_hash', key_hash).eq('is_active', True).maybe_single().execute()
                    if result.data:
                        # 사용 횟수 증가 + last_used_at 업데이트
                        now = datetime.now(timezone.utc).isoformat()
                        client.table('ie_user_api_keys').update({
                            'last_used_at': now,
                        }).eq('key_hash', key_hash).execute()
                        # usage_count는 RPC 또는 트리거로 증가하는 게 이상적이나, 간단히 처리
                        return {
                            'user_id': result.data['user_id'],
                            'name': result.data.get('name', 'default'),
                        }
                except Exception as e:
                    logger.error(f"API 키 검증 실패: {e}")
                    return None

            # 로컬 폴백
            data = _load_local()
            for user_id, keys in data.items():
                for k in keys:
                    if k.get('key_hash') == key_hash and k.get('is_active', True):
                        k['usage_count'] = k.get('usage_count', 0) + 1
                        k['last_used_at'] = datetime.now(timezone.utc).isoformat()
                        _save_local(data)
                        return {'user_id': user_id, 'name': k.get('name', 'default')}
            return None
        except Exception as e:
            logger.error("validate_key 실패: %s", e, exc_info=True)
            return {}


api_key_service = ApiKeyService()
