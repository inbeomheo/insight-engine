"""Quiz generation request service tests."""

import pytest

from services.content.quiz_generation_request_service import build_quiz_generation_response


def test_build_quiz_generation_response_requires_content():
    payload, status = build_quiz_generation_response(
        {"content": "   "},
        generate_quiz_func=lambda content, count: {"ok": True},
    )

    assert status == 400
    assert payload == {"error": "content required"}


def test_build_quiz_generation_response_defaults_count():
    calls = []

    payload, status = build_quiz_generation_response(
        {"content": "sample content"},
        generate_quiz_func=(
            lambda content, count: calls.append((content, count)) or {"quiz": []}
        ),
    )

    assert status == 200
    assert payload == {"quiz": []}
    assert calls == [("sample content", 5)]


def test_build_quiz_generation_response_passes_count():
    calls = []

    payload, status = build_quiz_generation_response(
        {"content": "sample content", "count": 3},
        generate_quiz_func=(
            lambda content, count: calls.append((content, count)) or {"quiz": [1, 2, 3]}
        ),
    )

    assert status == 200
    assert payload == {"quiz": [1, 2, 3]}
    assert calls == [("sample content", 3)]


def test_build_quiz_generation_response_propagates_generator_errors():
    def fail(content, count):
        raise ValueError("bad quiz input")

    with pytest.raises(ValueError, match="bad quiz input"):
        build_quiz_generation_response(
            {"content": "sample content"},
            generate_quiz_func=fail,
        )
