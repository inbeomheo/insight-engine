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
    get_service_supabase,
    get_supabase,
    get_user_supabase,
    get_validated_request_access_token,
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


def save_history(
    user_id: str,
    data: dict,
    *,
    validated_access_token: str | None = None,
) -> dict | None:
    """분석 히스토리 저장

    P3 버그 #12: user_id가 None이면 저장하지 않고 None 반환 (의도된 동작)
    - 비로그인 사용자는 클라우드 저장 생략
    - 로컬 스토리지에서 별도 관리됨
    """
    if not user_id:
        return None

    supabase = get_user_supabase(
        validated_access_token=validated_access_token,
    )
    if not supabase:
        return None

    def operation():
        transcript = data.get('transcript')
        transcript_preview = (
            transcript[:500]
            if isinstance(transcript, str)
            else None
        )
        result = supabase.table('ie_histories').insert({
            'user_id': user_id,
            'report_id': data.get('id'),
            'url': data.get('url') or '',
            'title': data.get('title') or '',
            'style': data.get('style') or 'unknown',
            'content': data.get('content'),
            'html': data.get('html'),
            'transcript_preview': transcript_preview,
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


def get_usage(
    user_id: str,
    *,
    validated_access_token: str | None = None,
) -> dict:
    """사용자 사용량 조회. 없으면 새로 생성.

    사용자 소유 RLS 테이블이므로 익명 클라이언트로 폴백하지 않는다. 일반 HTTP
    요청에서는 ``require_auth``가 검증해 ``g``에 저장한 JWT를 사용하고, 요청
    컨텍스트 밖에서는 호출자가 검증된 토큰을 명시적으로 넘겨야 한다.
    """
    if not user_id:
        return {'usage_count': 0, 'max_usage': MAX_USAGE_COUNT, 'can_use': False}

    def operation():
        supabase = get_user_supabase(
            validated_access_token=validated_access_token,
        )
        if not supabase:
            return {
                'usage_count': 0,
                'max_usage': MAX_USAGE_COUNT,
                'can_use': False,
            }

        result = supabase.rpc(
            'get_usage_safe',
            {'p_user_id': user_id},
        ).execute()
        payload = getattr(result, 'data', None)
        if not isinstance(payload, dict):
            raise RuntimeError('get_usage_safe returned a malformed payload')

        usage_count = int(payload.get('usage_count', 0))
        max_usage = int(payload.get('max_usage', MAX_USAGE_COUNT))
        return {
            'usage_count': usage_count,
            'max_usage': max_usage,
            'can_use': bool(payload.get('can_use', usage_count > 0)),
        }

    return _db_operation('Usage fetch', {'usage_count': 0, 'max_usage': MAX_USAGE_COUNT, 'can_use': False}, operation)


def decrement_usage(
    user_id: str,
    *,
    validated_access_token: str | None = None,
) -> bool:
    """사용량 1회를 인증된 사용자 RPC로 원자적으로 차감한다."""
    if not user_id:
        return False

    def operation():
        supabase = get_user_supabase(
            validated_access_token=validated_access_token,
        )
        if not supabase:
            return False

        result = supabase.rpc(
            'decrement_usage_safe',
            {'p_user_id': user_id, 'p_amount': 1},
        ).execute()
        payload = getattr(result, 'data', None)
        return bool(isinstance(payload, dict) and payload.get('success') is True)

    return _db_operation('Usage decrement', False, operation)

# =============================================
# 관리자 관리 — services/data/supabase_admin/ 패키지로 분리됨
# 외부 호환을 위해 동일한 이름으로 re-export
# =============================================
from services.data.supabase_admin import is_admin  # noqa: E402
