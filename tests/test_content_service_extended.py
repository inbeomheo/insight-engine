"""content_service 확장 테스트 — 캐시, HTTP, 폴백, get_transcript 등 미커버 함수"""
import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock, PropertyMock

import requests


class TestCacheDirectoryResolution(unittest.TestCase):
    """CONTENT_CACHE_DIR 설정과 로컬 호환 기본값을 검증한다."""

    def test_explicit_cache_directory_is_normalized(self):
        from services.core.content_service import _resolve_cache_dir

        with tempfile.TemporaryDirectory() as cache_dir, patch.dict(
            os.environ,
            {'CONTENT_CACHE_DIR': cache_dir},
        ):
            self.assertEqual(_resolve_cache_dir(), os.path.abspath(cache_dir))

    def test_empty_setting_preserves_legacy_services_cache(self):
        from services.core.content_service import _resolve_cache_dir

        with patch.dict(os.environ, {'CONTENT_CACHE_DIR': ''}):
            self.assertTrue(
                _resolve_cache_dir().endswith(os.path.join('services', 'cache'))
            )


class TestEnsureCacheDir(unittest.TestCase):
    """_ensure_cache_dir 테스트"""

    def test_creates_dir_if_missing(self):
        from services.core.content_service import _ensure_cache_dir, CACHE_DIR
        with patch('services.core.content_service.os.path.exists', return_value=False) as mock_exists, \
             patch('services.core.content_service.os.makedirs') as mock_makedirs:
            _ensure_cache_dir()
            mock_makedirs.assert_called_once_with(CACHE_DIR)

    def test_skips_if_exists(self):
        from services.core.content_service import _ensure_cache_dir
        with patch('services.core.content_service.os.path.exists', return_value=True), \
             patch('services.core.content_service.os.makedirs') as mock_makedirs:
            _ensure_cache_dir()
            mock_makedirs.assert_not_called()


class TestLoadSaveCache(unittest.TestCase):
    """_load_cache, _save_cache 테스트"""

    def test_load_cache_hit(self):
        from services.core.content_service import _load_cache
        fake_data = {'text': '자막', 'source': 'api'}
        with patch('services.core.content_service._get_cache_path', return_value='/tmp/fake.json'), \
             patch('services.core.content_service.os.path.exists', return_value=True), \
             patch('builtins.open', unittest.mock.mock_open(read_data=json.dumps(fake_data))):
            result = _load_cache('dQw4w9WgXcQ', 'transcript')
            self.assertEqual(result['text'], '자막')

    def test_load_cache_miss(self):
        from services.core.content_service import _load_cache
        with patch('services.core.content_service._get_cache_path', return_value='/tmp/fake.json'), \
             patch('services.core.content_service.os.path.exists', return_value=False):
            result = _load_cache('dQw4w9WgXcQ', 'transcript')
            self.assertIsNone(result)

    def test_load_cache_corrupted_json(self):
        from services.core.content_service import _load_cache
        with patch('services.core.content_service._get_cache_path', return_value='/tmp/fake.json'), \
             patch('services.core.content_service.os.path.exists', return_value=True), \
             patch('builtins.open', unittest.mock.mock_open(read_data='not json')):
            result = _load_cache('dQw4w9WgXcQ', 'transcript')
            self.assertIsNone(result)

    def test_save_cache_writes(self):
        from services.core.content_service import _save_cache
        m = unittest.mock.mock_open()
        with patch('services.core.content_service._ensure_cache_dir'), \
             patch('services.core.content_service._get_cache_path', return_value='/tmp/fake.json'), \
             patch('builtins.open', m):
            _save_cache('dQw4w9WgXcQ', 'transcript', {'text': 'test'})
            m.assert_called_once()

    def test_save_cache_io_error_ignored(self):
        from services.core.content_service import _save_cache
        with patch('services.core.content_service._ensure_cache_dir'), \
             patch('services.core.content_service._get_cache_path', return_value='/tmp/fake.json'), \
             patch('builtins.open', side_effect=IOError('disk full')):
            # IOError가 무시되어야 함
            _save_cache('dQw4w9WgXcQ', 'transcript', {'text': 'test'})


