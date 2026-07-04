"""아티클 URL /generate 경로 테스트."""
from __future__ import annotations

from unittest.mock import patch

from flask import jsonify

from app import create_app

_H = {"Origin": "http://localhost:3000"}


def _app_client():
    app = create_app({"TESTING": True})
    return app, app.test_client()


def test_generate_article_url_uses_article_text():
    _, client = _app_client()
    article = {
        "title": "원문 제목",
        "text": "아티클 본문입니다. 생성 파이프라인에 넣을 만큼 충분한 내용입니다. " * 3,
        "source_meta": {"source_type": "article", "url": "https://example.com/a"},
    }
    ai_result = {
        "title": "생성 제목",
        "content": "생성 본문",
        "html": "<p>생성 본문</p>",
        "usage": {"total_tokens": 1},
    }

    with (
        patch(
            "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
            return_value=False,
        ),
        patch("services.usage.usage_decorator.is_supabase_enabled", return_value=False),
        patch("services.content.article_service.fetch_article", return_value=article),
        patch("services.core.ai_service.create_content", return_value=(ai_result, "prompt")),
    ):
        resp = client.post(
            "/generate",
            json={"url": "https://example.com/a", "style": "summary"},
            headers=_H,
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "생성 제목"
    assert data["content"] == "생성 본문"
    assert data["source_meta"]["source_type"] == "article"
    assert data["source_title"] == "원문 제목"


def test_generate_youtube_url_still_uses_transcript_path():
    app, client = _app_client()
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def fake_save(*args, **kwargs):
        with app.app_context():
            return jsonify({"title": "YT 생성", "content": "본문"})

    with (
        patch(
            "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
            return_value=False,
        ),
        patch("services.usage.usage_decorator.is_supabase_enabled", return_value=False),
        patch("services.content.article_service.fetch_article") as mock_article,
        patch("routes.blog_routes._handle_cache_hit", return_value=None),
        patch("services.core.content_service.get_content_title", return_value="YT"),
        patch(
            "routes.blog_routes._fetch_youtube_content",
            return_value=("자막 본문", [], None, "자막 본문", "api", []),
        ) as mock_transcript,
        patch(
            "routes.blog_routes._call_ai_with_comments",
            return_value=({"title": "YT 생성", "content": "본문"}, "prompt", None),
        ),
        patch("routes.blog_routes._save_and_respond", side_effect=fake_save),
    ):
        resp = client.post("/generate", json={"url": url, "style": "summary"}, headers=_H)

    assert resp.status_code == 200
    mock_transcript.assert_called_once_with("dQw4w9WgXcQ", None)
    mock_article.assert_not_called()


def test_generate_article_value_error_keeps_safe_article_prefix():
    _, client = _app_client()

    with (
        patch(
            "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
            return_value=False,
        ),
        patch("services.usage.usage_decorator.is_supabase_enabled", return_value=False),
        patch(
            "routes.blog_routes._handle_web_source",
            side_effect=ValueError("[아티클 추출 실패] HTML 문서만 가져올 수 있습니다."),
        ),
    ):
        resp = client.post(
            "/generate",
            json={"url": "https://example.com/data.json", "style": "summary"},
            headers=_H,
        )

    assert resp.status_code == 400
    assert resp.get_json()["error"] == "[아티클 추출 실패] HTML 문서만 가져올 수 있습니다."


def test_generate_web_source_value_error_uses_safe_fallback():
    _, client = _app_client()

    with (
        patch(
            "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
            return_value=False,
        ),
        patch("services.usage.usage_decorator.is_supabase_enabled", return_value=False),
        patch(
            "routes.blog_routes._handle_web_source",
            side_effect=ValueError("requests.exceptions.ConnectionError: /home/app/.env"),
        ),
    ):
        resp = client.post(
            "/generate",
            json={"url": "https://example.com/a", "style": "summary"},
            headers=_H,
        )

    assert resp.status_code == 400
    assert resp.get_json()["error"] == "[생성 실패] 콘텐츠를 가져올 수 없습니다."
