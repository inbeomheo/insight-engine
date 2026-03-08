"""
Supabase 서비스 모듈
데이터베이스 연동 및 사용자 인증 처리
"""
import os
import base64
import hashlib
from functools import wraps
from typing import Callable
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
_supabase_admin: Client = None  # Admin 클라이언트 (service_role key)
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
    """Supabase 비활성 (로컬 전용 모드)."""
    return False


def _get_admin_client() -> Client:
    """Supabase Admin 클라이언트 (service_role key - 계정 삭제 등)"""
    global _supabase_admin

    if _supabase_admin is None:
        url = os.getenv('SUPABASE_URL')
        service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not url or not service_role_key:
            logger.warning("SUPABASE_SERVICE_ROLE_KEY 미설정 - admin 기능 비활성화")
            return None

        _supabase_admin = create_client(url, service_role_key)

    return _supabase_admin


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


def require_auth(f: Callable) -> Callable:
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


def optional_auth(f: Callable) -> Callable:
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
    """분석 히스토리 저장

    P3 버그 #12: user_id가 None이면 저장하지 않고 None 반환 (의도된 동작)
    - 비로그인 사용자는 클라우드 저장 생략
    - 로컬 스토리지에서 별도 관리됨
    """
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
            'transcript_source': data.get('transcript_source'),
            'mindmap_markdown': data.get('mindmapMarkdown'),
            'keywords': data.get('keywords', []),
            'usage': data.get('usage'),
            'elapsed_time': data.get('elapsed_time')
        }).execute()
        return result.data[0] if result.data else None

    return _db_operation('History save', None, operation)


def get_histories(user_id: str, page: int = 1, per_page: int = 20) -> dict:
    """사용자 히스토리 조회 (페이지네이션 지원)
    - 관리자: 모든 사용자의 히스토리
    - 일반 사용자: 본인 히스토리만

    Returns:
        dict: {
            'histories': [...],
            'total': int,
            'page': int,
            'per_page': int,
            'total_pages': int,
            'has_more': bool
        }
    """
    supabase = get_supabase()
    if not supabase or not user_id:
        return {'histories': [], 'total': 0, 'page': 1, 'per_page': per_page, 'total_pages': 0, 'has_more': False}

    def operation():
        is_admin_user = is_admin(user_id)

        # 1. 전체 개수 조회
        count_query = supabase.table('ie_histories').select('report_id', count='exact')
        if not is_admin_user:
            count_query = count_query.eq('user_id', user_id)
        count_result = count_query.execute()
        total = count_result.count or 0

        # 2. 페이지네이션 계산
        offset = (page - 1) * per_page
        total_pages = (total + per_page - 1) // per_page if total > 0 else 0

        # 3. 데이터 조회
        query = supabase.table('ie_histories').select('*')
        if not is_admin_user:
            query = query.eq('user_id', user_id)

        result = query.order('created_at', desc=True).range(offset, offset + per_page - 1).execute()
        histories = result.data or []

        return {
            'histories': histories,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': total_pages,
            'has_more': page < total_pages
        }

    return _db_operation('History fetch', {'histories': [], 'total': 0, 'page': 1, 'per_page': per_page, 'total_pages': 0, 'has_more': False}, operation)


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


def toggle_favorite(user_id: str, report_id: str) -> dict:
    """히스토리 즐겨찾기 토글"""
    supabase = get_supabase()
    if not supabase or not user_id:
        return {'success': False, 'error': 'Not authenticated'}

    def operation():
        # 현재 상태 조회
        result = supabase.table('ie_histories') \
            .select('is_favorite') \
            .eq('user_id', user_id) \
            .eq('report_id', report_id) \
            .limit(1) \
            .execute()

        if not result.data:
            return {'success': False, 'error': 'History not found'}

        current = result.data[0].get('is_favorite', False)
        new_value = not current

        supabase.table('ie_histories') \
            .update({'is_favorite': new_value}) \
            .eq('user_id', user_id) \
            .eq('report_id', report_id) \
            .execute()

        return {'success': True, 'is_favorite': new_value}

    return _db_operation('Toggle favorite', {'success': False}, operation)


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


def delete_user_account(user_id: str) -> bool:
    """사용자 계정 완전 삭제 (admin)

    auth.users 삭제 → CASCADE로 ie_* 테이블 자동 정리.
    """
    try:
        admin = _get_admin_client()
        if not admin:
            logger.error("Admin client 미초기화 - 계정 삭제 불가")
            return False

        admin.auth.admin.delete_user(user_id)
        logger.info(f"계정 삭제 완료: user_id={user_id}")
        return True
    except Exception as e:
        logger.error(f"계정 삭제 실패: user_id={user_id}, error={e}")
        return False


def update_user_profile(user_id: str, display_name: str) -> dict:
    """사용자 프로필(닉네임) 업데이트 (admin API)"""
    try:
        admin = _get_admin_client()
        if not admin:
            return {'success': False, 'error': 'Admin client 미초기화'}

        result = admin.auth.admin.update_user_by_id(
            user_id,
            {'user_metadata': {'display_name': display_name}}
        )
        logger.info(f"프로필 업데이트 완료: user_id={user_id}")
        return {'success': True, 'user': {'id': result.user.id, 'email': result.user.email,
                'user_metadata': result.user.user_metadata}}
    except Exception as e:
        logger.error(f"프로필 업데이트 실패: user_id={user_id}, error={e}")
        return {'success': False, 'error': str(e)}


