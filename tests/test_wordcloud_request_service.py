"""Wordcloud request service tests."""

import pytest

from services.media.wordcloud_request_service import build_wordcloud_response


def test_build_wordcloud_response_requires_text():
    payload, status = build_wordcloud_response(
        {"text": ""},
        generate_wordcloud_func=lambda text, max_words: "<svg />",
    )

    assert status == 400
    assert payload == {"error": "텍스트가 필요합니다."}


def test_build_wordcloud_response_generates_svg_with_default_max_words():
    calls = []

    payload, status = build_wordcloud_response(
        {"text": "alpha beta"},
        generate_wordcloud_func=lambda text, max_words: calls.append((text, max_words)) or "<svg />",
    )

    assert status == 200
    assert payload == {"svg": "<svg />"}
    assert calls == [("alpha beta", 60)]


def test_build_wordcloud_response_clamps_max_words_to_100():
    calls = []

    payload, status = build_wordcloud_response(
        {"text": "alpha beta", "max_words": 999},
        generate_wordcloud_func=lambda text, max_words: calls.append((text, max_words)) or "<svg />",
    )

    assert status == 200
    assert payload == {"svg": "<svg />"}
    assert calls == [("alpha beta", 100)]


def test_build_wordcloud_response_propagates_invalid_max_words():
    with pytest.raises(ValueError):
        build_wordcloud_response(
            {"text": "alpha beta", "max_words": "not-a-number"},
            generate_wordcloud_func=lambda text, max_words: "<svg />",
        )