class TestClearCache(unittest.TestCase):
    """clear_cache 테스트"""

    def test_no_cache_dir(self):
        from services.core.content_service import clear_cache
        with patch('services.core.content_service.os.path.exists', return_value=False):
            self.assertEqual(clear_cache(), 0)

    def test_clear_specific_video(self):
        from services.core.content_service import clear_cache
        with patch('services.core.content_service.os.path.exists', return_value=True), \
             patch('services.core.content_service.os.listdir', return_value=['dQw4w9WgXcQ_transcript.json', 'other_transcript.json']), \
             patch('services.core.content_service.os.remove') as mock_rm:
            result = clear_cache('dQw4w9WgXcQ')
            self.assertEqual(result, 1)
            self.assertEqual(mock_rm.call_count, 1)

    def test_clear_all(self):
        from services.core.content_service import clear_cache
        with patch('services.core.content_service.os.path.exists', return_value=True), \
             patch('services.core.content_service.os.listdir', return_value=['a_transcript.json', 'b_comments.json']), \
             patch('services.core.content_service.os.remove') as mock_rm:
            result = clear_cache(None)
            self.assertEqual(result, 2)


class TestPurgeExpiredCache(unittest.TestCase):
    """purge_expired_cache 테스트"""

    def test_no_cache_dir(self):
        from services.core.content_service import purge_expired_cache
        with patch('services.core.content_service.os.path.exists', return_value=False):
            result = purge_expired_cache()
            self.assertEqual(result['purged'], 0)

    def test_purges_old_files(self):
        from services.core.content_service import purge_expired_cache
        old_time = time.time() - 100000  # 오래된 파일
        with patch('services.core.content_service.os.path.exists', return_value=True), \
             patch('services.core.content_service.os.listdir', return_value=['old.json']), \
             patch('services.core.content_service.os.path.isfile', return_value=True), \
             patch('services.core.content_service.os.path.getmtime', return_value=old_time), \
             patch('services.core.content_service.os.path.getsize', return_value=1024), \
             patch('services.core.content_service.os.remove') as mock_rm:
            result = purge_expired_cache(max_age_hours=1)
            self.assertEqual(result['purged'], 1)
            self.assertEqual(result['freed_bytes'], 1024)

    def test_keeps_recent_files(self):
        from services.core.content_service import purge_expired_cache
        recent_time = time.time() - 10  # 매우 최근 파일
        with patch('services.core.content_service.os.path.exists', return_value=True), \
             patch('services.core.content_service.os.listdir', return_value=['recent.json']), \
             patch('services.core.content_service.os.path.isfile', return_value=True), \
             patch('services.core.content_service.os.path.getmtime', return_value=recent_time):
            result = purge_expired_cache(max_age_hours=1)
            self.assertEqual(result['purged'], 0)
            self.assertEqual(result['remaining'], 1)


class TestIsSafeCaptionUrl(unittest.TestCase):
    """_is_safe_caption_url 테스트"""

    def test_youtube_domain(self):
        from services.core.content_service import _is_safe_caption_url
        self.assertTrue(_is_safe_caption_url('https://www.youtube.com/api/timedtext?v=abc'))

    def test_google_domain(self):
        from services.core.content_service import _is_safe_caption_url
        self.assertTrue(_is_safe_caption_url('https://video.google.com/timedtext'))

    def test_googlevideo_domain(self):
        from services.core.content_service import _is_safe_caption_url
        self.assertTrue(_is_safe_caption_url('https://r1---sn-abc.googlevideo.com/timedtext'))

    def test_external_domain_blocked(self):
        from services.core.content_service import _is_safe_caption_url
        self.assertFalse(_is_safe_caption_url('https://evil.com/timedtext'))

    def test_empty_url(self):
        from services.core.content_service import _is_safe_caption_url
        self.assertFalse(_is_safe_caption_url(''))

    def test_ftp_scheme_blocked(self):
        from services.core.content_service import _is_safe_caption_url
        self.assertFalse(_is_safe_caption_url('ftp://youtube.com/caption'))


