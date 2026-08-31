"""
사용량 체크 데코레이터
blog_routes.py의 중복 코드 제거

내부 구현은 Identity & Access BC의 어댑터에 위임된다:
- 차감은 `UsageService.decrement` → `SupabaseUsageGateway.check_and_consume`
  → `SupabaseAccountRepository.consume_quota_atomic`
- 조회(`check_can_use`)는 기존 `services.data.supabase_service`를 그대로 사용
  (Phase 2-f 범위 외 — 차후 마이그레이션 예정).

외부 시그니처(@require_usage, @check_usage, get_usage_for_response)와
에러 응답 형식(`code='USAGE_LIMIT_EXCEEDED'`, 429)은 100% 기존 호환.
"""
from functools import wraps
from flask import g, jsonify, make_response

from src.shared.infrastructure.supabase_client import is_supabase_enabled
from services.usage.usage_service import UsageService, ADMIN_USAGE
from services.core.logging_config import ServiceLogger

# Identity BC 게이트웨이 (eager import — 데코레이터 호출 경로의 위임 지점을
# 명시적으로 노출). 실제 사용은 UsageService.decrement 내부에서 위임된다.
from src.contexts.identity.infrastructure.supabase_usage_gateway import (  # noqa: F401
    SupabaseUsageGateway,
)

logger = ServiceLogger('UsageDecorator')


def _is_success_response(result) -> bool:
    """Return True when route output maps to HTTP 2xx/3xx."""
    try:
        response = make_response(result)
        return 200 <= response.status_code < 400
    except Exception:
        return False


def check_usage(f):
    """
    사용량 체크 데코레이터 (차감하지 않음)
    사용 불가 시 429 응답 반환

    Usage:
        @require_auth
        @check_usage
        def my_route():
            # g.usage에 현재 사용량 정보가 설정됨
            # g.is_admin에 관리자 여부가 설정됨
            pass
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Supabase 비활성화 시 통과
        if not is_supabase_enabled():
            g.usage = ADMIN_USAGE
            g.is_admin = False
            return f(*args, **kwargs)

        user_id = getattr(g, 'user_id', None)
        if not user_id:
            g.usage = ADMIN_USAGE
            g.is_admin = False
            return f(*args, **kwargs)

        # 사용량 체크
        can_use, usage = UsageService.check_can_use(user_id)
        g.usage = usage
        g.is_admin = usage.get('is_admin', False)

        if not can_use:
            return jsonify({
                'error': '오늘 사용 가능 횟수를 모두 소진했습니다. 내일 다시 시도해주세요.',
                'code': 'USAGE_LIMIT_EXCEEDED',
                'usage': usage
            }), 429

        return f(*args, **kwargs)
    return decorated


def require_usage(f):
    """
    사용량 체크 + 실행 전 원자적 예약 데코레이터
    콘텐츠 생성 등 실제 리소스 소비 API에 사용

    Usage:
        @require_auth
        @require_usage
        def generate():
            # 함수 실행 전 사용량을 예약하고, 검증/프로바이더 실패 시 환불
            pass

    Note:
        - 관리자는 차감하지 않음
        - 예약 실패 시 라우트를 실행하지 않음 (결과 미전달)
        - 2xx/3xx가 아니면 refund
        - skip_usage_decrement(캐시 히트 등)이면 refund
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Supabase 비활성화 시 통과
        if not is_supabase_enabled():
            g.usage = ADMIN_USAGE
            g.updated_usage = ADMIN_USAGE
            g.is_admin = False
            return f(*args, **kwargs)

        user_id = getattr(g, 'user_id', None)
        if not user_id:
            g.usage = ADMIN_USAGE
            g.updated_usage = ADMIN_USAGE
            g.is_admin = False
            return f(*args, **kwargs)

        consumed, usage = UsageService.try_consume_atomic(user_id)
        g.usage = usage
        g.is_admin = usage.get('is_admin', False)

        if g.is_admin:
            g.updated_usage = ADMIN_USAGE
            return f(*args, **kwargs)

        if not consumed:
            return jsonify({
                'error': '오늘 사용 가능 횟수를 모두 소진했습니다. 내일 다시 시도해주세요.',
                'code': 'USAGE_LIMIT_EXCEEDED',
                'usage': usage
            }), 429

        g.quota_reserved = True
        try:
            result = f(*args, **kwargs)
        except Exception:
            UsageService.refund(user_id)
            g.quota_reserved = False
            raise

        if getattr(g, 'skip_usage_decrement', False) or not _is_success_response(result):
            g.updated_usage = UsageService.refund(user_id)
            g.quota_reserved = False
        else:
            g.updated_usage = usage

        return result
    return decorated


def get_usage_for_response() -> dict:
    """
    응답에 포함할 사용량 정보 반환
    데코레이터 사용 후 호출

    Returns:
        dict: 업데이트된 사용량 또는 현재 사용량
    """
    return getattr(g, 'updated_usage', None) or getattr(g, 'usage', ADMIN_USAGE)
