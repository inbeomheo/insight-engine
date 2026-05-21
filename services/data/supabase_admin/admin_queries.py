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


def get_admin_permissions(user_id: str) -> dict:
    """관리자 권한 조회"""
    from services.data.supabase_service import _db_operation, get_supabase

    supabase = get_supabase()
    if not supabase or not user_id:
        return {}

    def operation():
        result = supabase.table('ie_admins') \
            .select('permissions') \
            .eq('user_id', user_id) \
            .limit(1) \
            .execute()
        return result.data[0].get('permissions', {}) if result.data and len(result.data) > 0 else {}

    return _db_operation('Admin permissions', {}, operation)


def get_all_users_usage() -> list:
    """모든 사용자의 사용량 조회 (관리자용) - 이메일 포함"""
    from services.data.supabase_service import _db_operation, get_supabase

    supabase = get_supabase()
    if not supabase:
        return []

    def operation():
        # view를 사용하여 이메일 포함 조회
        result = supabase.table('ie_usage_with_email') \
            .select('user_id, usage_count, last_reset_date, email') \
            .order('usage_count', desc=False) \
            .execute()
        return result.data or []

    return _db_operation('All users usage', [], operation)


def reset_user_usage(user_id: str) -> bool:
    """특정 사용자 사용량 리셋 (관리자용)"""
    from services.data.supabase_service import (
        MAX_USAGE_COUNT, _db_operation, get_supabase,
    )

    supabase = get_supabase()
    if not supabase or not user_id:
        return False

    def operation():
        from datetime import date
        supabase.table('ie_usage') \
            .update({
                'usage_count': MAX_USAGE_COUNT,
                'last_reset_date': date.today().isoformat(),
                'updated_at': 'now()'
            }) \
            .eq('user_id', user_id) \
            .execute()
        return True

    return _db_operation('Reset user usage', False, operation)


def get_usage_stats() -> dict:
    """사용량 통계 조회 (관리자용)"""
    from services.data.supabase_service import (
        MAX_USAGE_COUNT, _db_operation, get_supabase,
    )

    supabase = get_supabase()
    if not supabase:
        return {}

    def operation():
        # 전체 사용자 수
        users_result = supabase.table('ie_usage').select('user_id', count='exact').execute()
        total_users = users_result.count or 0

        # 오늘 사용한 사용자 수
        from datetime import date
        today = date.today().isoformat()
        active_result = supabase.table('ie_usage') \
            .select('user_id', count='exact') \
            .eq('last_reset_date', today) \
            .lt('usage_count', MAX_USAGE_COUNT) \
            .execute()
        active_today = active_result.count or 0

        # 사용량 소진 사용자 수
        exhausted_result = supabase.table('ie_usage') \
            .select('user_id', count='exact') \
            .eq('usage_count', 0) \
            .execute()
        exhausted_users = exhausted_result.count or 0

        return {
            'total_users': total_users,
            'active_today': active_today,
            'exhausted_users': exhausted_users,
            'max_usage': MAX_USAGE_COUNT
        }

    return _db_operation('Usage stats', {}, operation)


def get_all_contents(page: int = 1, per_page: int = 20, user_id: str = None) -> dict:
    """모든 사용자의 생성 콘텐츠 조회 (관리자용)

    Args:
        page: 페이지 번호
        per_page: 페이지당 항목 수
        user_id: 특정 사용자 필터 (None이면 전체)
    """
    from services.data.supabase_service import _db_operation, get_supabase

    supabase = get_supabase()
    if not supabase:
        return {'contents': [], 'total': 0}

    def operation():
        # 전체 개수 쿼리
        count_query = supabase.table('ie_histories').select('report_id', count='exact')
        if user_id:
            count_query = count_query.eq('user_id', user_id)
        count_result = count_query.execute()
        total = count_result.count or 0

        # 페이지네이션 - view를 사용하여 이메일 포함 조회
        offset = (page - 1) * per_page
        query = supabase.table('ie_histories_with_email') \
            .select('report_id, user_id, user_email, url, title, style, created_at')

        if user_id:
            query = query.eq('user_id', user_id)

        result = query.order('created_at', desc=True) \
            .range(offset, offset + per_page - 1) \
            .execute()

        contents = []
        for item in (result.data or []):
            item_user_email = item.get('user_email')
            item_user_id = item.get('user_id', '')
            contents.append({
                'id': item.get('report_id'),
                'user_id': item_user_id,
                'user_email': item_user_email or (item_user_id[:8] + '...' if item_user_id else '-'),
                'url': item.get('url'),
                'title': item.get('title'),
                'style': item.get('style'),
                'created_at': item.get('created_at')
            })

        return {
            'contents': contents,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page,
            'filtered_user_id': user_id
        }

    return _db_operation('All contents', {'contents': [], 'total': 0}, operation)


def get_content_detail(report_id: str) -> dict:
    """특정 콘텐츠 상세 조회 (관리자용)"""
    from services.data.supabase_service import _db_operation, get_supabase

    supabase = get_supabase()
    if not supabase or not report_id:
        return {}

    def operation():
        result = supabase.table('ie_histories') \
            .select('*') \
            .eq('report_id', report_id) \
            .single() \
            .execute()
        return result.data or {}

    return _db_operation('Content detail', {}, operation)