class TestDownloadCaptionFromUrl(unittest.TestCase):
    """_download_caption_from_url 테스트"""

    def test_empty_url(self):
        from services.core.content_service import _download_caption_from_url
        self.assertEqual(_download_caption_from_url(''), '')

    def test_unsafe_url(self):
        from services.core.content_service import _download_caption_from_url
        with patch('services.core.content_service._is_safe_caption_url', return_value=False):
            self.assertEqual(_download_caption_from_url('https://evil.com/cap'), '')

    @patch('services.core.content_service.requests.get')
    def test_vtt_response(self, mock_get):
        from services.core.content_service import _download_caption_from_url
        mock_resp = MagicMock()
        mock_resp.text = "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n테스트 자막"
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        with patch('services.core.content_service._is_safe_caption_url', return_value=True):
            result = _download_caption_from_url('https://www.youtube.com/api/timedtext?v=x')
            self.assertIn('테스트 자막', result)

    @patch('services.core.content_service.requests.get')
    def test_xml_response(self, mock_get):
        from services.core.content_service import _download_caption_from_url
        mock_resp = MagicMock()
        mock_resp.text = '<transcript><text start="0" dur="3">XML 자막</text></transcript>'
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        with patch('services.core.content_service._is_safe_caption_url', return_value=True):
            result = _download_caption_from_url('https://www.youtube.com/api/timedtext?v=x')
            self.assertIn('XML 자막', result)

    @patch('services.core.content_service.requests.get')
    def test_timeout(self, mock_get):
        from services.core.content_service import _download_caption_from_url
        mock_get.side_effect = requests.exceptions.Timeout('timeout')
        with patch('services.core.content_service._is_safe_caption_url', return_value=True):
            self.assertEqual(_download_caption_from_url('https://www.youtube.com/api/timedtext'), '')


class TestCreateHttpSession(unittest.TestCase):
    """_create_http_session 테스트"""

    def test_creates_session_no_proxy(self):
        from services.core.content_service import _create_http_session
        # _create_http_session은 services.transcript._shared.create_http_session의 alias.
        # _shared 모듈의 get_proxy_config를 patch해야 효과가 있다.
        with patch('services.transcript._shared.get_proxy_config', return_value=None):
            session = _create_http_session()
            self.assertIsInstance(session, requests.Session)
            self.assertIn('User-Agent', session.headers)

    def test_creates_session_with_proxy(self):
        from services.core.content_service import _create_http_session
        def fake_proxy(proxy_type):
            return 'http://proxy:8080' if proxy_type == 'HTTP' else None
        with patch('services.transcript._shared.get_proxy_config', side_effect=fake_proxy):
            session = _create_http_session()
            self.assertIn('http', session.proxies)


class TestGetProxyConfig(unittest.TestCase):
    """_get_proxy_config 테스트"""

    def test_from_env(self):
        from services.core.content_service import _get_proxy_config
        # current_app는 LocalProxy이므로 직접 패치하지 않고 앱 컨텍스트 없이 실행
        with patch.dict(os.environ, {'YT_HTTP_PROXY': 'http://proxy:8080'}):
            result = _get_proxy_config('HTTP')
            self.assertEqual(result, 'http://proxy:8080')


class TestOrderTranscriptTracks(unittest.TestCase):
    """_order_transcript_tracks 테스트"""

    def test_preferred_order(self):
        from services.core.content_service import _order_transcript_tracks
        ko_manual = MagicMock(language_code='ko', is_generated=False)
        en_manual = MagicMock(language_code='en', is_generated=False)
        ko_auto = MagicMock(language_code='ko', is_generated=True)
        result = _order_transcript_tracks([en_manual, ko_auto, ko_manual])
        # ko manual이 먼저 나와야 함
        self.assertIs(result[0], ko_manual)

    def test_empty_list(self):
        from services.core.content_service import _order_transcript_tracks
        self.assertEqual(_order_transcript_tracks([]), [])


