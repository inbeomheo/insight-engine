"""
Core 도구 — AI 콘텐츠 생성 + YouTube 자막/댓글 추출

services/core/ 서비스를 Tool로 래핑.
config.py 의존성을 함수 파라미터로 주입.
"""
from __future__ import annotations

import json
import logging

from agent.registry import registry

logger = logging.getLogger(__name__)


# ── create_content ──

def _handle_create_content(args: dict, **kwargs) -> str:
    """AI 모델로 콘텐츠를 생성합니다."""
    from services.core.ai_service import create_content

    transcript = args.get("transcript", "")
    style_prompt = args.get("style_prompt", "")
    style_id = args.get("style_id", "blog_seo")
    model = args.get("model")
    language = args.get("language", "ko")

    if not transcript:
        return json.dumps({"error": "transcript가 필요합니다."})

    # style_prompt 없으면 기본 프롬프트 빌드
    if not style_prompt:
        try:
            from prompts import build_full_prompt
            modifiers = {"language": language}
            style_prompt = build_full_prompt(style_id, modifiers)
        except Exception:
            style_prompt = f"다음 자막을 기반으로 {style_id} 스타일의 콘텐츠를 작성하세요."

    try:
        result = create_content(
            transcript=transcript,
            style_prompt=style_prompt,
            model=model,
            style_id=style_id,
        )
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"콘텐츠 생성 실패: {e}"}, ensure_ascii=False)


registry.register(
    name="create_content",
    toolset="core",
    description=(
        "AI 모델을 사용하여 콘텐츠를 생성합니다. "
        "자막 텍스트와 스타일을 기반으로 블로그, 요약, 튜토리얼 등을 작성합니다. "
        "14가지 스타일 지원: blog_seo, summary, tutorial, qna, app_ideas, "
        "yozm_it, brunch_essay, naver_popular, sns_post, newsletter, "
        "show_notes, shorts_script, geo_seo, course"
    ),
    parameters={
        "type": "object",
        "properties": {
            "transcript": {
                "type": "string",
                "description": "원본 자막/콘텐츠 텍스트",
            },
            "style_id": {
                "type": "string",
                "description": "콘텐츠 스타일 ID (기본: blog_seo)",
                "default": "blog_seo",
            },
            "style_prompt": {
                "type": "string",
                "description": "커스텀 스타일 프롬프트 (생략하면 자동 빌드)",
            },
            "model": {
                "type": "string",
                "description": "사용할 AI 모델 ID (생략하면 기본 모델)",
            },
            "language": {
                "type": "string",
                "enum": ["ko", "en", "ja"],
                "description": "출력 언어 (기본: ko)",
                "default": "ko",
            },
        },
        "required": ["transcript"],
    },
    handler=_handle_create_content,
)


# ── get_transcript ──

def _handle_get_transcript(args: dict, **kwargs) -> str:
    """YouTube 영상의 자막을 추출합니다."""
    from services.core.content_service import get_transcript, get_video_id

    url = args.get("url", "")
    video_id = args.get("video_id", "")

    if not video_id and url:
        video_id = get_video_id(url)

    if not video_id:
        return json.dumps({"error": "url 또는 video_id가 필요합니다."})

    try:
        result = get_transcript(video_id)
        if isinstance(result, dict):
            if result.get("error"):
                return json.dumps({"error": result["error"]})
            text = result.get("text", "")
            source = result.get("source", "unknown")
        else:
            text = str(result)
            source = "unknown"

        # 자막이 너무 길면 자르기
        if len(text) > 80000:
            text = text[:80000] + f"\n\n... [자막 축약: 원본 {len(text)}자]"

        return json.dumps({
            "video_id": video_id,
            "text": text,
            "source": source,
            "length": len(text),
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"자막 추출 실패: {e}"}, ensure_ascii=False)


registry.register(
    name="get_transcript",
    toolset="core",
    description=(
        "YouTube 영상의 자막을 추출합니다. "
        "4단계 폴백: youtube-transcript-api → watch 파싱 → Supadata API → Whisper. "
        "URL 또는 video_id로 사용 가능합니다."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "YouTube 영상 URL",
            },
            "video_id": {
                "type": "string",
                "description": "YouTube 영상 ID (URL 대신 사용 가능)",
            },
        },
    },
    handler=_handle_get_transcript,
)


# ── get_video_comments ──

def _handle_get_comments(args: dict, **kwargs) -> str:
    """YouTube 영상의 댓글을 수집합니다."""
    from services.core.content_service import get_video_id

    url = args.get("url", "")
    video_id = args.get("video_id", "")
    max_comments = args.get("max_comments", 50)

    if not video_id and url:
        video_id = get_video_id(url)

    if not video_id:
        return json.dumps({"error": "url 또는 video_id가 필요합니다."})

    try:
        from services.core.content_service import get_video_comments
        comments = get_video_comments(video_id, max_results=max_comments)
        return json.dumps({
            "video_id": video_id,
            "comments": comments[:max_comments],
            "count": len(comments),
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"댓글 수집 실패: {e}"}, ensure_ascii=False)


registry.register(
    name="get_video_comments",
    toolset="core",
    description=(
        "YouTube 영상의 댓글을 수집합니다. "
        "YOUTUBE_API_KEY 환경변수가 필요합니다."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "YouTube 영상 URL"},
            "video_id": {"type": "string", "description": "YouTube 영상 ID"},
            "max_comments": {
                "type": "integer",
                "description": "최대 댓글 수 (기본: 50)",
                "default": 50,
            },
        },
    },
    handler=_handle_get_comments,
    check_fn=lambda: bool(__import__("os").getenv("YOUTUBE_API_KEY")),
    requires_env=["YOUTUBE_API_KEY"],
)


# ── get_content_title ──

def _handle_get_title(args: dict, **kwargs) -> str:
    """URL의 콘텐츠 제목을 가져옵니다."""
    from services.core.content_service import get_content_title

    url = args.get("url", "")
    if not url:
        return json.dumps({"error": "url이 필요합니다."})

    title = get_content_title(url) or ""
    return json.dumps({"url": url, "title": title}, ensure_ascii=False)


registry.register(
    name="get_content_title",
    toolset="core",
    description="URL의 콘텐츠 제목을 가져옵니다.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "제목을 가져올 URL"},
        },
        "required": ["url"],
    },
    handler=_handle_get_title,
)
