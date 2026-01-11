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

# Supabase 클라이언트 초기화
_supabase_client: Client = None
_fernet_instance: Fernet = None


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


def _get_fernet() -> Fernet:
    """Fernet 인스턴스 싱글톤 (암호화용)"""
    global _fernet_instance

    if _fernet_instance is None:
        secret = os.getenv('ENCRYPTION_SECRET', 'default-secret-change-in-production')
        key = hashlib.sha256(secret.encode()).digest()
        _fernet_instance = Fernet(base64.urlsafe_b64encode(key))

    return _fernet_instance


def encrypt_api_key(api_key: str) -> str:
    """API 키 암호화"""
    return _get_fernet().encrypt(api_key.encode()).decode() if api_key else None


def decrypt_api_key(encrypted_key: str) -> str:
    """API 키 복호화"""
    if not encrypted_key:
        return None
    try:
        return _get_fernet().decrypt(encrypted_key.encode()).decode()
    except Exception:
        return None

# =============================================
# 인증 헬퍼 및 데코레이터
# =============================================

def _extract_bearer_token() -> str:
    """Authorization 헤더에서 Bearer 토큰 추출"""
    auth_header = request.headers.get('Authorization', '')
    return auth_header[7:] if auth_header.startswith('Bearer ') else None


def _validate_token(token: str) -> bool:
    """토큰 검증 및 g 객체에 사용자 정보 설정"""
    try:
        supabase = get_supabase()
        user = supabase.auth.get_user(token)
        g.user_id = user.user.id
        g.access_token = token
        return True
    except Exception:
        return False


def require_auth(f):
    """JWT 토큰 검증 데코레이터"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not is_supabase_enabled():
            g.user_id = None
            return f(*args, **kwargs)

        token = _extract_bearer_token()
        if not token:
            return jsonify({'error': '인증이 필요합니다.'}), 401

        if not _validate_token(token):
            return jsonify({'error': '유효하지 않은 토큰입니다.'}), 401

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
            _validate_token(token)  # 실패해도 무시

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
        print(f"{operation_name} error: {e}")
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
            .single() \
            .execute()

        if not result.data:
            return {}

        data = result.data
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
