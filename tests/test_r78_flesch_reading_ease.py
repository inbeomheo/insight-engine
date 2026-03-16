"""R78: /api/content/stats에 flesch_reading_ease 가독성 점수 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestFleschReadingEase(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_flesch_field_present(self, _mock_sb):
        """flesch_reading_ease 필드가 응답에 포함된다."""
        resp = self.client.post('/api/content/stats',
                                json={'content': '안녕하세요. 테스트 문장입니다. 세 번째 문장.'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('flesch_reading_ease', data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_flesch_score_range(self, _mock_sb):
        """flesch_reading_ease 값은 0~100 사이."""
        resp = self.client.post('/api/content/stats',
                                json={'content': '짧은 문장. 긴 문장도 있습니다. 매우 긴 문장이 여기에 포함되어 있습니다.'},
                                headers=_HEADERS)
        data = resp.get_json()
        score = data['flesch_reading_ease']
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_flesch_is_numeric(self, _mock_sb):
        """flesch_reading_ease 값은 숫자 타입."""
        resp = self.client.post('/api/content/stats',
                                json={'content': '테스트 콘텐츠입니다. 두 번째 문장.'},
                                headers=_HEADERS)
        data = resp.get_json()
        self.assertIsInstance(data['flesch_reading_ease'], (int, float))


if __name__ == '__main__':
    unittest.main()
