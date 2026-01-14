"""
사용량 체크 데코레이터
blog_routes.py의 중복 코드 제거
"""
from functools import wraps
from flask import g, jsonify

from services.supabase_service import is_supabase_enabled
from services.usage.usage_service import UsageService, ADMIN_USAGE
from services.logging_config import ServiceLogger

logger = ServiceLogger('UsageDecorator')


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
    사용량 체크 + 성공 시 자동 차감 데코레이터
    콘텐츠 생성 등 실제 리소스 소비 API에 사용

    Usage:
        @require_auth
        @require_usage
        def generate():
            # 함수 실행 후 자동으로 사용량 차감
            # g.usage에 차감 전 사용량 정보
            # g.updated_usage에 차감 후 사용량 정보 (함수 실행 후)
            pass

    Note:
        - 관리자는 차감하지 않음
        - 함수가 성공적으로 완료된 경우에만 차감됨
        - 응답에 자동으로 usage 필드 추가하려면 _add_usage_to_response 사용
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

        # 함수 실행
        result = f(*args, **kwargs)

        # 성공 시 사용량 차감 (관리자 제외)
        if not g.is_admin:
            g.updated_usage = UsageService.decrement(user_id)
        else:
            g.updated_usage = ADMIN_USAGE

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
