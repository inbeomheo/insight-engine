"""
Supabase 서비스 모듈
데이터베이스 연동 및 사용자 인증 처리

Issue #17 (소PR A): 인프라 헬퍼는 `src/shared/infrastructure/supabase_client.py`로
이전되었으며, 본 파일은 호환성 유지를 위해 동일 심볼을 re-export 한다.
Issue #17 (소PR B-1): 인증 데코레이터(`require_auth` 등)는
`src/contexts/identity/interface/auth_decorators.py`로 이전. 본 파일은 shim re-export.

신규 호출처는 새 위치를 직접 import할 것:

    from src.shared.infrastructure.supabase_client import (
        get_supabase, is_supabase_enabled, encrypt_api_key, decrypt_api_key,
    )
    from src.contexts.identity.interface.auth_decorators import require_auth
"""
from services.core.logging_config import supabase_logger as logger

# 인프라 헬퍼 re-export (호환 shim) — 신규 호출처는 src.shared.infrastructure 사용 권장
from src.shared.infrastructure.supabase_client import (  # noqa: F401
    _get_admin_client,
    _get_fernet,
    _is_encryption_enabled,
    _lazy_create_client,
    decrypt_api_key,
    encrypt_api_key,
    get_supabase,
    is_supabase_enabled,
)

# 인증 데코레이터 re-export (호환 shim) — 신규 호출처는 contexts.identity.interface 사용 권장
from src.contexts.identity.interface.auth_decorators import (  # noqa: F401
    _extract_bearer_token,
    _validate_token,
    require_auth,
)

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
# 관리자 관리 — services/data/supabase_admin/ 패키지로 분리됨
# 외부 호환을 위해 동일한 이름으로 re-export
# =============================================
from services.data.supabase_admin import is_admin  # noqa: E402

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
