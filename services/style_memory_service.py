"""
개인 스타일 메모리 서비스
사용자의 과거 콘텐츠 생성 패턴을 분석하여 개인화된 스타일 프로필을 학습하고,
AI 프롬프트에 자동 주입하는 기능을 담당합니다.
"""
from services.supabase_service import get_supabase, is_supabase_enabled
from services.logging_config import supabase_logger as logger

# 스타일 ID → 한국어 레이블 매핑
STYLE_LABELS = {
    'blog_seo': '블로그+SEO',
    'summary': '요약',
    'tutorial': '튜토리얼',
    'qna': 'Q&A',
    'app_ideas': '앱 아이디어',
    'yozm_it': '요즘IT',
    'brunch_essay': '브런치 에세이',
    'naver_popular': '네이버 인기글',
    'sns_post': 'SNS 게시글',
    'newsletter': '뉴스레터',
    'show_notes': '쇼 노트',
    'shorts_script': 'Shorts 스크립트',
    'geo_seo': 'GEO SEO',
}

# 문체 → 한국어 레이블 매핑
WRITING_STYLE_LABELS = {
    'conversational': '대화체',
    'explanatory': '설명체',
    'casual': '캐주얼',
    'expert': '전문가체',
}

# 길이 → 한국어 레이블 매핑
LENGTH_LABELS = {
    'short': '짧게',
    'medium': '보통',
    'long': '길게',
}

# 기본 프로필 값
DEFAULT_PROFILE = {
    'preferred_styles': [],
    'preferred_length': 'medium',
    'preferred_writing_style': 'conversational',
    'tone_keywords': [],
    'avoid_keywords': [],
    'custom_instructions': '',
    'style_memory_enabled': True,
    'generation_count': 0,
}


def _db_op(name: str, default, fn):
    """DB 작업 공통 래퍼 (에러 로깅 통합)"""
    try:
        return fn()
    except Exception as e:
        logger.error(f"[StyleMemory] {name} 오류: {e}")
        return default


def get_profile(user_id: str) -> dict:
    """사용자의 스타일 프로필을 조회합니다.

    Supabase 비활성화 또는 프로필 없음 시 기본값을 반환합니다.

    Args:
        user_id: 조회할 사용자 ID

    Returns:
        dict: 스타일 프로필 (기본값 포함)
    """
    if not is_supabase_enabled():
        return dict(DEFAULT_PROFILE)

    supabase = get_supabase()
    if not supabase:
        return dict(DEFAULT_PROFILE)

    def operation():
        result = (
            supabase.table('ie_style_profiles')
            .select('*')
            .eq('user_id', user_id)
            .limit(1)
            .execute()
        )
        if not result.data:
            return dict(DEFAULT_PROFILE)

        row = result.data[0]
        return {
            'preferred_styles': row.get('preferred_styles') or [],
            'preferred_length': row.get('preferred_length') or 'medium',
            'preferred_writing_style': row.get('preferred_writing_style') or 'conversational',
            'tone_keywords': row.get('tone_keywords') or [],
            'avoid_keywords': row.get('avoid_keywords') or [],
            'custom_instructions': row.get('custom_instructions') or '',
            'style_memory_enabled': row.get('style_memory_enabled', True),
            'generation_count': row.get('generation_count') or 0,
        }

    return _db_op('get_profile', dict(DEFAULT_PROFILE), operation)


