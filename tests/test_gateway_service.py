"""CLIProxyAPI 연결·모델 허용·과금 전 설정 검사 회귀 테스트."""
import importlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import Mock, patch

import pytest

from services.core.gateway_service import (
    GatewayConfigurationError,
    apply_gateway_kwargs,
    gateway_connection,
)


@pytest.mark.parametrize('model', [
    'cliproxyapi/gpt-5.5', 'chatmock/gpt-5.5', 'gpt-5.5',
])
def test_gpt_models_use_authenticated_gateway_with_reasoning(model, monkeypatch):
    monkeypatch.setenv('CLIPROXYAPI_BASE_URL', 'http://gateway.test:8317/v1/')
    monkeypatch.setenv('CLIPROXYAPI_API_KEY', 'test-selected-key')
    kwargs = {'temperature': 0.3, 'stream': True, 'stream_options': {'include_usage': True}}

    apply_gateway_kwargs(kwargs, model)

    assert kwargs['model'] == 'gpt-5.5'
    assert kwargs['custom_llm_provider'] == 'openai'
    assert kwargs['api_base'] == 'http://gateway.test:8317/v1'
    assert kwargs['api_key'] == 'test-selected-key'
    assert kwargs['reasoning_effort'] == 'medium'
    assert 'temperature' not in kwargs
    assert kwargs['stream_options'] == {'include_usage': True}


@pytest.mark.parametrize('model,actual', [
    ('cliproxyapi/claude-sonnet-4-6', 'claude-sonnet-4-6'),
    ('cliproxyapi/gemini-3.1-pro-preview', 'gemini-3.1-pro-preview'),
    ('cliproxyapi/team/custom-model', 'team/custom-model'),
])
def test_other_gateway_models_never_select_a_direct_provider(model, actual):
    kwargs = {'temperature': 0.2, 'reasoning_effort': 'high'}
    apply_gateway_kwargs(kwargs, model)
    assert kwargs['model'] == actual
    assert kwargs['custom_llm_provider'] == 'openai'
    assert kwargs['api_base'] == 'http://127.0.0.1:8317/v1'
    assert kwargs['api_key'] == 'test-gateway-key'
    assert kwargs['temperature'] == 0.2
    assert 'reasoning_effort' not in kwargs


def test_previous_gateway_and_openai_credentials_are_never_fallbacks(monkeypatch):
    monkeypatch.delenv('CLIPROXYAPI_BASE_URL')
    monkeypatch.delenv('CLIPROXYAPI_API_KEY')
    monkeypatch.setenv('CHATMOCK_BASE_URL', 'http://old-gateway.test:8000/v1')
    monkeypatch.setenv('CHATMOCK_API_KEY', 'test-old-key')
    monkeypatch.setenv('OPENAI_API_KEY', 'test-unrelated-key')
    assert gateway_connection() == ('http://127.0.0.1:8317/v1', '')
    with pytest.raises(GatewayConfigurationError, match='CLIPROXYAPI_API_KEY'):
        apply_gateway_kwargs({}, 'cliproxyapi/gpt-5.5')


@pytest.mark.parametrize('address', [
    '', '  ', 'gateway.test/v1', 'file:///tmp/gateway', 'https://',
    'http://user:password@gateway.test/v1', 'http://gateway.test/v1?key=test',
    'http://gateway.test/v1#secret', 'http://gateway.test:wrong/v1',
    'http://gateway.test:99999/v1', 'http://bad host/v1',
])
def test_invalid_gateway_address_fails_before_cost_or_provider(address, monkeypatch):
    from services.core.ai_service import call_litellm
    from routes.utility.operations import _check_cliproxyapi_ready

    monkeypatch.setenv('CLIPROXYAPI_BASE_URL', address)
    callback = Mock()
    with patch('litellm.completion') as provider, patch('routes.utility.operations.requests.get') as request:
        with pytest.raises(GatewayConfigurationError, match='CLIPROXYAPI_BASE_URL'):
            call_litellm([{'role': 'user', 'content': '내용'}], on_cost_start=callback)
        assert _check_cliproxyapi_ready() is False
    callback.assert_not_called()
    provider.assert_not_called()
    request.assert_not_called()


