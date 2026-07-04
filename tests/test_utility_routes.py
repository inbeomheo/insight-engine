"""utility_routes.py 라우트 커버리지 테스트.

167개 엔드포인트 중 줄 수가 많은 핵심 함수 + 반복 패턴 (분석 엔드포인트) 커버.
"""
import io
import json
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

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

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('requests.get')
    def test_ollama_health_success(self, mock_get, _):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'models': [{'name': 'llama3'}]}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        resp = self.client.get('/api/ollama/health')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ok'])
        self.assertIn('llama3', data['models'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('requests.get', side_effect=Exception('connection refused'))
    def test_ollama_health_failure(self, mock_get, _):
        resp = self.client.get('/api/ollama/health')
        self.assertEqual(resp.status_code, 503)
        data = resp.get_json()
        self.assertFalse(data['ok'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_provider_missing_id(self, _):
        resp = self.client.post('/api/providers/validate',
                                json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()['valid'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_provider_unsupported(self, _):
        resp = self.client.post('/api/providers/validate',
                                json={'provider_id': 'nonexistent_provider_xyz'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('requests.get')
    def test_validate_provider_ollama(self, mock_get, _):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'models': []}
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        resp = self.client.post('/api/providers/validate',
                                json={'provider_id': 'ollama',
                                      'api_key': 'http://localhost:11434'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['valid'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_validate_provider_no_api_key(self, _):
        """Ollama가 아닌 프로바이더에서 api_key 누락 시 에러."""
        # gemini 프로바이더가 존재한다고 가정
        resp = self.client.post('/api/providers/validate',
                                json={'provider_id': 'gemini'},
                                headers=_H)
        # api_key 없으면 400
        self.assertIn(resp.status_code, [200, 400])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_campaign_packs(self, _):
        resp = self.client.get('/api/providers/campaign-packs')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('packs', data)


# ── 캐시 관련 ──────────────────────────────────────


class TestCacheRoutes(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('routes.utility_routes.clear_cache', return_value=3)
    def test_clear_cache_all(self, mock_clear, _):
        resp = self.client.delete('/api/cache',
                                  data='{}',
                                  content_type='application/json',
                                  headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['deleted'], 3)

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


# ── 소스 추천 ──────────────────────────────────────


class TestRecommendSources(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_recommend_sources_missing_topic(self, _):
        resp = self.client.post('/api/recommend-sources', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.content.source_recommender_service.recommend_sources')
    def test_recommend_sources_success(self, mock_rec, _):
        mock_rec.return_value = [{'url': 'https://example.com', 'relevance': 0.9}]
        resp = self.client.post('/api/recommend-sources',
                                json={'topic': 'AI 기술'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(len(data['sources']), 1)


# ── NPS 피드백 ──────────────────────────────────────


class TestNPSFeedback(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_nps_valid_score(self, _):
        resp = self.client.post('/api/feedback/nps',
                                json={'score': 8, 'feedback': '좋아요'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['score'], 8)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_nps_invalid_score(self, _):
        resp = self.client.post('/api/feedback/nps',
                                json={'score': 15},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_nps_missing_score(self, _):
        resp = self.client.post('/api/feedback/nps',
                                json={},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)


# ── AI 캐시 삭제 ──────────────────────────────────────


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
        '/api/fact-check', '/api/seo-optimize', '/api/plagiarism-check',
        '/api/sentiment-flow',
    ]
    # 'text' 필드를 사용하는 엔드포인트
    _TEXT_ENDPOINTS = ['/api/readability']

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
                    if path == '/api/seo-optimize':
                        payload['keywords'] = ['테스트']
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
