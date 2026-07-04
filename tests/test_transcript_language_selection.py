"""P7b: transcript_language 선택 기능 테스트.

- youtube-transcript-api 폴백 언어 우선순위 전달
- Supadata 폴백 lang 파라미터 전달
- get_transcript()의 transcript_language 파라미터 → source_meta 기록
- 언어 미존재 시 폴백(생성 실패로 이어지지 않음)
- /generate 요청 파라미터 검증 (허용값/기본값/오류)
- 회귀: transcript_language 생략 시 기존 동작과 동일
"""
import time
import unittest
from unittest.mock import patch, MagicMock

from app import create_app


# ==================== fallbacks/youtube_api.py ====================

class TestOrderTranscriptTracksPreferredLanguage(unittest.TestCase):
    """order_transcript_tracks의 preferred_language 파라미터 테스트."""

    def test_preferred_language_overrides_default_order(self):
        from services.transcript.fallbacks.youtube_api import order_transcript_tracks
        ko_manual = MagicMock(language_code='ko', is_generated=False)
        en_manual = MagicMock(language_code='en', is_generated=False)
        ja_manual = MagicMock(language_code='ja', is_generated=False)
        result = order_transcript_tracks([ko_manual, en_manual, ja_manual], preferred_language='ja')
        self.assertIs(result[0], ja_manual)

    def test_no_preferred_language_keeps_default_order(self):
        from services.transcript.fallbacks.youtube_api import order_transcript_tracks
        ko_manual = MagicMock(language_code='ko', is_generated=False)
        en_manual = MagicMock(language_code='en', is_generated=False)
        result = order_transcript_tracks([en_manual, ko_manual])
        # 기존 PREFERRED_LANGUAGES = ('ko', 'en') 순서 유지
        self.assertIs(result[0], ko_manual)

    def test_preferred_language_missing_falls_back_to_default_order(self):
        """요청 언어 트랙이 없으면 기존 우선순위로 정상 폴백 (실패하지 않음)."""
        from services.transcript.fallbacks.youtube_api import order_transcript_tracks
        ko_manual = MagicMock(language_code='ko', is_generated=False)
        en_manual = MagicMock(language_code='en', is_generated=False)
        result = order_transcript_tracks([en_manual, ko_manual], preferred_language='ja')
        # ja 트랙이 없으므로 기존 순서(ko 우선)로 폴백
        self.assertIs(result[0], ko_manual)


class TestFetchTranscriptWithApiLanguage(unittest.TestCase):
    """fetch_transcript_with_api의 preferred_language 전달 테스트."""

    def test_passes_preferred_language_first_in_languages_list(self):
        from services.transcript.fallbacks.youtube_api import fetch_transcript_with_api
        ytt_api = MagicMock()
        ytt_api.fetch.return_value = ['snippet']
        fetch_transcript_with_api(ytt_api, 'dQw4w9WgXcQ', preferred_language='ja')
        called_languages = ytt_api.fetch.call_args.kwargs['languages']
        self.assertEqual(called_languages[0], 'ja')

    def test_no_preferred_language_uses_default_languages(self):
        from services.transcript.fallbacks.youtube_api import fetch_transcript_with_api
        from services.transcript._shared import PREFERRED_LANGUAGES
        ytt_api = MagicMock()
        ytt_api.fetch.return_value = ['snippet']
        fetch_transcript_with_api(ytt_api, 'dQw4w9WgXcQ')
        called_languages = ytt_api.fetch.call_args.kwargs['languages']
        self.assertEqual(called_languages, PREFERRED_LANGUAGES)

    def test_list_fallback_uses_preferred_language_order(self):
        """fetch()가 NoTranscriptFound 등으로 실패하면 list() 폴백에서도 언어 우선순위가 반영된다."""
        from services.transcript.fallbacks.youtube_api import fetch_transcript_with_api
        from youtube_transcript_api import NoTranscriptFound

        ja_track = MagicMock(language_code='ja', is_generated=False)
        ja_track.fetch.return_value = ['ja segment']
        ko_track = MagicMock(language_code='ko', is_generated=False)
        ko_track.fetch.return_value = ['ko segment']

        ytt_api = MagicMock()
        ytt_api.fetch.side_effect = NoTranscriptFound('dQw4w9WgXcQ', ['ko', 'en'], {})
        ytt_api.list.return_value = [ko_track, ja_track]

        result = fetch_transcript_with_api(ytt_api, 'dQw4w9WgXcQ', preferred_language='ja')
        self.assertEqual(result, ['ja segment'])


