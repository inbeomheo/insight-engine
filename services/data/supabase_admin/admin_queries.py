"""Supabase 관리자 조회/통계 함수.

분리 원본: services/data/supabase_service.py (라인 657-865).
공용 헬퍼(`get_supabase`, `_db_operation`, `logger`, `MAX_USAGE_COUNT`)는
supabase_service에서 lazy import (순환 import 회피).
"""
from __future__ import annotations


def is_admin(user_id: str) -> bool:
    """service-role로 ``ie_admins.user_id`` 등록 여부를 확인한다."""
    from services.data.supabase_service import (
        _db_operation, get_service_supabase, logger,
    )

    if not user_id:
        return False

    try:
        # ie_admins는 의도적으로 일반 사용자 RLS 접근을 모두 거부한다.
        # anon/user client로 조회하면 실제 관리자도 항상 false가 되므로
        # 서버 내부의 권한 판별만 명시적 service-role로 수행한다.
        supabase = get_service_supabase()
    except Exception as exc:
        logger.error(f"is_admin service-role client 오류: {exc}")
        return False

    if not supabase or not user_id:
        logger.warning(
            f"is_admin: supabase={supabase is not None}, "
            f"user_id={user_id[:8] if user_id else None}"
        )
        return False

    def operation():
        result = supabase.table('ie_admins') \
            .select('user_id') \
            .eq('user_id', user_id) \
            .limit(1) \
            .execute()

        is_registered = bool(result.data)
        logger.info(
            f"is_admin check: user_id={user_id[:8]}..., "
            f"is_admin={is_registered}"
        )
        return is_registered

    result = _db_operation('Admin check', False, operation)
    logger.info(f"is_admin final result for {user_id[:8] if user_id else None}: {result}")
    return result
