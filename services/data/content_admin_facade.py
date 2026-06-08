"""콘텐츠 관리자 facade — auth 라우트용 도메인별 진입점.

관리자 콘텐츠 조회 함수를 `supabase_admin` 패키지에서 재노출(re-export)한다
(PR #20 Phase 5-e).
"""
from services.data.supabase_admin import get_all_contents, get_content_detail

__all__ = ["get_all_contents", "get_content_detail"]
