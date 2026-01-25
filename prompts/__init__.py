"""
프롬프트 시스템 v3.0
- 5개 핵심 스타일: blog_seo, summary, tutorial, qna, app_ideas
- 2개 모디파이어: length, writing_style
- 레거시 호환성 완전 제거

사용법:
    from prompts import build_full_prompt
    prompt = build_full_prompt('blog_seo', {'length': 'medium', 'writing_style': 'conversational'})
"""

from .base import BASE_PROMPT, FORBIDDEN_EXPRESSIONS, build_prompt
from .modifiers import (
    MODIFIERS,
    DEFAULT_MODIFIERS,
    MODIFIER_OPTIONS,
    build_modifier_text,
    get_modifier_text
)
from .styles import (
    STYLE_PROMPTS,
    get_style_prompt,
    BLOG_SEO_PROMPT,
    SUMMARY_PROMPT,
    TUTORIAL_PROMPT,
    QNA_PROMPT,
    APP_IDEAS_PROMPT,
)


def build_full_prompt(style: str, modifiers: dict = None) -> str:
    """
    베이스 프롬프트 + 스타일 + 모디파이어를 조합하여 최종 프롬프트 생성

    Args:
        style: 스타일 이름 (blog_seo, summary, tutorial, qna, app_ideas)
        modifiers: 모디파이어 딕셔너리
                   {'length': 'medium', 'writing_style': 'conversational'}
                   지정하지 않은 항목은 기본값 사용

    Returns:
        조합된 최종 프롬프트

    Example:
        >>> prompt = build_full_prompt('blog_seo', {'length': 'long', 'writing_style': 'expert'})
    """
    # 스타일 프롬프트 가져오기
    style_prompt = STYLE_PROMPTS.get(style, BLOG_SEO_PROMPT)

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
        'blog_seo': '🔍 블로그+SEO',
        'summary': '⚡ 요약',
        'tutorial': '📚 튜토리얼',
        'qna': '❓ Q&A',
        'app_ideas': '💡 앱 아이디어',
    }


def get_modifier_info() -> dict:
    """
    모디파이어 정보 반환 (UI 구성용)

    Returns:
        MODIFIER_OPTIONS 딕셔너리
    """
    return MODIFIER_OPTIONS


__all__ = [
    # 메인 API
    'build_full_prompt',
    'get_available_styles',
    'get_modifier_info',

    # 베이스
    'BASE_PROMPT',
    'FORBIDDEN_EXPRESSIONS',
    'build_prompt',

    # 모디파이어
    'MODIFIERS',
    'DEFAULT_MODIFIERS',
    'MODIFIER_OPTIONS',
    'build_modifier_text',
    'get_modifier_text',

    # 스타일 프롬프트
    'STYLE_PROMPTS',
    'get_style_prompt',
    'BLOG_SEO_PROMPT',
    'SUMMARY_PROMPT',
    'TUTORIAL_PROMPT',
    'QNA_PROMPT',
    'APP_IDEAS_PROMPT',
]