def update_profile(user_id: str, generation_params: dict) -> None:
    """생성 완료 시 사용자 스타일 프로필을 업데이트합니다.

    사용한 스타일/길이/문체 빈도를 추적하여 선호도를 자동 갱신합니다.
    fire-and-forget 패턴으로 호출해야 합니다 (응답 블로킹 금지).

    Args:
        user_id: 업데이트할 사용자 ID
        generation_params: 생성에 사용된 파라미터
            - style: 사용한 스타일 ID
            - modifiers: {length, writing_style} 딕셔너리
    """
    if not is_supabase_enabled():
        return

    supabase = get_supabase()
    if not supabase:
        return

    style_id = generation_params.get('style', '')
    modifiers = generation_params.get('modifiers') or {}
    length = modifiers.get('length', 'medium')
    writing_style = modifiers.get('writing_style', 'conversational')

    def operation():
        # 기존 프로필 조회
        result = (
            supabase.table('ie_style_profiles')
            .select('*')
            .eq('user_id', user_id)
            .limit(1)
            .execute()
        )

        if result.data:
            # 기존 프로필 업데이트
            row = result.data[0]
            existing_styles = row.get('preferred_styles') or []
            updated_styles = _increment_style_count(existing_styles, style_id)
            dominant_length = _get_dominant_value(updated_styles, 'length', length)
            dominant_ws = _get_dominant_value(updated_styles, 'writing_style', writing_style)

            supabase.table('ie_style_profiles').update({
                'preferred_styles': updated_styles,
                'preferred_length': dominant_length,
                'preferred_writing_style': dominant_ws,
                'generation_count': (row.get('generation_count') or 0) + 1,
                'last_updated': 'now()',
            }).eq('user_id', user_id).execute()
        else:
            # 신규 프로필 생성
            initial_styles = _increment_style_count([], style_id)
            supabase.table('ie_style_profiles').insert({
                'user_id': user_id,
                'preferred_styles': initial_styles,
                'preferred_length': length,
                'preferred_writing_style': writing_style,
                'tone_keywords': [],
                'avoid_keywords': [],
                'custom_instructions': '',
                'style_memory_enabled': True,
                'generation_count': 1,
            }).execute()

    _db_op('update_profile', None, operation)


def save_user_preferences(user_id: str, preferences: dict) -> bool:
    """사용자가 직접 설정한 선호도를 저장합니다.

    Args:
        user_id: 저장할 사용자 ID
        preferences: 변경할 필드
            - avoid_keywords: list[str] — 피하고 싶은 표현
            - custom_instructions: str — 커스텀 지시사항
            - style_memory_enabled: bool — 기능 활성화 여부

    Returns:
        bool: 저장 성공 여부
    """
    if not is_supabase_enabled():
        return False

    supabase = get_supabase()
    if not supabase:
        return False

    # 허용된 필드만 업데이트
    allowed_fields = {'avoid_keywords', 'custom_instructions', 'style_memory_enabled'}
    update_data = {}

    if 'avoid_keywords' in preferences:
        keywords = preferences['avoid_keywords']
        if isinstance(keywords, list):
            # 각 키워드: 문자열, 최대 20자, 최대 20개
            update_data['avoid_keywords'] = [
                str(k)[:20] for k in keywords if k
            ][:20]

    if 'custom_instructions' in preferences:
        instructions = preferences['custom_instructions']
        if isinstance(instructions, str):
            update_data['custom_instructions'] = instructions.strip()[:500]

    if 'style_memory_enabled' in preferences:
        update_data['style_memory_enabled'] = bool(preferences['style_memory_enabled'])

    if not update_data:
        return False

    def operation():
        # upsert: 없으면 생성, 있으면 업데이트
        check = (
            supabase.table('ie_style_profiles')
            .select('user_id')
            .eq('user_id', user_id)
            .limit(1)
            .execute()
        )

        if check.data:
            supabase.table('ie_style_profiles').update(update_data).eq('user_id', user_id).execute()
        else:
            supabase.table('ie_style_profiles').insert({
                **DEFAULT_PROFILE,
                'user_id': user_id,
                **update_data,
            }).execute()

        return True

    return _db_op('save_user_preferences', False, operation) or False


