"""
프롬프트 템플릿 갤러리 서비스
사용자가 커스텀 프롬프트를 저장/공유/재사용하는 기능
"""
from services.supabase_service import get_supabase, is_supabase_enabled
from services.logging_config import supabase_logger as logger

# 페이지당 최대 항목 수
MAX_TEMPLATES_PER_USER = 50
PAGE_SIZE = 20


def _db_op(name: str, default, fn):
    """DB 작업 공통 래퍼 (에러 로깅 통합)"""
    try:
        return fn()
    except Exception as e:
        logger.error(f"[PromptTemplate] {name} 오류: {e}")
        return default


# =============================================
# 목록 조회
# =============================================

def _user_filter_expr(user_id: str | None) -> str:
    """사용자 필터 표현식을 생성합니다."""
    if user_id:
        return f"is_public.eq.true,user_id.eq.{user_id}"
    return "is_public.eq.true"


def _build_page_result(
    templates_data: list, total: int, page: int, user_id: str | None,
) -> dict:
    """템플릿 목록과 페이지 정보를 API 응답으로 변환합니다."""
    offset = (page - 1) * PAGE_SIZE
    return {
        'templates': [_format_template(t, user_id) for t in (templates_data or [])],
        'total': total,
        'page': page,
        'per_page': PAGE_SIZE,
        'has_more': (offset + PAGE_SIZE) < total,
    }


def get_templates(user_id: str | None, page: int = 1, search: str = '') -> dict:
    """템플릿 목록 조회

    - 공개 템플릿: 모든 사용자에게 노출 (usage_count DESC)
    - 본인 템플릿: 로그인한 경우 추가로 노출
    - Supabase 비활성화 시 빈 목록 반환

    Returns:
        dict: {templates, total, page, per_page, has_more}
    """
    if not is_supabase_enabled():
        return _empty_page(page)

    supabase = get_supabase()
    if not supabase:
        return _empty_page(page)

    def operation():
        filter_expr = _user_filter_expr(user_id)
        query = supabase.table('ie_prompt_templates').select('*', count='exact')
        if search:
            query = query.or_(f"name.ilike.%{search}%,description.ilike.%{search}%")
        if user_id:
            query = query.or_(filter_expr)
        else:
            query = query.eq('is_public', True)

        total = (query.execute()).count or 0
        offset = (page - 1) * PAGE_SIZE

        result = (
            supabase.table('ie_prompt_templates').select('*')
            .or_(filter_expr)
            .order('usage_count', desc=True)
            .order('created_at', desc=True)
            .range(offset, offset + PAGE_SIZE - 1)
            .execute()
        )
        return _build_page_result(result.data, total, page, user_id)

    return _db_op('get_templates', _empty_page(page), operation)


def get_template_by_id(template_id: str, user_id: str | None) -> dict | None:
    """특정 템플릿 조회 (공개 또는 본인 소유)"""
    if not is_supabase_enabled():
        return None

    supabase = get_supabase()
    if not supabase:
        return None

    def operation():
        query = supabase.table('ie_prompt_templates').select('*').eq('id', template_id)

        if user_id:
            query = query.or_(f"is_public.eq.true,user_id.eq.{user_id}")
        else:
            query = query.eq('is_public', True)

        result = query.limit(1).execute()
        if not result.data:
            return None
        return _format_template(result.data[0], user_id)

    return _db_op('get_template_by_id', None, operation)


# =============================================
# CRUD
# =============================================

def create_template(user_id: str, data: dict) -> dict | None:
    """템플릿 생성

    Args:
        user_id: 소유자 ID
        data: {name, description?, prompt_text, style_base?, is_public?}

    Returns:
        생성된 템플릿 dict 또는 None (실패 시)
    """
    if not is_supabase_enabled():
        return _local_template(data)

    supabase = get_supabase()
    if not supabase:
        return _local_template(data)

    def operation():
        # 사용자당 최대 개수 제한
        count_result = (
            supabase.table('ie_prompt_templates')
            .select('id', count='exact')
            .eq('user_id', user_id)
            .execute()
        )
        if (count_result.count or 0) >= MAX_TEMPLATES_PER_USER:
            raise ValueError(f"템플릿은 최대 {MAX_TEMPLATES_PER_USER}개까지 저장할 수 있습니다.")

        result = (
            supabase.table('ie_prompt_templates')
            .insert({
                'user_id': user_id,
                'name': data['name'],
                'description': data.get('description', ''),
                'prompt_text': data['prompt_text'],
                'style_base': data.get('style_base', 'blog_seo'),
                'is_public': bool(data.get('is_public', False)),
                'usage_count': 0,
            })
            .execute()
        )
        return _format_template(result.data[0], user_id) if result.data else None

    return _db_op('create_template', None, operation)


