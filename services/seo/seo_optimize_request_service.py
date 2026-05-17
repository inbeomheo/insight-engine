"""SEO optimize request helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def build_seo_optimize_response(
    data: Mapping[str, Any],
    *,
    optimize_seo_func: Callable[[Any, Any], dict[str, Any]],
    required_error: str = "content required",
) -> tuple[dict[str, Any], int]:
    """Validate SEO optimize input and build the response payload."""
    content = data.get("content", "")
    if not content:
        return {"error": required_error}, 400

    keywords = data.get("keywords", [])
    return optimize_seo_func(content, keywords), 200
