"""Content analysis request service tests."""

import pytest

from services.analysis.content_analysis_request_service import build_single_field_analysis_response


def test_build_single_field_analysis_response_requires_field_value():
    payload, status = build_single_field_analysis_response(
        {"content": ""},
        field_name="content",
        required_error="content ??",
        analysis_func=lambda content: {"ok": True},
    )

    assert status == 400
    assert payload == {"error": "content ??"}


def test_build_single_field_analysis_response_calls_analyzer_with_value():
    calls = []

    payload, status = build_single_field_analysis_response(
        {"content": "??? ??"},
        field_name="content",
        required_error="content ??",
        analysis_func=lambda content: calls.append(content) or {"verdict": "ok"},
    )

    assert status == 200
    assert payload == {"verdict": "ok"}
    assert calls == ["??? ??"]


def test_build_single_field_analysis_response_uses_configured_field_and_error():
    payload, status = build_single_field_analysis_response(
        {"text": None},
        field_name="text",
        required_error="text ??",
        analysis_func=lambda text: {"ok": True},
    )

    assert status == 400
    assert payload == {"error": "text ??"}


def test_build_single_field_analysis_response_propagates_analyzer_errors():
    def fail(content):
        raise ValueError("bad content")

    with pytest.raises(ValueError, match="bad content"):
        build_single_field_analysis_response(
            {"content": "??? ??"},
            field_name="content",
            required_error="content ??",
            analysis_func=fail,
        )
