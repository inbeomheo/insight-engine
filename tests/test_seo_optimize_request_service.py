"""SEO optimize request service tests."""

import pytest

from services.seo.seo_optimize_request_service import build_seo_optimize_response


def test_build_seo_optimize_response_requires_content():
    payload, status = build_seo_optimize_response(
        {"content": ""},
        optimize_seo_func=lambda content, keywords: {"ok": True},
    )

    assert status == 400
    assert payload == {"error": "content required"}


def test_build_seo_optimize_response_defaults_keywords():
    calls = []

    payload, status = build_seo_optimize_response(
        {"content": "sample content"},
        optimize_seo_func=lambda content, keywords: calls.append((content, keywords)) or {"score": 90},
    )

    assert status == 200
    assert payload == {"score": 90}
    assert calls == [("sample content", [])]


def test_build_seo_optimize_response_passes_keywords():
    calls = []

    payload, status = build_seo_optimize_response(
        {"content": "sample content", "keywords": ["ai", "seo"]},
        optimize_seo_func=lambda content, keywords: calls.append((content, keywords)) or {"score": 95},
    )

    assert status == 200
    assert payload == {"score": 95}
    assert calls == [("sample content", ["ai", "seo"])]


def test_build_seo_optimize_response_propagates_optimizer_errors():
    def fail(content, keywords):
        raise ValueError("bad seo input")

    with pytest.raises(ValueError, match="bad seo input"):
        build_seo_optimize_response(
            {"content": "sample content"},
            optimize_seo_func=fail,
        )
