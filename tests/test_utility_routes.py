"""utility_routes.py 라우트 커버리지 테스트.

167개 엔드포인트 중 줄 수가 많은 핵심 함수 + 반복 패턴 (분석 엔드포인트) 커버.
"""
import io
import json
import unittest
from unittest.mock import patch

from flask import g

from app import create_app
from src.contexts.identity.domain.exceptions import QuotaExceeded

_H = {'Origin': 'http://localhost:3000'}


class _BaseTestCase(unittest.TestCase):
    """공통 setUp: Flask test client + Supabase 비활성화."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    # Supabase mock 데코레이터를 각 테스트에 적용하는 대신
    # 테스트 메서드에서 직접 사용


# ── 헬퍼 함수 테스트 ──────────────────────────────────────


class TestHelperFunctions(unittest.TestCase):
    """모듈 레벨 헬퍼 함수 (increment/get 카운터)."""

    def test_increment_request_count(self):
        # 카운터 상태는 routes.utility._state 모듈에 정의됨 (순환 import 제거 후)
        from routes.utility_routes import (
            increment_request_count, get_request_count,
        )
        import routes.utility._state as mod
        original = mod._total_request_count
        increment_request_count()
        self.assertEqual(get_request_count(), original + 1)
        # 복원
        with mod._total_request_count_lock:
            mod._total_request_count = original

    def test_increment_error_count(self):
        from routes.utility_routes import (
            increment_error_count, get_error_count,
        )
        import routes.utility._state as mod
        original = mod._total_error_count
        increment_error_count()
        self.assertEqual(get_error_count(), original + 1)
        with mod._total_error_count_lock:
            mod._total_error_count = original

    def test_get_error_rate_zero_requests(self):
        from routes.utility_routes import get_error_rate
        import routes.utility._state as mod
        orig_req = mod._total_request_count
        orig_err = mod._total_error_count
        mod._total_request_count = 0
        mod._total_error_count = 0
        self.assertEqual(get_error_rate(), 0.0)
        mod._total_request_count = orig_req
        mod._total_error_count = orig_err

    def test_get_error_rate_nonzero(self):
        from routes.utility_routes import get_error_rate
        import routes.utility._state as mod
        orig_req = mod._total_request_count
        orig_err = mod._total_error_count
        mod._total_request_count = 100
        mod._total_error_count = 5
        self.assertEqual(get_error_rate(), 0.05)
        mod._total_request_count = orig_req
        mod._total_error_count = orig_err

    def test_active_requests_counter(self):
        from routes.utility_routes import (
            increment_active_requests, decrement_active_requests,
            get_active_requests
        )
        import routes.utility._state as mod
        orig = mod._active_requests_counter
        mod._active_requests_counter = 0
        increment_active_requests()
        self.assertEqual(get_active_requests(), 1)
        decrement_active_requests()
        self.assertEqual(get_active_requests(), 0)
        # 0 아래로 내려가지 않아야 함
        decrement_active_requests()
        self.assertEqual(get_active_requests(), 0)
        mod._active_requests_counter = orig

    def test_cleanup_stale_clients(self):
        import time
        from routes.utility_routes import _cleanup_stale_clients, _CLIENT_TRACKER
        _CLIENT_TRACKER['old_client'] = time.time() - 600  # 10분 전
        _CLIENT_TRACKER['new_client'] = time.time()
        _cleanup_stale_clients()
        self.assertNotIn('old_client', _CLIENT_TRACKER)
        self.assertIn('new_client', _CLIENT_TRACKER)
        _CLIENT_TRACKER.pop('new_client', None)


# ── 헬스체크 / 홈 / 하트비트 ──────────────────────────────────────


class TestHealthAndHome(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_health_returns_200(self, _):
        resp = self.client.get('/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'healthy')
        self.assertIn('api_version', data)
        self.assertIn('request_count', data)
        self.assertIn('error_rate', data)

    def test_ready_skips_external_probes_outside_production(self):
        with patch.dict('os.environ', {'FLASK_ENV': 'testing'}, clear=False), \
                patch('routes.utility.operations._check_chatmock_ready') as chatmock, \
                patch('routes.utility.operations._check_full_stack_frontend_ready') as frontend, \
                patch('routes.utility.operations._check_redis_ready') as redis, \
                patch(
                    'routes.utility.operations.is_supabase_enabled',
                    return_value=False,
                ), \
                patch('routes.utility.operations.get_supabase') as get_supabase:
            resp = self.client.get('/ready')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['status'], 'ready')
        self.assertEqual(
            resp.get_json()['dependencies']['supabase_schema']['reason'],
            'skipped_outside_production',
        )
        chatmock.assert_not_called()
        frontend.assert_not_called()
        redis.assert_not_called()
        get_supabase.assert_not_called()

    def test_ready_fails_closed_when_production_dependency_is_down(self):
        schema_status = {'ready': True, 'current_version': 9}
        with patch.dict('os.environ', {'FLASK_ENV': 'production'}, clear=False), \
                patch('routes.utility.operations._check_chatmock_ready', return_value=True), \
                patch(
                    'routes.utility.operations._check_full_stack_frontend_ready',
                    return_value=None,
                ), \
                patch('routes.utility.operations._check_redis_ready', return_value=False), \
                patch(
                    'routes.utility.operations._supabase_schema_status',
                    return_value=schema_status,
                ):
            resp = self.client.get('/ready')

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.get_json(), {
            'status': 'not_ready',
            'dependencies': {
                'chatmock': True,
                'frontend': 'not_required',
                'redis': False,
                'supabase_schema': schema_status,
            },
        })

    def test_ready_accepts_traffic_when_production_dependencies_are_live(self):
        schema_status = {'ready': True, 'current_version': 9}
        with patch.dict('os.environ', {'FLASK_ENV': 'production'}, clear=False), \
                patch('routes.utility.operations._check_chatmock_ready', return_value=True), \
                patch(
                    'routes.utility.operations._check_full_stack_frontend_ready',
                    return_value=True,
                ), \
                patch('routes.utility.operations._check_redis_ready', return_value=True), \
                patch(
                    'routes.utility.operations._supabase_schema_status',
                    return_value=schema_status,
                ):
            resp = self.client.get('/ready')

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['status'], 'ready')

    def test_ready_fails_closed_when_full_stack_frontend_is_down(self):
        schema_status = {'ready': True, 'current_version': 9}
        with patch.dict('os.environ', {'FLASK_ENV': 'production'}, clear=False), \
                patch('routes.utility.operations._check_chatmock_ready', return_value=True), \
                patch(
                    'routes.utility.operations._check_full_stack_frontend_ready',
                    return_value=False,
                ), \
                patch('routes.utility.operations._check_redis_ready', return_value=True), \
                patch(
                    'routes.utility.operations._supabase_schema_status',
                    return_value=schema_status,
                ):
            resp = self.client.get('/ready')

        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.get_json()['dependencies']['frontend'], False)

    def test_full_stack_frontend_probe_rejects_non_loopback_configuration(self):
        from routes.utility.operations import _check_full_stack_frontend_ready

        with patch.dict(
            'os.environ',
            {'FULL_STACK_FRONTEND_READINESS_URL': 'https://example.com/'},
            clear=False,
        ), patch('routes.utility.operations.requests.get') as get:
            result = _check_full_stack_frontend_ready()

        self.assertFalse(result)
        get.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_home_returns_ok(self, _):
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'ok')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_heartbeat_success(self, _):
        resp = self.client.post('/api/heartbeat',
                                json={'clientId': 'test-client-123'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ok'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_heartbeat_missing_client_id(self, _):
        resp = self.client.post('/api/heartbeat', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_heartbeat_rejects_oversized_client_id(self, _):
        resp = self.client.post(
            '/api/heartbeat',
            json={'clientId': 'x' * 129},
            headers=_H,
        )
        self.assertEqual(resp.status_code, 400)

    def test_heartbeat_tracker_is_bounded(self):
        from routes.utility import _state

        _state._CLIENT_TRACKER.clear()
        with patch.object(_state, '_CLIENT_TRACKER_MAX_ITEMS', 2):
            _state.record_client_heartbeat('client-1', now=1)
            _state.record_client_heartbeat('client-2', now=2)
            _state.record_client_heartbeat('client-3', now=3)

        self.assertEqual(list(_state._CLIENT_TRACKER), ['client-2', 'client-3'])
        _state._CLIENT_TRACKER.clear()


# ── 프로바이더 관련 ──────────────────────────────────────


class TestProviderRoutes(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_providers_returns_list(self, _):
        resp = self.client.get('/api/providers')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('providers', data)
        self.assertIn('styles', data)
        self.assertIn('hasAutoFallback', data)

# ── 캐시 관련 ──────────────────────────────────────


class TestCacheRoutes(_BaseTestCase):

    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    @patch('routes.utility_routes.clear_cache')
    def test_clear_cache_requires_auth_in_production(self, mock_clear, _mock_enabled):
        resp = self.client.delete('/api/cache', json={}, headers=_H)

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()['code'], 'AUTH_REQUIRED')
        mock_clear.assert_not_called()

    @patch('routes.utility_routes.is_supabase_enabled', return_value=False)
    @patch('routes.utility_routes.clear_cache', return_value=3)
    def test_clear_cache_all_in_local_mode_requires_explicit_scope(self, mock_clear, _):
        resp = self.client.delete('/api/cache',
                                  data='{"scope": "all"}',
                                  content_type='application/json',
                                  headers=_H,
                                  environ_overrides={'REMOTE_ADDR': '198.51.100.51'})
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['deleted'], 3)
        mock_clear.assert_called_once_with(None)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.utility_routes.clear_cache')
    def test_clear_cache_invalid_url_never_clears_all(self, mock_clear, _):
        resp = self.client.delete(
            '/api/cache',
            json={'url': 'https://example.com/no-video'},
            headers=_H,
            environ_overrides={'REMOTE_ADDR': '198.51.100.52'},
        )

        self.assertEqual(resp.status_code, 400)
        mock_clear.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.utility_routes.clear_cache')
    def test_clear_cache_non_youtube_url_with_video_like_id_is_rejected(self, mock_clear, _):
        resp = self.client.delete(
            '/api/cache',
            json={'url': 'https://example.com/watch?v=abcdefghijk'},
            headers=_H,
            environ_overrides={'REMOTE_ADDR': '198.51.100.56'},
        )

        self.assertEqual(resp.status_code, 400)
        mock_clear.assert_not_called()

    @patch('routes.utility_routes.is_supabase_enabled', return_value=True)
    @patch('routes.utility_routes.UsageService.is_admin_user', return_value=False)
    @patch('routes.utility_routes.clear_cache')
    def test_clear_cache_all_forbidden_for_regular_user(self, mock_clear, mock_admin, _):
        def authenticate(_token):
            g.user_id = 'regular-user'
            return {'valid': True, 'error': None, 'code': None}

        with patch(
            'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
            return_value=True,
        ), patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=authenticate,
        ):
            resp = self.client.delete(
                '/api/cache',
                json={'scope': 'all'},
                headers={**_H, 'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.53'},
            )

        self.assertEqual(resp.status_code, 403)
        mock_admin.assert_called_once_with('regular-user')
        mock_clear.assert_not_called()

    @patch('routes.utility_routes.is_supabase_enabled', return_value=True)
    @patch('routes.utility_routes.UsageService.is_admin_user', return_value=True)
    @patch('routes.utility_routes.clear_cache', return_value=4)
    def test_clear_cache_all_allowed_for_admin(self, mock_clear, mock_admin, _):
        def authenticate(_token):
            g.user_id = 'admin-user'
            return {'valid': True, 'error': None, 'code': None}

        with patch(
            'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
            return_value=True,
        ), patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=authenticate,
        ):
            resp = self.client.delete(
                '/api/cache',
                json={'scope': 'all'},
                headers={**_H, 'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.54'},
            )

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['deleted'], 4)
        mock_admin.assert_called_once_with('admin-user')
        mock_clear.assert_called_once_with(None)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.utility_routes.clear_cache', return_value=1)
    def test_clear_cache_is_rate_limited(self, _mock_clear, _):
        responses = [
            self.client.delete(
                '/api/cache',
                json={'videoId': 'abcdefghijk'},
                headers=_H,
                environ_overrides={'REMOTE_ADDR': '198.51.100.57'},
            )
            for _index in range(6)
        ]

        self.assertTrue(all(response.status_code == 200 for response in responses[:5]))
        self.assertEqual(responses[5].status_code, 429)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.utility_routes.clear_cache', return_value=1)
    def test_clear_cache_by_video_id(self, mock_clear, _):
        resp = self.client.delete('/api/cache',
                                  data='{"videoId": "abc123"}',
                                  content_type='application/json',
                                  headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('abc123', data['message'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.utility_routes.clear_cache', return_value=1)
    @patch('routes.utility_routes.content_service')
    def test_clear_cache_by_url(self, mock_cs, mock_clear, _):
        mock_cs.get_video_id.return_value = 'xyz789'
        resp = self.client.delete('/api/cache',
                                  data='{"url": "https://youtube.com/watch?v=xyz789"}',
                                  content_type='application/json',
                                  headers=_H)
        self.assertEqual(resp.status_code, 200)


# ── 웹훅 테스트 ──────────────────────────────────────


class TestWebhookRoutes(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_webhook_test_missing_url(self, _):
        resp = self.client.post('/api/webhook/test', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.platform.webhook_service.WebhookService.test')
    def test_webhook_test_success(self, mock_test, _):
        mock_test.return_value = {'success': True, 'status_code': 200}
        resp = self.client.post('/api/webhook/test',
                                json={'url': 'https://hooks.example.com/test'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['success'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.platform.webhook_service.WebhookService.test')
    def test_webhook_test_failure(self, mock_test, _):
        mock_test.return_value = {'success': False, 'error': '연결 실패'}
        resp = self.client.post('/api/webhook/test',
                                json={'url': 'https://hooks.example.com/bad'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)


# ── 재생목록 ──────────────────────────────────────


class TestPlaylistRoutes(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_playlist_missing_url(self, _):
        resp = self.client.post('/api/playlist-videos', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.is_channel_url', return_value=False)
    @patch('services.core.content_service.is_playlist_url', return_value=False)
    def test_playlist_invalid_url(self, *_):
        resp = self.client.post('/api/playlist-videos',
                                json={'url': 'https://example.com'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.get_playlist_videos')
    @patch('services.core.content_service.is_channel_url', return_value=False)
    @patch('services.core.content_service.is_playlist_url', return_value=True)
    def test_playlist_success(self, mock_is_pl, mock_is_ch, mock_get, _):
        mock_get.return_value = {'videos': [{'id': 'v1'}], 'total': 1}
        resp = self.client.post('/api/playlist-videos',
                                json={'url': 'https://youtube.com/playlist?list=PL123'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['total'], 1)


# ── 피드백 ──────────────────────────────────────


class TestFeedback(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_optimizer_service.save_feedback')
    def test_feedback_submit(self, mock_submit, _):
        mock_submit.return_value = {'success': True}
        resp = self.client.post('/api/feedback',
                                json={'style_id': 'blog_seo', 'content_id': 'c1',
                                      'rating': 'like'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_feedback_submit_missing_fields(self, _):
        resp = self.client.post('/api/feedback',
                                json={'style_id': 'blog_seo'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)


# ── 콘텐츠 분석 엔드포인트 (반복 패턴) ──────────────────────────────
# content → service 호출 → jsonify 패턴. 정상 + 빈 입력 테스트.


class TestAnalysisEndpoints(_BaseTestCase):
    """분석 엔드포인트를 일괄 테스트.

    모두 동일한 패턴: POST + content → service → jsonify.
    빈 content 400 + 정상 호출 200 테스트.
    """

    # 빈 content/text 400 테스트 대상 (엔드포인트 경로, 필드명) 튜플
    # 'content' 필드를 사용하는 엔드포인트
    _CONTENT_ENDPOINTS = [
        '/api/fact-check', '/api/plagiarism-check',
        '/api/sentiment-flow',
    ]
    # 'text' 필드를 사용하는 엔드포인트
    _TEXT_ENDPOINTS = ['/api/readability']

    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_fact_check_requires_auth_when_supabase_enabled(self, _):
        resp = self.client.post(
            '/api/fact-check',
            json={'content': '테스트 콘텐츠'},
            headers=_H,
            environ_overrides={'REMOTE_ADDR': '198.51.100.41'},
        )

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()['code'], 'AUTH_REQUIRED')

    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_sentiment_flow_requires_auth_when_supabase_enabled(self, _):
        resp = self.client.post(
            '/api/sentiment-flow',
            json={'content': '테스트 콘텐츠'},
            headers=_H,
            environ_overrides={'REMOTE_ADDR': '198.51.100.51'},
        )

        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()['code'], 'AUTH_REQUIRED')

    @patch(
        'services.usage.usage_decorator.UsageService.reserve_for_request',
        side_effect=QuotaExceeded,
    )
    @patch(
        'services.usage.usage_decorator.is_supabase_enabled',
        return_value=True,
    )
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_fact_check_rejects_exhausted_usage(self, _, __, mock_reserve):
        def authenticate(_token):
            g.user_id = 'user-fact-check'
            return {'valid': True, 'error': None, 'code': None}

        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=authenticate,
        ), patch('services.agents.fact_check_agent.fact_check') as mock_fact_check:
            resp = self.client.post(
                '/api/fact-check',
                json={'content': '테스트 콘텐츠'},
                headers={
                    **_H,
                    'Authorization': 'Bearer valid-token',
                },
                environ_overrides={'REMOTE_ADDR': '198.51.100.42'},
            )

        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.get_json()['code'], 'USAGE_LIMIT_EXCEEDED')
        mock_reserve.assert_called_once_with('user-fact-check')
        mock_fact_check.assert_not_called()

    @patch(
        'services.usage.usage_decorator.UsageService.reserve_for_request',
        side_effect=QuotaExceeded,
    )
    @patch(
        'services.usage.usage_decorator.is_supabase_enabled',
        return_value=True,
    )
    @patch(
        'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
        return_value=True,
    )
    def test_sentiment_flow_rejects_exhausted_usage(self, _, __, mock_reserve):
        def authenticate(_token):
            g.user_id = 'user-sentiment'
            return {'valid': True, 'error': None, 'code': None}

        with patch(
            'src.contexts.identity.interface.auth_decorators._validate_token',
            side_effect=authenticate,
        ), patch(
            'services.analysis.nlp_analysis_service.analyze_sentiment_flow'
        ) as mock_analyze:
            resp = self.client.post(
                '/api/sentiment-flow',
                json={'content': '테스트 콘텐츠'},
                headers={**_H, 'Authorization': 'Bearer valid-token'},
                environ_overrides={'REMOTE_ADDR': '198.51.100.52'},
            )

        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.get_json()['code'], 'USAGE_LIMIT_EXCEEDED')
        mock_reserve.assert_called_once_with('user-sentiment')
        mock_analyze.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.analysis.nlp_analysis_service.analyze_sentiment_flow')
    def test_sentiment_flow_rejects_unlisted_model(self, mock_analyze, _):
        resp = self.client.post(
            '/api/sentiment-flow',
            json={
                'content': '테스트 콘텐츠',
                'model': 'attacker/arbitrary-model',
            },
            headers=_H,
            environ_overrides={'REMOTE_ADDR': '198.51.100.53'},
        )

        self.assertEqual(resp.status_code, 400)
        mock_analyze.assert_not_called()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_empty_content_returns_400(self, _):
        """분석 엔드포인트에서 빈 content/text는 400."""
        for path in self._CONTENT_ENDPOINTS:
            with self.subTest(path=path):
                resp = self.client.post(path, json={'content': ''}, headers=_H)
                self.assertEqual(resp.status_code, 400,
                                 f'{path}: 빈 content에 400 기대, {resp.status_code} 반환')
        for path in self._TEXT_ENDPOINTS:
            with self.subTest(path=path):
                resp = self.client.post(path, json={'text': ''}, headers=_H)
                self.assertEqual(resp.status_code, 400,
                                 f'{path}: 빈 text에 400 기대, {resp.status_code} 반환')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_no_body_returns_400(self, _):
        """본문 없이 요청 시 400."""
        for path in self._CONTENT_ENDPOINTS:
            with self.subTest(path=path):
                resp = self.client.post(path, json={}, headers=_H)
                self.assertEqual(resp.status_code, 400,
                                 f'{path}: 빈 body에 400 기대, {resp.status_code} 반환')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_simple_analysis_services_return_200(self, _):
        """간단한 content-only 서비스: fact-check, plagiarism, readability, sentiment-flow."""
        # 서비스 함수가 단순 content 파라미터만 받는 것들만 테스트
        simple_services = [
            ('/api/fact-check', 'services.agents.fact_check_agent.fact_check', 'content'),
            ('/api/plagiarism-check', 'services.quality.plagiarism_service.check_plagiarism', 'content'),
            ('/api/readability', 'services.analysis.readability_service.analyze_readability', 'text'),
            ('/api/sentiment-flow', 'services.analysis.nlp_analysis_service.analyze_sentiment_flow', 'content'),
        ]
        for path, service_path, field_name in simple_services:
            with self.subTest(path=path):
                with patch(service_path, return_value={'score': 0.8, 'result': 'ok'}) as mock_svc:
                    payload = {field_name: '테스트용 콘텐츠입니다. 충분히 긴 텍스트.'}
                    resp = self.client.post(path, json=payload, headers=_H)
                    self.assertEqual(resp.status_code, 200,
                                     f'{path}: 200 기대, {resp.status_code} 반환 — {resp.get_json()}')


# ── RSS 피드 ──────────────────────────────────────


class TestRSSFeed(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_rss_feed_returns_xml(self, _):
        resp = self.client.get('/feed.xml')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('xml', resp.content_type)


if __name__ == '__main__':
    unittest.main()