class TestBuildTranscriptResult(unittest.TestCase):
    """_build_transcript_result 테스트"""

    def test_builds_result(self):
        from services.core.content_service import _build_transcript_result
        with patch('services.core.content_service._save_cache'), \
             patch('services.core.content_service._detect_language_from_text', return_value='ko'):
            result = _build_transcript_result(
                '자막 내용', 'api', 0.95, False, time.time(), 'dQw4w9WgXcQ'
            )
            self.assertEqual(result['text'], '자막 내용')
            self.assertEqual(result['source'], 'api')
            self.assertEqual(result['source_meta']['quality_score'], 0.95)
            self.assertIn('extraction_time_ms', result)

    def test_includes_segments(self):
        from services.core.content_service import _build_transcript_result
        segments = [{'start': 0.0, 'text': '시작', 'duration': 3.0}]
        with patch('services.core.content_service._save_cache'), \
             patch('services.core.content_service._detect_language_from_text', return_value='ko'):
            result = _build_transcript_result(
                '자막', 'api', 0.9, False, time.time(), 'dQw4w9WgXcQ', segments=segments
            )
            self.assertEqual(len(result['segments']), 1)


class TestGetTranscriptFromWatchPage(unittest.TestCase):
    """_get_transcript_from_watch_page 테스트"""

    def test_empty_video_id(self):
        from services.core.content_service import _get_transcript_from_watch_page
        result = _get_transcript_from_watch_page('')
        self.assertIn('error', result)

    @patch('services.core.content_service.requests.get')
    def test_no_caption_tracks(self, mock_get):
        from services.core.content_service import _get_transcript_from_watch_page
        mock_resp = MagicMock()
        mock_resp.text = '<html>no player response</html>'
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp
        result = _get_transcript_from_watch_page('dQw4w9WgXcQ')
        self.assertIn('error', result)

    @patch('services.core.content_service.requests.get')
    def test_network_error(self, mock_get):
        from services.core.content_service import _get_transcript_from_watch_page
        mock_get.side_effect = requests.exceptions.ConnectionError('fail')
        result = _get_transcript_from_watch_page('dQw4w9WgXcQ')
        self.assertIn('error', result)


class TestExtractYtInitialPlayerResponse(unittest.TestCase):
    """_extract_yt_initial_player_response 테스트"""

    def test_valid_html(self):
        from services.core.content_service import _extract_yt_initial_player_response
        html = 'var ytInitialPlayerResponse = {"captions": {"test": true}};'
        result = _extract_yt_initial_player_response(html)
        self.assertIsNotNone(result)
        self.assertIn('captions', result)

    def test_no_match(self):
        from services.core.content_service import _extract_yt_initial_player_response
        result = _extract_yt_initial_player_response('<html>nothing here</html>')
        self.assertIsNone(result)

    def test_empty_input(self):
        from services.core.content_service import _extract_yt_initial_player_response
        self.assertIsNone(_extract_yt_initial_player_response(''))
        self.assertIsNone(_extract_yt_initial_player_response(None))


class TestDetectAutoCaption(unittest.TestCase):
    """_detect_auto_caption 테스트"""

    def test_auto_caption_detected(self):
        from services.core.content_service import _detect_auto_caption
        ytt_api = MagicMock()
        track = MagicMock(is_generated=True)
        ytt_api.list.return_value = [track]
        self.assertTrue(_detect_auto_caption(ytt_api, 'dQw4w9WgXcQ'))

    def test_manual_caption(self):
        from services.core.content_service import _detect_auto_caption
        ytt_api = MagicMock()
        track = MagicMock(is_generated=False)
        ytt_api.list.return_value = [track]
        self.assertFalse(_detect_auto_caption(ytt_api, 'dQw4w9WgXcQ'))

    def test_exception_returns_false(self):
        from services.core.content_service import _detect_auto_caption
        ytt_api = MagicMock()
        ytt_api.list.side_effect = Exception('fail')
        self.assertFalse(_detect_auto_caption(ytt_api, 'dQw4w9WgXcQ'))


