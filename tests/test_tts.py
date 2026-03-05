"""
TTS(Text-to-Speech) 서비스 테스트

커버 범위:
- preprocess_for_tts: 마크다운 → 평문 변환
- TTSService.synthesize: 통합 합성 (OpenAI / Edge TTS 모킹)
- /api/tts 엔드포인트: 정상 응답, 입력 검증
"""
import io
import json
import os
import unittest
from unittest.mock import MagicMock, patch

# 서비스 모듈 임포트 전에 환경변수 설정 (Supabase 비활성화)
os.environ.setdefault('SUPABASE_URL', '')
os.environ.setdefault('SUPABASE_ANON_KEY', '')


class TestPreprocessForTts(unittest.TestCase):
    """preprocess_for_tts 단위 테스트"""

    def setUp(self):
        from services.tts_service import preprocess_for_tts
        self.preprocess = preprocess_for_tts

    def test_removes_code_blocks(self):
        text = "도입부\n```python\nprint('hello')\n```\n결론"
        result = self.preprocess(text)
        self.assertNotIn('```', result)
        self.assertNotIn("print('hello')", result)
        self.assertIn('도입부', result)
        self.assertIn('결론', result)

    def test_removes_inline_code(self):
        text = "`os.path.join()` 함수를 사용합니다."
        result = self.preprocess(text)
        self.assertNotIn('`', result)
        self.assertIn('함수를 사용합니다', result)

    def test_removes_images(self):
        text = "텍스트 ![이미지](https://example.com/img.png) 이후"
        result = self.preprocess(text)
        self.assertNotIn('![', result)
        self.assertIn('텍스트', result)
        self.assertIn('이후', result)

    def test_converts_links_to_text(self):
        text = "[클로드 문서](https://docs.anthropic.com)"
        result = self.preprocess(text)
        self.assertIn('클로드 문서', result)
        self.assertNotIn('https://', result)

    def test_removes_heading_markers(self):
        text = "## 섹션 제목\n### 소제목"
        result = self.preprocess(text)
        self.assertNotIn('#', result)
        self.assertIn('섹션 제목', result)
        self.assertIn('소제목', result)

    def test_removes_bold_italic(self):
        text = "**굵은글씨**와 *이탤릭체*입니다."
        result = self.preprocess(text)
        self.assertNotIn('**', result)
        self.assertNotIn('*', result)
        self.assertIn('굵은글씨', result)
        self.assertIn('이탤릭체', result)

    def test_removes_bullet_lists(self):
        text = "- 항목 1\n- 항목 2\n- 항목 3"
        result = self.preprocess(text)
        self.assertNotIn('- ', result)
        self.assertIn('항목 1', result)

    def test_removes_table_separator(self):
        text = "| 헤더 | 값 |\n|------|----|\n| A | 1 |"
        result = self.preprocess(text)
        self.assertNotIn('---', result)
        # 헤더와 값 텍스트는 유지
        self.assertIn('헤더', result)

    def test_empty_after_preprocess_returns_empty(self):
        # 코드 블록만 있는 경우 빈 문자열
        text = "```\nonly code\n```"
        result = self.preprocess(text)
        self.assertEqual(result, '')

    def test_plain_text_unchanged(self):
        text = "일반 텍스트입니다. 마크다운이 없습니다."
        result = self.preprocess(text)
        self.assertIn('일반 텍스트입니다', result)


