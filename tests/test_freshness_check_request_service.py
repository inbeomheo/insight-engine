"""Freshness check request service tests."""

import pytest

from services.seo.freshness_check_request_service import build_freshness_check_response


def test_build_freshness_check_response_requires_content():
    payload, status = build_freshness_check_response(
        {"content": "   ", "published_date": "2026-05-17"},
        check_freshness_func=lambda content, published_date: {"ok": True},
    )

    assert status == 400
    assert payload == {"error": "content required"}


def test_build_freshness_check_response_requires_published_date():
    payload, status = build_freshness_check_response(
        {"content": "sample content"},
        check_freshness_func=lambda content, published_date: {"ok": True},
    )

    assert status == 400
    assert payload == {"error": "published_date required"}


def test_build_freshness_check_response_calls_checker():
    calls = []

    payload, status = build_freshness_check_response(
        {"content": "sample content", "published_date": "2026-05-17"},
        check_freshness_func=(
            lambda content, published_date: calls.append((content, published_date))
            or {"status": "fresh"}
        ),
    )

    assert status == 200
    assert payload == {"status": "fresh"}
    assert calls == [("sample content", "2026-05-17")]


def test_build_freshness_check_response_propagates_checker_errors():
    def fail(content, published_date):
        raise ValueError("bad freshness input")

    with pytest.raises(ValueError, match="bad freshness input"):
        build_freshness_check_response(
            {"content": "sample content", "published_date": "2026-05-17"},
            check_freshness_func=fail,
        )
