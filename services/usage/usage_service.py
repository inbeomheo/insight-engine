"""
사용량 관리 서비스
비즈니스 로직 캡슐화

내부 구현은 Identity & Access BC의 게이트웨이/리포지토리에 위임하지만,
외부 시그니처(check_can_use/decrement/try_consume_atomic/get_current/is_admin_user)는
기존과 동일하게 유지한다.
"""
from src.shared.infrastructure.supabase_client import is_supabase_enabled
from src.contexts.identity.domain.constants import (
    DEFAULT_DAILY_LIMIT as MAX_USAGE_COUNT,
)
from services.data.usage_admin_facade import (
    decrement_usage,
    get_usage,
    is_admin,
)
from services.core.logging_config import ServiceLogger

logger = ServiceLogger('UsageService')

# 관리자 더미 사용량 (무제한)
ADMIN_USAGE = {
    'usage_count': 999,
    'max_usage': 999,
    'can_use': True,
    'is_admin': True
}


def _get_account_repository():
    """SupabaseAccountRepository 싱글톤 lazy import.

    상위 import 시점에 src.contexts.identity가 로드되지 않도록 함수 호출 시점에 import.
    """
    from src.contexts.identity.infrastructure.supabase_account_repository import (
        SupabaseAccountRepository,
    )
    # 매 호출마다 생성해도 stateless라 비용은 미미. 단순화를 위해 그대로 둠.
    return SupabaseAccountRepository()


def _is_admin_cached(user_id: str) -> bool:
    """is_admin 결과를 요청 스코프(flask.g)에 메모이즈한다.

    check_can_use → decrement 흐름에서 동일 요청에 ie_admins를 2~3회
    조회하던 것을 1회로 줄인다. 요청 컨텍스트 밖에서는 그대로 조회.
    """
    try:
        from flask import g, has_request_context
        if has_request_context():
            cache = getattr(g, '_is_admin_cache', None)
            if cache is None:
                cache = {}
                g._is_admin_cache = cache
            if user_id not in cache:
                cache[user_id] = is_admin(user_id)
            return cache[user_id]
    except Exception:
        pass
    return is_admin(user_id)