def update_template(template_id: str, user_id: str, data: dict) -> dict | None:
    """템플릿 수정 (소유자만 가능)

    Args:
        template_id: 수정할 템플릿 UUID
        user_id: 요청자 ID (소유자 확인용)
        data: {name?, description?, prompt_text?, style_base?, is_public?}

    Returns:
        수정된 템플릿 dict 또는 None (실패/권한 없음)
    """
    if not is_supabase_enabled():
        return None

    supabase = get_supabase()
    if not supabase:
        return None

    def operation():
        # 소유자 확인
        check = (
            supabase.table('ie_prompt_templates')
            .select('id')
            .eq('id', template_id)
            .eq('user_id', user_id)
            .limit(1)
            .execute()
        )
        if not check.data:
            return None  # 없거나 권한 없음

        update_data = {}
        for field in ('name', 'description', 'prompt_text', 'style_base'):
            if field in data:
                update_data[field] = data[field]
        if 'is_public' in data:
            update_data['is_public'] = bool(data['is_public'])

        result = (
            supabase.table('ie_prompt_templates')
            .update(update_data)
            .eq('id', template_id)
            .eq('user_id', user_id)
            .execute()
        )
        return _format_template(result.data[0], user_id) if result.data else None

    return _db_op('update_template', None, operation)


def delete_template(template_id: str, user_id: str) -> bool:
    """템플릿 삭제 (소유자만 가능)"""
    if not is_supabase_enabled():
        return False

    supabase = get_supabase()
    if not supabase:
        return False

    def operation():
        result = (
            supabase.table('ie_prompt_templates')
            .delete()
            .eq('id', template_id)
            .eq('user_id', user_id)
            .execute()
        )
        return bool(result.data)

    return _db_op('delete_template', False, operation)


def increment_usage(template_id: str) -> bool:
    """템플릿 사용 횟수 증가 (사용 시 호출)"""
    if not is_supabase_enabled():
        return False

    supabase = get_supabase()
    if not supabase:
        return False

    def operation():
        supabase.rpc('increment_template_usage', {'p_template_id': template_id}).execute()
        return True

    return _db_op('increment_usage', False, operation)


# =============================================
# 내부 헬퍼
# =============================================

def _format_template(row: dict, viewer_user_id: str | None) -> dict:
    """DB 행을 API 응답 형식으로 변환"""
    return {
        'id': row.get('id'),
        'name': row.get('name', ''),
        'description': row.get('description', ''),
        'prompt_text': row.get('prompt_text', ''),
        'style_base': row.get('style_base', 'blog_seo'),
        'is_public': row.get('is_public', False),
        'usage_count': row.get('usage_count', 0),
        'created_at': row.get('created_at'),
        'updated_at': row.get('updated_at'),
        # 소유자 여부 (UI에서 편집/삭제 버튼 표시용)
        'is_owner': viewer_user_id is not None and row.get('user_id') == viewer_user_id,
    }


def _empty_page(page: int) -> dict:
    """빈 페이지 응답"""
    return {
        'templates': [],
        'total': 0,
        'page': page,
        'per_page': PAGE_SIZE,
        'has_more': False,
    }


def _local_template(data: dict) -> dict:
    """Supabase 비활성화 시 로컬 템플릿 반환 (UUID 없음 — 클라이언트에서 처리)"""
    import time
    return {
        'id': f"local_{int(time.time() * 1000)}",
        'name': data.get('name', ''),
        'description': data.get('description', ''),
        'prompt_text': data.get('prompt_text', ''),
        'style_base': data.get('style_base', 'blog_seo'),
        'is_public': False,
        'usage_count': 0,
        'created_at': None,
        'updated_at': None,
        'is_owner': True,
    }
