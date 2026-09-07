"""에이전트 도구의 중첩 provider 비용 경계 회귀 테스트."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent.registry import TOOL_EXECUTION_ERROR_MESSAGE, registry
from agent.tools.collector_tools import _handle_collect_content
from agent.tools.core_tools import (
    _handle_create_content,
    _handle_get_comments,
    _handle_get_transcript,
)
from services.usage.usage_lock import UsageLockUnavailable


def _completion_response(content: str = "답변") -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))],
    )


def test_core_create_content_checks_trusted_callback_before_provider():
    events = []

    def provider(**kwargs):
        kwargs["on_cost_start"]()
        events.append("provider")
        assert kwargs["content"] == "원본 자막"
        return {"content": "생성 결과"}

    with patch(
        "services.core.ai_service.resolve_public_model",
        return_value="cliproxyapi/gpt-5.5",
    ), patch(
        "services.core.ai_service.create_content",
        side_effect=provider,
    ):
        payload = json.loads(_handle_create_content(
            {
                "transcript": "원본 자막",
                "style_prompt": "요약하세요.",
                "on_cost_start": "모델이 주입한 값",
            },
            on_cost_start=lambda: events.append("cost"),
        ))

    assert payload["content"] == "생성 결과"
    assert events == ["cost", "provider"]


def test_core_create_content_lock_loss_prevents_provider():
    provider = MagicMock()

    def reject_cost():
        raise UsageLockUnavailable("임대 소유권 상실")

    def call_ai(**kwargs):
        kwargs["on_cost_start"]()
        return provider()

    with patch(
        "services.core.ai_service.resolve_public_model",
        return_value="cliproxyapi/gpt-5.5",
    ), patch(
        "services.core.ai_service.create_content",
        side_effect=call_ai,
    ), pytest.raises(UsageLockUnavailable):
        _handle_create_content(
            {"transcript": "원본", "style_prompt": "요약"},
            on_cost_start=reject_cost,
        )

    provider.assert_not_called()


def test_core_create_content_generic_failure_hides_provider_secret():
    secret = "Bearer sk-tool-secret https://internal.example"
    with patch(
        "services.core.ai_service.resolve_public_model",
        return_value="cliproxyapi/gpt-5.5",
    ), patch(
        "services.core.ai_service.create_content",
        side_effect=RuntimeError(secret),
    ):
        payload = json.loads(_handle_create_content({
            "transcript": "원본",
            "style_prompt": "요약",
        }))

    assert payload == {"error": TOOL_EXECUTION_ERROR_MESSAGE}
    assert secret not in json.dumps(payload, ensure_ascii=False)


def test_core_transcript_forwards_callback_to_paid_fallback_boundary():
    callback = MagicMock()

    def get_transcript(video_id, *, on_cost_start=None):
        assert video_id == "video-id"
        assert on_cost_start is callback
        return {"text": "자막", "source": "cache"}

    with patch(
        "services.core.content_service.get_transcript",
        side_effect=get_transcript,
    ):
        payload = json.loads(_handle_get_transcript(
            {
                "video_id": "video-id",
                "on_cost_start": "모델이 주입한 값",
            },
            on_cost_start=callback,
        ))

    assert payload["text"] == "자막"
    callback.assert_not_called()


def test_core_comments_forwards_callback_without_running_it_on_cache_hit():
    callback = MagicMock()

    def get_comments(video_id, *, on_cost_start=None):
        assert video_id == "video-id"
        assert on_cost_start is callback
        return ["댓글"]

    with patch(
        "services.core.content_service.get_top_comments",
        side_effect=get_comments,
    ):
        payload = json.loads(_handle_get_comments(
            {"video_id": "video-id"},
            on_cost_start=callback,
        ))

    assert payload["comments"] == ["댓글"]
    callback.assert_not_called()


def test_collector_tool_forwards_only_trusted_callback():
    callback = MagicMock()

    def collect(url, source_type=None, on_cost_start=None):
        assert url == "https://youtube.com/watch?v=video-id"
        assert source_type == "youtube"
        assert on_cost_start is callback
        return {"content": "자막"}

    with patch(
        "services.content.multi_source_collector.collect_content",
        side_effect=collect,
    ):
        payload = json.loads(_handle_collect_content(
            {
                "url": "https://youtube.com/watch?v=video-id",
                "source_type": "youtube",
                "on_cost_start": "모델이 주입한 값",
            },
            on_cost_start=callback,
        ))

    assert payload["content"] == "자막"


def test_youtube_collector_threads_callback_to_transcript_service():
    from services.content.multi_source_collector import _collect_youtube

    callback = MagicMock()
    with patch(
        "services.core.content_service.get_video_id",
        return_value="video-id",
    ), patch(
        "services.core.content_service.get_transcript",
        return_value={"text": "자막", "source": "cache"},
    ) as get_transcript, patch(
        "services.core.content_service.get_content_title",
        return_value="제목",
    ) as get_title:
        result = _collect_youtube(
            "https://youtube.com/watch?v=video-id",
            on_cost_start=callback,
        )

    assert result["content"] == "자막"
    assert get_transcript.call_args.kwargs["on_cost_start"] is callback
    assert get_title.call_args.kwargs["on_cost_start"] is callback


def test_youtube_api_callback_runs_only_at_actual_comments_request():
    from app import create_app
    from services.core.content_service import get_top_comments

    events = []
    request = MagicMock()
    request.execute.side_effect = lambda: events.append("provider") or {
        "items": [],
    }
    youtube = MagicMock()
    youtube.commentThreads.return_value.list.return_value = request

    app = create_app({"TESTING": True, "YOUTUBE_API_KEY": "test-key"})
    with app.app_context(), patch(
        "services.core.content_service._load_cache",
        return_value=None,
    ), patch(
        "services.core.content_service._get_youtube_build",
        return_value=lambda *_args, **_kwargs: youtube,
    ):
        assert get_top_comments(
            "video-id",
            on_cost_start=lambda: events.append("cost"),
        ) == []

    assert events == ["cost", "provider"]


def test_youtube_comments_cache_hit_does_not_run_cost_callback():
    from services.core.content_service import get_top_comments

    callback = MagicMock()
    with patch(
        "services.core.content_service._load_cache",
        return_value=["캐시 댓글"],
    ):
        assert get_top_comments(
            "video-id",
            on_cost_start=callback,
        ) == ["캐시 댓글"]

    callback.assert_not_called()


def test_youtube_comments_lock_loss_prevents_provider_and_propagates():
    from app import create_app
    from services.core.content_service import get_top_comments

    provider = MagicMock()
    youtube = MagicMock()
    youtube.commentThreads.return_value.list.return_value.execute = provider

    def reject_cost():
        raise UsageLockUnavailable("임대 소유권 상실")

    app = create_app({"TESTING": True, "YOUTUBE_API_KEY": "test-key"})
    with app.app_context(), patch(
        "services.core.content_service._load_cache",
        return_value=None,
    ), patch(
        "services.core.content_service._get_youtube_build",
        return_value=lambda *_args, **_kwargs: youtube,
    ), pytest.raises(UsageLockUnavailable):
        get_top_comments("video-id", on_cost_start=reject_cost)

    provider.assert_not_called()


@pytest.mark.parametrize(
    "tool_name",
    [
        "generate_brief",
        "add_commentary",
        "analyze_channel",
        "generate_podcast_episode",
        "answer_question",
    ],
)
def test_auto_registered_cost_callback_is_hidden_from_model_schema(tool_name):
    from agent.tools import content_tools, media_tools  # noqa: F401

    entry = registry.get(tool_name)
    assert entry is not None
    assert "on_cost_start" not in entry.parameters["properties"]
    assert "on_cost_start" not in entry.parameters["required"]


@pytest.mark.parametrize("tool_name", ["add_commentary", "generate_podcast_episode"])
def test_auto_registered_paid_tool_model_is_hidden_from_model_schema(tool_name):
    from agent.tools import content_tools, media_tools  # noqa: F401

    entry = registry.get(tool_name)
    assert entry is not None
    assert "model" not in entry.parameters["properties"]
    assert "model" not in entry.parameters["required"]


def test_commentary_auto_wrapper_ignores_model_supplied_model():
    from agent.tools import content_tools  # noqa: F401

    with patch(
        "services.content.commentary_service._get_model",
        return_value="cliproxyapi/gpt-5.5",
    ), patch(
        "services.core.ai_service.create_content",
        return_value={"content": "원문"},
    ) as provider:
        registry.dispatch(
            "add_commentary",
            {"content": "원문", "model": "openai/arbitrary-paid-model"},
            on_cost_start=lambda: None,
        )

    assert provider.call_args.args[1] == "cliproxyapi/gpt-5.5"


def test_podcast_auto_wrapper_ignores_model_supplied_model():
    from agent.tools import media_tools  # noqa: F401

    with patch(
        "services.media.podcast_service._generate_script",
        return_value="Host: 안녕\nGuest: 반가워요",
    ) as generate_script, patch(
        "services.media.podcast_service._synthesize_podcast",
        return_value=b"audio",
    ):
        registry.dispatch(
            "generate_podcast_episode",
            {
                "content": "원문",
                "title": "제목",
                "model": "openai/arbitrary-paid-model",
            },
            on_cost_start=lambda: None,
        )

    assert generate_script.call_args.args[2] == "cliproxyapi/gpt-5.5"


def test_content_auto_wrapper_uses_trusted_callback_and_ignores_model_value():
    from agent.tools import content_tools  # noqa: F401

    events = []

    def provider(*_args, **kwargs):
        kwargs["on_cost_start"]()
        events.append("provider")
        return {"content": '{"title_suggestions": ["제목"]}'}

    with patch(
        "services.content.brief_service._get_model",
        return_value="cliproxyapi/gpt-5.5",
    ), patch(
        "services.core.ai_service.create_content",
        side_effect=provider,
    ):
        payload = json.loads(registry.dispatch(
            "generate_brief",
            {
                "topic": "주제",
                "on_cost_start": "모델이 주입한 값",
            },
            on_cost_start=lambda: events.append("cost"),
        ))

    assert payload["title_suggestions"] == ["제목"]
    assert events == ["cost", "provider"]


def test_content_auto_wrapper_rethrows_lock_loss_before_provider():
    from agent.tools import content_tools  # noqa: F401

    provider = MagicMock()

    def reject_cost():
        raise UsageLockUnavailable("임대 소유권 상실")

    def call_ai(*_args, **kwargs):
        kwargs["on_cost_start"]()
        return provider()

    with patch(
        "services.content.brief_service._get_model",
        return_value="cliproxyapi/gpt-5.5",
    ), patch(
        "services.core.ai_service.create_content",
        side_effect=call_ai,
    ), pytest.raises(UsageLockUnavailable):
        registry.dispatch(
            "generate_brief",
            {"topic": "주제"},
            on_cost_start=reject_cost,
        )

    provider.assert_not_called()


def test_media_auto_wrapper_checks_trusted_callback_before_video_qa_provider():
    from agent.tools import media_tools  # noqa: F401

    events = []

    def provider(**_kwargs):
        events.append("provider")
        return _completion_response()

    with patch(
        "services.media.video_qa_service._LITELLM_AVAILABLE",
        True,
    ), patch(
        "services.media.video_qa_service.search_relevant_chunks",
        return_value=[{"text": "자막", "chunk_index": 0, "distance": 0.1}],
    ), patch(
        "services.media.video_qa_service.litellm_completion",
        side_effect=provider,
    ):
        payload = json.loads(registry.dispatch(
            "answer_question",
            {
                "video_id": "video-id",
                "question": "질문",
                "on_cost_start": "모델이 주입한 값",
            },
            on_cost_start=lambda: events.append("cost"),
        ))

    assert payload["answer"] == "답변"
    assert events == ["cost", "provider"]


def test_media_auto_wrapper_rethrows_lock_loss_before_video_qa_provider():
    from agent.tools import media_tools  # noqa: F401

    provider = MagicMock()

    def reject_cost():
        raise UsageLockUnavailable("임대 소유권 상실")

    with patch(
        "services.media.video_qa_service._LITELLM_AVAILABLE",
        True,
    ), patch(
        "services.media.video_qa_service.search_relevant_chunks",
        return_value=[{"text": "자막", "chunk_index": 0, "distance": 0.1}],
    ), patch(
        "services.media.video_qa_service.litellm_completion",
        provider,
    ), pytest.raises(UsageLockUnavailable):
        registry.dispatch(
            "answer_question",
            {"video_id": "video-id", "question": "질문"},
            on_cost_start=reject_cost,
        )

    provider.assert_not_called()


def test_podcast_threads_callback_to_ai_and_every_tts_call():
    from services.media.podcast_service import (
        _generate_script,
        _synthesize_podcast,
    )

    events = []
    callback = lambda: events.append("cost")

    with patch(
        "services.media.podcast_service.ai_service.create_content",
        side_effect=lambda *_args, **_kwargs: (
            events.append("provider") or {"content": "Host: 안녕"}
        ),
    ) as create_content:
        assert _generate_script(
            "콘텐츠",
            "제목",
            "cliproxyapi/gpt-5.5",
            on_cost_start=callback,
        ) == "Host: 안녕"

    assert create_content.call_args.kwargs["on_cost_start"] is callback
    assert events == ["provider"]

    with patch(
        "services.media.podcast_service.TTSService.synthesize",
        return_value=b"audio",
    ) as synthesize:
        assert _synthesize_podcast(
            [("host", "안녕"), ("guest", "반가워")],
            on_cost_start=callback,
        ) == b"audioaudio"

    assert synthesize.call_count == 2
    assert all(
        call.kwargs["on_cost_start"] is callback
        for call in synthesize.call_args_list
    )


def test_podcast_does_not_swallow_tts_lock_loss():
    from services.media.podcast_service import _synthesize_podcast

    with patch(
        "services.media.podcast_service.TTSService.synthesize",
        side_effect=UsageLockUnavailable("임대 소유권 상실"),
    ), pytest.raises(UsageLockUnavailable):
        _synthesize_podcast([("host", "안녕")])


def test_channel_provider_callback_rejection_is_not_swallowed():
    from services.content.channel_analysis_service import _get_channel_info

    provider = MagicMock()

    def reject_cost():
        raise UsageLockUnavailable("임대 소유권 상실")

    with patch(
        "services.content.channel_analysis_service.requests.get",
        provider,
    ), pytest.raises(UsageLockUnavailable):
        _get_channel_info("channel-id", on_cost_start=reject_cost)

    provider.assert_not_called()


def test_channel_cost_callback_runs_immediately_before_request():
    from services.content.channel_analysis_service import _get_channel_info

    events = []
    response = MagicMock()
    response.json.return_value = {
        "items": [{
            "snippet": {"title": "채널"},
            "statistics": {},
        }],
    }

    def provider(*_args, **_kwargs):
        events.append("provider")
        return response

    with patch(
        "services.content.channel_analysis_service.requests.get",
        side_effect=provider,
    ):
        result = _get_channel_info(
            "channel-id",
            on_cost_start=lambda: events.append("cost"),
        )

    assert result is not None
    assert result["title"] == "채널"
    assert events == ["cost", "provider"]


@pytest.mark.parametrize(
    "tool_name",
    [
        "analyze_content",
        "evaluate_quality",
        "evaluate_retrieval_quality",
        "extract_entities",
        "rerank",
    ],
)
def test_analysis_quality_rag_cost_context_is_hidden_from_schema(tool_name):
    from agent.tools import analysis_tools, quality_tools, rag_tools  # noqa: F401

    entry = registry.get(tool_name)
    assert entry is not None
    assert "on_cost_start" not in entry.parameters["properties"]
    assert "model" not in entry.parameters["properties"]


def test_unsafe_internal_rag_and_quality_functions_are_not_auto_registered():
    from agent.tools import quality_tools, rag_tools  # noqa: F401

    assert registry.get("auto_regenerate") is None
    assert registry.get("corrective_search") is None
    assert registry.get("get_chroma_client") is None


def test_analysis_auto_wrapper_uses_only_trusted_cost_callback():
    from agent.tools import analysis_tools  # noqa: F401

    events = []

    def provider(**kwargs):
        events.append("provider")
        assert kwargs["model"] == "gpt-5.4-mini"
        return _completion_response(
            '{"keywords": [], "sentiment": {"overall": "neutral", '
            '"score": 0, "aspects": []}, "topics": []}'
        )

    with patch(
        "services.core.ai_service.resolve_public_model",
        return_value="cliproxyapi/gpt-5.5",
    ), patch("litellm.completion", side_effect=provider):
        payload = json.loads(registry.dispatch(
            "analyze_content",
            {
                "content": "분석할 콘텐츠",
                "model": "attacker/arbitrary-model",
                "on_cost_start": "모델이 주입한 값",
            },
            on_cost_start=lambda: events.append("cost"),
        ))

    assert payload["sentiment"]["overall"] == "neutral"
    assert events == ["cost", "provider"]


def test_quality_auto_wrapper_rethrows_trusted_lock_loss_before_provider():
    from agent.tools import quality_tools  # noqa: F401

    provider = MagicMock()

    def reject_cost():
        raise UsageLockUnavailable("임대 소유권 상실")

    with patch(
        "services.quality.quality_service._get_eval_model",
        return_value="cliproxyapi/gpt-5.5",
    ), patch("litellm.completion", provider), pytest.raises(
        UsageLockUnavailable
    ):
        registry.dispatch(
            "evaluate_quality",
            {
                "content": "품질 평가 본문",
                "source_summary": "원본 요약",
                "model": "attacker/arbitrary-model",
                "on_cost_start": "모델이 주입한 값",
            },
            on_cost_start=reject_cost,
        )

    provider.assert_not_called()


def test_rag_auto_wrapper_forwards_trusted_callback_to_graph_provider():
    from agent.tools import rag_tools  # noqa: F401

    events = []

    def provider(**kwargs):
        events.append("provider")
        assert kwargs["model"] == "gpt-5.5"
        assert kwargs["custom_llm_provider"] == "openai"
        assert kwargs["api_base"] == "http://127.0.0.1:8317/v1"
        return _completion_response(
            '{"entities": [{"name": "Python", "type": "technology"}], '
            '"relations": []}'
        )

    with patch(
        "services.rag.graph_builder.litellm.completion",
        side_effect=provider,
    ):
        payload = json.loads(registry.dispatch(
            "extract_entities",
            {
                "text": "Python은 프로그래밍 언어다.",
                "model": "attacker/arbitrary-model",
                "on_cost_start": "모델이 주입한 값",
            },
            on_cost_start=lambda: events.append("cost"),
        ))

    assert payload[0]["name"] == "Python"
    assert events == ["cost", "provider"]


def test_platform_channel_tool_hides_and_uses_only_trusted_cost_callback():
    from agent.tools import platform_tools  # noqa: F401

    entry = registry.get("get_latest_video")
    assert entry is not None
    assert "on_cost_start" not in entry.parameters["properties"]
    assert registry.get("check_monitors") is None

    events = []
    response = MagicMock()
    response.json.return_value = {"items": []}

    def provider(*_args, **_kwargs):
        events.append("provider")
        return response

    with patch.dict(
        "os.environ",
        {"YOUTUBE_API_KEY": "test-key"},
        clear=False,
    ), patch("requests.get", side_effect=provider):
        assert json.loads(registry.dispatch(
            "get_latest_video",
            {
                "channel_id": "UC_test",
                "on_cost_start": "모델이 주입한 값",
            },
            on_cost_start=lambda: events.append("cost"),
        )) is None

    assert events == ["cost", "provider"]


def test_export_google_docs_tool_uses_server_key_and_trusted_cost_callback():
    from agent.tools import export_tools  # noqa: F401

    entry = registry.get("extract_google_doc")
    assert entry is not None
    assert "api_key" not in entry.parameters["properties"]
    assert "on_cost_start" not in entry.parameters["properties"]

    events = []
    export_response = MagicMock(status_code=403, text="")
    api_response = MagicMock(status_code=200)
    api_response.json.return_value = {
        "title": "API 문서",
        "body": {
            "content": [{
                "paragraph": {
                    "elements": [{"textRun": {"content": "본문"}}],
                },
            }],
        },
    }

    def provider(*_args, **kwargs):
        events.append("provider")
        if len(events) == 1:
            return export_response
        assert kwargs["params"]["key"] == "server-google-key"
        return api_response

    with patch.dict(
        "os.environ",
        {"GOOGLE_DOCS_API_KEY": "server-google-key"},
        clear=False,
    ), patch(
        "services.export.gdocs_service.requests.get",
        side_effect=provider,
    ):
        payload = json.loads(registry.dispatch(
            "extract_google_doc",
            {
                "url": "https://docs.google.com/document/d/test123/edit",
                "api_key": "model-injected-key",
                "on_cost_start": "model-injected-callback",
            },
            on_cost_start=lambda: events.append("cost"),
        ))

    assert payload["title"] == "API 문서"
    assert events == ["provider", "cost", "provider"]
