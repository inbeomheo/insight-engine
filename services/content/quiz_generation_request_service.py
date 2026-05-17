"""Quiz generation request helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def build_quiz_generation_response(
    data: Mapping[str, Any],
    *,
    generate_quiz_func: Callable[[Any, Any], Any],
    required_error: str = "content required",
) -> tuple[Any, int]:
    """Validate quiz generation input and build the response payload."""
    content = data.get("content", "")
    if not content or not content.strip():
        return {"error": required_error}, 400

    count = data.get("count", 5)
    return generate_quiz_func(content, count), 200
