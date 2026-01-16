"""
Supabase 서비스 모듈
데이터베이스 연동 및 사용자 인증 처리
"""
import os
import base64
import hashlib
from functools import wraps
from flask import request, jsonify, g
from supabase import create_client, Client
from cryptography.fernet import Fernet

from services.logging_config import supabase_logger as logger
from services.exceptions import (
    ConfigurationError, AuthenticationError,
    TokenExpiredError, TokenInvalidError
)

# Supabase 클라이언트 초기화
_supabase_client: Client = None
_fernet_instance: Fernet = None
_encryption_enabled: bool = None  # 암호화 활성화 여부


def get_supabase() -> Client:
    """Supabase 클라이언트 싱글톤"""
    global _supabase_client

    if _supabase_client is None:
        url = os.getenv('SUPABASE_URL')
        key = os.getenv('SUPABASE_ANON_KEY')

        if not url or not key:
            return None

        _supabase_client = create_client(url, key)

    return _supabase_client


def is_supabase_enabled() -> bool:
    """Supabase가 활성화되어 있는지 확인"""
    return bool(os.getenv('SUPABASE_URL') and os.getenv('SUPABASE_ANON_KEY'))


def _is_encryption_enabled() -> bool:
    """암호화 활성화 여부 확인"""
    global _encryption_enabled
    if _encryption_enabled is None:
        secret = os.getenv('ENCRYPTION_SECRET')
        _encryption_enabled = bool(secret and secret.strip())
        if not _encryption_enabled:
            logger.warning("ENCRYPTION_SECRET이 설정되지 않았습니다. API 키 암호화가 비활성화됩니다.")
    return _encryption_enabled


def _get_fernet() -> Fernet:
    """Fernet 인스턴스 싱글톤 (암호화용)

    Raises:
        ConfigurationError: ENCRYPTION_SECRET 환경변수가 설정되지 않은 경우
    """
    global _fernet_instance

    if _fernet_instance is None:
        secret = os.getenv('ENCRYPTION_SECRET')

        if not secret or not secret.strip():
            raise ConfigurationError(
                "ENCRYPTION_SECRET 환경변수가 필요합니다. API 키 암호화를 위해 설정해주세요.",
                config_key='ENCRYPTION_SECRET'
            )

        key = hashlib.sha256(secret.encode()).digest()
        _fernet_instance = Fernet(base64.urlsafe_b64encode(key))

    return _fernet_instance


def encrypt_api_key(api_key: str) -> str:
    """API 키 암호화

    암호화가 비활성화된 경우 원본 반환 (개발 환경용)
    """
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
    """API 키 복호화

    암호화가 비활성화된 경우 원본 반환
    """
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

# =============================================
# 인증 헬퍼 및 데코레이터
# =============================================

def _extract_bearer_token() -> str:
    """Authorization 헤더에서 Bearer 토큰 추출"""
    auth_header = request.headers.get('Authorization', '')
    return auth_header[7:] if auth_header.startswith('Bearer ') else None


def _validate_token(token: str) -> dict:
    """토큰 검증 및 g 객체에 사용자 정보 설정

    Returns:
        dict: {'valid': bool, 'error': str|None, 'code': str|None}
    """
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user(token)
        g.user_id = user.user.id
        g.access_token = token
        return {'valid': True, 'error': None, 'code': None}
    except Exception as e:
        error_str = str(e).lower()

        # 토큰 만료 감지
        if 'expired' in error_str or 'token has expired' in error_str:
            logger.debug("토큰 만료")
            return {'valid': False, 'error': '인증 토큰이 만료되었습니다.', 'code': 'TOKEN_EXPIRED'}

        # 무효 토큰 감지
        if 'invalid' in error_str or 'malformed' in error_str:
            logger.debug("무효 토큰")
            return {'valid': False, 'error': '유효하지 않은 토큰입니다.', 'code': 'TOKEN_INVALID'}

        # 기타 인증 오류
        logger.warning(f"토큰 검증 실패: {e}")
        return {'valid': False, 'error': '인증에 실패했습니다.', 'code': 'AUTH_FAILED'}


