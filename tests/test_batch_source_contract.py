"""실제 배치 작업자의 소스 수집/옵션/사용량 계약. 외부 I/O는 모두 대체한다."""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from flask import g

from app import create_app
from services.content.article_service import fetch_article as real_fetch_article
from services.core.ai_service import create_content as real_create_content


@pytest.fixture
def batch():
    app = create_app({'TESTING': True, 'RATELIMIT_ENABLED': False})
    before = {'usage_count': 3, 'max_usage': 5, 'can_use': True}
    reservation = SimpleNamespace(usage_before=before, usage_after={**before, 'usage_count': 2})

    def authenticated(_token):
        g.user_id = 'trusted-owner'
        return {'valid': True}

    def article(url):
        return {'title': f'원문 {url}', 'text': f'본문 {url}', 'source_meta': {'url': url}}

    def create_content(content, _model, _prompt, **kwargs):
        kwargs['on_cost_start']()
        return ({
            'title': '생성 제목', 'content': content, 'html': '<p>생성 결과</p>',
            'usage': {'total_tokens': 23},
        }, 'prompt')

    with (
        patch('src.contexts.identity.interface.auth_decorators.is_supabase_enabled', return_value=True),
        patch('src.contexts.identity.interface.auth_decorators._validate_token', side_effect=authenticated),
        patch('routes.blog_routes.is_supabase_enabled', return_value=False),
        patch('services.usage.usage_service.UsageService.reserve_for_request', return_value=reservation) as reserve,
        patch('services.usage.usage_service.UsageService.refund_reservation', return_value=before) as refund,
        patch('services.usage.usage_service.UsageService.refund_reservation_quietly', return_value=before) as quiet_refund,
        patch('src.contexts.content_library.save_many_history_entries') as save,
        patch('services.content.article_service.fetch_article', side_effect=article) as fetch,
        patch('services.content.multi_source_collector.collect_content') as collect,
        patch('services.core.content_service.get_content_title', return_value='영상 원제목') as title,
        patch('services.core.content_service.get_transcript', return_value={
            'text': '영상에서 추출한 자막 본문', 'source': 'api',
            'segments': [{'start': 0, 'text': '영상 본문'}],
        }) as transcript,
        patch('services.core.content_service.get_top_comments', return_value=[]) as comments,
        patch('services.core.ai_service.create_content', side_effect=create_content) as ai,
    ):
        client = app.test_client()

        def post(urls, **options):
            return client.post('/generate-batch', json={
                'urls': urls, 'style': 'summary', **options,
            }, headers={'Origin': 'http://localhost:3000', 'Authorization': 'Bearer test-token'})

        yield SimpleNamespace(
            app=app, post=post, reserve=reserve, refund=refund,
            quiet_refund=quiet_refund, save=save, fetch=fetch,
            collect=collect, title=title, transcript=transcript,
            comments=comments, ai=ai, reservation=reservation,
        )


