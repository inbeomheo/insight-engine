"""
사용량 관리 서비스
비즈니스 로직 캡슐화
"""
from flask import g

from services.supabase_service import (
    is_supabase_enabled, get_usage, decrement_usage, is_admin
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
