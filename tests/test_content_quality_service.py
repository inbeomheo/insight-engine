"""Luna 품질 경로: 실계정 호출 없이 계약·비용 경계·실패 차단 검증."""
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from flask import Flask

from config import STYLE_MODIFIERS
from services.core import ai_service
from services.core.content_quality_service import (
    ContentQualityError, enabled, generate_verified, inspect_output,
)
from services.usage.usage_lock import UsageLockUnavailable

MODEL = 'cliproxyapi/gpt-5.6-luna'
SOURCE = '틀린 질문은 다음 날 확인합니다. 쉬운 질문은 간격을 늘립니다.'
DRAFT = '# 복습\n\n틀린 질문은 다음 날 확인합니다.'
EVIDENCE = {'ids': [0]}
APPROVED = {'supported': True, 'issues': []}


def response(value, finish='stop'):
    return SimpleNamespace(
        choices=[SimpleNamespace(finish_reason=finish, message=SimpleNamespace(
            content=json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else value))],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )


@pytest.fixture
def provider(monkeypatch):
    mock = Mock()
    monkeypatch.setattr(ai_service, '_get_completion', lambda: mock)
    return mock


def generate(provider, outputs, **kwargs):
    provider.side_effect = [response(x) for x in outputs]
    return generate_verified(SOURCE, '요약', MODEL, {'model': 'gpt-5.6-luna'},
                             {'length': 'short', 'language': 'ko'}, 'summary', **kwargs)


def test_three_calls_aggregate_usage_and_charge_before_each_call(provider):
    callback = Mock()
    text, usage = generate(provider, [EVIDENCE, DRAFT, APPROVED], on_cost_start=callback)
    assert text == DRAFT and usage['total_tokens'] == 45
    assert callback.call_count == provider.call_count == 3
    assert all(call.kwargs['model'] == 'gpt-5.6-luna' for call in provider.call_args_list)
    assert all(call.kwargs['messages'][0]['role'] == 'system' for call in provider.call_args_list)
    assert [call.kwargs['reasoning_effort'] for call in provider.call_args_list] == ['medium', 'medium', 'high']


def test_unquoted_evidence_fails_before_draft(provider):
    with pytest.raises(ContentQualityError, match='원문'):
        generate(provider, [{'ids': [999]}])
    assert provider.call_count == 1


def test_unsupported_claim_repaired_then_reaudited(provider):
    bad = {'supported': False, 'issues': ['즉시가 아니라 다음 날로 고치세요.']}
    text, usage = generate(provider, [EVIDENCE, '# 복습\n즉시 확인합니다.', bad, DRAFT, APPROVED])
    assert text == DRAFT and usage['total_tokens'] == 75


def test_fails_closed_after_two_repairs(provider):
    bad = {'supported': False, 'issues': ['근거 부족']}
    with pytest.raises(ContentQualityError, match='두 차례'):
        generate(provider, [EVIDENCE, DRAFT, bad, DRAFT, bad, DRAFT, bad])
    assert provider.call_count == 7


@pytest.mark.parametrize('value', ['not json', [], {'supported': 'true', 'issues': []}])
def test_invalid_audit_not_accepted(provider, value):
    with pytest.raises(ContentQualityError):
        generate(provider, [EVIDENCE, DRAFT, value])


def test_lease_loss_stops_before_any_model_call(provider):
    callback = Mock(side_effect=UsageLockUnavailable('lost'))
    with pytest.raises(UsageLockUnavailable):
        generate(provider, [EVIDENCE], on_cost_start=callback)
    provider.assert_not_called()


def test_truncated_response_not_accepted(provider):
    provider.return_value = response(EVIDENCE, finish='length')
    with pytest.raises(ContentQualityError, match='완성'):
        generate_verified(SOURCE, '요약', MODEL, {}, {}, 'summary')


@pytest.mark.parametrize('language,text', [('en', '# Title\n한국어 혼합'), ('ja', '# 題名\n日本語です. 한국어 제목')])
def test_mixed_language_detected(language, text):
    assert inspect_output(text, language, 'short', 'summary')


def test_length_includes_markdown_but_excludes_title():
    assert not inspect_output('# 제목\n' + '가' * 800, 'ko', 'short', 'summary')
    assert inspect_output('# 제목\n' + '가' * 801, 'ko', 'short', 'summary')


def test_transform_and_unspecified_styles_keep_structured_contract():
    for style in ('mindmap', 'chapter_split', 'comment_summary', 'knowledge_note', None):
        assert not enabled(MODEL, style)
    assert enabled(MODEL, 'summary')