def update_user_password(user_id: str, new_password: str) -> dict:
    """사용자 비밀번호 변경 (admin API)"""
    try:
        admin = _get_admin_client()
        if not admin:
            return {'success': False, 'error': 'Admin client 미초기화'}

        admin.auth.admin.update_user_by_id(
            user_id,
            {'password': new_password}
        )
        logger.info(f"비밀번호 변경 완료: user_id={user_id}")
        return {'success': True}
    except Exception as e:
        logger.error(f"비밀번호 변경 실패: user_id={user_id}, error={e}")
        return {'success': False, 'error': str(e)}


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

MAX_USAGE_COUNT = 20  # 기본 최대 사용 횟수 (하루 20회)


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
    """사용량 1 차감. 원자적 RPC 함수 사용으로 Race Condition 방지."""
    supabase = get_supabase()
    if not supabase or not user_id:
        return False

    def operation():
        # 원자적 차감 (Race Condition 방지)
        try:
            result = supabase.rpc('decrement_usage_safe', {'p_user_id': user_id}).execute()
            if result.data:
                return result.data.get('success', False)
            return False
        except Exception as e:
            # RPC 함수가 없는 경우 기존 방식으로 폴백 (하위 호환성)
            import logging
            logging.warning(f"decrement_usage_safe RPC 실패, 폴백 사용: {e}")

            # 폴백: 기존 방식 (Race Condition 가능성 있음)
            result = supabase.table('ie_usage') \
                .select('usage_count') \
                .eq('user_id', user_id) \
                .limit(1) \
                .execute()

            if not result.data or len(result.data) == 0 or result.data[0].get('usage_count', 0) <= 0:
                return False

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
        return False

    def operation():
        result = supabase.table('ie_admins') \
            .select('user_id') \
            .eq('user_id', user_id) \
            .limit(1) \
            .execute()
        return bool(result.data and len(result.data) > 0)

    return _db_operation('Admin check', False, operation)


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
    """모든 사용자의 사용량 조회 (관리자용) - 이메일 포함"""
    supabase = get_supabase()
    if not supabase:
        return []

    def operation():
        # view를 사용하여 이메일 포함 조회
        result = supabase.table('ie_usage_with_email') \
            .select('user_id, usage_count, last_reset_date, email') \
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


def get_all_contents(page: int = 1, per_page: int = 20, user_id: str = None) -> dict:
    """모든 사용자의 생성 콘텐츠 조회 (관리자용)

    Args:
        page: 페이지 번호
        per_page: 페이지당 항목 수
        user_id: 특정 사용자 필터 (None이면 전체)
    """
    supabase = get_supabase()
    if not supabase:
        return {'contents': [], 'total': 0}

    def operation():
        # 전체 개수 쿼리
        count_query = supabase.table('ie_histories').select('report_id', count='exact')
        if user_id:
            count_query = count_query.eq('user_id', user_id)
        count_result = count_query.execute()
        total = count_result.count or 0

        # 페이지네이션 - view를 사용하여 이메일 포함 조회
        offset = (page - 1) * per_page
        query = supabase.table('ie_histories_with_email') \
            .select('report_id, user_id, user_email, url, title, style, created_at')

        if user_id:
            query = query.eq('user_id', user_id)

        result = query.order('created_at', desc=True) \
            .range(offset, offset + per_page - 1) \
            .execute()

        contents = []
        for item in (result.data or []):
            item_user_email = item.get('user_email')
            item_user_id = item.get('user_id', '')
            contents.append({
                'id': item.get('report_id'),
                'user_id': item_user_id,
                'user_email': item_user_email or (item_user_id[:8] + '...' if item_user_id else '-'),
                'url': item.get('url'),
                'title': item.get('title'),
                'style': item.get('style'),
                'created_at': item.get('created_at')
            })

        return {
            'contents': contents,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'filtered_user_id': user_id
        }

    return _db_operation('All contents', {'contents': [], 'total': 0}, operation)


def get_content_detail(report_id: str) -> dict:
    """특정 콘텐츠 상세 조회 (관리자용)"""
    supabase = get_supabase()
    if not supabase or not report_id:
        return {}

    def operation():
        result = supabase.table('ie_histories') \
            .select('*') \
            .eq('report_id', report_id) \
            .single() \
            .execute()
        return result.data or {}

    return _db_operation('Content detail', {}, operation)

# =============================================
# 스니펫 라이브러리
# =============================================

def get_user_snippets(user_id: str) -> list:
    """사용자의 스니펫 목록을 반환합니다."""
    supabase = get_supabase()
    if not supabase or not user_id:
        return []

    def operation():
        result = supabase.table('ie_snippets') \
            .select('*') \
            .eq('user_id', user_id) \
            .order('created_at', desc=True) \
            .execute()
        return result.data or []

    return _db_operation('Snippets fetch', [], operation)


def create_snippet(user_id: str, data: dict) -> dict:
    """새 스니펫을 생성합니다."""
    supabase = get_supabase()
    if not supabase or not user_id:
        return {'error': 'Supabase 미연결'}

    def operation():
        row = {
            'user_id': user_id,
            'category': (data.get('category') or 'general')[:50],
            'label': (data.get('label') or '제목 없음')[:100],
            'content': (data.get('content') or '')[:5000],
        }
        result = supabase.table('ie_snippets').insert(row).execute()
        return (result.data or [{}])[0]

    return _db_operation('Snippet create', {'error': '스니펫 생성 실패'}, operation)


def delete_snippet(user_id: str, snippet_id: str) -> bool:
    """스니펫을 삭제합니다."""
    supabase = get_supabase()
    if not supabase or not user_id:
        return False

    def operation():
        supabase.table('ie_snippets') \
            .delete() \
            .eq('id', snippet_id) \
            .eq('user_id', user_id) \
            .execute()
        return True

    return _db_operation('Snippet delete', False, operation)
