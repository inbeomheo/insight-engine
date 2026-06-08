"""커스텀 스타일 facade — auth 라우트용 도메인별 진입점.

routes가 `supabase_service`를 직접 다중 import하지 않도록, 도메인 단위로
필요한 함수만 재노출(re-export)한다 (PR #20 Phase 5-e).
"""
from services.data.supabase_service import (
    save_custom_style,
    get_custom_styles,
    delete_custom_style,
)

__all__ = ["save_custom_style", "get_custom_styles", "delete_custom_style"]
