"""
Collector 도구 — URL에서 콘텐츠 수집

multi_source_collector 서비스를 Tool로 래핑.
YouTube, 웹페이지, arXiv, RSS, Twitter, Reddit, GitHub, HN, Podcast, SO 지원.
"""
from __future__ import annotations

import json
import logging

from agent.registry import registry

logger = logging.getLogger(__name__)


def _handle_collect_content(args: dict, **kwargs) -> str:
    """URL에서 콘텐츠를 수집합니다."""
    from services.content.multi_source_collector import collect_content, detect_source_type

    url = args.get("url", "").strip()
    source_type = args.get("source_type")

    if not url:
        return json.dumps({"error": "url이 필요합니다."})

    try:
        result = collect_content(url, source_type=source_type)
        # 콘텐츠가 너무 길면 자르기 (LLM 컨텍스트 보호)
        content = result.get("content", "")
        if len(content) > 50000:
            result["content"] = content[:50000] + f"\n\n... [콘텐츠 축약: {len(content)}자 → 50000자]"
            result["truncated"] = True
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"error": f"콘텐츠 수집 실패: {e}"}, ensure_ascii=False)


def _handle_detect_source(args: dict, **kwargs) -> str:
    """URL의 소스 타입을 감지합니다."""
    from services.content.multi_source_collector import detect_source_type

    url = args.get("url", "").strip()
    if not url:
        return json.dumps({"error": "url이 필요합니다."})

    source_type = detect_source_type(url)
    return json.dumps({"url": url, "source_type": source_type})


# ── 통합 수집 도구 ──

registry.register(
    name="collect_content",
    toolset="collector",
    description=(
        "URL에서 콘텐츠를 자동 수집합니다. "
        "YouTube 자막, 웹페이지 본문, arXiv 논문, RSS 피드, "
        "Twitter 스레드, Reddit 포스트, GitHub README 등을 지원합니다. "
        "URL 타입은 자동 감지됩니다."
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "수집할 콘텐츠의 URL",
            },
            "source_type": {
                "type": "string",
                "enum": [
                    "youtube", "webpage", "arxiv", "rss", "twitter",
                    "reddit", "github", "hackernews", "podcast", "stackoverflow",
                ],
                "description": "소스 타입 (생략하면 자동 감지)",
            },
        },
        "required": ["url"],
    },
    handler=_handle_collect_content,
)

registry.register(
    name="detect_source_type",
    toolset="collector",
    description="URL의 소스 타입을 감지합니다 (youtube, webpage, arxiv 등).",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "감지할 URL"},
        },
        "required": ["url"],
    },
    handler=_handle_detect_source,
)