class TestTryWatchPageFallback(unittest.TestCase):
    """_try_watch_page_fallback 테스트"""

    def test_success(self):
        from services.core.content_service import _try_watch_page_fallback
        with patch('services.core.content_service._get_transcript_from_watch_page', return_value='자막 텍스트'):
            result = _try_watch_page_fallback('dQw4w9WgXcQ')
            self.assertIsNotNone(result)
            self.assertEqual(result[0], 'watch')
            self.assertEqual(result[1], '자막 텍스트')

    def test_failure(self):
        from services.core.content_service import _try_watch_page_fallback
        with patch('services.core.content_service._get_transcript_from_watch_page', return_value={'error': 'fail'}):
            result = _try_watch_page_fallback('dQw4w9WgXcQ')
            self.assertIsNone(result)


class TestGetTranscript(unittest.TestCase):
    """get_transcript 통합 테스트"""

    def test_cache_hit(self):
        from services.core.content_service import get_transcript
        cached = {'text': '캐시된 자막', 'source': 'api'}
        with patch('services.core.content_service._load_cache', return_value=cached):
            result = get_transcript('dQw4w9WgXcQ')
            self.assertEqual(result['text'], '캐시된 자막')

    def test_cache_hit_old_format(self):
        from services.core.content_service import get_transcript
        with patch('services.core.content_service._load_cache', return_value='구버전 캐시 문자열'):
            result = get_transcript('dQw4w9WgXcQ')
            self.assertEqual(result['text'], '구버전 캐시 문자열')
            self.assertEqual(result['source'], 'cache')

    def test_all_methods_fail(self):
        from services.core.content_service import get_transcript
        with patch('services.core.content_service._load_cache', return_value=None), \
             patch('services.core.content_service._build_ytt_api'), \
             patch('services.core.content_service._fetch_transcript_with_api', return_value=None), \
             patch('services.core.content_service._run_parallel_fallbacks', return_value=None), \
             patch.dict(os.environ, {'WHISPER_ENABLED': 'false', 'SUPADATA_API_KEY': ''}):
            result = get_transcript('dQw4w9WgXcQ')
            self.assertIn('error', result)


class TestGetYoutubeTitle(unittest.TestCase):
    """get_youtube_title 테스트"""

    def test_no_api_key(self):
        from services.core.content_service import get_youtube_title
        from app import create_app
        app = create_app({'TESTING': True, 'YOUTUBE_API_KEY': None})
        with app.app_context():
            app.config['YOUTUBE_API_KEY'] = None
            result = get_youtube_title('dQw4w9WgXcQ')
            self.assertIsNone(result)


class TestGetContentTitle(unittest.TestCase):
    """get_content_title 테스트"""

    def test_non_youtube_url(self):
        from services.core.content_service import get_content_title
        result = get_content_title('https://example.com/page')
        self.assertIsNone(result)

    def test_youtube_url_with_title(self):
        from services.core.content_service import get_content_title
        with patch('services.core.content_service.get_youtube_title', return_value='영상 제목'):
            result = get_content_title('https://www.youtube.com/watch?v=dQw4w9WgXcQ')
            self.assertEqual(result, '영상 제목')


class TestGetTopComments(unittest.TestCase):
    """get_top_comments 테스트"""

    def test_cache_hit(self):
        from services.core.content_service import get_top_comments
        cached = ['댓글1', '댓글2']
        with patch('services.core.content_service._load_cache', return_value=cached):
            result = get_top_comments('dQw4w9WgXcQ')
            self.assertEqual(result, cached)

    def test_no_api_key(self):
        from services.core.content_service import get_top_comments
        from app import create_app
        app = create_app({'TESTING': True, 'YOUTUBE_API_KEY': None})
        with app.app_context():
            app.config['YOUTUBE_API_KEY'] = None
            with patch('services.core.content_service._load_cache', return_value=None):
                result = get_top_comments('dQw4w9WgXcQ')
                self.assertEqual(result, [])


class TestLogFunctions(unittest.TestCase):
    """_log_info, _log_warning 테스트"""

    def test_log_info_outside_context(self):
        from services.core.content_service import _log_info
        # RuntimeError 무시되어야 함
        _log_info('test message')

    def test_log_warning_outside_context(self):
        from services.core.content_service import _log_warning
        _log_warning('test warning')


if __name__ == '__main__':
    unittest.main()
