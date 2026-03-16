"""R17: get_transcript() 반환값에 extraction_time_ms 포함 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from flask import Flask


class TestTranscriptTiming(unittest.TestCase):
    """get_transcript 반환값의 extraction_time_ms 필드 검증"""

    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['YOUTUBE_API_KEY'] = ''

    @patch('services.core.content_service._load_cache')
    def test_cached_result_has_extraction_time_ms(self, mock_cache):
        """캐시 히트 시 extraction_time_ms 포함"""
        mock_cache.return_value = {'text': '캐시된 자막', 'source': 'cache'}

        with self.app.app_context():
            from services.core.content_service import get_transcript
            result = get_transcript('test12345ab')

        self.assertIn('extraction_time_ms', result)
        self.assertIsInstance(result['extraction_time_ms'], float)
        # 캐시 조회이므로 매우 빠르게 완료되어야 함
        self.assertLess(result['extraction_time_ms'], 1000)

    @patch('services.core.content_service._save_cache')
    @patch('services.core.content_service._load_cache', return_value=None)
    @patch('services.core.content_service._detect_auto_caption', return_value=False)
    @patch('services.core.content_service._extract_segments_from_transcript', return_value=[])
    @patch('services.core.content_service._extract_text_from_transcript', return_value='자막 텍스트')
    @patch('services.core.content_service._fetch_transcript_with_api')
    @patch('services.core.content_service._build_ytt_api')
    def test_api_result_has_extraction_time_ms(self, mock_build, mock_fetch,
                                                mock_extract, mock_segments,
                                                mock_auto, mock_no_cache, mock_save):
        """youtube-transcript-api 경로 성공 시 extraction_time_ms 포함"""
        mock_build.return_value = MagicMock()
        mock_fetch.return_value = [{'text': '자막', 'start': 0, 'duration': 5}]

        with self.app.app_context():
            from services.core.content_service import get_transcript
            result = get_transcript('apiTest1234a')

        self.assertIn('extraction_time_ms', result)
        self.assertIsInstance(result['extraction_time_ms'], float)
        self.assertGreaterEqual(result['extraction_time_ms'], 0)

    @patch('services.core.content_service._save_cache')
    @patch('services.core.content_service._load_cache', return_value=None)
    @patch('services.core.content_service._get_transcript_from_watch_page', return_value='watch 페이지 자막')
    @patch('services.core.content_service._fetch_transcript_with_api', return_value=None)
    @patch('services.core.content_service._build_ytt_api')
    def test_watch_page_result_has_extraction_time_ms(self, mock_build, mock_fetch,
                                                       mock_watch, mock_no_cache, mock_save):
        """watch 페이지 폴백 시 extraction_time_ms 포함"""
        mock_build.return_value = MagicMock()

        with self.app.app_context():
            from services.core.content_service import get_transcript
            result = get_transcript('watchTest123')

        self.assertIn('extraction_time_ms', result)
        self.assertEqual(result['source'], 'watch')

    @patch('services.core.content_service._load_cache')
    def test_extraction_time_ms_is_positive(self, mock_cache):
        """extraction_time_ms 값이 0 이상인지 확인"""
        mock_cache.return_value = {'text': '텍스트', 'source': 'api'}

        with self.app.app_context():
            from services.core.content_service import get_transcript
            result = get_transcript('positiveTest')

        self.assertGreaterEqual(result['extraction_time_ms'], 0)

    @patch('services.core.content_service._load_cache', return_value=None)
    @patch('services.core.content_service._save_cache')
    @patch('services.core.content_service.get_transcript_via_supadata', return_value='supadata 자막')
    @patch('services.core.content_service._get_transcript_from_watch_page', return_value={'error': '실패'})
    @patch('services.core.content_service._fetch_transcript_with_api', return_value=None)
    @patch('services.core.content_service._build_ytt_api')
    @patch.dict('os.environ', {'SUPADATA_API_KEY': 'test-key'})
    def test_supadata_result_has_extraction_time_ms(self, mock_build, mock_fetch,
                                                     mock_watch, mock_supadata,
                                                     mock_save, mock_no_cache):
        """Supadata 폴백 시 extraction_time_ms 포함"""
        mock_build.return_value = MagicMock()

        with self.app.app_context():
            from services.core.content_service import get_transcript
            result = get_transcript('supadataTest')

        self.assertIn('extraction_time_ms', result)
        self.assertEqual(result['source'], 'supadata')


if __name__ == '__main__':
    unittest.main()
