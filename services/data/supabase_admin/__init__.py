"""Supabase 관리자 기능 모듈 — 관리자 전용 조회/통계/사용량 리셋.

여기에 분리된 함수들은 호환성을 위해 services/data/supabase_service.py에서
그대로 re-export된다.
"""
from services.data.supabase_admin.admin_queries import (
    get_admin_permissions,
    get_all_contents,
    get_all_users_usage,
    get_content_detail,
    get_usage_stats,
    is_admin,
    reset_user_usage,
)

__all__ = [
    'is_admin',
    'get_admin_permissions',
    'get_all_users_usage',
    'reset_user_usage',
    'get_usage_stats',
    'get_all_contents',
    'get_content_detail',
]
