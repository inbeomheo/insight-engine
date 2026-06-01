"""API 키 저장소 facade.

라우트 계층이 거대한 supabase_service를 직접 import하지 않도록 분리한다.
"""

from services.data.supabase_service import get_api_keys, save_api_keys

__all__ = ["save_api_keys", "get_api_keys"]