def test_stream_only_emits_verified_output_and_total_usage(provider):
    provider.side_effect = [response(x) for x in [EVIDENCE, DRAFT, APPROVED]]
    app = Flask(__name__)
    app.config['STYLE_MODIFIERS'] = STYLE_MODIFIERS
    callback = Mock()
    with app.app_context():
        stream = ai_service.create_content_stream(SOURCE, MODEL, '요약', style_id='summary', on_cost_start=callback)
        assert next(stream) == DRAFT
        assert provider.call_count == 3
        with pytest.raises(StopIteration) as stopped:
            next(stream)
    assert stopped.value.value['usage']['total_tokens'] == 45


def test_regular_generation_preserves_html_title_and_usage(provider):
    provider.side_effect = [response(x) for x in [EVIDENCE, DRAFT, APPROVED]]
    app = Flask(__name__)
    app.config['STYLE_MODIFIERS'] = STYLE_MODIFIERS
    with app.app_context():
        result = ai_service.create_content(SOURCE, MODEL, '요약', style_id='summary')
    assert result['title'] == '복습'
    assert '<p>' in result['html']
    assert result['usage']['total_tokens'] == 45


def test_length_violation_triggers_repair_even_if_reviewer_approves(provider):
    text, _ = generate(provider, [EVIDENCE, '# 제목\n' + '가' * 801, APPROVED, DRAFT, APPROVED])
    assert text == DRAFT and provider.call_count == 5


def test_timeout_prevents_another_provider_call(provider, monkeypatch):
    monkeypatch.setattr('services.core.content_quality_service.time.monotonic', Mock(side_effect=[0, 241]))
    with pytest.raises(ContentQualityError, match='제한 시간'):
        generate(provider, [EVIDENCE])
    provider.assert_not_called()


def test_provider_limit_does_not_retry_or_change_model(provider):
    provider.side_effect = RuntimeError('rate limit')
    with pytest.raises(RuntimeError, match='rate limit'):
        generate_verified(SOURCE, '요약', MODEL, {'model': 'gpt-5.6-luna'}, {}, 'summary')
    assert provider.call_count == 1
    assert provider.call_args.kwargs['num_retries'] == 0
    assert provider.call_args.kwargs['model'] == 'gpt-5.6-luna'


def test_all_source_chunks_are_considered(provider, monkeypatch):
    monkeypatch.setattr('services.core.content_quality_service.CHUNK_SIZE', 10)
    count = (len(SOURCE) + 9) // 10
    provider.side_effect = [response({'ids': [0]}) for _ in range(count)] + [response(DRAFT), response(APPROVED)]
    generate_verified(SOURCE, '요약', MODEL, {}, {}, 'summary')
    assert provider.call_count == count + 2


def test_failed_stream_never_exposes_draft(provider):
    bad = {'supported': False, 'issues': ['근거 부족']}
    provider.side_effect = [response(x) for x in [EVIDENCE, DRAFT, bad, DRAFT, bad, DRAFT, bad]]
    app = Flask(__name__)
    with app.app_context():
        stream = ai_service.create_content_stream(SOURCE, MODEL, '요약', style_id='summary')
        with pytest.raises(Exception, match='두 차례'):
            next(stream)


def test_metadata_labels_only_are_exempt_from_language_check():
    text = '# Review\n| **메타 설명** | Review |\n| **타겟 키워드** | review |\n| **추천 URL** | review |\n**태그**: #review'
    assert not inspect_output(text, 'en', 'short', 'blog_seo')
    assert inspect_output(text + '\n### 한국어 제목', 'en', 'short', 'blog_seo')


def test_minimum_length_with_sufficient_evidence_requires_repair(provider):
    source = '가나다라를 관찰했습니다. ' * 200
    # 하나의 긴 근거 문단을 그대로 선택해 분량 근거를 충분히 제공한다.
    source = source.replace('. ', ', ')
    expanded = '# 관찰\n' + '가' * 2100
    provider.side_effect = [response(x) for x in [EVIDENCE, DRAFT, APPROVED, expanded, APPROVED]]
    text, _ = generate_verified(source, '요약', MODEL, {}, {'length': 'long'}, 'summary')
    assert text == expanded
    assert provider.call_count == 5


def test_short_source_does_not_require_invented_padding(provider):
    generate(provider, [EVIDENCE, DRAFT, APPROVED])
    assert provider.call_count == 3


def test_progress_and_cancellation_after_first_call(provider):
    from services.core.quality_stream_service import QualityGenerationCancelled
    stages = []

    def cancelled():
        if provider.call_count:
            raise QualityGenerationCancelled()

    with pytest.raises(QualityGenerationCancelled):
        generate(provider, [EVIDENCE], check_cancelled=cancelled, on_progress=stages.append)
    assert stages == ['evidence']
    assert provider.call_count == 1