# ==================== fallbacks/supadata.py ====================

class TestSupadataLanguageParam(unittest.TestCase):
    """get_transcript_via_supadata의 lang 파라미터 전달 테스트."""

    @patch('services.transcript.fallbacks.supadata.requests.get')
    def test_passes_lang_param_when_specified(self, mock_get):
        from services.transcript.fallbacks.supadata import get_transcript_via_supadata
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {'content': '자막'})
        get_transcript_via_supadata('dQw4w9WgXcQ', 'test-key', preferred_language='en')
        params = mock_get.call_args.kwargs['params']
        self.assertEqual(params.get('lang'), 'en')

    @patch('services.transcript.fallbacks.supadata.requests.get')
    def test_omits_lang_param_when_not_specified(self, mock_get):
        from services.transcript.fallbacks.supadata import get_transcript_via_supadata
        mock_get.return_value = MagicMock(status_code=200, json=lambda: {'content': '자막'})
        get_transcript_via_supadata('dQw4w9WgXcQ', 'test-key')
        params = mock_get.call_args.kwargs['params']
        self.assertNotIn('lang', params)


# ==================== content_service.get_transcript ====================

class TestGetTranscriptLanguageParam(unittest.TestCase):
    """get_transcript()의 transcript_language 파라미터 통합 테스트."""

    def test_language_threaded_to_api_fetch(self):
        from services.core.content_service import get_transcript
        with patch('services.core.content_service._load_cache', return_value=None), \
             patch('services.core.content_service._build_ytt_api'), \
             patch('services.core.content_service._fetch_transcript_with_api') as mock_fetch, \
             patch('services.core.content_service._extract_text_from_transcript', return_value='자막 텍스트'), \
             patch('services.core.content_service._extract_segments_from_transcript', return_value=[]), \
             patch('services.core.content_service._save_cache'):
            mock_fetch.return_value = MagicMock(is_generated=False)
            result = get_transcript('dQw4w9WgXcQ', transcript_language='en')
            self.assertEqual(mock_fetch.call_args.kwargs['preferred_language'], 'en')
            self.assertEqual(result['source_meta']['requested_language'], 'en')

    def test_language_recorded_in_source_meta_with_match_flag(self):
        from services.core.content_service import get_transcript
        with patch('services.core.content_service._load_cache', return_value=None), \
             patch('services.core.content_service._build_ytt_api'), \
             patch('services.core.content_service._fetch_transcript_with_api') as mock_fetch, \
             patch('services.core.content_service._extract_text_from_transcript', return_value='Hello world English text'), \
             patch('services.core.content_service._extract_segments_from_transcript', return_value=[]), \
             patch('services.core.content_service._save_cache'):
            mock_fetch.return_value = MagicMock(is_generated=False)
            result = get_transcript('dQw4w9WgXcQ', transcript_language='en')
            self.assertTrue(result['source_meta']['language_matched'])
            self.assertEqual(result['source_meta']['language'], 'en')

    def test_language_unavailable_falls_back_without_failure(self):
        """1순위(youtube-transcript-api)가 실패해도 병렬 폴백으로 자막을 가져오면 생성이 실패하지 않는다."""
        from services.core.content_service import get_transcript
        with patch('services.core.content_service._load_cache', return_value=None), \
             patch('services.core.content_service._build_ytt_api'), \
             patch('services.core.content_service._fetch_transcript_with_api', return_value=None), \
             patch('services.core.content_service._run_parallel_fallbacks') as mock_parallel:
            mock_parallel.return_value = {
                'text': 'watch 폴백 자막', 'source': 'watch',
                'source_meta': {'source_type': 'watch', 'quality_score': 0.85, 'is_auto': False, 'language': 'ko'},
                'extraction_time_ms': 1.0,
            }
            result = get_transcript('dQw4w9WgXcQ', transcript_language='ja')
            self.assertNotIn('error', result)
            self.assertEqual(result['text'], 'watch 폴백 자막')
            # 병렬 폴백 호출에도 requested_language가 전달됨 (source_meta 기록용)
            self.assertEqual(mock_parallel.call_args.kwargs.get('requested_language'), 'ja')

    def test_no_language_param_skips_cache_language_check(self):
        """transcript_language 미지정 시 캐시를 그대로 사용 (기존 동작)."""
        from services.core.content_service import get_transcript
        cached = {'text': '캐시된 자막', 'source': 'api'}
        with patch('services.core.content_service._load_cache', return_value=cached):
            result = get_transcript('dQw4w9WgXcQ')
            self.assertEqual(result['text'], '캐시된 자막')

    def test_language_param_bypasses_cache(self):
        """transcript_language 지정 시 기존 캐시(언어 무관)를 재사용하지 않고 재추출한다."""
        from services.core.content_service import get_transcript
        cached = {'text': '캐시된 자막', 'source': 'api'}
        with patch('services.core.content_service._load_cache', return_value=cached) as mock_load, \
             patch('services.core.content_service._build_ytt_api'), \
             patch('services.core.content_service._fetch_transcript_with_api', return_value=None), \
             patch('services.core.content_service._run_parallel_fallbacks', return_value=None), \
             patch.dict('os.environ', {'WHISPER_ENABLED': 'false', 'SUPADATA_API_KEY': ''}):
            result = get_transcript('dQw4w9WgXcQ', transcript_language='en')
            # 캐시를 사용하지 않고 재추출을 시도했으므로 캐시된 텍스트가 반환되지 않음
            self.assertNotEqual(result.get('text'), '캐시된 자막')


