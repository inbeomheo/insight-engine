"""
사용량 관리 서비스
비즈니스 로직 캡슐화
"""
from flask import g

from services.supabase_service import (
    is_supabase_enabled, get_usage, decrement_usage, is_admin,
    get_supabase, MAX_USAGE_COUNT
)
from services.logging_config import ServiceLogger

logger = ServiceLogger('UsageService')

# 관리자 더미 사용량 (무제한)
ADMIN_USAGE = {
    'usage_count': 999,
    'max_usage': 999,
    'can_use': True,
    'is_admin': True
}


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
            return True, ADMIN_USAGE

        # 관리자는 무제한
        if is_admin(user_id):
            logger.debug(f"관리자 사용: {user_id[:8]}...")
            return True, ADMIN_USAGE

        usage = get_usage(user_id)
        can_use = usage.get('can_use', False)

        if not can_use:
            logger.info(f"사용량 소진: {user_id[:8]}...")

        return can_use, usage

    @staticmethod
    def decrement(user_id: str) -> dict:
        """
        사용량 차감 후 업데이트된 사용량 반환

        Args:
            user_id: 사용자 ID

        Returns:
            dict: 업데이트된 사용량 정보
        """
        if not is_supabase_enabled() or not user_id:
            return ADMIN_USAGE

        if is_admin(user_id):
            return ADMIN_USAGE

        decrement_usage(user_id)
        return get_usage(user_id)

    @staticmethod
    def try_consume_atomic(user_id: str) -> tuple[bool, dict]:
        """
        원자적으로 사용량 체크 + 차감을 시도합니다.
        Race Condition을 방지하기 위해 Supabase RPC를 사용합니다.

        Args:
            user_id: 사용자 ID

        Returns:
            tuple: (성공 여부, 사용량 정보)
                - 성공: (True, {'usage_count': n, 'can_use': True, 'max_usage': 20})
                - 실패: (False, {'usage_count': 0, 'can_use': False})
        """
        if not is_supabase_enabled() or not user_id:
            return True, ADMIN_USAGE

        if is_admin(user_id):
            return True, ADMIN_USAGE

        try:
            supabase = get_supabase()
            if not supabase:
                logger.warning("Supabase 클라이언트 없음, 폴백 사용")
                return UsageService.check_can_use(user_id)

            result = supabase.rpc('decrement_usage_safe', {'p_user_id': user_id}).execute()

            data = result.data
            # RPC 결과가 리스트로 반환될 경우 처리
            if isinstance(data, list) and len(data) > 0:
                data = data[0]

            if data and data.get('success'):
                return True, {
                    'usage_count': data['new_count'],
                    'can_use': True,
                    'max_usage': MAX_USAGE_COUNT
                }

            # 실패 사유 로깅
            reason = data.get('reason', 'unknown') if data else 'no_data'
            logger.info(f"사용량 차감 실패: {user_id[:8]}... - {reason}")
            return False, {'usage_count': 0, 'can_use': False, 'max_usage': MAX_USAGE_COUNT}

        except Exception as e:
            logger.error(f"사용량 RPC 호출 실패: {e}, 폴백 사용")
            # 폴백: 기존 check_can_use 로직 사용 (안전장치)
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

        if is_admin(user_id):
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
        return is_admin(user_id)


# 싱글톤 인스턴스
usage_service = UsageService()