def require_auth(f):
    """JWT 토큰 검증 데코레이터"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_supabase_enabled():
            g.user_id = None
            return f(*args, **kwargs)

        token = _extract_bearer_token()
        if not token:
            return jsonify({'error': '인증이 필요합니다.', 'code': 'AUTH_REQUIRED'}), 401

        result = _validate_token(token)
        if not result['valid']:
            return jsonify({'error': result['error'], 'code': result['code']}), 401

        return f(*args, **kwargs)
    return decorated


def optional_auth(f):
    """선택적 인증 (로그인 안해도 사용 가능)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        g.user_id = None
        g.access_token = None

        if not is_supabase_enabled():
            return f(*args, **kwargs)

        token = _extract_bearer_token()
        if token:
            _validate_token(token)  # 실패해도 무시 (결과 사용 안 함)

        return f(*args, **kwargs)
    return decorated

# =============================================
# 히스토리 CRUD
# =============================================

def _db_operation(operation_name: str, default_return, operation_func):
    """DB 작업 공통 래퍼 (에러 핸들링 통합)"""
    try:
        return operation_func()
    except Exception as e:
        logger.error(f"{operation_name} 오류: {e}")
        return default_return


def save_history(user_id: str, data: dict) -> dict:
    """분석 히스토리 저장"""
    supabase = get_supabase()
    if not supabase or not user_id:
        return None

    def operation():
        result = supabase.table('ie_histories').insert({
            'user_id': user_id,
            'report_id': data.get('id'),
            'url': data.get('url'),
            'title': data.get('title'),
            'style': data.get('style'),
            'content': data.get('content'),
            'html': data.get('html'),
            'transcript': data.get('transcript'),
            'mindmap_markdown': data.get('mindmapMarkdown'),
            'usage': data.get('usage'),
            'elapsed_time': data.get('elapsed_time')
        }).execute()
        return result.data[0] if result.data else None

    return _db_operation('History save', None, operation)


def get_histories(user_id: str, limit: int = 50) -> list:
    """사용자 히스토리 조회"""
    supabase = get_supabase()
    if not supabase or not user_id:
        return []

    def operation():
        result = supabase.table('ie_histories') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .limit(limit) \
            .execute()
        return result.data or []

    return _db_operation('History fetch', [], operation)


def update_history(user_id: str, report_id: str, updates: dict) -> bool:
    """히스토리 업데이트 (마인드맵 캐싱 등)"""
    supabase = get_supabase()
    if not supabase or not user_id:
        return False

    def operation():
        supabase.table('ie_histories') \
            .update(updates) \
            .eq('user_id', user_id) \
            .eq('report_id', report_id) \
            .execute()
        return True

    return _db_operation('History update', False, operation)


def delete_history(user_id: str, report_id: str) -> bool:
    """히스토리 삭제"""
    supabase = get_supabase()
    if not supabase or not user_id:
        return False

    def operation():
        supabase.table('ie_histories') \
            .delete() \
            .eq('user_id', user_id) \
            .eq('report_id', report_id) \
            .execute()
        return True

    return _db_operation('History delete', False, operation)

# =============================================
# API 키 관리
# =============================================

# API 키 필드 매핑 (프론트엔드 키 -> DB 컬럼명)
_API_KEY_FIELDS = ['openai', 'anthropic', 'google', 'zhipu', 'deepseek', 'supadata']


def save_api_keys(user_id: str, keys: dict) -> bool:
    """API 키 저장 (암호화)"""
    supabase = get_supabase()
    if not supabase or not user_id:
        return False

    def operation():
        encrypted_data = {'user_id': user_id, 'selected_provider': keys.get('selectedProvider')}
        for field in _API_KEY_FIELDS:
            encrypted_data[f'{field}_key'] = encrypt_api_key(keys.get(field))

        supabase.table('ie_api_keys').upsert(encrypted_data).execute()
        return True

    return _db_operation('API keys save', False, operation)


