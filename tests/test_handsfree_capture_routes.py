"""핸즈프리 음성 캡처 라우트 단위 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestHandsfreeCaptureRoutes(unittest.TestCase):
    """음성 캡처 / 병합 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_capture_speech_success(self, _mock_sb):
        """음성 텍스트 정돈 성공."""
        resp = self.client.post(
            '/api/capture/speech',
            json={'text': '음 그러니까 정말 정말 좋은 아이디어입니다'},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('text', data)
        self.assertGreater(data['word_count'], 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_capture_speech_empty(self, _mock_sb):
        """빈 텍스트 시 400."""
        resp = self.client.post(
            '/api/capture/speech',
            json={'text': ''},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_merge_captures(self, _mock_sb):
        """여러 텍스트 병합."""
        resp = self.client.post(
            '/api/capture/merge',
            json={'texts': ['첫 번째 문장입니다.', '두 번째 문장입니다.']},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('첫 번째', data['text'])
        self.assertIn('두 번째', data['text'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_merge_empty_list(self, _mock_sb):
        """빈 목록 병합 시 400."""
        resp = self.client.post(
            '/api/capture/merge',
            json={'texts': []},
            headers=_HEADERS,
        )
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
