"""계정 관리 facade — auth 라우트용 도메인별 진입점.

계정 삭제/프로필/비밀번호 변경 함수를 `supabase_service`에서
재노출(re-export)한다 (PR #20 Phase 5-e).
"""
from services.data.supabase_service import (
    delete_user_account,
    update_user_profile,
    update_user_password,
)

__all__ = ["delete_user_account", "update_user_profile", "update_user_password"]
