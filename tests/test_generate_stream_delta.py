"""P7+: /generate-stream 토큰 delta SSE 회귀 테스트."""
import json
import threading
import time
import unittest
from contextlib import ExitStack, contextmanager
from unittest.mock import MagicMock, patch

from app import create_app
from src.contexts.identity.application.ports import QuotaReservation
from src.contexts.identity.domain.exceptions import QuotaExceeded
from services.usage.usage_service import UsageReservation, UsageReservationReplay


_H = {'Origin': 'http://localhost:3000'}


def _usage_reservation(*, before=None, after=None, owned=True):
    before = before or {'remaining': 5, 'is_admin': False}
    after = after or {'remaining': 4, 'is_admin': False}
    quota = QuotaReservation(
        reservation_id='reservation-1',
        idempotency_key='client:key',
        request_fingerprint='a' * 64,
        owner_token_hash='b' * 64,
        amount=1,
        remaining=after.get('usage_count', after.get('remaining', 4)),
        max_usage=before.get('max_usage', 5),
        owned=owned,
        replayed=not owned,
    )
    return UsageReservation(quota, before, after, True)


class _FakeCache:
    def __init__(self):
        self.store = {}

    def get(self, cache_key):
        value = self.store.get(cache_key)
        return dict(value) if value else None

    def put(self, cache_key, video_id, style_id, model, length, writing_style, result):
        self.store[cache_key] = dict(result)


def _parse_sse(body: str) -> list[dict]:
    events = []
    for block in body.strip().split('\n\n'):
        data_lines = [
            line.removeprefix('data: ')
            for line in block.splitlines()
            if line.startswith('data: ')
        ]
        if data_lines:
            events.append(json.loads('\n'.join(data_lines)))
    return events


