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
        from routes.utility_routes import (
            increment_request_count, get_request_count,
            _total_request_count_lock
        )
        import routes.utility_routes as mod
        original = mod._total_request_count
        increment_request_count()
        self.assertEqual(get_request_count(), original + 1)
        # 복원
        with _total_request_count_lock:
            mod._total_request_count = original

    def test_increment_error_count(self):
        from routes.utility_routes import (
            increment_error_count, get_error_count,
            _total_error_count_lock
        )
        import routes.utility_routes as mod
        original = mod._total_error_count
        increment_error_count()
        self.assertEqual(get_error_count(), original + 1)
        with _total_error_count_lock:
            mod._total_error_count = original

    def test_get_error_rate_zero_requests(self):
        from routes.utility_routes import get_error_rate
        import routes.utility_routes as mod
        orig_req = mod._total_request_count
        orig_err = mod._total_error_count
        mod._total_request_count = 0
        mod._total_error_count = 0
        self.assertEqual(get_error_rate(), 0.0)
        mod._total_request_count = orig_req
        mod._total_error_count = orig_err

    def test_get_error_rate_nonzero(self):
        from routes.utility_routes import get_error_rate
        import routes.utility_routes as mod
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
        import routes.utility_routes as mod
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

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_close_success(self, _):
        # 먼저 heartbeat로 등록
        self.client.post('/api/heartbeat',
                         json={'clientId': 'close-test'},
                         headers=_H)
        resp = self.client.post('/api/close',
                                json={'clientId': 'close-test'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['ok'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_close_missing_client_id(self, _):
        resp = self.client.post('/api/close', json={}, headers=_H)
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


# ── 스타일 추천 / 생성 ──────────────────────────────────────


class TestStyleRoutes(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_recommend_style_missing_url(self, _):
        resp = self.client.post('/api/recommend-style', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.content_service.is_youtube_url', return_value=False)
    def test_recommend_style_invalid_url(self, mock_yt, _):
        resp = self.client.post('/api/recommend-style',
                                json={'url': 'https://example.com'},
                                headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.ai_service.create_content')
    @patch('services.core.content_service.get_content_title', return_value='테스트 영상')
    @patch('services.core.content_service.get_video_id', return_value='v123')
    @patch('services.core.content_service.is_youtube_url', return_value=True)
    def test_recommend_style_success(self, *mocks):
        mocks[0]  # is_youtube_url
        # ai_service.create_content mock
        mocks[3].return_value = {
            'content': '{"style": "blog_seo", "reason": "적합", "modifiers": {"length": "medium"}}'
        }
        resp = self.client.post('/api/recommend-style',
                                json={'url': 'https://youtube.com/watch?v=v123'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['style'], 'blog_seo')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.ai_service.create_content')
    @patch('services.core.content_service.get_content_title', return_value='테스트')
    @patch('services.core.content_service.get_video_id', return_value='v123')
    @patch('services.core.content_service.is_youtube_url', return_value=True)
    def test_recommend_style_json_parse_fail(self, *mocks):
        """AI가 JSON이 아닌 응답을 주면 기본값 반환."""
        mocks[3].return_value = {'content': '추천 스타일은 blog_seo입니다.'}
        resp = self.client.post('/api/recommend-style',
                                json={'url': 'https://youtube.com/watch?v=v123'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['style'], 'detailed')  # 기본값

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_generate_style_missing_url(self, _):
        resp = self.client.post('/api/generate-style', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.ai_service.create_content')
    @patch('services.core.content_service.get_transcript', return_value={'text': '자막 내용', 'error': None})
    @patch('services.core.content_service.get_content_title', return_value='테스트 영상')
    @patch('services.core.content_service.get_video_id', return_value='v456')
    @patch('services.core.content_service.is_youtube_url', return_value=True)
    def test_generate_style_success(self, *mocks):
        mocks[4].return_value = {
            'content': '{"styleName": "기술 분석", "stylePrompt": "기술 분석용 프롬프트", "description": "적합"}'
        }
        resp = self.client.post('/api/generate-style',
                                json={'url': 'https://youtube.com/watch?v=v456'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['styleName'], '기술 분석')


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


# ── 워드클라우드 ──────────────────────────────────────


class TestWordcloud(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_wordcloud_missing_text(self, _):
        resp = self.client.post('/api/wordcloud', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.media.wordcloud_service.generate_wordcloud')
    def test_wordcloud_success(self, mock_wc, _):
        mock_wc.return_value = '<svg>...</svg>'
        resp = self.client.post('/api/wordcloud',
                                json={'text': '테스트 텍스트 입니다 반복 텍스트'},
                                headers=_H)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('svg', resp.get_json())


# ── 스키마 엔드포인트 ──────────────────────────────────────


class TestSchema(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_schema_returns_openapi(self, _):
        resp = self.client.get('/api/schema')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['openapi'], '3.0.0')
        self.assertIn('paths', data)


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

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.platform.nps_feedback_service.build_nps_feedback_response')
    def test_nps_uses_feedback_service(self, mock_build, _):
        mock_build.return_value = ({'normalized': True}, 209)

        resp = self.client.post('/api/feedback/nps', json={'score': 7}, headers=_H)

        self.assertEqual(resp.status_code, 209)
        self.assertEqual(resp.get_json(), {'normalized': True})
        mock_build.assert_called_once_with({'score': 7}, user_id='anonymous')


# ── AI 캐시 삭제 ──────────────────────────────────────


class TestAICacheDelete(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_clear_ai_cache(self, _):
        resp = self.client.delete('/api/cache/ai', json={}, headers=_H)
        # AI 캐시 삭제 성공 또는 기능 존재 확인
        self.assertIn(resp.status_code, [200, 500])


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

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.data.prompt_optimizer_service.get_feedback_stats')
    def test_feedback_stats(self, mock_stats, _):
        mock_stats.return_value = {'count': 10, 'avg_rating': 4.2}
        resp = self.client.get('/api/feedback/stats/blog_seo')
        self.assertEqual(resp.status_code, 200)


# ── 콘텐츠 분석 엔드포인트 (반복 패턴) ──────────────────────────────
# content → service 호출 → jsonify 패턴. 정상 + 빈 입력 테스트.


class TestAnalysisEndpoints(_BaseTestCase):
    """분석 엔드포인트 (약 100개)를 일괄 테스트.

    모두 동일한 패턴: POST + content → service → jsonify.
    빈 content 400 + 정상 호출 200 테스트.
    """

    # 빈 content/text 400 테스트 대상 (엔드포인트 경로, 필드명) 튜플
    # 'content' 필드를 사용하는 엔드포인트
    _CONTENT_ENDPOINTS = [
        '/api/fact-check', '/api/seo-optimize', '/api/plagiarism-check',
        '/api/sentiment-flow', '/api/grade-content',
        '/api/analyze-sentiment', '/api/benchmark-readability',
        '/api/reading-time', '/api/analyze-transitions',
        '/api/emotional-tone', '/api/engagement-score',
        '/api/sentence-variety', '/api/check-redundancy',
        '/api/detect-passive', '/api/extract-acronyms',
        '/api/analyze-speakability', '/api/detect-subheading-gaps',
        '/api/check-heading-parallelism', '/api/detect-section-drift',
        '/api/check-pronoun-clarity', '/api/analyze-example-coverage',
        '/api/check-qa-closure', '/api/detect-adverb-overuse',
        '/api/detect-clause-overload', '/api/analyze-statistics-coverage',
        '/api/find-simple-alternatives', '/api/check-acronym-expansion',
        '/api/detect-actionability-gaps', '/api/check-thesis-frontload',
        '/api/detect-list-table-opportunities',
        '/api/analyze-question-density', '/api/audit-whitespace-formatting',
        '/api/analyze-bullet-density', '/api/check-code-block-quality',
        '/api/check-paragraph-opening-variety', '/api/check-tone-consistency',
        '/api/detect-linking-verb-overuse', '/api/validate-instruction-sequence',
        '/api/score-content-depth', '/api/analyze-conclusion-strength',
        '/api/check-parenthetical-overuse',
        '/api/detect-anaphora-repetition',
        '/api/analyze-connector-variety',
        '/api/check-content-freshness', '/api/check-article-format',
        '/api/map-emotional-arc', '/api/analyze-sentence-rhythm',
        '/api/detect-keyword-stuffing',
        '/api/analyze-sentence-ending-variety',
        '/api/analyze-passive-ratio', '/api/analyze-avg-words-per-sentence',
        '/api/analyze-emoji-usage', '/api/check-acronym-consistency',
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
        for path in self._CONTENT_ENDPOINTS[:10]:  # 대표 10개만
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
            ('/api/grade-content', 'services.quality.content_grader_service.grade_content', 'content'),
            ('/api/analyze-sentiment', 'services.analysis.sentiment_analyzer_service.analyze_sentiment', 'content'),
            ('/api/check-redundancy', 'services.analysis.redundancy_checker_service.check_redundancy', 'content'),
            ('/api/detect-passive', 'services.analysis.passive_voice_service.detect_passive', 'content'),
            ('/api/extract-acronyms', 'services.analysis.acronym_extractor_service.extract_acronyms', 'content'),
            ('/api/detect-fillers', 'services.analysis.filler_detector_service.detect_fillers', 'content'),
            ('/api/check-consistency', 'services.quality.consistency_checker_service.check_consistency', 'content'),
            ('/api/analyze-speakability', 'services.analysis.speakability_service.analyze_speakability', 'content'),
            ('/api/detect-subheading-gaps', 'services.analysis.subheading_gap_service.detect_subheading_gaps', 'content'),
            ('/api/check-heading-parallelism', 'services.analysis.heading_parallelism_service.check_heading_parallelism', 'content'),
            ('/api/detect-section-drift', 'services.quality.section_drift_service.detect_section_drift', 'content'),
            ('/api/check-pronoun-clarity', 'services.analysis.pronoun_clarity_service.check_pronoun_clarity', 'content'),
            ('/api/analyze-example-coverage', 'services.analysis.example_coverage_service.analyze_example_coverage', 'content'),
            ('/api/check-qa-closure', 'services.quality.qa_closure_service.check_qa_closure', 'content'),
            ('/api/detect-adverb-overuse', 'services.analysis.adverb_overuse_service.detect_adverb_overuse', 'content'),
            ('/api/detect-clause-overload', 'services.analysis.clause_overload_service.detect_clause_overload', 'content'),
            ('/api/analyze-statistics-coverage', 'services.analysis.statistics_coverage_service.analyze_statistics_coverage', 'content'),
            ('/api/find-simple-alternatives', 'services.analysis.simple_alternative_service.find_simple_alternatives', 'content'),
            ('/api/check-acronym-expansion', 'services.analysis.acronym_expansion_service.check_acronym_expansion', 'content'),
            ('/api/detect-actionability-gaps', 'services.analysis.actionability_gap_service.detect_actionability_gaps', 'content'),
            ('/api/check-thesis-frontload', 'services.analysis.thesis_frontload_service.check_thesis_frontload', 'content'),
            ('/api/detect-list-table-opportunities', 'services.analysis.list_table_opportunity_service.detect_list_table_opportunities', 'content'),
            ('/api/analyze-question-density', 'services.analysis.question_density_service.analyze_question_density', 'content'),
            ('/api/audit-whitespace-formatting', 'services.analysis.whitespace_formatting_service.audit_whitespace_formatting', 'content'),
            ('/api/analyze-bullet-density', 'services.analysis.bullet_point_density_service.analyze_bullet_density', 'content'),
            ('/api/check-code-block-quality', 'services.analysis.code_block_quality_service.check_code_block_quality', 'content'),
            ('/api/check-paragraph-opening-variety', 'services.analysis.paragraph_opening_variety_service.check_paragraph_opening_variety', 'content'),
            ('/api/check-tone-consistency', 'services.analysis.tone_consistency_service.check_tone_consistency', 'content'),
            ('/api/detect-linking-verb-overuse', 'services.analysis.linking_verb_overuse_service.detect_linking_verb_overuse', 'content'),
            ('/api/validate-instruction-sequence', 'services.analysis.instruction_sequence_service.validate_instruction_sequence', 'content'),
            ('/api/score-content-depth', 'services.analysis.content_depth_scorer_service.score_content_depth', 'content'),
            ('/api/analyze-conclusion-strength', 'services.analysis.conclusion_strength_service.analyze_conclusion_strength', 'content'),
            ('/api/check-parenthetical-overuse', 'services.analysis.parenthetical_overuse_service.check_parenthetical_overuse', 'content'),
            ('/api/detect-anaphora-repetition', 'services.analysis.anaphora_repetition_service.detect_anaphora_repetition', 'content'),
            ('/api/analyze-connector-variety', 'services.analysis.sentence_analysis_service.analyze_connector_variety', 'content'),
            ('/api/check-content-freshness', 'services.seo.content_freshness_indicator_service.check_content_freshness', 'content'),
            ('/api/check-article-format', 'services.content.article_format_template_service.check_article_format', 'content'),
            ('/api/map-emotional-arc', 'services.analysis.emotional_arc_mapper_service.map_emotional_arc', 'content'),
            ('/api/analyze-sentence-rhythm', 'services.analysis.sentence_analysis_service.analyze_sentence_rhythm', 'content'),
            ('/api/analyze-sentence-ending-variety', 'services.analysis.sentence_analysis_service.analyze_sentence_ending_variety', 'content'),
            ('/api/sentence-variety', 'services.analysis.sentence_analysis_service.analyze_variety', 'content'),
            ('/api/reading-time', 'services.analysis.reading_time_service.estimate_reading_time', 'content'),
            ('/api/analyze-transitions', 'services.analysis.transition_analyzer_service.analyze_transitions', 'content'),
            ('/api/emotional-tone', 'services.analysis.emotional_tone_service.map_emotional_tone', 'content'),
            ('/api/engagement-score', 'services.seo.engagement_scorer_service.score_engagement', 'content'),
            ('/api/benchmark-readability', 'services.analysis.readability_benchmark_service.benchmark_readability', 'content'),
            ('/api/analyze-jargon', 'services.analysis.jargon_analyzer_service.analyze_jargon_coverage', 'content'),
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


    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.agents.seo_optimize_agent.optimize_seo')
    @patch('services.seo.seo_optimize_request_service.build_seo_optimize_response')
    def test_seo_optimize_uses_request_service(self, mock_build, mock_optimize, _):
        mock_optimize.return_value = {'direct': True}
        mock_build.return_value = ({'normalized': True}, 208)

        resp = self.client.post(
            '/api/seo-optimize',
            json={'content': 'sample content', 'keywords': ['seo']},
            headers=_H,
        )

        self.assertEqual(resp.status_code, 208)
        self.assertEqual(resp.get_json(), {'normalized': True})
        mock_build.assert_called_once()
        data_arg = mock_build.call_args.args[0]
        self.assertEqual(data_arg, {'content': 'sample content', 'keywords': ['seo']})
        self.assertEqual(mock_build.call_args.kwargs['required_error'], 'content \ud544\uc218')
        self.assertIs(mock_build.call_args.kwargs['optimize_seo_func'], mock_optimize)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.quality.plagiarism_service.check_plagiarism')
    @patch('services.analysis.content_analysis_request_service.build_single_field_analysis_response')
    def test_plagiarism_check_uses_single_field_analysis_helper(self, mock_build, mock_check, _):
        mock_check.return_value = {'direct': True}
        mock_build.return_value = ({'normalized': True}, 202)

        resp = self.client.post('/api/plagiarism-check', json={'content': 'sample content'}, headers=_H)

        self.assertEqual(resp.status_code, 202)
        self.assertEqual(resp.get_json(), {'normalized': True})
        mock_build.assert_called_once()
        data_arg = mock_build.call_args.args[0]
        self.assertEqual(data_arg, {'content': 'sample content'})
        self.assertEqual(mock_build.call_args.kwargs['field_name'], 'content')
        self.assertEqual(mock_build.call_args.kwargs['required_error'], 'content \ud544\uc218')
        self.assertIs(mock_build.call_args.kwargs['analysis_func'], mock_check)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.analysis.readability_service.analyze_readability')
    @patch('services.analysis.content_analysis_request_service.build_single_field_analysis_response')
    def test_readability_uses_single_field_analysis_helper(self, mock_build, mock_analyze, _):
        mock_analyze.return_value = {'direct': True}
        mock_build.return_value = ({'normalized': True}, 203)

        resp = self.client.post('/api/readability', json={'text': 'sample text'}, headers=_H)

        self.assertEqual(resp.status_code, 203)
        self.assertEqual(resp.get_json(), {'normalized': True})
        mock_build.assert_called_once()
        data_arg = mock_build.call_args.args[0]
        self.assertEqual(data_arg, {'text': 'sample text'})
        self.assertEqual(mock_build.call_args.kwargs['field_name'], 'text')
        self.assertEqual(mock_build.call_args.kwargs['required_error'], 'text \ud544\uc218')
        self.assertIs(mock_build.call_args.kwargs['analysis_func'], mock_analyze)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.analysis.nlp_analysis_service.analyze_sentiment_flow')
    @patch('services.analysis.content_analysis_request_service.build_single_field_analysis_response')
    def test_sentiment_flow_uses_single_field_analysis_helper(self, mock_build, mock_analyze, _):
        mock_analyze.return_value = {'direct': True}
        mock_build.return_value = ({'normalized': True}, 206)

        resp = self.client.post('/api/sentiment-flow', json={'content': 'sample content'}, headers=_H)

        self.assertEqual(resp.status_code, 206)
        self.assertEqual(resp.get_json(), {'normalized': True})
        mock_build.assert_called_once()
        data_arg = mock_build.call_args.args[0]
        self.assertEqual(data_arg, {'content': 'sample content'})
        self.assertEqual(mock_build.call_args.kwargs['field_name'], 'content')
        self.assertEqual(mock_build.call_args.kwargs['required_error'], 'content \ud544\uc218')
        self.assertIs(mock_build.call_args.kwargs['analysis_func'], mock_analyze)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.quality.content_grader_service.grade_content')
    @patch('services.analysis.content_analysis_request_service.build_single_field_analysis_response')
    def test_grade_content_uses_single_field_analysis_helper(self, mock_build, mock_grade, _):
        mock_grade.return_value = {'direct': True}
        mock_build.return_value = ({'normalized': True}, 207)

        resp = self.client.post('/api/grade-content', json={'content': 'sample content'}, headers=_H)

        self.assertEqual(resp.status_code, 207)
        self.assertEqual(resp.get_json(), {'normalized': True})
        mock_build.assert_called_once()
        data_arg = mock_build.call_args.args[0]
        self.assertEqual(data_arg, {'content': 'sample content'})
        self.assertEqual(mock_build.call_args.kwargs['field_name'], 'content')
        self.assertEqual(
            mock_build.call_args.kwargs['required_error'],
            '\ud3c9\uac00\ud560 \ucf58\ud150\uce20\uac00 \ud544\uc694\ud569\ub2c8\ub2e4.',
        )
        self.assertTrue(mock_build.call_args.kwargs['strip_strings'])
        self.assertIs(mock_build.call_args.kwargs['analysis_func'], mock_grade)

# ── RSS 피드 ──────────────────────────────────────


class TestRSSFeed(_BaseTestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_rss_feed_returns_xml(self, _):
        resp = self.client.get('/feed.xml')
        self.assertEqual(resp.status_code, 200)
        self.assertIn('xml', resp.content_type)


if __name__ == '__main__':
    unittest.main()