def test_two_web_urls_keep_options_owner_result_usage_and_one_reservation(batch):
    urls = ['https://example.com/first', 'https://example.com/second']
    response = batch.post(
        urls, detail_level='deep', transcript_language='ja',
        enable_web_search=True, user_id='forged-owner',
        modifiers={'length': 'long', 'language': 'ja'}, customPrompt='사용자 스타일',
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data['successful'] == 2
    assert [result['url'] for result in data['results']] == urls
    assert data['usage'] == batch.reservation.usage_after
    batch.reserve.assert_called_once_with('trusted-owner')
    batch.refund.assert_not_called()
    batch.collect.assert_not_called()
    batch.transcript.assert_not_called()
    for call in batch.ai.call_args_list:
        assert call.args[2] == '사용자 스타일'
        assert call.kwargs['detail_level'] == 'deep'
        assert call.kwargs['web_search'] is True
        assert call.kwargs['user_id'] == 'trusted-owner'
        assert call.kwargs['modifiers']['language'] == 'ja'
    for result in data['results']:
        assert result['usage'] == {'total_tokens': 23}
        assert result['source_type'] == 'article'
        assert result['source_meta']['url'] == result['url']
        assert result['id']
        assert result['elapsed_time'] >= 0
    assert all(entry['usage'] == {'total_tokens': 23} for entry in batch.save.call_args.args[1])


def test_mixed_youtube_article_batch_preserves_video_and_language(batch):
    youtube = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
    response = batch.post([youtube, 'https://example.com/news'], transcript_language='en')
    assert response.status_code == 200
    data = response.get_json()
    assert data['successful'] == 2
    video = data['results'][0]
    assert video['source_type'] == 'youtube'
    assert video['youtube_title'] == '영상 원제목'
    assert video['transcript_source'] == 'api'
    assert video['transcript_segments'] == [{'start': 0, 'text': '영상 본문'}]
    assert video['video_id'] == 'dQw4w9WgXcQ'
    assert batch.transcript.call_args.kwargs['transcript_language'] == 'en'
    assert callable(batch.transcript.call_args.kwargs['on_cost_start'])
    batch.reserve.assert_called_once()


@pytest.mark.parametrize(('url', 'source_type'), [
    ('https://example.com/feed.xml', 'rss'),
    ('https://arxiv.org/abs/2303.08774', 'arxiv'),
    ('https://open.spotify.com/episode/episode-id', 'podcast'),
])
def test_other_detected_sources_use_existing_collector(batch, url, source_type):
    batch.collect.return_value = {'title': '수집 제목', 'content': '소스 본문'}
    response = batch.post([url], source_type='youtube', web_search=True, detail_level='brief')
    assert response.status_code == 200
    assert response.get_json()['results'][0]['source_type'] == source_type
    assert batch.collect.call_args.kwargs['source_type'] == source_type
    assert callable(batch.collect.call_args.kwargs['on_cost_start'])
    assert batch.ai.call_args.kwargs['detail_level'] == 'brief'
    assert batch.ai.call_args.kwargs['web_search'] is True
    batch.fetch.assert_not_called()


def test_client_hint_cannot_force_podcast_collector(batch):
    response = batch.post(['https://example.com/article'], source_type='podcast')
    assert response.get_json()['successful'] == 1
    batch.fetch.assert_called_once_with('https://example.com/article')
    batch.collect.assert_not_called()


def test_web_batch_retains_article_private_address_validation(batch):
    batch.fetch.side_effect = real_fetch_article
    with (
        patch('services.content.article_service.is_safe_public_url', return_value=False),
        patch('services.content.article_service._fetch_html') as download,
    ):
        response = batch.post(['http://127.0.0.1/private'], source_type='podcast')
    assert response.get_json()['successful'] == 0
    download.assert_not_called()
    batch.collect.assert_not_called()
    batch.ai.assert_not_called()
    batch.refund.assert_called_once()


def test_partial_collection_failure_returns_remaining_success(batch):
    def fetch(url):
        if url.endswith('/bad'):
            raise ValueError('본문을 찾을 수 없습니다.')
        return {'title': '정상 글', 'text': '정상 본문'}

    batch.fetch.side_effect = fetch
    response = batch.post(['https://example.com/bad', 'https://example.com/good'])
    data = response.get_json()
    assert response.status_code == 200
    assert (data['successful'], data['failed']) == (1, 1)
    assert [result['success'] for result in data['results']] == [False, True]
    batch.reserve.assert_called_once()
    batch.ai.assert_called_once()
    batch.refund.assert_not_called()


def test_all_collection_failures_refund_before_any_provider_call(batch):
    batch.fetch.side_effect = ValueError('본문을 찾을 수 없습니다.')
    response = batch.post(['https://example.com/bad', 'https://example.com/empty'])
    assert response.get_json()['successful'] == 0
    assert response.get_json()['usage'] == batch.reservation.usage_before
    batch.ai.assert_not_called()
    batch.refund.assert_called_once_with('trusted-owner', batch.reservation)


def test_web_search_provider_failure_after_cost_start_keeps_reservation(batch):
    def fail_after_search(_content, _model, _prompt, **kwargs):
        assert kwargs['web_search'] is True
        kwargs['on_cost_start']()
        raise RuntimeError('검색 공급자 응답 실패')

    batch.ai.side_effect = fail_after_search
    response = batch.post(['https://example.com/news'], web_search=True)
    assert response.get_json()['successful'] == 0
    assert response.get_json()['usage'] == batch.reservation.usage_after
    batch.refund.assert_not_called()


def test_agent_receives_options_and_shared_cost_callback(batch):
    with patch('services.agents.Orchestrator') as orchestrator:
        def run(**kwargs):
            assert kwargs['detail_level'] == 'deep'
            assert kwargs['web_search'] is True
            assert kwargs['user_id'] == 'trusted-owner'
            orchestrator.call_args.kwargs['on_cost_start']()
            return {'title': '에이전트 결과', 'content': '본문', 'html': '<p>본문</p>', 'usage': {'total_tokens': 42}}

        orchestrator.return_value.run.side_effect = run
        response = batch.post(['https://example.com/news'], enable_agent_mode=True, enable_web_search=True, detail_level='deep')
    result = response.get_json()['results'][0]
    assert result['agent_mode'] is True
    assert result['usage'] == {'total_tokens': 42}
    batch.ai.assert_not_called()
    batch.refund.assert_not_called()


@pytest.mark.parametrize('web_search', [False, True])
def test_real_agent_pipeline_obeys_search_and_writer_detail(batch, web_search):
    def completion(**kwargs):
        prompt = kwargs['messages'][0]['content']
        if 'search_query' in prompt:
            content = '{"main_topic": "주제", "search_query": "소스 확인"}'
        elif '전문 콘텐츠 작성자' in prompt:
            content = '# 초안\n본문'
        elif '"grade"' in prompt:
            content = '{"grade": "A"}'
        elif 'meta_title' in prompt:
            content = '{"meta_title": "최종", "keywords": []}'
        else:
            content = '# 최종\n본문'
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    def search(_query, **kwargs):
        kwargs['on_cost_start']()
        return []

    with (
        patch('litellm.completion', side_effect=completion) as provider,
        patch('services.data.web_search_service.search', side_effect=search) as search_provider,
        patch('services.seo.seo_metadata_service.generate_video_object_schema', return_value={}),
    ):
        response = batch.post(
            ['https://example.com/news'], enable_agent_mode=True,
            enable_web_search=web_search, detail_level='deep',
            modifiers={'language': 'en', 'writing_style': 'expert'},
        )
    assert response.status_code == 200
    result = response.get_json()['results'][0]
    assert result['agent_mode'] is True
    assert provider.call_count == 5
    writer = next(call for call in provider.call_args_list if '전문 콘텐츠 작성자' in call.kwargs['messages'][0]['content'])
    assert writer.kwargs['max_tokens'] == 16000
    editor = next(call for call in provider.call_args_list if '전문 편집자' in call.kwargs['messages'][0]['content'])
    assert editor.kwargs['max_tokens'] >= writer.kwargs['max_tokens']
    assert '가능한 한 상세하게 작성하세요.' in writer.kwargs['messages'][0]['content']
    assert 'You MUST write the entire result in English.' in writer.kwargs['messages'][0]['content']
    assert '결과는 반드시 한국어로 작성하세요.' not in writer.kwargs['messages'][0]['content']
    assert search_provider.call_count == int(web_search)
    batch.ai.assert_not_called()
    batch.reserve.assert_called_once()
    batch.refund.assert_not_called()


def test_real_agent_provider_failure_still_commits_batch_charge(batch):
    batch.ai.side_effect = RuntimeError('일반 생성 공급자도 실패')
    with patch('litellm.completion', side_effect=RuntimeError('에이전트 공급자 실패')) as provider:
        response = batch.post(['https://example.com/news'], enable_agent_mode=True)
    assert response.get_json()['successful'] == 0
    assert response.get_json()['usage'] == batch.reservation.usage_after
    assert provider.call_count >= 2
    batch.ai.assert_called_once()
    batch.refund.assert_not_called()


def test_agent_cost_lock_loss_propagates_without_fallback_provider(batch):
    lease = MagicMock(lost=False, released=False)

    with (
        patch('routes.blog_routes.is_supabase_enabled', return_value=True),
        patch('routes.blog_routes.acquire_usage_request_lock', return_value=lease),
        patch('services.agents.Orchestrator') as orchestrator,
    ):
        def run(**_kwargs):
            lease.lost = True
            orchestrator.call_args.kwargs['on_cost_start']()
            pytest.fail('잠금 상실 후 공급자를 호출하면 안 됩니다.')

        orchestrator.return_value.run.side_effect = run
        response = batch.post(['https://example.com/news'], agent_mode=True)
    assert response.status_code == 503
    assert response.get_json()['code'] == 'USAGE_LOCK_UNAVAILABLE'
    batch.ai.assert_not_called()
    batch.quiet_refund.assert_called_once_with('trusted-owner', batch.reservation)


def test_real_ai_web_context_callback_stops_cost_after_lease_loss(batch):
    lease = MagicMock(lost=False, released=False)
    batch.ai.side_effect = real_create_content

    def grounding(_content, on_cost_start):
        lease.lost = True
        on_cost_start()
        pytest.fail('사용량 잠금을 잃으면 웹 검색 공급자에 진입하면 안 됩니다.')

    with (
        patch('routes.blog_routes.is_supabase_enabled', return_value=True),
        patch('routes.blog_routes.acquire_usage_request_lock', return_value=lease),
        patch('config.RAG_ENABLED', False),
        patch('services.data.style_memory_service.get_profile', return_value={}),
        patch('services.data.memory_service.memory_service.build_prompt_context', return_value=''),
        patch('services.data.web_search_service.extract_grounding_context', side_effect=grounding) as search,
        patch('services.core.ai_service._get_completion') as provider,
    ):
        response = batch.post(['https://example.com/news'], web_search=True)
    assert response.status_code == 503
    search.assert_called_once()
    provider.assert_not_called()
    batch.quiet_refund.assert_called_once_with('trusted-owner', batch.reservation)


def test_comment_parallel_worker_preserves_trusted_owner_and_detail(batch):
    batch.comments.return_value = ['댓글 하나']
    with patch('routes.generation_helpers._generate_comment_summary', return_value=None):
        response = batch.post(['https://youtube.com/watch?v=dQw4w9WgXcQ'], detail_level='deep')
    assert response.get_json()['successful'] == 1
    assert batch.ai.call_args.kwargs['user_id'] == 'trusted-owner'
    assert batch.ai.call_args.kwargs['detail_level'] == 'deep'


@pytest.mark.parametrize('options', [
    {'transcript_language': 'de'}, {'urls': ['']}, {'urls': [123]},
])
def test_invalid_options_rejected_before_reservation(batch, options):
    urls = options.pop('urls', ['https://example.com/news'])
    response = batch.post(urls, **options)
    assert response.status_code == 400
    batch.reserve.assert_not_called()
    batch.ai.assert_not_called()
