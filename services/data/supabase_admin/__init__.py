"""Supabase 관리자 기능 모듈 — 관리자 권한 확인.

여기에 분리된 함수는 호환성을 위해 services/data/supabase_service.py에서
그대로 re-export된다.
"""
from services.data.supabase_admin.admin_queries import is_admin

__all__ = [
    'is_admin',
]
