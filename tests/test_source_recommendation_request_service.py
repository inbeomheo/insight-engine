"""Source recommendation request service tests."""

import pytest

from services.content.source_recommendation_request_service import build_source_recommendation_response


def test_build_source_recommendation_response_requires_topic():
    payload, status = build_source_recommendation_response(
        {"topic": "   "},
        recommend_sources_func=lambda topic: [],
    )

    assert status == 400
    assert payload == {"error": "주제를 입력해주세요."}


def test_build_source_recommendation_response_strips_topic_and_returns_sources():
    calls = []

    payload, status = build_source_recommendation_response(
        {"topic": "  AI 뉴스  "},
        recommend_sources_func=lambda topic: calls.append(topic) or ["공식 블로그"],
    )

    assert status == 200
    assert payload == {"sources": ["공식 블로그"]}
    assert calls == ["AI 뉴스"]


def test_build_source_recommendation_response_propagates_domain_errors():
    def fail(topic):
        raise ValueError("unsupported topic")

    with pytest.raises(ValueError, match="unsupported topic"):
        build_source_recommendation_response(
            {"topic": "AI"},
            recommend_sources_func=fail,
        )
