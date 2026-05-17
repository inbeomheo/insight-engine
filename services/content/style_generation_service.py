"""AI custom style generation service."""

from __future__ import annotations

from collections.abc import Mapping
import json
import re
from typing import Any


def generate_custom_style(
    data: Mapping[str, Any],
    *,
    content_api: Any,
    ai_client: Any,
    default_model: str,
) -> tuple[dict[str, Any], int]:
    """Generate a custom blog style prompt for a YouTube URL."""
    url = data.get("url")
    model = data.get("model", default_model)

    if not url:
        return {"error": "YouTube URL이 필요합니다."}, 400
    if not content_api.is_youtube_url(url):
        return {"error": "유효한 YouTube URL을 입력해주세요."}, 400

    video_id = content_api.get_video_id(url)
    if not video_id:
        return {"error": "유효하지 않은 YouTube URL입니다."}, 400

    title = content_api.get_content_title(url) or "YouTube 영상"
    transcript_preview = _build_transcript_preview(content_api.get_transcript(video_id))
    prompt = _build_generation_prompt(title=title, transcript_preview=transcript_preview)

    response = ai_client.create_content(prompt, model, style_prompt="")
    content = response.get("content", "")
    json_match = re.search(r"\{[\s\S]*\}", content)
    if not json_match:
        return {"error": "AI 응답을 파싱할 수 없습니다.", "title": title}, 500

    try:
        result = json.loads(json_match.group())
    except json.JSONDecodeError:
        return {"error": "AI 응답 JSON 파싱 실패", "title": title}, 500

    result["title"] = title
    return result, 200


def _build_transcript_preview(transcript: Any) -> str:
    if isinstance(transcript, dict) and transcript.get("error"):
        return "(자막 없음)"

    text = transcript.get("text", "") if isinstance(transcript, dict) else str(transcript or "")
    return text[:500] if text else "(자막 없음)"


def _build_generation_prompt(*, title: str, transcript_preview: str) -> str:
    return f"""다음 YouTube 영상의 제목과 자막 일부를 분석하여, 이 영상 콘텐츠에 최적화된 블로그 작성 프롬프트를 생성해주세요.

영상 제목: {title}
자막 미리보기: {transcript_preview}

다음 JSON 형식으로만 응답해주세요:
{{
    "styleName": "이 스타일의 이름 (10자 이내, 예: '기술 분석', '리뷰 정리')",
    "stylePrompt": "AI가 블로그를 작성할 때 사용할 상세 프롬프트 (200-400자)",
    "description": "이 스타일이 왜 이 영상에 적합한지 (30자 이내)"
}}"""