class TestGenerateStreamDelta(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['REDIS_URL'] = ''
        self.app.ai_cache = _FakeCache()
        self.client = self.app.test_client()

    def _post(self, model='cliproxyapi/gpt-5.5', payload=None, headers=None):
        body = {
            'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            'model': model,
            'style': 'summary',
        }
        if payload:
            body.update(payload)
        return self.client.post(
            '/generate-stream',
            json=body,
            headers=headers or _H,
        )

    def _patch_common(self):
        return {
            'auth_supabase_enabled': patch(
                'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
                return_value=False,
            ),
            'route_supabase_enabled': patch('routes.blog_routes.is_supabase_enabled', return_value=False),
            'data_supabase_enabled': patch('services.data.supabase_service.is_supabase_enabled', return_value=False),
            'usage_supabase_enabled': patch('services.usage.usage_decorator.is_supabase_enabled', return_value=False),
            'reserve_usage': patch(
                'services.usage.usage_service.UsageService.reserve_for_request',
                return_value=_usage_reservation(),
            ),
            'refund_usage': patch(
                'services.usage.usage_service.UsageService.refund_reservation',
                return_value={'remaining': 5, 'is_admin': False},
            ),
            'is_youtube_url': patch('routes.blog_routes.content_service.is_youtube_url', return_value=True),
            'get_video_id': patch('routes.blog_routes.content_service.get_video_id', return_value='dQw4w9WgXcQ'),
            'get_content_title': patch('routes.blog_routes.content_service.get_content_title', return_value='YT'),
            'fetch_youtube': patch(
                'routes.blog_routes._fetch_youtube_content',
                return_value=('자막 본문', [], None, '자막 원문', 'api', []),
            ),
            'get_style_prompt': patch('routes.blog_routes._get_style_prompt', return_value='스타일 프롬프트'),
            'blog_usage_for_response': patch('routes.blog_routes.get_usage_for_response', return_value={'remaining': 4}),
            'cached_transcript': patch(
                'routes.generation_helpers.content_service.get_cached_transcript',
                return_value={'text': '자막 원문', 'source': 'cache'},
            ),
        }

    @contextmanager
    def _patched(self, **extra_patches):
        with ExitStack() as stack:
            patches = {**self._patch_common(), **extra_patches}
            mocks = {
                name: stack.enter_context(patch_obj)
                for name, patch_obj in patches.items()
            }
            yield mocks

    def _wait_for(self, predicate, timeout=1.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate():
                return True
            time.sleep(0.01)
        return predicate()

    def test_stream_rejects_enable_citations(self):
        with self._patched():
            resp = self._post(payload={'enable_citations': True})

        self.assertEqual(resp.status_code, 400)
        self.assertIn('스트리밍 생성은 인용 모드를 지원하지 않습니다', resp.get_json()['error'])

    def test_delta_events_accumulate_to_final_result_content(self):
        def fake_stream(*args, **kwargs):
            yield '본문 '
            yield '완성'
            return {
                'prompt': '사용된 프롬프트',
                'usage': {'prompt_tokens': 3, 'completion_tokens': 2, 'total_tokens': 5},
            }

        with self._patched(
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream', side_effect=fake_stream),
        ):
            resp = self._post()
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        events = _parse_sse(body)
        self.assertEqual([e['type'] for e in events], ['meta', 'delta', 'delta', 'result'])

        deltas = ''.join(e['delta'] for e in events if e['type'] == 'delta')
        result = events[-1]
        self.assertEqual(deltas, '본문 완성')
        self.assertEqual(result['content'], deltas)
        self.assertEqual(result['title'], 'YT')
        self.assertIn('html', result)
        self.assertEqual(result['usage']['total_tokens'], 5)
        self.assertNotIn('prompt', result)
        self.assertNotIn('prompt_length', result)
        self.assertFalse(result['cached'])
        self.assertFalse(result['comment_summary_included'])
        self.assertEqual(result['youtube_title'], 'YT')
        self.assertEqual(result['transcript_source'], 'api')
        self.assertEqual(result['quota'], {'remaining': 4, 'is_admin': False})

    def test_comments_path_emits_status_before_result(self):
        def fake_stream(*args, **kwargs):
            yield '본문'
            return {
                'prompt': '사용된 프롬프트',
                'usage': {'prompt_tokens': 3, 'completion_tokens': 2, 'total_tokens': 5},
            }

        comment_result = {
            'content': '댓글 요약',
            'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2},
        }

        def fake_comment_summary(
            _app,
            _comments,
            _model,
            on_cost_start=None,
        ):
            self.assertTrue(callable(on_cost_start))
            on_cost_start()
            return comment_result

        with self._patched(
            fetch_youtube=patch(
                'routes.blog_routes._fetch_youtube_content',
                return_value=('자막 본문', ['좋아요'], None, '자막 원문', 'api', []),
            ),
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream', side_effect=fake_stream),
            comment_summary=patch(
                'routes.blog_routes._generate_comment_summary',
                side_effect=fake_comment_summary,
            ),
        ) as mocks:
            resp = self._post()
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        events = _parse_sse(body)
        self.assertEqual([e['type'] for e in events], ['meta', 'delta', 'status', 'result'])
        self.assertEqual(events[2]['stage'], 'comment_summary')
        self.assertTrue(events[-1]['comment_summary_included'])
        self.assertIn('댓글 요약', events[-1]['content'])
        self.assertIs(
            mocks['comment_summary'].call_args.args[3],
            mocks['create_stream'].call_args.kwargs['on_cost_start'],
        )

    def test_cache_hit_stream_emits_meta_and_result_only(self):
        self.app.ai_cache.store['cache-key'] = {
            'title': '캐시 제목',
            'content': '캐시 본문',
            'html': '<p>캐시 본문</p>',
            'comment_summary_included': False,
            'prompt': '캐시 프롬프트',
            'youtube_title': '캐시 YT',
        }

        with self._patched(
            make_key=patch('services.core.cache_service.AICacheService.make_key', return_value='cache-key'),
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream'),
        ) as mocks:
            resp = self._post()
            body = resp.get_data(as_text=True)

        events = _parse_sse(body)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([e['type'] for e in events], ['meta', 'result'])
        self.assertEqual(events[0]['youtube_title'], '캐시 YT')
        self.assertEqual(events[-1]['content'], '캐시 본문')
        self.assertTrue(events[-1]['cached'])
        self.assertNotIn('prompt', events[-1])
        self.assertNotIn('prompt_length', events[-1])
        mocks['get_content_title'].assert_not_called()
        mocks['fetch_youtube'].assert_not_called()
        mocks['create_stream'].assert_not_called()
        mocks['refund_usage'].assert_called_once()

    def test_authenticated_stream_bypasses_shared_cache(self):
        self.app.ai_cache.store['cache-key'] = {
            'title': '캐시 제목',
            'content': '캐시 본문',
            'html': '<p>캐시 본문</p>',
            'comment_summary_included': False,
            'prompt': '캐시 프롬프트',
            'youtube_title': '캐시 YT',
        }
        real_usage = {'remaining': 1, 'is_admin': False}

        def fake_validate(_token):
            from flask import g
            g.user_id = 'user-1'
            return {'valid': True, 'error': None, 'code': None}

        def fake_stream(*_args, **kwargs):
            kwargs['on_cost_start']()
            if False:
                yield None
            return {}

        with self._patched(
            auth_supabase_enabled=patch(
                'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
                return_value=True,
            ),
            route_supabase_enabled=patch('routes.blog_routes.is_supabase_enabled', return_value=True),
            validate_token=patch(
                'src.contexts.identity.interface.auth_decorators._validate_token',
                side_effect=fake_validate,
            ),
            reserve_usage=patch(
                'services.usage.usage_service.UsageService.reserve_for_request',
                return_value=_usage_reservation(
                    before=real_usage,
                    after={'remaining': 0, 'is_admin': False},
                ),
            ),
            refund_usage=patch(
                'services.usage.usage_service.UsageService.refund_reservation',
                return_value=real_usage,
            ),
            make_key=patch('services.core.cache_service.AICacheService.make_key', return_value='cache-key'),
            create_stream=patch(
                'routes.blog_routes.ai_service.create_content_stream',
                side_effect=fake_stream,
            ),
        ) as mocks:
            resp = self._post(headers={**_H, 'Authorization': 'Bearer token'})
            body = resp.get_data(as_text=True)

        events = _parse_sse(body)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([e['type'] for e in events], ['meta', 'result'])
        self.assertFalse(events[-1]['cached'])
        self.assertEqual(events[-1]['quota'], {'remaining': 0, 'is_admin': False})
        mocks['create_stream'].assert_called_once()
        mocks['refund_usage'].assert_not_called()

    def test_cache_hit_still_returns_429_when_usage_exhausted(self):
        self.app.ai_cache.store['cache-key'] = {
            'title': '캐시 제목',
            'content': '캐시 본문',
            'html': '<p>캐시 본문</p>',
            'youtube_title': '캐시 YT',
        }

        def fake_validate(_token):
            from flask import g
            g.user_id = 'user-1'
            return {'valid': True, 'error': None, 'code': None}

        with self._patched(
            auth_supabase_enabled=patch(
                'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
                return_value=True,
            ),
            route_supabase_enabled=patch('routes.blog_routes.is_supabase_enabled', return_value=True),
            validate_token=patch(
                'src.contexts.identity.interface.auth_decorators._validate_token',
                side_effect=fake_validate,
            ),
            reserve_usage=patch(
                'services.usage.usage_service.UsageService.reserve_for_request',
                side_effect=QuotaExceeded('no usage left'),
            ),
            make_key=patch('services.core.cache_service.AICacheService.make_key', return_value='cache-key'),
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream'),
        ) as mocks:
            resp = self._post(headers={**_H, 'Authorization': 'Bearer token'})

        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.get_json()['code'], 'USAGE_LIMIT_EXCEEDED')
        mocks['create_stream'].assert_not_called()
        mocks['get_content_title'].assert_not_called()

    def test_stream_replay_is_rejected_before_cache_or_costly_work(self):
        with self._patched(
            reserve_usage=patch(
                'services.usage.usage_service.UsageService.reserve_for_request',
                side_effect=UsageReservationReplay({
                    'usage_count': 4,
                    'max_usage': 5,
                    'can_use': True,
                }),
            ),
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream'),
        ) as mocks:
            resp = self._post()

        self.assertEqual(resp.status_code, 409)
        self.assertEqual(resp.get_json()['code'], 'IDEMPOTENCY_REPLAY')
        mocks['create_stream'].assert_not_called()
        mocks['get_content_title'].assert_not_called()

    def test_provider_failure_after_cost_start_keeps_its_reservation(self):
        def failing_stream(*_args, **kwargs):
            kwargs['on_cost_start']()
            raise RuntimeError('provider failed')
            yield  # pragma: no cover

        with self._patched(
            create_stream=patch(
                'routes.blog_routes.ai_service.create_content_stream',
                side_effect=failing_stream,
            ),
        ) as mocks:
            resp = self._post()
            events = _parse_sse(resp.get_data(as_text=True))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(events[-1]['type'], 'error')
        mocks['refund_usage'].assert_not_called()

    def test_result_serialization_failure_after_delta_keeps_reservation(self):
        def fake_stream(*_args, **kwargs):
            kwargs['on_cost_start']()
            yield '본문'
            return {'web_sources': object()}

        with self._patched(
            create_stream=patch(
                'routes.blog_routes.ai_service.create_content_stream',
                side_effect=fake_stream,
            ),
        ) as mocks:
            resp = self._post()
            events = _parse_sse(resp.get_data(as_text=True))

        self.assertEqual(events[-1]['type'], 'error')
        mocks['refund_usage'].assert_not_called()

    def test_disconnect_before_cost_start_refunds_reservation(self):
        with self._patched(
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream'),
        ) as mocks:
            response = self.client.post(
                '/generate-stream',
                json={
                    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'model': 'cliproxyapi/gpt-5.5',
                    'style': 'summary',
                },
                headers=_H,
                buffered=False,
            )
            iterator = iter(response.response)
            meta = next(iterator).decode('utf-8')
            self.assertIn('"type": "meta"', meta)
            response.close()

        mocks['create_stream'].assert_not_called()
        mocks['refund_usage'].assert_called_once()

    def test_disconnect_after_first_delta_cannot_refund_provider_cost(self):
        def two_part_stream(*_args, **kwargs):
            kwargs['on_cost_start']()
            yield '첫 토큰'
            yield '두 번째 토큰'

        with self._patched(
            create_stream=patch(
                'routes.blog_routes.ai_service.create_content_stream',
                side_effect=two_part_stream,
            ),
        ) as mocks:
            response = self.client.post(
                '/generate-stream',
                json={
                    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'model': 'cliproxyapi/gpt-5.5',
                    'style': 'summary',
                },
                headers=_H,
                buffered=False,
            )
            iterator = iter(response.response)
            self.assertIn('"type": "meta"', next(iterator).decode('utf-8'))
            self.assertIn('"type": "delta"', next(iterator).decode('utf-8'))
            response.close()

        mocks['create_stream'].assert_called_once()
        mocks['refund_usage'].assert_not_called()

    def test_stream_lost_lease_after_reservation_stops_before_costly_work(self):
        def fake_validate(_token):
            from flask import g
            g.user_id = 'stream-lease-user'
            return {'valid': True, 'error': None, 'code': None}

        lease = MagicMock()
        lease.lost = False
        lease.lost_reason = RuntimeError('renewal lost')
        reservation = _usage_reservation()

        def reserve_then_lose(_user_id):
            lease.lost = True
            return reservation

        with self._patched(
            auth_supabase_enabled=patch(
                'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
                return_value=True,
            ),
            route_supabase_enabled=patch('routes.blog_routes.is_supabase_enabled', return_value=True),
            validate_token=patch(
                'src.contexts.identity.interface.auth_decorators._validate_token',
                side_effect=fake_validate,
            ),
            acquire_lease=patch(
                'routes.blog_routes.acquire_usage_request_lock',
                return_value=lease,
            ),
            reserve_usage=patch(
                'services.usage.usage_service.UsageService.reserve_for_request',
                side_effect=reserve_then_lose,
            ),
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream'),
        ) as mocks:
            resp = self._post(headers={**_H, 'Authorization': 'Bearer token'})

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.get_json()['code'], 'USAGE_LOCK_UNAVAILABLE')
        mocks['create_stream'].assert_not_called()
        mocks['refund_usage'].assert_called_once()
        lease.release.assert_called_once_with()

    def test_same_user_stream_holds_usage_lock_until_completion(self):
        entered = threading.Event()
        finish = threading.Event()
        first_result = {}
        account_usage = {
            'usage_count': 3,
            'max_usage': 5,
            'can_use': True,
            'is_admin': False,
        }
        updated_usage = {**account_usage, 'usage_count': 2}

        def fake_validate(_token):
            from flask import g
            g.user_id = 'stream-user'
            return {'valid': True, 'error': None, 'code': None}

        def slow_stream(*_args, **kwargs):
            kwargs['on_cost_start']()
            entered.set()
            finish.wait(timeout=2)
            yield '완료'
            return {
                'prompt': '프롬프트',
                'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2},
            }

        headers = {**_H, 'Authorization': 'Bearer token'}

        def first_request():
            client = self.app.test_client()
            resp = client.post(
                '/generate-stream',
                json={
                    'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                    'model': 'cliproxyapi/gpt-5.5',
                    'style': 'summary',
                },
                headers=headers,
                environ_overrides={'REMOTE_ADDR': '198.51.100.71'},
            )
            first_result['status'] = resp.status_code
            first_result['body'] = resp.get_data(as_text=True)

        with self._patched(
            auth_supabase_enabled=patch(
                'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
                return_value=True,
            ),
            route_supabase_enabled=patch('routes.blog_routes.is_supabase_enabled', return_value=True),
            validate_token=patch(
                'src.contexts.identity.interface.auth_decorators._validate_token',
                side_effect=fake_validate,
            ),
            reserve_usage=patch(
                'services.usage.usage_service.UsageService.reserve_for_request',
                return_value=_usage_reservation(
                    before=account_usage,
                    after=updated_usage,
                ),
            ),
            create_stream=patch(
                'routes.blog_routes.ai_service.create_content_stream',
                side_effect=slow_stream,
            ),
        ) as mocks:
            worker = threading.Thread(target=first_request)
            worker.start()
            self.assertTrue(entered.wait(timeout=1))
            try:
                second = self.app.test_client().post(
                    '/generate-stream',
                    json={
                        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                        'model': 'cliproxyapi/gpt-5.5',
                        'style': 'summary',
                    },
                    headers=headers,
                    environ_overrides={'REMOTE_ADDR': '198.51.100.72'},
                )
            finally:
                finish.set()
                worker.join(timeout=2)

        self.assertFalse(worker.is_alive())
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.get_json()['code'], 'USAGE_REQUEST_IN_PROGRESS')
        self.assertEqual(first_result['status'], 200)
        self.assertIn('"type": "result"', first_result['body'])
        mocks['reserve_usage'].assert_called_once_with('stream-user')
        mocks['refund_usage'].assert_not_called()

    def test_force_true_bypasses_warmed_cache_and_regenerates(self):
        self.app.ai_cache.store['cache-key'] = {
            'title': '캐시 제목',
            'content': '캐시 본문',
            'html': '<p>캐시 본문</p>',
            'youtube_title': '캐시 YT',
        }

        def fake_stream(*args, **kwargs):
            yield '새 본문'
            return {
                'prompt': '새 프롬프트',
                'usage': {'prompt_tokens': 1, 'completion_tokens': 1, 'total_tokens': 2},
            }

        with self._patched(
            make_key=patch('services.core.cache_service.AICacheService.make_key', return_value='cache-key'),
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream', side_effect=fake_stream),
        ):
            resp = self._post(payload={'force': True})
            body = resp.get_data(as_text=True)

        events = _parse_sse(body)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([e['type'] for e in events], ['meta', 'delta', 'result'])
        self.assertEqual(events[1]['delta'], '새 본문')
        self.assertFalse(events[-1]['cached'])
        self.assertEqual(events[-1]['content'], '새 본문')

    def test_successful_stream_writes_cache_and_next_request_hits(self):
        def fake_stream(*args, **kwargs):
            yield '본문 '
            yield '완성'
            return {
                'prompt': '사용된 프롬프트',
                'usage': {'prompt_tokens': 3, 'completion_tokens': 2, 'total_tokens': 5},
            }

        with self._patched(
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream', side_effect=fake_stream),
        ) as mocks:
            first = self._post()
            first_body = first.get_data(as_text=True)
            self.assertTrue(self._wait_for(lambda: bool(self.app.ai_cache.store)))

            second = self._post()
            second_body = second.get_data(as_text=True)

        first_events = _parse_sse(first_body)
        second_events = _parse_sse(second_body)
        self.assertEqual([e['type'] for e in first_events], ['meta', 'delta', 'delta', 'result'])
        self.assertEqual([e['type'] for e in second_events], ['meta', 'result'])
        self.assertFalse(first_events[-1]['cached'])
        self.assertTrue(second_events[-1]['cached'])
        self.assertEqual(second_events[-1]['content'], '본문 완성')
        self.assertEqual(mocks['create_stream'].call_count, 1)

    def test_successful_stream_saves_history_with_expected_fields(self):
        def fake_stream(*args, **kwargs):
            yield '본문 '
            yield '완성'
            return {
                'prompt': '사용된 프롬프트',
                'usage': {'prompt_tokens': 3, 'completion_tokens': 2, 'total_tokens': 5},
            }

        def fake_validate(_token):
            from flask import g
            g.user_id = 'user-1'
            return {'valid': True, 'error': None, 'code': None}

        headers = {**_H, 'Authorization': 'Bearer token'}
        with self._patched(
            auth_supabase_enabled=patch(
                'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
                return_value=True,
            ),
            route_supabase_enabled=patch('routes.blog_routes.is_supabase_enabled', return_value=False),
            validate_token=patch(
                'src.contexts.identity.interface.auth_decorators._validate_token',
                side_effect=fake_validate,
            ),
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream', side_effect=fake_stream),
            save_history=patch('routes.generation_helpers.save_history'),
        ) as mocks:
            resp = self._post(headers=headers)
            body = resp.get_data(as_text=True)
            save_history_mock = mocks['save_history']
            self.assertTrue(self._wait_for(lambda: save_history_mock.call_count == 1))

        events = _parse_sse(body)
        history_user, history = save_history_mock.call_args.args
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(history_user, 'user-1')
        self.assertEqual(history['id'], events[-1]['id'])
        self.assertEqual(history['url'], 'https://www.youtube.com/watch?v=dQw4w9WgXcQ')
        self.assertEqual(history['title'], 'YT')
        self.assertEqual(history['style'], 'summary')
        self.assertEqual(history['content'], '본문 완성')
        self.assertEqual(history['transcript'], '자막 원문')
        self.assertEqual(history['transcript_source'], 'api')
        self.assertEqual(history['usage']['total_tokens'], 5)

    def test_mid_stream_error_emits_korean_error_event(self):
        def broken_stream(*args, **kwargs):
            yield '부분'
            raise RuntimeError('boom')

        with self._patched(
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream', side_effect=broken_stream),
        ):
            resp = self._post()
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        events = _parse_sse(body)
        self.assertEqual([e['type'] for e in events], ['meta', 'delta', 'error'])
        self.assertIn('생성 중 오류', events[-1]['error'])
        self.assertEqual(events[-1]['message'], events[-1]['error'])

    def test_chatmock_stream_emits_delta_and_result(self):
        def fake_stream(*args, **kwargs):
            yield 'ChatMock 본문'
            return {
                'prompt': 'ChatMock 프롬프트',
                'usage': {'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18},
            }

        with self._patched(
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream', side_effect=fake_stream),
        ) as mocks:
            resp = self._post(model='cliproxyapi/gpt-5.5')
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        events = _parse_sse(body)
        self.assertEqual([e['type'] for e in events], ['meta', 'delta', 'result'])
        self.assertEqual(events[1]['delta'], 'ChatMock 본문')
        self.assertEqual(events[-1]['content'], 'ChatMock 본문')
        self.assertEqual(events[-1]['usage']['total_tokens'], 18)
        self.assertTrue(callable(
            mocks['create_stream'].call_args.kwargs['on_cost_start']
        ))

    def test_direct_text_stream_emits_meta_delta_and_text_result(self):
        text = '직접 붙여넣은 학습 텍스트입니다. 충분한 길이의 본문을 넣어 스트리밍 생성을 검증합니다. ' * 2

        def fake_stream(*args, **kwargs):
            yield '텍스트 '
            yield '결과'
            return {
                'prompt': '직접 텍스트 프롬프트',
                'usage': {'prompt_tokens': 4, 'completion_tokens': 2, 'total_tokens': 6},
            }

        with self._patched(
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream', side_effect=fake_stream),
        ) as mocks:
            resp = self._post(payload={'url': '', 'content': text})
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        events = _parse_sse(body)
        self.assertEqual([e['type'] for e in events], ['meta', 'delta', 'delta', 'result'])
        self.assertEqual(events[0]['source_type'], 'text')
        self.assertEqual(events[0]['transcript_source'], 'direct_input')

        result = events[-1]
        self.assertEqual(result['content'], '텍스트 결과')
        self.assertEqual(result['source_type'], 'text')
        self.assertEqual(result['source_meta']['source_type'], 'text')
        self.assertEqual(result['source_meta']['chars'], len(text))
        self.assertEqual(result['source_meta']['quality_score'], 1.0)
        self.assertEqual(result['transcript_source'], 'direct_input')
        self.assertFalse(result['comment_summary_included'])
        self.assertEqual(result['usage']['total_tokens'], 6)
        self.assertNotIn('prompt', result)
        self.assertNotIn('prompt_length', result)
        mocks['is_youtube_url'].assert_not_called()
        mocks['get_video_id'].assert_not_called()
        mocks['get_content_title'].assert_not_called()
        mocks['fetch_youtube'].assert_not_called()

    def test_direct_text_stream_rejects_url_and_content_before_sse(self):
        text = 'URL과 함께 보내면 안 되는 충분히 긴 직접 입력 텍스트입니다. ' * 3

        with self._patched(
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream'),
        ) as mocks:
            resp = self._post(payload={'content': text})

        self.assertEqual(resp.status_code, 400)
        self.assertNotEqual(resp.mimetype, 'text/event-stream')
        self.assertIn('동시에 입력할 수 없습니다', resp.get_json()['error'])
        mocks['create_stream'].assert_not_called()

    def test_direct_text_stream_rejects_short_content_before_sse(self):
        with self._patched(
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream'),
        ) as mocks:
            resp = self._post(payload={'url': '', 'content': '짧음'})

        self.assertEqual(resp.status_code, 400)
        self.assertNotEqual(resp.mimetype, 'text/event-stream')
        self.assertIn('50자 이상', resp.get_json()['error'])
        mocks['create_stream'].assert_not_called()

    def test_direct_text_stream_rejects_too_long_content_before_sse(self):
        with self._patched(
            max_chars=patch('config.DIRECT_TEXT_MAX_CHARS', 50),
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream'),
        ) as mocks:
            resp = self._post(payload={'url': '', 'content': '가' * 51})

        self.assertEqual(resp.status_code, 400)
        self.assertNotEqual(resp.mimetype, 'text/event-stream')
        self.assertIn('텍스트가 너무 깁니다', resp.get_json()['error'])
        mocks['create_stream'].assert_not_called()


if __name__ == '__main__':
    unittest.main()