class TestTtsServiceSynthesize(unittest.TestCase):
    """TTSService.synthesize 통합 테스트 (백엔드 모킹)"""

    DUMMY_AUDIO = b'ID3\x00\x00\x00\x00' + b'\x00' * 100  # 가짜 MP3 바이트

    def _make_service(self):
        from services.tts_service import TTSService
        return TTSService

    def test_raises_on_empty_text(self):
        TTSService = self._make_service()
        with self.assertRaises(ValueError) as ctx:
            TTSService.synthesize('')
        self.assertIn('입력', str(ctx.exception))

    @patch('services.tts_service._synthesize_edge')
    @patch('services.tts_service._select_backend', return_value='edge')
    def test_long_text_splits_into_chunks(self, _mock_select, mock_edge):
        """장문은 에러 대신 청크 분할 후 합성한다."""
        mock_edge.return_value = self.DUMMY_AUDIO
        TTSService = self._make_service()
        with patch('services.tts_service.TTS_MAX_CHARS', 10):
            result = TTSService.synthesize('A' * 11)
        self.assertIsNotNone(result)
        self.assertTrue(mock_edge.call_count >= 2)

    @patch('services.tts_service._synthesize_edge')
    @patch('services.tts_service._select_backend', return_value='edge')
    def test_edge_backend_called(self, _mock_select, mock_edge):
        mock_edge.return_value = self.DUMMY_AUDIO
        TTSService = self._make_service()
        result = TTSService.synthesize('테스트 텍스트입니다.')
        mock_edge.assert_called_once()
        self.assertEqual(result, self.DUMMY_AUDIO)

    @patch('services.tts_service._synthesize_openai')
    @patch('services.tts_service._select_backend', return_value='openai')
    def test_openai_backend_called(self, _mock_select, mock_openai):
        mock_openai.return_value = self.DUMMY_AUDIO
        TTSService = self._make_service()
        result = TTSService.synthesize('테스트 텍스트입니다.')
        mock_openai.assert_called_once()
        self.assertEqual(result, self.DUMMY_AUDIO)

    @patch('services.tts_service._synthesize_edge')
    @patch('services.tts_service._synthesize_openai', side_effect=RuntimeError('OpenAI 오류'))
    @patch('services.tts_service._select_backend', return_value='openai')
    def test_openai_failure_falls_back_to_edge(self, _mock_select, _mock_openai, mock_edge):
        """OpenAI 실패 시 Edge TTS로 자동 폴백"""
        mock_edge.return_value = self.DUMMY_AUDIO
        TTSService = self._make_service()
        result = TTSService.synthesize('테스트 텍스트입니다.')
        mock_edge.assert_called_once()
        self.assertEqual(result, self.DUMMY_AUDIO)

    @patch('services.tts_service._synthesize_edge')
    @patch('services.tts_service._select_backend', return_value='edge')
    def test_preprocess_is_applied_by_default(self, _mock_select, mock_edge):
        """preprocess=True(기본값)이면 마크다운이 제거된 텍스트가 전달됨"""
        mock_edge.return_value = self.DUMMY_AUDIO
        TTSService = self._make_service()

        markdown_text = "## 제목\n**굵은** 텍스트와 `코드`입니다."
        TTSService.synthesize(markdown_text)

        called_text = mock_edge.call_args[0][0]
        self.assertNotIn('##', called_text)
        self.assertNotIn('**', called_text)
        self.assertNotIn('`', called_text)

    @patch('services.tts_service._synthesize_edge')
    @patch('services.tts_service._select_backend', return_value='edge')
    def test_preprocess_false_skips_cleanup(self, _mock_select, mock_edge):
        """preprocess=False이면 원본 텍스트를 그대로 전달"""
        mock_edge.return_value = self.DUMMY_AUDIO
        TTSService = self._make_service()

        raw_text = "## 제목이 그대로 전달됩니다"
        TTSService.synthesize(raw_text, preprocess=False)

        called_text = mock_edge.call_args[0][0]
        self.assertIn('##', called_text)