def test_legacy_prefix_only_accepts_same_supported_model():
    from services.core.ai_service import resolve_public_model

    assert resolve_public_model('chatmock/gpt-5.5') == 'cliproxyapi/gpt-5.5'
    assert resolve_public_model('chatmock/gpt-5.3-codex-spark') == 'cliproxyapi/gpt-5.3-codex-spark'
    for unsupported in ('chatmock/gpt-5.4-mini', 'chatmock/gpt-5.4', 'cliproxyapi/unknown', 'anthropic/claude'):
        with pytest.raises(ValueError, match='지원하지 않는 AI 모델'):
            resolve_public_model(unsupported)


def test_configured_extra_models_are_advertised_and_allowed():
    result = subprocess.run(
        [sys.executable, '-c',
         'import json; from config import SUPPORTED_PROVIDERS; '
         'from services.core.ai_service import resolve_public_model; '
         'print(json.dumps([resolve_public_model(m["id"]) for m in '
         'SUPPORTED_PROVIDERS["cliproxyapi"]["models"]]))'],
        cwd=Path(__file__).resolve().parents[1],
        env={'CLIPROXYAPI_MODELS': 'claude-sonnet-4-6, gemini-3.1-pro-preview'},
        check=True, capture_output=True, text=True,
    )
    assert json.loads(result.stdout) == [
        'cliproxyapi/gpt-5.5', 'cliproxyapi/gpt-5.3-codex-spark',
        'cliproxyapi/claude-sonnet-4-6', 'cliproxyapi/gemini-3.1-pro-preview',
    ]


@pytest.mark.parametrize('module,function,args,extra', [
    ('services.core.ai_service', 'call_litellm', ([{'role': 'user', 'content': '내용'}],), {}),
    ('services.analysis.nlp_analysis_service', 'analyze_content', ('내용',), {}),
    ('services.analysis.nlp_analysis_service', 'analyze_sentiment_flow', ('내용',), {}),
    ('services.quality.quality_service', 'evaluate_quality', ('내용', '원문'), {}),
    ('services.rag.graph_builder', 'extract_entities', ('내용',), {}),
    ('services.rag.reranker', 'rerank', ('질문', [{'text': '가'}, {'text': '나'}]), {'top_k': 1}),
    ('services.rag.corrective_rag', 'evaluate_retrieval_quality', ('질문', [{'text': '내용'}]), {}),
    ('services.rag.corrective_rag', 'reformulate_query', ('질문', '피드백'), {}),
    ('agent.compressor', '_summarize_middle', ([{'role': 'user', 'content': '오래된 대화'}],), {}),
])
def test_missing_key_stops_each_call_before_usage_and_provider(module, function, args, extra, monkeypatch):
    monkeypatch.delenv('CLIPROXYAPI_API_KEY')
    invoke = getattr(importlib.import_module(module), function)
    on_cost_start = Mock()
    with patch('litellm.completion') as provider, patch(
        'services.usage.usage_decorator.mark_usage_charge_committed'
    ) as charge:
        with pytest.raises(GatewayConfigurationError, match='CLIPROXYAPI_API_KEY'):
            invoke(*args, model='cliproxyapi/gpt-5.5', on_cost_start=on_cost_start, **extra)
    on_cost_start.assert_not_called()
    charge.assert_not_called()
    provider.assert_not_called()


def test_agent_without_gateway_key_fails_before_callback(monkeypatch):
    from agent.core import AIAgent

    agent = AIAgent(model='cliproxyapi/gpt-5.5', on_cost_start=Mock())
    monkeypatch.delenv('CLIPROXYAPI_API_KEY')
    with patch('litellm.completion') as provider:
        with pytest.raises(GatewayConfigurationError, match='CLIPROXYAPI_API_KEY'):
            agent._call_llm([{'role': 'user', 'content': '내용'}], [])
    agent._on_cost_start.assert_not_called()
    provider.assert_not_called()


