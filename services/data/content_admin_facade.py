"""관리자 콘텐츠 조회 facade."""

from services.data.supabase_admin import get_all_contents, get_content_detail

__all__ = ["get_all_contents", "get_content_detail"]
