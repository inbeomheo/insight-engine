"""realtime_translate_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.transcript.realtime_translate_service import (
    _translate_with_deepl,
    _DEEPL_LANG_MAP,
    _TRANSLATE_PROMPTS,
    RealtimeTranslateService,
)


class TestConstants(unittest.TestCase):

    def test_deepl_lang_map_has_ko_en_ja(self):
        """DeepL 언어 매핑에 ko, en, ja 포함"""
        for lang in ('ko', 'en', 'ja'):
            self.assertIn(lang, _DEEPL_LANG_MAP)

    def test_translate_prompts_has_ko_en_ja(self):
        """번역 프롬프트에 ko, en, ja 포함"""
        for lang in ('ko', 'en', 'ja'):
            self.assertIn(lang, _TRANSLATE_PROMPTS)
            self.assertTrue(len(_TRANSLATE_PROMPTS[lang]) > 10)


class TestTranslateWithDeepL(unittest.TestCase):

    @patch('services.transcript.realtime_translate_service.DEEPL_API_KEY', '')
    def test_no_api_key(self):
        """API 키 없음 → None"""
        result = _translate_with_deepl('hello', 'ko')
        self.assertIsNone(result)

    @patch('services.transcript.realtime_translate_service.DEEPL_API_KEY', 'test-key')
    def test_unsupported_lang(self):
        """지원하지 않는 언어 → None"""
        result = _translate_with_deepl('hello', 'xx')
        self.assertIsNone(result)

    @patch('services.transcript.realtime_translate_service.DEEPL_API_KEY', 'test-key:fx')
    def test_free_api_url(self):
        """무료 API 키(:fx) → api-free.deepl.com"""
        mock_httpx = MagicMock()
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'translations': [{'text': '안녕'}]}
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.Client.return_value = mock_client

        with patch.dict('sys.modules', {'httpx': mock_httpx}):
            result = _translate_with_deepl('hello', 'ko')
        self.assertEqual(result, '안녕')
        self.assertFalse(mock_httpx.Client.call_args.kwargs['follow_redirects'])
        call_args = mock_client.post.call_args
        self.assertIn('api-free', call_args[0][0])

    @patch('services.transcript.realtime_translate_service.DEEPL_API_KEY', 'test-key')
    def test_redirect_blocked(self):
        """DeepL API 3xx 응답은 AI 폴백 대상으로 처리"""
        mock_httpx = MagicMock()
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.Client.return_value = mock_client

        with patch.dict('sys.modules', {'httpx': mock_httpx}):
            result = _translate_with_deepl('hello', 'ko')
        self.assertIsNone(result)
        self.assertFalse(mock_httpx.Client.call_args.kwargs['follow_redirects'])


class TestRealtimeTranslateService(unittest.TestCase):

    def test_empty_text(self):
        """빈 텍스트 → 빈 결과"""
        svc = RealtimeTranslateService()
        result = svc.translate('', 'ko')
        self.assertEqual(result['translated'], '')
        self.assertEqual(result['source'], 'none')

    def test_whitespace_text(self):
        """공백 텍스트 → 빈 결과"""
        svc = RealtimeTranslateService()
        result = svc.translate('   ', 'en')
        self.assertEqual(result['translated'], '')

    def test_unsupported_lang(self):
        """지원하지 않는 언어 → ValueError"""
        svc = RealtimeTranslateService()
        with self.assertRaises(ValueError) as ctx:
            svc.translate('hello', 'xx')
        self.assertIn('지원하지 않는', str(ctx.exception))

    @patch('services.transcript.realtime_translate_service._translate_with_deepl', return_value='번역 결과')
    def test_deepl_priority(self, mock_deepl):
        """DeepL 우선 사용"""
        svc = RealtimeTranslateService()
        result = svc.translate('hello world', 'ko')
        self.assertEqual(result['translated'], '번역 결과')
        self.assertEqual(result['source'], 'deepl')

    @patch('services.transcript.realtime_translate_service._translate_with_ai', return_value='AI 번역')
    @patch('services.transcript.realtime_translate_service._translate_with_deepl', return_value=None)
    def test_ai_fallback(self, mock_deepl, mock_ai):
        """DeepL 실패 → AI 폴백"""
        svc = RealtimeTranslateService()
        result = svc.translate('hello', 'ko')
        self.assertEqual(result['translated'], 'AI 번역')
        self.assertEqual(result['source'], 'ai')

    @patch('services.transcript.realtime_translate_service._translate_with_ai', return_value='AI only')
    def test_use_ai_only(self, mock_ai):
        """use_ai_only=True → DeepL 건너뜀"""
        svc = RealtimeTranslateService()
        result = svc.translate('hello', 'ko', use_ai_only=True)
        self.assertEqual(result['source'], 'ai')

    @patch('services.transcript.realtime_translate_service._translate_with_ai', side_effect=Exception('fail'))
    @patch('services.transcript.realtime_translate_service._translate_with_deepl', return_value=None)
    def test_both_fail(self, mock_deepl, mock_ai):
        """둘 다 실패 → RuntimeError"""
        svc = RealtimeTranslateService()
        with self.assertRaises(RuntimeError):
            svc.translate('hello', 'ko')


class TestTranslateContent(unittest.TestCase):

    @patch.object(RealtimeTranslateService, 'translate')
    def test_single_chunk(self, mock_translate):
        """짧은 텍스트 → 단일 청크"""
        mock_translate.return_value = {'translated': '번역됨'}
        svc = RealtimeTranslateService()
        result = svc.translate_content('짧은 텍스트', 'en')
        self.assertEqual(result, '번역됨')
        self.assertEqual(mock_translate.call_count, 1)

    @patch.object(RealtimeTranslateService, 'translate')
    def test_multiple_chunks(self, mock_translate):
        """긴 텍스트 → 다중 청크"""
        mock_translate.return_value = {'translated': '번역'}
        long_text = ('A' * 100 + '\n\n') * 5
        svc = RealtimeTranslateService()
        result = svc.translate_content(long_text, 'en', chunk_size=150)
        self.assertGreater(mock_translate.call_count, 1)


if __name__ == '__main__':
    unittest.main()
