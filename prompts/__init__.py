"""
스타일별 프롬프트 템플릿 패키지
각 모듈에서 프롬프트를 가져와 STYLE_PROMPTS로 통합

사용법:
    from prompts import STYLE_PROMPTS
    prompt = STYLE_PROMPTS.get('blog', '')
"""

# 각 모듈에서 프롬프트 가져오기
from .blog import BLOG_PROMPT
from .summary import SUMMARY_PROMPT, EASY_PROMPT
from .professional import SEO_PROMPT, NEWS_PROMPT
from .creative import SCRIPT_PROMPT, SNS_PROMPT
from .analytical import NEEDS_PROMPT, COMPARE_PROMPT, INFOGRAPHIC_PROMPT
from .structured import QNA_PROMPT, MINDMAP_PROMPT

# 스타일 프롬프트 매핑
STYLE_PROMPTS = {
    'blog': BLOG_PROMPT,
    'detailed': BLOG_PROMPT,  # blog와 동일
    'seo': SEO_PROMPT,
    'summary': SUMMARY_PROMPT,
    'easy': EASY_PROMPT,
    'news': NEWS_PROMPT,
    'script': SCRIPT_PROMPT,
    'needs': NEEDS_PROMPT,
    'qna': QNA_PROMPT,
    'infographic': INFOGRAPHIC_PROMPT,
    'compare': COMPARE_PROMPT,
    'sns': SNS_PROMPT,
    'mindmap': MINDMAP_PROMPT
}

# 개별 프롬프트도 export (하위 호환성)
__all__ = [
    'STYLE_PROMPTS',
    'BLOG_PROMPT',
    'SUMMARY_PROMPT',
    'EASY_PROMPT',
    'SEO_PROMPT',
    'NEWS_PROMPT',
    'SCRIPT_PROMPT',
    'SNS_PROMPT',
    'NEEDS_PROMPT',
    'COMPARE_PROMPT',
    'INFOGRAPHIC_PROMPT',
    'QNA_PROMPT',
    'MINDMAP_PROMPT',
]
