"""Wordcloud route request helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def build_wordcloud_response(
    data: Mapping[str, Any],
    *,
    generate_wordcloud_func: Callable[..., str],
) -> tuple[dict[str, Any], int]:
    """Validate request data and build the wordcloud response."""
    text = data.get("text", "")
    max_words = min(int(data.get("max_words", 60)), 100)

    if not text:
        return {"error": "텍스트가 필요합니다."}, 400

    svg = generate_wordcloud_func(text, max_words=max_words)
    return {"svg": svg}, 200
