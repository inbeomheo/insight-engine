"""Headline optimize request service tests."""

import pytest

from services.seo.headline_optimize_request_service import build_headline_optimize_response


def test_build_headline_optimize_response_requires_title():
    payload, status = build_headline_optimize_response(
        {"title": "   "},
        optimize_headline_func=lambda title, content: {"ok": True},
    )

    assert status == 400
    assert payload == {"error": "title required"}


def test_build_headline_optimize_response_defaults_content():
    calls = []

    payload, status = build_headline_optimize_response(
        {"title": "sample title"},
        optimize_headline_func=lambda title, content: calls.append((title, content)) or {"score": 88},
    )

    assert status == 200
    assert payload == {"score": 88}
    assert calls == [("sample title", "")]


def test_build_headline_optimize_response_passes_content():
    calls = []

    payload, status = build_headline_optimize_response(
        {"title": "sample title", "content": "sample content"},
        optimize_headline_func=lambda title, content: calls.append((title, content)) or {"score": 92},
    )

    assert status == 200
    assert payload == {"score": 92}
    assert calls == [("sample title", "sample content")]


def test_build_headline_optimize_response_propagates_optimizer_errors():
    def fail(title, content):
        raise ValueError("bad headline")

    with pytest.raises(ValueError, match="bad headline"):
        build_headline_optimize_response(
            {"title": "sample title"},
            optimize_headline_func=fail,
        )
