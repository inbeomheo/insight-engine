"""Headline optimize request helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def build_headline_optimize_response(
    data: Mapping[str, Any],
    *,
    optimize_headline_func: Callable[[Any, Any], dict[str, Any]],
    required_error: str = "title required",
) -> tuple[dict[str, Any], int]:
    """Validate headline optimize input and build the response payload."""
    title = data.get("title", "")
    if not title or not title.strip():
        return {"error": required_error}, 400

    content = data.get("content", "")
    return optimize_headline_func(title, content), 200
