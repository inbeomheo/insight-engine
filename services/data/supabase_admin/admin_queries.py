"""Supabase 관리자 조회/통계 함수.

분리 원본: services/data/supabase_service.py (라인 657-865).
공용 헬퍼(`get_supabase`, `_db_operation`, `logger`, `MAX_USAGE_COUNT`)는
supabase_service에서 lazy import (순환 import 회피).
"""
from __future__ import annotations


def is_admin(user_id: str) -> bool:
    """사용자가 관리자인지 확인 (user_id 또는 이메일)"""
    from flask import g

    from services.data.supabase_service import (
        _db_operation, get_supabase, logger,
    )

    supabase = get_supabase()
    if not supabase or not user_id:
        logger.warning(f"is_admin: supabase={supabase is not None}, user_id={user_id[:8] if user_id else None}")
        return False

    def operation():
        # 1. user_id로 체크
        result = supabase.table('ie_admins') \
            .select('user_id') \
            .eq('user_id', user_id) \
            .limit(1) \
            .execute()

        if result.data and len(result.data) > 0:
            logger.info(f"is_admin check (user_id): user_id={user_id[:8]}..., is_admin=True")
            return True

        # 2. g.user_email이 있으면 이메일로도 체크
        user_email = getattr(g, 'user_email', None)
        if user_email:
            logger.info(f"is_admin: g.user_email 발견: {user_email}")
            result = supabase.table('ie_admins') \
                .select('user_id') \
                .eq('user_id', user_email) \
                .limit(1) \
                .execute()

            if result.data and len(result.data) > 0:
                logger.info(f"is_admin check (email): email={user_email}, is_admin=True")
                return True

        logger.info(f"is_admin check: user_id={user_id[:8]}..., is_admin=False")
        return False

    result = _db_operation('Admin check', False, operation)
    logger.info(f"is_admin final result for {user_id[:8] if user_id else None}: {result}")
    return result

