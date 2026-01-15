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
from .review import REVIEW_PROMPT
from .tutorial import TUTORIAL_PROMPT
from .newsletter import NEWSLETTER_PROMPT

# 스타일 프롬프트 매핑 (16개 스타일)
STYLE_PROMPTS = {
    # 블로그 계열
    'blog': BLOG_PROMPT,
    'detailed': BLOG_PROMPT,  # blog와 동일

    # 요약 계열
    'summary': SUMMARY_PROMPT,
    'easy': EASY_PROMPT,

    # 전문가 계열
    'seo': SEO_PROMPT,
    'news': NEWS_PROMPT,

    # 크리에이티브 계열
    'script': SCRIPT_PROMPT,
    'sns': SNS_PROMPT,

    # 분석 계열
    'needs': NEEDS_PROMPT,
    'compare': COMPARE_PROMPT,
    'infographic': INFOGRAPHIC_PROMPT,

    # 구조화 계열
    'qna': QNA_PROMPT,
    'mindmap': MINDMAP_PROMPT,

    # 신규 스타일
    'review': REVIEW_PROMPT,
    'tutorial': TUTORIAL_PROMPT,
    'newsletter': NEWSLETTER_PROMPT,
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
    'REVIEW_PROMPT',
    'TUTORIAL_PROMPT',
    'NEWSLETTER_PROMPT',
]