class TestGetTranscriptRegressionOmittedParam(unittest.TestCase):
    """transcript_language 생략 시 기존 동작과 동일한지 회귀 테스트."""

    def test_omitted_param_identical_to_explicit_none(self):
        from services.core.content_service import get_transcript
        with patch('services.core.content_service._load_cache', return_value=None), \
             patch('services.core.content_service._build_ytt_api'), \
             patch('services.core.content_service._fetch_transcript_with_api') as mock_fetch, \
             patch('services.core.content_service._extract_text_from_transcript', return_value='자막 텍스트'), \
             patch('services.core.content_service._extract_segments_from_transcript', return_value=[]), \
             patch('services.core.content_service._save_cache'):
            mock_fetch.return_value = MagicMock(is_generated=False)

            result_omitted = get_transcript('dQw4w9WgXcQ')
            result_explicit_none = get_transcript('dQw4w9WgXcQ', transcript_language=None)

            # source_meta에 requested_language/language_matched 키가 추가되지 않아야 함 (기존 스키마 유지)
            self.assertNotIn('requested_language', result_omitted['source_meta'])
            self.assertNotIn('requested_language', result_explicit_none['source_meta'])
            self.assertEqual(result_omitted['source_meta'].keys(), result_explicit_none['source_meta'].keys())

            # fetch_transcript_with_api에도 preferred_language=None으로 동일하게 전달됨
            self.assertIsNone(mock_fetch.call_args_list[0].kwargs['preferred_language'])
            self.assertIsNone(mock_fetch.call_args_list[1].kwargs['preferred_language'])


# ==================== 라우트 요청 검증 ====================