def get_api_keys(user_id: str) -> dict:
    """API 키 조회 (복호화)"""
    supabase = get_supabase()
    if not supabase or not user_id:
        return {}

    def operation():
        result = supabase.table('ie_api_keys') \
            .select('*') \
            .eq('user_id', user_id) \
            .limit(1) \
            .execute()

        if not result.data or len(result.data) == 0:
            return {}

        data = result.data[0]
        decrypted = {'selectedProvider': data.get('selected_provider')}
        for field in _API_KEY_FIELDS:
            decrypted[field] = decrypt_api_key(data.get(f'{field}_key'))

        return decrypted

    return _db_operation('API keys fetch', {}, operation)

# =============================================
# 커스텀 스타일 관리
# =============================================

def save_custom_style(user_id: str, style: dict) -> bool:
    """커스텀 스타일 저장"""
    supabase = get_supabase()
    if not supabase or not user_id:
        return False

    def operation():
        supabase.table('ie_custom_styles').upsert({
            'user_id': user_id,
            'style_id': style.get('id'),
            'name': style.get('name'),
            'icon': style.get('icon', 'edit_note'),
            'prompt': style.get('prompt')
        }).execute()
        return True

    return _db_operation('Custom style save', False, operation)


def get_custom_styles(user_id: str) -> list:
    """커스텀 스타일 조회"""
    supabase = get_supabase()
    if not supabase or not user_id:
        return []

    def operation():
        result = supabase.table('ie_custom_styles') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('created_at') \
            .execute()

        return [{
            'id': s['style_id'],
            'name': s['name'],
            'icon': s['icon'],
            'prompt': s['prompt']
        } for s in (result.data or [])]

    return _db_operation('Custom styles fetch', [], operation)


def delete_custom_style(user_id: str, style_id: str) -> bool:
    """커스텀 스타일 삭제"""
    supabase = get_supabase()
    if not supabase or not user_id:
        return False

    def operation():
        supabase.table('ie_custom_styles') \
            .delete() \
            .eq('user_id', user_id) \
            .eq('style_id', style_id) \
            .execute()
        return True

    return _db_operation('Custom style delete', False, operation)

# =============================================
# 사용량 관리
# =============================================

MAX_USAGE_COUNT = 5  # 기본 최대 사용 횟수 (하루 5회)


def get_usage(user_id: str) -> dict:
    """사용자 사용량 조회. 없으면 새로 생성."""
    supabase = get_supabase()
    if not supabase or not user_id:
        return {'usage_count': 0, 'max_usage': MAX_USAGE_COUNT, 'can_use': False}

    def operation():
        from datetime import date

        # 사용량 조회 (.single() 대신 .limit(1) 사용하여 에러 방지)
        result = supabase.table('ie_usage') \
            .select('*') \
            .eq('user_id', user_id) \
            .limit(1) \
            .execute()

        if result.data and len(result.data) > 0:
            data = result.data[0]
            # 날짜가 바뀌면 사용량 리셋
            last_reset = data.get('last_reset_date')
            today = date.today().isoformat()

            if last_reset != today:
                # 사용량 리셋
                supabase.table('ie_usage') \
                    .update({
                        'usage_count': MAX_USAGE_COUNT,
                        'last_reset_date': today,
                        'updated_at': 'now()'
                    }) \
                    .eq('user_id', user_id) \
                    .execute()
                return {
                    'usage_count': MAX_USAGE_COUNT,
                    'max_usage': data.get('max_usage', MAX_USAGE_COUNT),
                    'can_use': True
                }

            return {
                'usage_count': data.get('usage_count', 0),
                'max_usage': data.get('max_usage', MAX_USAGE_COUNT),
                'can_use': data.get('usage_count', 0) > 0
            }

        # 새 사용자: 레코드 생성
        supabase.table('ie_usage').insert({
            'user_id': user_id,
            'usage_count': MAX_USAGE_COUNT,
            'max_usage': MAX_USAGE_COUNT,
            'last_reset_date': date.today().isoformat()
        }).execute()

        return {
            'usage_count': MAX_USAGE_COUNT,
            'max_usage': MAX_USAGE_COUNT,
            'can_use': True
        }

    return _db_operation('Usage fetch', {'usage_count': 0, 'max_usage': MAX_USAGE_COUNT, 'can_use': False}, operation)


