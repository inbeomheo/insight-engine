"""직접 텍스트 입력(paste-text) /generate 경로 테스트."""
from __future__ import annotations

from unittest.mock import patch

from app import create_app
from config import DIRECT_TEXT_MAX_CHARS, DIRECT_TEXT_MIN_CHARS

_H = {"Origin": "http://localhost:3000"}


def _app_client():
    app = create_app({"TESTING": True})
    return app, app.test_client()


def _no_auth_patches():
    return (
        patch(
            "src.contexts.identity.interface.auth_decorators.is_supabase_enabled",
            return_value=False,
        ),
        patch("services.usage.usage_decorator.is_supabase_enabled", return_value=False),
    )


def test_generate_direct_text_happy_path_sets_source_meta():
    _, client = _app_client()
    ai_result = {
        "title": "생성 제목",
        "content": "생성 본문",
        "html": "<p>생성 본문</p>",
        "usage": {"total_tokens": 1},
    }
    text = "붙여넣은 학습 텍스트입니다. 충분히 긴 내용을 담고 있습니다. " * 3

    p1, p2 = _no_auth_patches()
    with (
        p1,
        p2,
        patch("services.core.ai_service.create_content", return_value=(ai_result, "prompt")),
    ):
        resp = client.post(
            "/generate",
            json={"content": text, "style": "summary"},
            headers=_H,
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data["title"] == "생성 제목"
    assert data["content"] == "생성 본문"
    assert data["transcript_source"] == "direct_input"
    assert data["source_type"] == "text"
    assert data["source_meta"]["source_type"] == "text"
    assert data["source_meta"]["is_auto"] is False
    assert data["source_meta"]["chars"] == len(text)


def test_generate_direct_text_zai_rate_limit_returns_429_with_recovery_hint():
    _, client = _app_client()
    text = "Z.AI 요청 제한 응답을 검증하기 위한 충분히 긴 직접 입력 텍스트입니다. " * 3
    provider_error = (
        "[요청 제한] Z.AI 요청이 일시적으로 제한되었습니다. "
        "잠시 후 다시 시도하거나 OPEN AI 모델을 선택해주세요."
    )

    p1, p2 = _no_auth_patches()
    with (
        p1,
        p2,
        patch("services.core.ai_service.create_content", side_effect=Exception(provider_error)),
    ):
        resp = client.post(
            "/generate",
            json={"content": text, "model": "zai/glm-5.3-flash", "style": "summary"},
            headers=_H,
        )

    assert resp.status_code == 429
    assert resp.get_json()["error"] == provider_error


def test_generate_direct_text_empty_model_response_returns_503_not_500():
    _, client = _app_client()
    text = "빈 AI 응답을 일반 서버 오류와 구분하기 위한 충분히 긴 직접 입력 텍스트입니다. " * 3
    provider_error = (
        "[생성 실패] AI 모델이 빈 응답을 반환했습니다. "
        "잠시 후 다시 시도하거나 다른 모델을 선택해주세요."
    )

    p1, p2 = _no_auth_patches()
    with (
        p1,
        p2,
        patch("services.core.ai_service.create_content", side_effect=Exception(provider_error)),
    ):
        resp = client.post(
            "/generate",
            json={"content": text, "model": "zai/glm-5.3-flash", "style": "summary"},
            headers=_H,
        )

    assert resp.status_code == 503
    assert resp.get_json()["error"] == provider_error


def test_generate_direct_text_too_short_returns_400_korean_message():
    _, client = _app_client()

    p1, p2 = _no_auth_patches()
    with p1, p2:
        resp = client.post(
            "/generate",
            json={"content": "짧은 텍스트"},
            headers=_H,
        )

    assert resp.status_code == 400
    assert "50자 이상" in resp.get_json()["error"]


def test_generate_direct_text_blank_returns_400():
    _, client = _app_client()

    p1, p2 = _no_auth_patches()
    with p1, p2:
        resp = client.post(
            "/generate",
            json={"content": "   "},
            headers=_H,
        )

    assert resp.status_code == 400
    assert "50자 이상" in resp.get_json()["error"]


def test_generate_direct_text_over_max_chars_returns_400():
    _, client = _app_client()
    oversized_text = "가" * (DIRECT_TEXT_MAX_CHARS + 1)

    p1, p2 = _no_auth_patches()
    with p1, p2:
        resp = client.post(
            "/generate",
            json={"content": oversized_text},
            headers=_H,
        )

    assert resp.status_code == 400
    assert "너무 깁니다" in resp.get_json()["error"]


def test_generate_no_url_no_content_returns_400():
    _, client = _app_client()

    p1, p2 = _no_auth_patches()
    with p1, p2:
        resp = client.post("/generate", json={}, headers=_H)

    assert resp.status_code == 400


def test_generate_direct_text_exactly_at_min_chars_passes():
    """정확히 DIRECT_TEXT_MIN_CHARS 길이의 텍스트는 통과해야 한다."""
    _, client = _app_client()
    ai_result = {
        "title": "T", "content": "C", "html": "<p>C</p>",
        "usage": {"total_tokens": 1},
    }
    text = "가" * DIRECT_TEXT_MIN_CHARS

    p1, p2 = _no_auth_patches()
    with (
        p1,
        p2,
        patch("services.core.ai_service.create_content", return_value=(ai_result, "prompt")),
    ):
        resp = client.post("/generate", json={"content": text}, headers=_H)

    assert resp.status_code == 200


def test_generate_direct_text_exactly_at_max_chars_passes():
    """정확히 DIRECT_TEXT_MAX_CHARS 길이의 텍스트는 통과해야 한다 (설정값을 작게 패치)."""
    _, client = _app_client()
    ai_result = {
        "title": "T", "content": "C", "html": "<p>C</p>",
        "usage": {"total_tokens": 1},
    }
    text = "가" * 100

    p1, p2 = _no_auth_patches()
    with (
        p1,
        p2,
        patch("config.DIRECT_TEXT_MAX_CHARS", 100),
        patch("services.core.ai_service.create_content", return_value=(ai_result, "prompt")),
    ):
        resp = client.post("/generate", json={"content": text}, headers=_H)

    assert resp.status_code == 200


def test_generate_url_and_blank_content_url_path_wins():
    """url과 빈 content가 동시에 오면 URL(웹소스) 경로가 우선한다."""
    _, client = _app_client()

    p1, p2 = _no_auth_patches()
    with (
        p1,
        p2,
        patch("routes.blog_routes._handle_direct_text") as mock_direct,
        patch(
            "routes.blog_routes._handle_web_source",
            return_value=({"title": "웹", "content": "결과"}, 200),
        ) as mock_web,
    ):
        client.post(
            "/generate",
            json={"url": "https://example.com/a", "content": "   "},
            headers=_H,
        )

    mock_direct.assert_not_called()
    mock_web.assert_called_once()


def test_generate_url_and_content_together_returns_400():
    """url과 content가 동시에 오면 스트리밍 경로와 동일하게 400을 반환한다."""
    _, client = _app_client()
    text = "URL과 함께 보내면 안 되는 충분히 긴 직접 입력 텍스트입니다. " * 3

    p1, p2 = _no_auth_patches()
    with (
        p1,
        p2,
        patch("routes.blog_routes._handle_direct_text") as mock_direct,
        patch("routes.blog_routes._handle_web_source") as mock_web,
    ):
        resp = client.post(
            "/generate",
            json={"url": "https://example.com/a", "content": text},
            headers=_H,
        )

    assert resp.status_code == 400
    assert "동시에 입력할 수 없습니다" in resp.get_json()["error"]
    mock_direct.assert_not_called()
    mock_web.assert_not_called()


def test_generate_direct_text_source_meta_quality_score_is_one():
    """직접 입력 텍스트는 자동 추출이 아니므로 quality_score가 1.0으로 고정된다."""
    _, client = _app_client()
    ai_result = {
        "title": "T", "content": "C", "html": "<p>C</p>",
        "usage": {"total_tokens": 1},
    }
    text = "충분히 긴 붙여넣기 텍스트입니다. " * 5

    p1, p2 = _no_auth_patches()
    with (
        p1,
        p2,
        patch("services.core.ai_service.create_content", return_value=(ai_result, "prompt")),
    ):
        resp = client.post("/generate", json={"content": text}, headers=_H)

    assert resp.get_json()["source_meta"]["quality_score"] == 1.0


def test_generate_direct_text_saves_history_when_authenticated():
    """인증된 사용자의 직접 텍스트 생성은 아티클/YouTube와 동일하게 히스토리에 저장된다."""
    from flask import g

    app = create_app({"TESTING": True})
    ai_result = {
        "title": "생성 제목", "content": "생성 본문", "html": "<p>생성 본문</p>",
        "usage": {"total_tokens": 1},
    }
    text = "충분히 긴 붙여넣기 텍스트입니다. " * 5

    with app.test_request_context(
        "/generate", method="POST", json={"content": text, "style": "summary"}, headers=_H
    ):
        g.user_id = "test-user-id"
        g.skip_usage_decrement = False

        with (
            patch("routes.generation_helpers.get_usage_for_response", return_value={}),
            patch("services.core.ai_service.create_content", return_value=(ai_result, "prompt")),
            patch("routes.generation_helpers.save_history") as mock_save,
        ):
            from routes.generation_helpers import _handle_direct_text
            from routes.blog_routes import _get_request_data
            from flask import request

            params = _get_request_data(request)
            _handle_direct_text(params, 0)

        mock_save.assert_called_once()
        call_user_id, call_data = mock_save.call_args[0]
        assert call_user_id == "test-user-id"
        assert call_data["title"] == "생성 제목"
        assert call_data["content"] == "생성 본문"
        assert call_data["transcript_source"] == "direct_input"
        assert call_data["transcript"] == text[:5000]