class UsageService:
    """사용량 관리 서비스 클래스"""

    @staticmethod
    def check_can_use(user_id: str) -> tuple[bool, dict]:
        """
        사용 가능 여부 확인

        Args:
            user_id: 사용자 ID

        Returns:
            tuple: (can_use: bool, usage: dict)
        """
        if not is_supabase_enabled() or not user_id:
            logger.info(f"Supabase 비활성 또는 user_id 없음, ADMIN_USAGE 반환")
            return True, ADMIN_USAGE

        # 관리자는 무제한 (요청 스코프 캐시로 중복 조회 방지)
        admin_status = _is_admin_cached(user_id)
        logger.info(f"check_can_use: user_id={user_id[:8]}..., is_admin={admin_status}")
        if admin_status:
            logger.info(f"관리자 사용: {user_id[:8]}..., ADMIN_USAGE 반환")
            return True, ADMIN_USAGE

        # 조회는 기존 supabase_service.get_usage를 유지 (미마이그레이션).
        usage = get_usage(user_id)
        can_use = usage.get('can_use', False)
        logger.info(f"일반 사용자: user_id={user_id[:8]}..., usage={usage}, can_use={can_use}")

        if not can_use:
            logger.warning(f"사용량 소진: {user_id[:8]}...")

        return can_use, usage

    @staticmethod
    def decrement(user_id: str) -> dict:
        """
        사용량 차감 후 업데이트된 사용량 반환

        내부적으로 Identity BC의 SupabaseUsageGateway를 경유하여 원자적 차감.
        한도 초과/예외 시에는 기존 폴백(get_usage)을 사용해 호환성을 유지한다.

        Args:
            user_id: 사용자 ID

        Returns:
            dict: 업데이트된 사용량 정보
        """
        if not is_supabase_enabled() or not user_id:
            return ADMIN_USAGE

        if _is_admin_cached(user_id):
            return ADMIN_USAGE

        # Identity BC 게이트웨이로 차감 (원자적).
        try:
            from src.contexts.identity.domain.exceptions import QuotaExceeded
            from src.contexts.identity.infrastructure.supabase_usage_gateway import (
                SupabaseUsageGateway,
            )
            from src.shared.domain.value_objects import AccountId

            gateway = SupabaseUsageGateway(_get_account_repository())
            try:
                remaining = gateway.check_and_consume(AccountId(value=user_id), 1)
                return {
                    'usage_count': remaining,
                    'max_usage': MAX_USAGE_COUNT,
                    'can_use': remaining > 0,
                    'is_admin': False,
                }
            except QuotaExceeded:
                # 한도 초과 — 호환을 위해 0/can_use=False dict 반환 (기존엔 get_usage 결과)
                logger.info(f"decrement: 한도 초과 {user_id[:8]}...")
                return {
                    'usage_count': 0,
                    'max_usage': MAX_USAGE_COUNT,
                    'can_use': False,
                    'is_admin': False,
                }
        except Exception as exc:
            # 인프라 실패 시 기존 흐름으로 폴백
            logger.warning(f"decrement gateway 실패, supabase_service 폴백: {exc}")
            decrement_usage(user_id)
            return get_usage(user_id)

    @staticmethod
    def try_consume_atomic(user_id: str) -> tuple[bool, dict]:
        """
        원자적으로 사용량 체크 + 차감을 시도합니다.
        Race Condition을 방지하기 위해 Identity BC 게이트웨이에 위임합니다.

        Args:
            user_id: 사용자 ID

        Returns:
            tuple: (성공 여부, 사용량 정보)
                - 성공: (True, {'usage_count': n, 'can_use': True, 'max_usage': 20})
                - 실패: (False, {'usage_count': 0, 'can_use': False})
        """
        if not is_supabase_enabled() or not user_id:
            return True, ADMIN_USAGE

        if _is_admin_cached(user_id):
            return True, ADMIN_USAGE

        # Identity BC 게이트웨이로 위임. QuotaExceeded는 한도 초과 응답으로 변환.
        try:
            from src.contexts.identity.domain.exceptions import QuotaExceeded
            from src.shared.domain.value_objects import AccountId

            repo = _get_account_repository()
            remaining = repo.consume_quota_atomic(AccountId(value=user_id), 1)
            return True, {
                'usage_count': remaining,
                'can_use': True,
                'max_usage': MAX_USAGE_COUNT,
            }
        except Exception as exc:
            # QuotaExceeded는 lazy import이므로 isinstance 체크를 위해 한 번 더 import
            try:
                from src.contexts.identity.domain.exceptions import QuotaExceeded
                if isinstance(exc, QuotaExceeded):
                    logger.info(f"사용량 차감 실패: {user_id[:8]}... - quota_exceeded")
                    return False, {
                        'usage_count': 0,
                        'can_use': False,
                        'max_usage': MAX_USAGE_COUNT,
                    }
            except Exception:  # pragma: no cover
                pass

            # 그 외 예외는 기존 폴백 — 안전장치 (check_can_use)
            logger.error(f"사용량 RPC 호출 실패: {exc}, 폴백 사용")
            return UsageService.check_can_use(user_id)

    @staticmethod
    def get_current(user_id: str) -> dict:
        """
        현재 사용량 조회

        Args:
            user_id: 사용자 ID

        Returns:
            dict: 사용량 정보
        """
        if not is_supabase_enabled() or not user_id:
            return ADMIN_USAGE

        if _is_admin_cached(user_id):
            return ADMIN_USAGE

        return get_usage(user_id)

    @staticmethod
    def is_admin_user(user_id: str) -> bool:
        """
        관리자 여부 확인

        Args:
            user_id: 사용자 ID

        Returns:
            bool: 관리자 여부
        """
        if not is_supabase_enabled() or not user_id:
            return False
        return _is_admin_cached(user_id)


# 싱글톤 인스턴스
usage_service = UsageService()
