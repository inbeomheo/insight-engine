"""메인 생성 전 선택 컨텍스트 공급자의 비용·임대 경계 회귀 테스트."""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from services.usage.usage_lock import UsageLockUnavailable


def _reject_cost_start():
    raise UsageLockUnavailable("lease lost")


def _app() -> Flask:
    app = Flask(__name__)
    app.config.update(TESTING=True)
    return app


def test_tavily_lock_loss_stops_http_provider_call():
    from services.data.web_search_service import search

    provider = MagicMock()
    with patch.dict("os.environ", {"TAVILY_API_KEY": "test-key"}), patch(
        "services.data.web_search_service.requests.post",
        provider,
    ), pytest.raises(UsageLockUnavailable):
        search("query", on_cost_start=_reject_cost_start)

    provider.assert_not_called()


def test_tavily_without_api_key_is_free_and_does_not_commit():
    from services.data.web_search_service import search

    callback = MagicMock()
    with patch.dict("os.environ", {"TAVILY_API_KEY": ""}), patch(
        "services.data.web_search_service.requests.post",
    ) as provider:
        assert search("query", on_cost_start=callback) == []

    callback.assert_not_called()
    provider.assert_not_called()


def test_reranker_lock_loss_stops_llm_and_is_not_fallbacked():
    from services.rag.reranker import rerank_with_fallback

    chunks = [
        {"text": f"chunk-{index}", "distance": index / 10}
        for index in range(3)
    ]
    with patch("services.rag.reranker.litellm.completion") as provider, pytest.raises(
        UsageLockUnavailable
    ):
        rerank_with_fallback(
            "query",
            chunks,
            top_k=1,
            on_cost_start=_reject_cost_start,
        )

    provider.assert_not_called()


def test_crag_lock_loss_stops_llm_and_is_not_fallbacked():
    from services.rag.corrective_rag import evaluate_retrieval_quality

    chunks = [{"text": "chunk", "metadata": {}}]
    with patch("services.rag.corrective_rag.litellm.completion") as provider, pytest.raises(
        UsageLockUnavailable
    ):
        evaluate_retrieval_quality(
            "query",
            chunks,
            on_cost_start=_reject_cost_start,
        )

    provider.assert_not_called()


def test_prompt_context_passes_one_trusted_callback_to_web_and_rag():
    from services.core.ai_prompt_context import build_optional_prompt_contexts

    callback = MagicMock()
    with patch.multiple(
        "config",
        RAG_ENABLED=True,
        RAG_TOP_K=5,
        WEB_SEARCH_ENABLED=True,
    ), patch(
        "services.rag.context_builder.RAGContextBuilder.build_context",
        return_value="rag context",
    ) as rag, patch(
        "services.data.web_search_service.extract_grounding_context",
        return_value={"enabled": False, "context_text": "", "results": []},
    ) as web, patch(
        "services.data.style_memory_service.get_profile",
        return_value=None,
    ), patch(
        "services.data.style_memory_service.build_style_context",
        return_value="",
    ), patch(
        "services.data.memory_service.memory_service.build_prompt_context",
        return_value="",
    ):
        build_optional_prompt_contexts(
            "content",
            user_id="user-1",
            web_search=True,
            validated_access_token="validated-token",
            on_cost_start=callback,
        )

    assert rag.call_args.kwargs["on_cost_start"] is callback
    assert web.call_args.kwargs["on_cost_start"] is callback


def test_prompt_context_does_not_swallow_worker_lock_loss():
    from services.core.ai_prompt_context import build_optional_prompt_contexts

    with patch.multiple(
        "config",
        RAG_ENABLED=False,
        RAG_TOP_K=5,
        WEB_SEARCH_ENABLED=True,
    ), patch(
        "services.data.web_search_service.extract_grounding_context",
        side_effect=UsageLockUnavailable("lease lost"),
    ), pytest.raises(UsageLockUnavailable):
        build_optional_prompt_contexts(
            "content",
            web_search=True,
            on_cost_start=MagicMock(),
        )


def test_sync_web_context_lock_loss_stops_tavily_and_main_llm():
    from services.core import ai_service

    app = _app()
    with app.app_context(), patch.dict(
        "os.environ",
        {"TAVILY_API_KEY": "test-key"},
    ), patch(
        "services.data.web_search_service.requests.post",
    ) as tavily, patch(
        "services.core.ai_service._get_completion",
    ) as main_provider, pytest.raises(UsageLockUnavailable):
        ai_service.create_content(
            "content",
            "cliproxyapi/gpt-5.5",
            web_search=True,
            on_cost_start=_reject_cost_start,
        )

    tavily.assert_not_called()
    main_provider.assert_not_called()


def test_stream_rag_context_lock_loss_stops_rag_and_main_llm():
    from services.core import ai_service

    app = _app()

    def rag_provider_boundary(*_args, **kwargs):
        kwargs["on_cost_start"]()
        raise AssertionError("callback must stop the RAG provider")

    with app.app_context(), patch.multiple(
        "config",
        RAG_ENABLED=True,
        RAG_TOP_K=5,
        WEB_SEARCH_ENABLED=False,
    ), patch(
        "services.rag.context_builder.RAGContextBuilder.build_context",
        side_effect=rag_provider_boundary,
    ) as rag, patch(
        "services.core.ai_service._get_completion",
    ) as main_provider:
        stream = ai_service.create_content_stream(
            "content",
            "cliproxyapi/gpt-5.5",
            user_id="user-1",
            on_cost_start=_reject_cost_start,
        )
        with pytest.raises(UsageLockUnavailable):
            next(stream)

    rag.assert_called_once()
    main_provider.assert_not_called()


def test_quality_evaluation_lock_loss_stops_judge_provider():
    from services.quality.quality_service import evaluate_quality

    app = _app()
    with app.app_context(), patch(
        "services.quality.quality_service._get_eval_model",
        return_value="cliproxyapi/gpt-5.5",
    ), patch("litellm.completion") as provider, pytest.raises(
        UsageLockUnavailable
    ):
        evaluate_quality(
            "generated content",
            "source summary",
            on_cost_start=_reject_cost_start,
        )

    provider.assert_not_called()
