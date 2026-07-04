"""P7+: /generate-stream 토큰 delta SSE 회귀 테스트."""
import json
import time
import unittest
from contextlib import ExitStack, contextmanager
from unittest.mock import patch

from app import create_app


_H = {'Origin': 'http://localhost:3000'}


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
        self.app.ai_cache = _FakeCache()
        self.client = self.app.test_client()

    def _post(self, model='test/model', payload=None, headers=None):
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
        self.assertEqual(result['prompt'], '사용된 프롬프트')
        self.assertFalse(result['cached'])
        self.assertFalse(result['comment_summary_included'])
        self.assertEqual(result['youtube_title'], 'YT')
        self.assertEqual(result['transcript_source'], 'api')
        self.assertEqual(result['quota'], {'remaining': 4})

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

        with self._patched(
            fetch_youtube=patch(
                'routes.blog_routes._fetch_youtube_content',
                return_value=('자막 본문', ['좋아요'], None, '자막 원문', 'api', []),
            ),
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream', side_effect=fake_stream),
            comment_summary=patch('routes.blog_routes._generate_comment_summary', return_value=comment_result),
        ):
            resp = self._post()
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        events = _parse_sse(body)
        self.assertEqual([e['type'] for e in events], ['meta', 'delta', 'status', 'result'])
        self.assertEqual(events[2]['stage'], 'comment_summary')
        self.assertTrue(events[-1]['comment_summary_included'])
        self.assertIn('댓글 요약', events[-1]['content'])

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
        mocks['get_content_title'].assert_not_called()
        mocks['fetch_youtube'].assert_not_called()
        mocks['create_stream'].assert_not_called()

    def test_cache_hit_uses_real_usage_quota_after_usage_check(self):
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
            check_can_use=patch(
                'services.usage.usage_service.UsageService.check_can_use',
                return_value=(True, real_usage),
            ),
            make_key=patch('services.core.cache_service.AICacheService.make_key', return_value='cache-key'),
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream'),
        ):
            resp = self._post(headers={**_H, 'Authorization': 'Bearer token'})
            body = resp.get_data(as_text=True)

        events = _parse_sse(body)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual([e['type'] for e in events], ['meta', 'result'])
        self.assertTrue(events[-1]['cached'])
        self.assertEqual(events[-1]['quota'], real_usage)

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
            check_can_use=patch(
                'services.usage.usage_service.UsageService.check_can_use',
                return_value=(False, {'remaining': 0}),
            ),
            make_key=patch('services.core.cache_service.AICacheService.make_key', return_value='cache-key'),
            create_stream=patch('routes.blog_routes.ai_service.create_content_stream'),
        ) as mocks:
            resp = self._post(headers={**_H, 'Authorization': 'Bearer token'})

        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.get_json()['code'], 'USAGE_LIMIT_EXCEEDED')
        mocks['create_stream'].assert_not_called()
        mocks['get_content_title'].assert_not_called()

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

    def test_glm_fallback_emits_single_delta_and_result_from_meta_result(self):
        fallback_result = {
            'title': 'GLM 제목',
            'content': 'GLM 본문',
            'html': '<p>GLM 본문</p>',
            'usage': {'prompt_tokens': 11, 'completion_tokens': 7, 'total_tokens': 18},
        }

        with self._patched(
            create_content=patch('services.core.ai_service.create_content', return_value=(fallback_result, 'GLM 프롬프트')),
        ):
            resp = self._post(model='zhipuai/GLM-4.7')
            body = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        events = _parse_sse(body)
        self.assertEqual([e['type'] for e in events], ['meta', 'delta', 'result'])
        self.assertEqual(events[1]['delta'], 'GLM 본문')
        self.assertEqual(events[-1]['title'], 'GLM 제목')
        self.assertEqual(events[-1]['content'], 'GLM 본문')
        self.assertEqual(events[-1]['usage']['total_tokens'], 18)


if __name__ == '__main__':
    unittest.main()
