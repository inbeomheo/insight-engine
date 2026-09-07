from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from services.usage.usage_lock import UsageLockUnavailable


def _app() -> Flask:
    app = Flask(__name__)
    app.config.update(TESTING=True)
    return app


def test_worker_free_context_failure_does_not_commit_usage():
    from routes.generation_helpers import _generate_main_content_with_web_search

    app = _app()
    on_cost_start = MagicMock()
    provider = MagicMock()
    with patch(
        "services.core.ai_prompt_context.build_optional_prompt_contexts",
        side_effect=ValueError("free context failed"),
    ), patch(
        "services.core.ai_service._get_completion",
        return_value=provider,
    ), pytest.raises(Exception, match="free context failed"):
        _generate_main_content_with_web_search(
            app,
            "content",
            "chatmock/gpt-5.4-mini",
            "style",
            {},
            style_id="summary",
            on_cost_start=on_cost_start,
        )

    on_cost_start.assert_not_called()
    provider.assert_not_called()


def test_worker_lost_lease_stops_actual_provider_call():
    from routes.generation_helpers import _generate_main_content

    app = _app()
    provider = MagicMock()

    def reject_cost():
        raise UsageLockUnavailable("임대 소유권 상실")

    with patch(
        "services.core.ai_prompt_context.build_optional_prompt_contexts",
        return_value=("", "", [], "", ""),
    ), patch(
        "services.core.ai_service._get_completion",
        return_value=provider,
    ), pytest.raises(UsageLockUnavailable):
        _generate_main_content(
            app,
            "content",
            "chatmock/gpt-5.4-mini",
            "style",
            {},
            style_id="summary",
            on_cost_start=reject_cost,
        )

    provider.assert_not_called()


def test_comment_summary_does_not_swallow_usage_lock_failure():
    from routes.generation_helpers import _generate_comment_summary

    app = _app()
    with patch(
        "routes.generation_helpers.ai_service.create_content",
        side_effect=UsageLockUnavailable("임대 소유권 상실"),
    ), pytest.raises(UsageLockUnavailable):
        _generate_comment_summary(
            app,
            ["댓글"],
            "chatmock/gpt-5.4-mini",
            on_cost_start=MagicMock(),
        )


def test_youtube_comment_fallback_does_not_swallow_usage_lock_failure():
    from routes.generation_helpers import _fetch_youtube_content

    transcript = {"text": "transcript", "source": "api", "segments": []}
    with patch(
        "routes.generation_helpers.content_service.get_transcript",
        return_value=transcript,
    ), patch(
        "routes.generation_helpers.content_service.get_top_comments",
        side_effect=UsageLockUnavailable("임대 소유권 상실"),
    ), pytest.raises(UsageLockUnavailable):
        _fetch_youtube_content(
            "dQw4w9WgXcQ",
            on_cost_start=MagicMock(),
        )


def test_youtube_comment_provider_receives_trusted_callback():
    from routes.generation_helpers import _fetch_youtube_content

    callback = MagicMock()
    transcript = {"text": "transcript", "source": "api", "segments": []}
    with patch(
        "routes.generation_helpers.content_service.get_transcript",
        return_value=transcript,
    ) as get_transcript, patch(
        "routes.generation_helpers.content_service.get_top_comments",
        return_value=[],
    ) as get_comments:
        _fetch_youtube_content(
            "dQw4w9WgXcQ",
            on_cost_start=callback,
        )

    assert get_transcript.call_args.kwargs["on_cost_start"] is callback
    assert get_comments.call_args.kwargs["on_cost_start"] is callback