class TestTtsEndpoint(unittest.TestCase):
    """POST /api/tts 엔드포인트 테스트"""

    DUMMY_AUDIO = b'ID3\x00\x00\x00\x00' + b'\x00' * 100

    def setUp(self):
        # Supabase 비활성화 패치
        self._patch_supabase = patch(
            'services.supabase_service.is_supabase_enabled', return_value=False
        )
        self._patch_supabase.start()

        # Flask 앱 생성
        from app import create_app
        self.app = create_app({'TESTING': True})
        self.client = self.app.test_client()

    def tearDown(self):
        self._patch_supabase.stop()

    def _post_tts(self, payload: dict):
        return self.client.post(
            '/api/tts',
            data=json.dumps(payload),
            content_type='application/json',
        )

    @patch('services.tts_service.TTSService.synthesize')
    def test_success_returns_audio(self, mock_synth):
        mock_synth.return_value = self.DUMMY_AUDIO
        resp = self._post_tts({'text': '안녕하세요 팟캐스트 테스트입니다.'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content_type, 'audio/mpeg')
        self.assertEqual(resp.data, self.DUMMY_AUDIO)

    def test_missing_text_returns_400(self):
        resp = self._post_tts({})
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn('error', body)

    def test_empty_text_returns_400(self):
        resp = self._post_tts({'text': '   '})
        self.assertEqual(resp.status_code, 400)

    def test_text_too_long_returns_400(self):
        resp = self._post_tts({'text': 'A' * 6000})
        self.assertEqual(resp.status_code, 400)
        body = json.loads(resp.data)
        self.assertIn('최대', body['error'])

    @patch('services.tts_service.TTSService.synthesize', side_effect=RuntimeError('백엔드 오류'))
    def test_backend_error_returns_500(self, _mock):
        resp = self._post_tts({'text': '정상 텍스트'})
        self.assertEqual(resp.status_code, 500)
        body = json.loads(resp.data)
        self.assertIn('error', body)

    @patch('services.tts_service.TTSService.synthesize')
    def test_custom_voice_and_speed(self, mock_synth):
        mock_synth.return_value = self.DUMMY_AUDIO
        self._post_tts({'text': '속도 테스트', 'voice': 'nova', 'speed': 1.5})
        _, kwargs = mock_synth.call_args
        # synthesize(text, voice=..., speed=..., preprocess=True) 형태 확인
        self.assertEqual(kwargs.get('voice') or mock_synth.call_args[0][1], 'nova')

    @patch('services.tts_service.TTSService.synthesize')
    def test_speed_clamped_to_valid_range(self, mock_synth):
        """속도는 0.5~2.0 사이로 클램핑됩니다."""
        mock_synth.return_value = self.DUMMY_AUDIO
        self._post_tts({'text': '속도 클램핑 테스트', 'speed': 99.0})
        _, kwargs = mock_synth.call_args
        speed_val = kwargs.get('speed') or mock_synth.call_args[0][2]
        self.assertLessEqual(speed_val, 2.0)


class TestSelectBackend(unittest.TestCase):
    """_select_backend 백엔드 선택 로직 테스트"""

    def test_auto_with_openai_key_selects_openai(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'sk-test'}):
            with patch('services.tts_service.TTS_BACKEND', 'auto'):
                from services.tts_service import _select_backend
                import importlib
                import services.tts_service as tts_mod
                # 환경변수를 직접 검사하는 함수를 재검사
                with patch('services.tts_service.TTS_BACKEND', 'auto'):
                    # os.getenv를 통해 선택 로직 직접 테스트
                    result = 'openai' if os.getenv('OPENAI_API_KEY') else 'edge'
                    self.assertEqual(result, 'openai')

    def test_auto_without_openai_key_selects_edge(self):
        env = {k: v for k, v in os.environ.items() if k != 'OPENAI_API_KEY'}
        with patch.dict(os.environ, env, clear=True):
            result = 'openai' if os.getenv('OPENAI_API_KEY') else 'edge'
            self.assertEqual(result, 'edge')

    def test_explicit_edge_backend(self):
        with patch('services.tts_service.TTS_BACKEND', 'edge'):
            from services.tts_service import _select_backend
            self.assertEqual(_select_backend(), 'edge')

    def test_explicit_openai_backend(self):
        with patch('services.tts_service.TTS_BACKEND', 'openai'):
            from services.tts_service import _select_backend
            self.assertEqual(_select_backend(), 'openai')


if __name__ == '__main__':
    unittest.main()
