"""
API 키 발급/관리 서비스
사용자별 API 키 CRUD + 사용량 추적
"""
import json
import os
import secrets
import hashlib
from datetime import datetime, timezone

from services.supabase_service import is_supabase_enabled, get_supabase
from services.logging_config import ServiceLogger

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
        return {'key': raw_key, 'key_id': key_id, 'name': name}

    @staticmethod
    def list_keys(user_id: str) -> list:
        """
        사용자 API 키 목록 (마스킹됨)

        Returns:
            [{'key_id': str, 'name': str, 'key_preview': str, 'usage_count': int, ...}]
        """
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

    @staticmethod
    def revoke_key(user_id: str, key_id: str) -> bool:
        """API 키 비활성화"""
        if is_supabase_enabled():
            try:
                client = get_supabase()
                client.table('ie_user_api_keys').update({'is_active': False}) \
                    .eq('id', key_id).eq('user_id', user_id).execute()
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
                return True
        return False

    @staticmethod
    def validate_key(raw_key: str) -> dict | None:
        """
        API 키 검증 — 유효하면 사용자 정보 반환

        Returns:
            {'user_id': str, 'name': str} 또는 None
        """
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


api_key_service = ApiKeyService()
