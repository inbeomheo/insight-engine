"""
프롬프트 시스템 v4.0
- 베이스 규칙(base.py) + 스타일(styles/) + 모디파이어(modifiers.py) 3계층
- 메인 생성 경로는 compose_style_prompt()로 베이스+스타일을 결합하고,
  모디파이어는 ai_service가 [추가 지시사항]으로 1회 주입한다
- build_full_prompt()는 베이스+스타일(+모디파이어)을 한 번에 조합하는 헬퍼 (fusion 등)

사용법:
    from prompts import compose_style_prompt, STYLE_PROMPTS
    prompt = compose_style_prompt('blog_seo', STYLE_PROMPTS['blog_seo'])
"""

from .base import BASE_PROMPT, FORBIDDEN_EXPRESSIONS, build_prompt, compose_style_prompt
from .modifiers import (
    MODIFIERS,
    DEFAULT_MODIFIERS,
    MODIFIER_OPTIONS,
    build_modifier_text,
    get_modifier_text
)
from .styles import (
    STYLE_PROMPTS,
    TRANSFORM_STYLE_IDS,
    get_style_prompt,
)


def build_full_prompt(style: str, modifiers: dict = None) -> str:
    """베이스 프롬프트 + 스타일 + (선택) 모디파이어를 조합하여 최종 프롬프트 생성

    Args:
        style: 스타일 이름 (blog_seo, summary, tutorial 등)
        modifiers: 모디파이어 딕셔너리. ai_service.create_content에 modifiers를
                   함께 넘기는 경로에서는 이중 주입을 피하기 위해 생략할 것.

    Returns:
        조합된 최종 프롬프트
    """
    style_prompt = STYLE_PROMPTS.get(style, STYLE_PROMPTS['blog_seo'])
    return build_prompt(style_prompt, modifiers)


__all__ = [
    # 메인 API
    'build_full_prompt',
    'compose_style_prompt',

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
    'TRANSFORM_STYLE_IDS',
    'get_style_prompt',
]