def decrement_usage(user_id: str) -> bool:
    """사용량 1 차감. 성공 시 True 반환."""
    supabase = get_supabase()
    if not supabase or not user_id:
        return False

    def operation():
        # 현재 사용량 확인
        result = supabase.table('ie_usage') \
            .select('usage_count') \
            .eq('user_id', user_id) \
            .limit(1) \
            .execute()

        if not result.data or len(result.data) == 0 or result.data[0].get('usage_count', 0) <= 0:
            return False

        # 차감
        new_count = result.data[0]['usage_count'] - 1
        supabase.table('ie_usage') \
            .update({
                'usage_count': new_count,
                'updated_at': 'now()'
            }) \
            .eq('user_id', user_id) \
            .execute()

        return True

    return _db_operation('Usage decrement', False, operation)

# =============================================
# 관리자 관리
# =============================================

def is_admin(user_id: str) -> bool:
    """사용자가 관리자인지 확인"""
    supabase = get_supabase()
    if not supabase or not user_id:
        logger.warning(f"is_admin: supabase={supabase is not None}, user_id={user_id[:8] if user_id else None}")
        return False

    def operation():
        result = supabase.table('ie_admins') \
            .select('user_id') \
            .eq('user_id', user_id) \
            .limit(1) \
            .execute()
        is_admin_user = bool(result.data and len(result.data) > 0)
        logger.info(f"is_admin check: user_id={user_id[:8]}..., result.data={result.data}, is_admin={is_admin_user}")
        return is_admin_user

    result = _db_operation('Admin check', False, operation)
    logger.info(f"is_admin final result for {user_id[:8] if user_id else None}: {result}")
    return result


def get_admin_permissions(user_id: str) -> dict:
    """관리자 권한 조회"""
    supabase = get_supabase()
    if not supabase or not user_id:
        return {}

    def operation():
        result = supabase.table('ie_admins') \
            .select('permissions') \
            .eq('user_id', user_id) \
            .limit(1) \
            .execute()
        return result.data[0].get('permissions', {}) if result.data and len(result.data) > 0 else {}

    return _db_operation('Admin permissions', {}, operation)


def get_all_users_usage() -> list:
    """모든 사용자의 사용량 조회 (관리자용)"""
    supabase = get_supabase()
    if not supabase:
        return []

    def operation():
        result = supabase.table('ie_usage') \
            .select('*') \
            .order('usage_count', desc=False) \
            .execute()
        return result.data or []

    return _db_operation('All users usage', [], operation)


def reset_user_usage(user_id: str) -> bool:
    """특정 사용자 사용량 리셋 (관리자용)"""
    supabase = get_supabase()
    if not supabase or not user_id:
        return False

    def operation():
        from datetime import date
        supabase.table('ie_usage') \
            .update({
                'usage_count': MAX_USAGE_COUNT,
                'last_reset_date': date.today().isoformat(),
                'updated_at': 'now()'
            }) \
            .eq('user_id', user_id) \
            .execute()
        return True

    return _db_operation('Reset user usage', False, operation)


def get_usage_stats() -> dict:
    """사용량 통계 조회 (관리자용)"""
    supabase = get_supabase()
    if not supabase:
        return {}

    def operation():
        # 전체 사용자 수
        users_result = supabase.table('ie_usage').select('user_id', count='exact').execute()
        total_users = users_result.count or 0

        # 오늘 사용한 사용자 수
        from datetime import date
        today = date.today().isoformat()
        active_result = supabase.table('ie_usage') \
            .select('user_id', count='exact') \
            .eq('last_reset_date', today) \
            .lt('usage_count', MAX_USAGE_COUNT) \
            .execute()
        active_today = active_result.count or 0

        # 사용량 소진 사용자 수
        exhausted_result = supabase.table('ie_usage') \
            .select('user_id', count='exact') \
            .eq('usage_count', 0) \
            .execute()
        exhausted_users = exhausted_result.count or 0

        return {
            'total_users': total_users,
            'active_today': active_today,
            'exhausted_users': exhausted_users,
            'max_usage': MAX_USAGE_COUNT
        }

    return _db_operation('Usage stats', {}, operation)
