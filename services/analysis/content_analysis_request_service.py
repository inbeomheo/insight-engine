"""Request helpers for simple content analysis endpoints."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def build_single_field_analysis_response(
    data: Mapping[str, Any],
    *,
    field_name: str,
    required_error: str,
    analysis_func: Callable[[Any], dict[str, Any]],
) -> tuple[dict[str, Any], int]:
    """Validate one required field and build an analysis response payload."""
    value = data.get(field_name, "")
    if not value:
        return {"error": required_error}, 400

    return analysis_func(value), 200
