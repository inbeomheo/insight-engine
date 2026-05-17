"""Source recommendation request helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def build_source_recommendation_response(
    data: Mapping[str, Any],
    *,
    recommend_sources_func: Callable[[str], list],
) -> tuple[dict[str, Any], int]:
    """Validate request data and build the source recommendation response."""
    topic = str(data.get("topic", "")).strip()
    if not topic:
        return {"error": "주제를 입력해주세요."}, 400

    sources = recommend_sources_func(topic)
    return {"sources": sources}, 200