def test_agent_stream_preserves_usage_only_chunk_and_finish_reason():
    from types import SimpleNamespace
    from agent.core import AIAgent

    agent = AIAgent(model='cliproxyapi/gpt-5.5', on_stream_delta=Mock())
    usage = {'prompt_tokens': 10, 'completion_tokens': 4, 'total_tokens': 14}
    chunks = [
        SimpleNamespace(choices=[SimpleNamespace(
            delta=SimpleNamespace(content='응답', tool_calls=None), finish_reason=None,
        )], usage=None),
        SimpleNamespace(choices=[SimpleNamespace(delta=None, finish_reason='length')], usage=None),
        SimpleNamespace(choices=[], usage=usage),
    ]
    with patch('litellm.completion', return_value=iter(chunks)) as provider:
        response = agent._call_llm([{'role': 'user', 'content': '내용'}], [])
    assert provider.call_args.kwargs['stream_options'] == {'include_usage': True}
    assert provider.call_args.kwargs['api_key'] == 'test-gateway-key'
    assert provider.call_args.kwargs['custom_llm_provider'] == 'openai'
    assert response.choices[0].message.content == '응답'
    assert response.choices[0].finish_reason == 'length'
    assert response.usage == usage


def test_generation_missing_key_does_not_start_optional_paid_contexts(monkeypatch):
    from flask import Flask
    # 지연 import가 패치된 함수를 모듈 전역에 영구 보관하지 않도록 먼저 로드합니다.
    import services.core.ai_streaming  # noqa: F401
    from services.core.ai_service import create_content, create_content_stream

    monkeypatch.delenv('CLIPROXYAPI_API_KEY')
    callback = Mock()
    with Flask(__name__).app_context(), patch(
        'services.core.ai_prompt_context.build_optional_prompt_contexts'
    ) as context, patch('services.core.ai_streaming.build_optional_prompt_contexts') as stream_context:
        with pytest.raises(Exception, match='CLIPROXYAPI_API_KEY'):
            create_content('내용', 'cliproxyapi/gpt-5.5', on_cost_start=callback)
        with pytest.raises(Exception, match='CLIPROXYAPI_API_KEY'):
            list(create_content_stream('내용', 'cliproxyapi/gpt-5.5', on_cost_start=callback))
    callback.assert_not_called()
    context.assert_not_called()
    stream_context.assert_not_called()


@pytest.mark.parametrize('payload,expected', [
    ({'data': [{'id': 'gpt-5.5'}]}, True),
    ({'data': [{'id': 'gpt-5.3-codex-spark'}]}, True),
    ({'data': []}, False),
    ({'data': [{'id': 'unsupported-model'}]}, False),
    ({'data': [{'id': None}, None]}, False),
    ({}, False),
    ([], False),
])
def test_readiness_requires_an_authenticated_usable_model(payload, expected):
    from routes.utility.operations import _check_cliproxyapi_ready

    response = Mock(status_code=200)
    response.json.return_value = payload
    with patch('routes.utility.operations.requests.get', return_value=response) as request:
        assert _check_cliproxyapi_ready() is expected
    request.assert_called_once_with(
        'http://127.0.0.1:8317/v1/models',
        headers={'Authorization': 'Bearer test-gateway-key'},
        timeout=3, allow_redirects=False,
    )


def test_readiness_without_key_never_calls_models(monkeypatch):
    from routes.utility.operations import _check_cliproxyapi_ready

    monkeypatch.delenv('CLIPROXYAPI_API_KEY')
    with patch('routes.utility.operations.requests.get') as request:
        assert _check_cliproxyapi_ready() is False
    request.assert_not_called()


def test_provider_response_does_not_expose_the_gateway_key():
    from app import create_app

    response = create_app({'TESTING': True}).test_client().get('/api/providers')
    assert response.status_code == 200
    assert 'test-gateway-key' not in response.get_data(as_text=True)
    provider = response.get_json()['providers']['cliproxyapi']
    assert provider['default_model'] == 'cliproxyapi/gpt-5.5'
    assert 'api_key' not in provider
    assert 'api_base' not in provider
