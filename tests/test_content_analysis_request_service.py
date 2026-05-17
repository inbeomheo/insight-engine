"""Content analysis request service tests."""

import pytest

from services.analysis.content_analysis_request_service import build_single_field_analysis_response


def test_build_single_field_analysis_response_requires_field_value():
    payload, status = build_single_field_analysis_response(
        {"content": ""},
        field_name="content",
        required_error="content required",
        analysis_func=lambda content: {"ok": True},
    )

    assert status == 400
    assert payload == {"error": "content required"}


def test_build_single_field_analysis_response_calls_analyzer_with_value():
    calls = []

    payload, status = build_single_field_analysis_response(
        {"content": "sample body"},
        field_name="content",
        required_error="content required",
        analysis_func=lambda content: calls.append(content) or {"verdict": "ok"},
    )

    assert status == 200
    assert payload == {"verdict": "ok"}
    assert calls == ["sample body"]


def test_build_single_field_analysis_response_uses_configured_field_and_error():
    payload, status = build_single_field_analysis_response(
        {"text": None},
        field_name="text",
        required_error="text required",
        analysis_func=lambda text: {"ok": True},
    )

    assert status == 400
    assert payload == {"error": "text required"}


def test_build_single_field_analysis_response_propagates_analyzer_errors():
    def fail(content):
        raise ValueError("bad content")

    with pytest.raises(ValueError, match="bad content"):
        build_single_field_analysis_response(
            {"content": "sample body"},
            field_name="content",
            required_error="content required",
            analysis_func=fail,
        )


def test_build_single_field_analysis_response_can_reject_blank_strings():
    payload, status = build_single_field_analysis_response(
        {"content": "   "},
        field_name="content",
        required_error="blank content",
        analysis_func=lambda content: {"ok": True},
        strip_strings=True,
    )

    assert status == 400
    assert payload == {"error": "blank content"}
