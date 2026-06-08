"""스니펫 facade — auth 라우트용 도메인별 진입점.

사용자 스니펫 CRUD 함수를 `supabase_service`에서 재노출(re-export)한다
(PR #20 Phase 5-e).
"""
from services.data.supabase_service import (
    get_user_snippets,
    create_snippet,
    delete_snippet,
)

__all__ = ["get_user_snippets", "create_snippet", "delete_snippet"]
