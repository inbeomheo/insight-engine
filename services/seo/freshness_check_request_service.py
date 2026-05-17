"""Freshness check request helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def build_freshness_check_response(
    data: Mapping[str, Any],
    *,
    check_freshness_func: Callable[[Any, Any], dict[str, Any]],
    required_content_error: str = "content required",
    required_published_date_error: str = "published_date required",
) -> tuple[dict[str, Any], int]:
    """Validate freshness check input and build the response payload."""
    content = data.get("content", "")
    if not content or not content.strip():
        return {"error": required_content_error}, 400

    published_date = data.get("published_date", "")
    if not published_date:
        return {"error": required_published_date_error}, 400

    return check_freshness_func(content, published_date), 200
