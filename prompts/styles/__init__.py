"""
스타일 패키지 v4.0
UI 노출 14개 스타일 + 내부 전용(comment_summary, mindmap, cited_summary)

콘텐츠 스타일은 베이스 규칙(prompts.base.BASE_PROMPT)과 결합되어 사용되고,
변환계 프롬프트(TRANSFORM_STYLE_IDS)는 결합 없이 단독 사용된다.
"""
import functools

from .blog_seo import BLOG_SEO_PROMPT
from .summary import SUMMARY_PROMPT
from .tutorial import TUTORIAL_PROMPT
from .qna import QNA_PROMPT
from .app_ideas import APP_IDEAS_PROMPT
from .yozm_it import YOZM_IT_PROMPT
from .brunch_essay import BRUNCH_ESSAY_PROMPT
from .naver_popular import NAVER_POPULAR_PROMPT
from .sns_post import SNS_POST_PROMPT
from .newsletter import NEWSLETTER_PROMPT
from .show_notes import SHOW_NOTES_PROMPT
from .comment_summary import COMMENT_SUMMARY_PROMPT
from .mindmap import MINDMAP_PROMPT
from .shorts_script import SHORTS_SCRIPT_PROMPT
from .geo_seo import GEO_SEO_PROMPT
from .course import COURSE_PROMPT
from .cited_summary import CITED_SUMMARY_PROMPT
from .knowledge_note import KNOWLEDGE_NOTE_PROMPT

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
    'sns_post': SNS_POST_PROMPT,
    'newsletter': NEWSLETTER_PROMPT,
    'show_notes': SHOW_NOTES_PROMPT,
    'shorts_script': SHORTS_SCRIPT_PROMPT,
    'geo_seo': GEO_SEO_PROMPT,
    'course': COURSE_PROMPT,
    'cited_summary': CITED_SUMMARY_PROMPT,
    # 내부 전용 (UI 비노출)
    'mindmap': MINDMAP_PROMPT,
    'knowledge_note': KNOWLEDGE_NOTE_PROMPT,
}

# 변환계 프롬프트 — 글쓰기 베이스 규칙(BASE_PROMPT)을 결합하지 않는 스타일
# (댓글 요약/마인드맵/챕터 분할은 콘텐츠 작성이 아니라 입력 변환 작업이므로)
TRANSFORM_STYLE_IDS = frozenset({'comment_summary', 'mindmap', 'chapter_split', 'knowledge_note'})


@functools.lru_cache(maxsize=32)
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
    'TRANSFORM_STYLE_IDS',
    'get_style_prompt',
    'BLOG_SEO_PROMPT',
    'SUMMARY_PROMPT',
    'TUTORIAL_PROMPT',
    'QNA_PROMPT',
    'APP_IDEAS_PROMPT',
    'YOZM_IT_PROMPT',
    'BRUNCH_ESSAY_PROMPT',
    'NAVER_POPULAR_PROMPT',
    'SNS_POST_PROMPT',
    'NEWSLETTER_PROMPT',
    'SHOW_NOTES_PROMPT',
    'COMMENT_SUMMARY_PROMPT',
    'MINDMAP_PROMPT',
    'SHORTS_SCRIPT_PROMPT',
    'GEO_SEO_PROMPT',
    'COURSE_PROMPT',
    'CITED_SUMMARY_PROMPT',
    'KNOWLEDGE_NOTE_PROMPT',
]
