"""
프롬프트 시스템 v2.0
- 베이스 프롬프트 + 스타일 오버라이드 구조
- 8개 핵심 스타일 (15개에서 통합)
- 7개 모디파이어 (4개에서 확장)

사용법:
    # 기존 방식 (하위 호환)
    from prompts import STYLE_PROMPTS
    prompt = STYLE_PROMPTS.get('blog', '')

    # 새로운 방식 (권장)
    from prompts import build_full_prompt
    prompt = build_full_prompt('professional', {'length': 'medium', 'tone': 'friendly'})
"""

# 새 시스템 import
from .base import BASE_PROMPT, build_prompt
from .modifiers import (
    MODIFIERS,
    DEFAULT_MODIFIERS,
    MODIFIER_OPTIONS,
    build_modifier_text,
    get_modifier_text
)
from .styles import (
    STYLE_PROMPTS as NEW_STYLE_PROMPTS,
    LEGACY_STYLE_MAP,
    get_style_prompt,
    PROFESSIONAL_PROMPT,
    SUMMARY_PROMPT,
    TUTORIAL_PROMPT,
    REVIEW_PROMPT,
    SEO_PROMPT,
    CREATIVE_PROMPT,
    ANALYSIS_PROMPT,
    STRUCTURED_PROMPT,
)

# ============================================================
# 하위 호환성을 위한 레거시 매핑
# ============================================================

# 레거시 스타일 → 새 스타일 변환
def _get_new_style(legacy_style: str) -> str:
    """레거시 스타일 이름을 새 스타일로 변환"""
    return LEGACY_STYLE_MAP.get(legacy_style, legacy_style)


# 레거시 STYLE_PROMPTS (기존 코드 호환용)
# 기존 15개 스타일 이름으로 접근 가능
STYLE_PROMPTS = {
    # 새 스타일 (8개)
    'professional': PROFESSIONAL_PROMPT,
    'summary': SUMMARY_PROMPT,
    'tutorial': TUTORIAL_PROMPT,
    'review': REVIEW_PROMPT,
    'seo': SEO_PROMPT,
    'creative': CREATIVE_PROMPT,
    'analysis': ANALYSIS_PROMPT,
    'structured': STRUCTURED_PROMPT,

    # 레거시 매핑 (15개 → 8개)
    'blog': PROFESSIONAL_PROMPT,
    'detailed': PROFESSIONAL_PROMPT,
    'news': PROFESSIONAL_PROMPT,
    'easy': TUTORIAL_PROMPT,
    'script': CREATIVE_PROMPT,
    'sns': CREATIVE_PROMPT,
    'needs': ANALYSIS_PROMPT,
    'infographic': ANALYSIS_PROMPT,
    'qna': STRUCTURED_PROMPT,
    'mindmap': STRUCTURED_PROMPT,
    'newsletter': STRUCTURED_PROMPT,
    'compare': REVIEW_PROMPT,
}

# 레거시 개별 프롬프트 export (하위 호환성)
BLOG_PROMPT = PROFESSIONAL_PROMPT
DETAILED_PROMPT = PROFESSIONAL_PROMPT
NEWS_PROMPT = PROFESSIONAL_PROMPT
EASY_PROMPT = TUTORIAL_PROMPT
SCRIPT_PROMPT = CREATIVE_PROMPT
SNS_PROMPT = CREATIVE_PROMPT
NEEDS_PROMPT = ANALYSIS_PROMPT
INFOGRAPHIC_PROMPT = ANALYSIS_PROMPT
QNA_PROMPT = STRUCTURED_PROMPT
MINDMAP_PROMPT = STRUCTURED_PROMPT
NEWSLETTER_PROMPT = STRUCTURED_PROMPT
COMPARE_PROMPT = REVIEW_PROMPT


# ============================================================
# 새 API (권장)
# ============================================================

def build_full_prompt(style: str, modifiers: dict = None) -> str:
    """
    베이스 프롬프트 + 스타일 + 모디파이어를 조합하여 최종 프롬프트 생성

    Args:
        style: 스타일 이름 (professional, summary, tutorial 등)
               레거시 이름도 지원 (blog → professional)
        modifiers: 모디파이어 딕셔너리
                   {'length': 'medium', 'tone': 'friendly', 'target': 'general', ...}
                   지정하지 않은 항목은 기본값 사용

    Returns:
        조합된 최종 프롬프트

    Example:
        >>> prompt = build_full_prompt('professional', {'length': 'long', 'tone': 'friendly'})
    """
    # 레거시 스타일 변환
    new_style = _get_new_style(style)

    # 스타일 프롬프트 가져오기
    style_prompt = NEW_STYLE_PROMPTS.get(new_style, PROFESSIONAL_PROMPT)

    # 모디파이어 기본값 적용
    final_modifiers = DEFAULT_MODIFIERS.copy()
    if modifiers:
        final_modifiers.update(modifiers)

    # 최종 프롬프트 조합
    return build_prompt(style_prompt, final_modifiers)


def get_available_styles() -> dict:
    """
    사용 가능한 스타일 목록 반환

    Returns:
        {style_id: description} 형태의 딕셔너리
    """
    return {
        'professional': '📝 전문 블로그/아티클',
        'summary': '⚡ 핵심 요약 리포트',
        'tutorial': '📚 단계별 튜토리얼',
        'review': '⭐ 리뷰/비교 분석',
        'seo': '🔍 SEO 최적화',
        'creative': '🎬 크리에이티브 (숏폼/SNS)',
        'analysis': '📊 분석 리포트',
        'structured': '📋 구조화된 정보',
    }


def get_modifier_info() -> dict:
    """
    모디파이어 정보 반환 (UI 구성용)

    Returns:
        MODIFIER_OPTIONS 딕셔너리
    """
    return MODIFIER_OPTIONS


# ============================================================
# Export
# ============================================================

__all__ = [
    # 새 API (권장)
    'build_full_prompt',
    'get_available_styles',
    'get_modifier_info',
    'BASE_PROMPT',
    'MODIFIERS',
    'DEFAULT_MODIFIERS',
    'MODIFIER_OPTIONS',

    # 새 스타일 프롬프트
    'PROFESSIONAL_PROMPT',
    'SUMMARY_PROMPT',
    'TUTORIAL_PROMPT',
    'REVIEW_PROMPT',
    'SEO_PROMPT',
    'CREATIVE_PROMPT',
    'ANALYSIS_PROMPT',
    'STRUCTURED_PROMPT',

    # 하위 호환성
    'STYLE_PROMPTS',
    'BLOG_PROMPT',
    'EASY_PROMPT',
    'NEWS_PROMPT',
    'SCRIPT_PROMPT',
    'SNS_PROMPT',
    'NEEDS_PROMPT',
    'COMPARE_PROMPT',
    'INFOGRAPHIC_PROMPT',
    'QNA_PROMPT',
    'MINDMAP_PROMPT',
    'NEWSLETTER_PROMPT',

    # 유틸리티
    'build_modifier_text',
    'get_modifier_text',
    'get_style_prompt',
    'LEGACY_STYLE_MAP',
]
