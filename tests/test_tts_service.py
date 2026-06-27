"""tts_service 단위 테스트 (내부 함수 위주)"""
import unittest
from unittest.mock import MagicMock, patch

from services.media.tts_service import (
    preprocess_for_tts,
    _synthesize_openai,
    _split_text,
    OPENAI_VOICES,
    EDGE_VOICE_KO,
    EDGE_VOICE_EN,
)


class TestConstants(unittest.TestCase):

    def test_openai_voices(self):
        """OpenAI 목소리 6종"""
        self.assertEqual(len(OPENAI_VOICES), 6)
        self.assertIn('alloy', OPENAI_VOICES)
        self.assertIn('nova', OPENAI_VOICES)

    def test_edge_voices(self):
        """Edge TTS 기본 목소리"""
        self.assertIn('ko-KR', EDGE_VOICE_KO)
        self.assertIn('en-US', EDGE_VOICE_EN)


class TestPreprocessForTts(unittest.TestCase):

    def test_remove_code_block(self):
        """코드 블록 제거"""
        md = '텍스트\n```python\nprint("hello")\n```\n나머지'
        result = preprocess_for_tts(md)
        self.assertNotIn('```', result)
        self.assertNotIn('print', result)
        self.assertIn('텍스트', result)

    def test_remove_inline_code(self):
        """인라인 코드 제거"""
        result = preprocess_for_tts('`변수명`을 사용합니다.')
        self.assertNotIn('`', result)
        self.assertNotIn('변수명', result)

    def test_remove_image(self):
        """이미지 마크다운 제거"""
        result = preprocess_for_tts('![alt](image.png)')
        self.assertNotIn('![', result)
        self.assertNotIn('image.png', result)

    def test_link_text_preserved(self):
        """링크 텍스트 유지, URL 제거"""
        result = preprocess_for_tts('[구글](https://google.com)로 검색')
        self.assertIn('구글', result)
        self.assertNotIn('https://', result)

    def test_heading_symbol_removed(self):
        """제목 # 기호 제거"""
        result = preprocess_for_tts('## 두 번째 제목\n\n내용입니다.')
        self.assertNotIn('##', result)
        self.assertIn('두 번째 제목', result)

    def test_bold_italic_preserved(self):
        """볼드/이탤릭 텍스트 유지"""
        result = preprocess_for_tts('**굵은 글씨**와 *기울임*')
        self.assertNotIn('**', result)
        self.assertNotIn('*', result)
        self.assertIn('굵은 글씨', result)

    def test_strikethrough_preserved(self):
        """취소선 텍스트 유지"""
        result = preprocess_for_tts('~~취소~~된 텍스트')
        self.assertNotIn('~~', result)
        self.assertIn('취소', result)

    def test_blockquote_removed(self):
        """블록쿼트 기호 제거"""
        result = preprocess_for_tts('> 인용문입니다.')
        self.assertNotIn('>', result)
        self.assertIn('인용문입니다', result)

    def test_bullet_removed(self):
        """불릿 기호 제거"""
        result = preprocess_for_tts('- 항목1\n- 항목2')
        self.assertNotIn('- ', result)
        self.assertIn('항목1', result)

    def test_empty_input(self):
        """빈 입력"""
        self.assertEqual(preprocess_for_tts(''), '')

    def test_plain_text_unchanged(self):
        """일반 텍스트는 그대로"""
        text = '안녕하세요. 좋은 하루입니다.'
        result = preprocess_for_tts(text)
        self.assertIn('안녕하세요', result)


class TestSplitText(unittest.TestCase):

    def test_short_text(self):
        """짧은 텍스트 → 분할 없음"""
        result = _split_text('짧은 텍스트', 100)
        self.assertEqual(len(result), 1)

    def test_split_at_sentence_boundary(self):
        """문장 경계에서 분할"""
        text = '첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다.'
        result = _split_text(text, 25)
        self.assertGreater(len(result), 1)
        # 각 청크가 max_chars 이하
        for chunk in result:
            self.assertLessEqual(len(chunk), 25)

    def test_no_empty_chunks(self):
        """빈 청크 없음"""
        text = '가나다라마. ' * 50
        result = _split_text(text, 30)
        for chunk in result:
            self.assertTrue(chunk.strip())

    def test_exact_max_chars(self):
        """정확히 max_chars와 같은 길이"""
        text = 'A' * 100
        result = _split_text(text, 100)
        self.assertEqual(len(result), 1)

    def test_forced_split(self):
        """문장 경계도 공백도 없을 때 강제 분할"""
        text = '가' * 100
        result = _split_text(text, 30)
        self.assertGreater(len(result), 1)


class TestOpenAITts(unittest.TestCase):

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}, clear=False)
    def test_openai_tts_disables_redirects(self):
        """OpenAI TTS 호출은 인증 헤더 redirect를 따르지 않음"""
        mock_httpx = MagicMock()
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'mp3-bytes'
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.Client.return_value = mock_client

        with patch.dict('sys.modules', {'httpx': mock_httpx}):
            result = _synthesize_openai('hello', 'alloy', 1.0)

        self.assertEqual(result, b'mp3-bytes')
        self.assertFalse(mock_httpx.Client.call_args.kwargs['follow_redirects'])

    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}, clear=False)
    def test_openai_tts_redirect_blocked(self):
        """OpenAI TTS 3xx 응답은 차단"""
        mock_httpx = MagicMock()
        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_resp.text = 'redirect'
        mock_client.post.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_httpx.Client.return_value = mock_client

        with patch.dict('sys.modules', {'httpx': mock_httpx}):
            with self.assertRaises(RuntimeError) as ctx:
                _synthesize_openai('hello', 'alloy', 1.0)

        self.assertIn('리다이렉트', str(ctx.exception))
        self.assertFalse(mock_httpx.Client.call_args.kwargs['follow_redirects'])


if __name__ == '__main__':
    unittest.main()
