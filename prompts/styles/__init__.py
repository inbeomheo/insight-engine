"""
스타일별 프롬프트 패키지
8개 핵심 스타일: professional, summary, tutorial, review, seo, creative, analysis, structured
"""

from .professional import PROFESSIONAL_PROMPT
from .summary import SUMMARY_PROMPT
from .tutorial import TUTORIAL_PROMPT
from .review import REVIEW_PROMPT
from .seo import SEO_PROMPT
from .creative import CREATIVE_PROMPT
from .analysis import ANALYSIS_PROMPT
from .structured import STRUCTURED_PROMPT

# 스타일 프롬프트 매핑
STYLE_PROMPTS = {
    'professional': PROFESSIONAL_PROMPT,
    'summary': SUMMARY_PROMPT,
    'tutorial': TUTORIAL_PROMPT,
    'review': REVIEW_PROMPT,
    'seo': SEO_PROMPT,
    'creative': CREATIVE_PROMPT,
    'analysis': ANALYSIS_PROMPT,
    'structured': STRUCTURED_PROMPT,
}

# 하위 호환성을 위한 레거시 매핑
LEGACY_STYLE_MAP = {
    'blog': 'professional',
    'detailed': 'professional',
    'news': 'professional',
    'easy': 'tutorial',
    'script': 'creative',
    'sns': 'creative',
    'needs': 'analysis',
    'infographic': 'analysis',
    'qna': 'structured',
    'mindmap': 'structured',
    'newsletter': 'structured',
    'compare': 'review',
}

def get_style_prompt(style: str) -> str:
    """
    스타일 이름으로 프롬프트를 반환합니다.
    레거시 스타일 이름도 지원합니다.

    Args:
        style: 스타일 이름 (professional, blog, summary 등)

    Returns:
        해당 스타일의 프롬프트
    """
    # 레거시 스타일 변환
    if style in LEGACY_STYLE_MAP:
        style = LEGACY_STYLE_MAP[style]

    return STYLE_PROMPTS.get(style, PROFESSIONAL_PROMPT)


__all__ = [
    'STYLE_PROMPTS',
    'LEGACY_STYLE_MAP',
    'get_style_prompt',
    'PROFESSIONAL_PROMPT',
    'SUMMARY_PROMPT',
    'TUTORIAL_PROMPT',
    'REVIEW_PROMPT',
    'SEO_PROMPT',
    'CREATIVE_PROMPT',
    'ANALYSIS_PROMPT',
    'STRUCTURED_PROMPT',
]