class TestValidateTranscriptLanguage(unittest.TestCase):

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_none_is_valid(self, _):
        from routes.blog_routes import _validate_transcript_language
        result, err = _validate_transcript_language(None)
        self.assertIsNone(result)
        self.assertIsNone(err)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_empty_string_is_valid(self, _):
        from routes.blog_routes import _validate_transcript_language
        result, err = _validate_transcript_language('')
        self.assertIsNone(result)
        self.assertIsNone(err)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_allowed_values(self, _):
        from routes.blog_routes import _validate_transcript_language
        for lang in ('ko', 'en', 'ja'):
            result, err = _validate_transcript_language(lang)
            self.assertEqual(result, lang)
            self.assertIsNone(err)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_invalid_value_returns_korean_error(self, _):
        from routes.blog_routes import _validate_transcript_language
        result, err = _validate_transcript_language('fr')
        self.assertIsNone(result)
        self.assertIsNotNone(err)
        # 앱 UI 노출 에러 메시지는 한국어여야 함
        self.assertIn('언어', err)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_invalid_type_returns_error(self, _):
        from routes.blog_routes import _validate_transcript_language
        result, err = _validate_transcript_language(123)
        self.assertIsNone(result)
        self.assertIsNotNone(err)


class TestGetRequestDataTranscriptLanguage(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_valid_language_included_in_params(self, _):
        from routes.blog_routes import _get_request_data
        with self.app.test_request_context(
            json={'url': 'https://youtube.com/watch?v=abc', 'transcript_language': 'ja'},
            content_type='application/json',
        ):
            from flask import request as flask_req
            params = _get_request_data(flask_req)
            self.assertEqual(params['transcript_language'], 'ja')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_omitted_defaults_to_none(self, _):
        from routes.blog_routes import _get_request_data
        with self.app.test_request_context(
            json={'url': 'https://youtube.com/watch?v=abc'},
            content_type='application/json',
        ):
            from flask import request as flask_req
            params = _get_request_data(flask_req)
            self.assertIsNone(params['transcript_language'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_invalid_language_normalized_to_none_in_params(self, _):
        """_get_request_data 자체는 무효값을 None으로 정규화(관용); 400 응답은 라우트에서 별도 처리."""
        from routes.blog_routes import _get_request_data
        with self.app.test_request_context(
            json={'url': 'https://youtube.com/watch?v=abc', 'transcript_language': 'fr'},
            content_type='application/json',
        ):
            from flask import request as flask_req
            params = _get_request_data(flask_req)
            self.assertIsNone(params['transcript_language'])


_H = {'Origin': 'http://localhost:3000'}


class TestGenerateRouteTranscriptLanguageValidation(unittest.TestCase):
    """POST /generate 요청의 transcript_language 검증 (400 응답)."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_invalid_transcript_language_returns_400_korean_error(self, _):
        resp = self.client.post(
            '/generate',
            json={'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'transcript_language': 'fr'},
            headers=_H,
        )
        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertIn('error', body)
        self.assertIn('언어', body['error'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_missing_transcript_language_does_not_400(self, _):
        """transcript_language 없이 URL만 없는 경우엔 '유효한 언어' 오류가 아니라 URL 관련 오류(또는 통과)여야 함."""
        resp = self.client.post('/generate', json={}, headers=_H)
        self.assertEqual(resp.status_code, 400)
        body = resp.get_json()
        self.assertNotIn('언어', body.get('error', ''))


# ==================== _fetch_youtube_content 통합 ====================

class TestFetchYoutubeContentLanguage(unittest.TestCase):

    def test_threads_transcript_language_to_get_transcript(self):
        from routes.generation_helpers import _fetch_youtube_content
        with patch('services.core.content_service.get_transcript') as mock_get, \
             patch('services.core.content_service.get_top_comments', return_value=[]):
            mock_get.return_value = {'text': '자막', 'source': 'api', 'segments': []}
            _fetch_youtube_content('dQw4w9WgXcQ', transcript_language='ko')
            mock_get.assert_called_once_with('dQw4w9WgXcQ', transcript_language='ko')

    def test_omitted_language_defaults_to_none(self):
        from routes.generation_helpers import _fetch_youtube_content
        with patch('services.core.content_service.get_transcript') as mock_get, \
             patch('services.core.content_service.get_top_comments', return_value=[]):
            mock_get.return_value = {'text': '자막', 'source': 'api', 'segments': []}
            _fetch_youtube_content('dQw4w9WgXcQ')
            mock_get.assert_called_once_with('dQw4w9WgXcQ', transcript_language=None)


if __name__ == '__main__':
    unittest.main()
