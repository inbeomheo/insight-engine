"""
스타일 패키지 v3.1
8개 스타일: blog_seo, summary, tutorial, qna, app_ideas, yozm_it, brunch_essay, naver_popular
+ 댓글 요약 전용 프롬프트 (UI 비노출)
"""

from .blog_seo import BLOG_SEO_PROMPT
from .summary import SUMMARY_PROMPT
from .tutorial import TUTORIAL_PROMPT
from .qna import QNA_PROMPT
from .app_ideas import APP_IDEAS_PROMPT
from .yozm_it import YOZM_IT_PROMPT
from .brunch_essay import BRUNCH_ESSAY_PROMPT
from .naver_popular import NAVER_POPULAR_PROMPT
from .comment_summary import COMMENT_SUMMARY_PROMPT

# 스타일 프롬프트 매핑
STYLE_PROMPTS = {
    'blog_seo': BLOG_SEO_PROMPT,
    'summary': SUMMARY_PROMPT,
    'tutorial': TUTORIAL_PROMPT,
    'qna': QNA_PROMPT,
    'app_ideas': APP_IDEAS_PROMPT,
    'yozm_it': YOZM_IT_PROMPT,
    'brunch_essay': BRUNCH_ESSAY_PROMPT,
    'naver_popular': NAVER_POPULAR_PROMPT,
}


def get_style_prompt(style: str) -> str:
    """
    스타일 이름으로 프롬프트를 반환합니다.

    Args:
        style: 스타일 이름 (blog_seo, summary, tutorial, qna, app_ideas, yozm_it, brunch_essay, naver_popular)

    Returns:
        해당 스타일의 프롬프트 (없으면 blog_seo 기본값)
    """
    return STYLE_PROMPTS.get(style, BLOG_SEO_PROMPT)


__all__ = [
    'STYLE_PROMPTS',
    'get_style_prompt',
    'BLOG_SEO_PROMPT',
    'SUMMARY_PROMPT',
    'TUTORIAL_PROMPT',
    'QNA_PROMPT',
    'APP_IDEAS_PROMPT',
    'YOZM_IT_PROMPT',
    'BRUNCH_ESSAY_PROMPT',
    'NAVER_POPULAR_PROMPT',
    'COMMENT_SUMMARY_PROMPT',
]
