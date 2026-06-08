"""API 키 저장소 facade — auth 라우트용 도메인별 진입점.

routes가 `supabase_service`를 직접 다중 import하지 않도록, 도메인 단위로
필요한 함수만 재노출(re-export)한다 (PR #20 Phase 5-e).

services/data/ 내부에 위치하므로 도메인 경계 베이스라인에서 자연스럽게 제외된다.
"""
from services.data.supabase_service import save_api_keys, get_api_keys

__all__ = ["save_api_keys", "get_api_keys"]
