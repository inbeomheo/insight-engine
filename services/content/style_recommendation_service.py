"""AI style recommendation service."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import json
import re
from typing import Any


def _default_recommendation(title: str, *, reason: str = "기본 추천") -> dict[str, Any]:
    return {
        "style": "detailed",
        "reason": reason,
        "modifiers": {"length": "medium", "tone": "professional", "emoji": "none"},
        "title": title,
    }


def recommend_content_style(
    data: Mapping[str, Any],
    *,
    content_api: Any,
    ai_client: Any,
    style_options: Sequence[Sequence[str]],
    default_model: str,
) -> tuple[dict[str, Any], int]:
    """Recommend the best content style for a YouTube URL."""
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
    style_list = ", ".join([f"{style[0]}({style[1]})" for style in style_options])
    prompt = _build_recommendation_prompt(title=title, style_list=style_list)

    response = ai_client.create_content(prompt, model, style_prompt="")
    content = response.get("content", "")
    json_match = re.search(r"\{[\s\S]*\}", content)
    if not json_match:
        return _default_recommendation(title), 200

    try:
        recommendation = json.loads(json_match.group())
    except json.JSONDecodeError:
        return _default_recommendation(title, reason="AI 응답 파싱 실패"), 200

    recommendation["title"] = title
    return recommendation, 200


def _build_recommendation_prompt(*, title: str, style_list: str) -> str:
    return f"""다음 YouTube 영상 제목을 분석하여 가장 적합한 콘텐츠 스타일을 추천해주세요.

영상 제목: {title}

사용 가능한 스타일: {style_list}

다음 JSON 형식으로만 응답해주세요 (다른 텍스트 없이):
{{
    "style": "추천 스타일 ID",
    "reason": "추천 이유 (20자 이내)",
    "modifiers": {{
        "length": "short|medium|long",
        "tone": "professional|friendly|humorous",
        "emoji": "use|none"
    }}
}}"""
