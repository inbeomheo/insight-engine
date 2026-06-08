"""사용량/관리자 facade — auth 라우트 및 usage 서비스용 도메인별 진입점.

사용량 조회/차감은 `supabase_service`, 관리자 전용 조회/통계는
`supabase_admin` 패키지에서 가져와 한 곳에 재노출(re-export)한다 (PR #20 Phase 5-e).
"""
from services.data.supabase_service import get_usage, decrement_usage
from services.data.supabase_admin import (
    is_admin,
    get_all_users_usage,
    reset_user_usage,
    get_usage_stats,
)

__all__ = [
    "get_usage",
    "decrement_usage",
    "is_admin",
    "get_all_users_usage",
    "reset_user_usage",
    "get_usage_stats",
]
