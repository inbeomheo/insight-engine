"""NPS feedback request helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_SCORE_RANGE_ERROR = "score\ub294 0~10 \uc0ac\uc774\uc5ec\uc57c \ud569\ub2c8\ub2e4."


def build_nps_feedback_response(
    data: Mapping[str, Any],
    *,
    user_id: str = "anonymous",
) -> tuple[dict[str, Any], int]:
    """Validate NPS feedback input and build the response payload."""
    raw_score = data.get("score")
    try:
        score = int(raw_score)
    except (TypeError, ValueError):
        return {"error": _SCORE_RANGE_ERROR}, 400

    if not 0 <= score <= 10:
        return {"error": _SCORE_RANGE_ERROR}, 400

    return {
        "success": True,
        "user_id": user_id,
        "score": score,
        "feedback": data.get("feedback", ""),
    }, 200