def reset_profile(user_id: str) -> bool:
    """사용자 스타일 프로필을 기본값으로 초기화합니다.

    Args:
        user_id: 초기화할 사용자 ID

    Returns:
        bool: 초기화 성공 여부
    """
    if not is_supabase_enabled():
        return False

    supabase = get_supabase()
    if not supabase:
        return False

    def operation():
        supabase.table('ie_style_profiles').upsert({
            'user_id': user_id,
            'preferred_styles': [],
            'preferred_length': 'medium',
            'preferred_writing_style': 'conversational',
            'tone_keywords': [],
            'avoid_keywords': [],
            'custom_instructions': '',
            'style_memory_enabled': True,
            'generation_count': 0,
        }).execute()
        return True

    return _db_op('reset_profile', False, operation) or False


def build_style_context(profile: dict) -> str:
    """스타일 프로필에서 AI 프롬프트 주입용 컨텍스트 문자열을 생성합니다.

    프로필이 비어있거나 style_memory_enabled=False이면 빈 문자열을 반환합니다.

    Args:
        profile: get_profile()이 반환한 프로필 dict

    Returns:
        str: '[사용자 선호 스타일]\\n...' 형식 문자열 또는 빈 문자열
    """
    if not profile:
        return ''

    if not profile.get('style_memory_enabled', True):
        return ''

    lines = []

    # 자주 사용하는 스타일 (상위 3개)
    preferred_styles = profile.get('preferred_styles') or []
    if preferred_styles:
        top_styles = sorted(preferred_styles, key=lambda x: x.get('count', 0), reverse=True)[:3]
        style_names = [STYLE_LABELS.get(s['style_id'], s['style_id']) for s in top_styles if 'style_id' in s]
        if style_names:
            lines.append(f"- 자주 사용 스타일: {', '.join(style_names)}")

    # 선호 길이
    preferred_length = profile.get('preferred_length', 'medium')
    length_label = LENGTH_LABELS.get(preferred_length, preferred_length)
    lines.append(f"- 선호 글 길이: {length_label}")

    # 선호 문체
    preferred_ws = profile.get('preferred_writing_style', 'conversational')
    ws_label = WRITING_STYLE_LABELS.get(preferred_ws, preferred_ws)
    lines.append(f"- 선호 문체: {ws_label}")

    # 선호 톤 키워드
    tone_keywords = profile.get('tone_keywords') or []
    if tone_keywords:
        lines.append(f"- 선호 톤: {', '.join(tone_keywords[:5])}")

    # 피하고 싶은 표현
    avoid_keywords = profile.get('avoid_keywords') or []
    if avoid_keywords:
        lines.append(f"- 피하는 표현: {', '.join(avoid_keywords[:10])}")

    # 커스텀 지시사항
    custom_instructions = (profile.get('custom_instructions') or '').strip()
    if custom_instructions:
        lines.append(f"- 추가 지시: {custom_instructions}")

    if not lines:
        return ''

    return '[사용자 선호 스타일]\n' + '\n'.join(lines)


# =============================================
# 내부 헬퍼
# =============================================

def _increment_style_count(styles: list, style_id: str) -> list:
    """스타일 목록에서 style_id의 카운트를 1 증가시킵니다.

    Args:
        styles: [{style_id, count}] 형식 목록
        style_id: 증가시킬 스타일 ID

    Returns:
        업데이트된 스타일 목록
    """
    if not style_id:
        return styles

    updated = list(styles)
    for item in updated:
        if item.get('style_id') == style_id:
            item['count'] = item.get('count', 0) + 1
            return updated

    # 없으면 새 항목 추가
    updated.append({'style_id': style_id, 'count': 1})
    return updated


def _get_dominant_value(styles: list, _field: str, fallback: str) -> str:
    """사용 빈도가 가장 높은 스타일의 모디파이어 값을 반환합니다.

    현재 구현에서는 가장 최근 생성에 사용한 값을 기본으로,
    모든 스타일 스코어 합산이 없으므로 fallback을 그대로 반환합니다.
    향후 확장 가능한 구조로 남겨둡니다.
    """
    return fallback
