"""R61: /api/content/stats 응답에 avg_word_length 필드 포함 테스트"""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestContentStatsAvgWordLength(unittest.TestCase):
    """/api/content/stats의 avg_word_length 필드 검증"""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_avg_word_length_field_exists(self, _):
        """응답에 avg_word_length 필드가 존재"""
        resp = self.client.post('/api/content/stats',
                                json={'content': '안녕하세요 테스트입니다'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('avg_word_length', data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_avg_word_length_calculation(self, _):
        """avg_word_length 계산이 올바른지 확인 (영어 단어)"""
        # "hello world" → 단어 2개, 총 글자 10, 평균 5.0
        resp = self.client.post('/api/content/stats',
                                json={'content': 'hello world'},
                                headers=_HEADERS)
        data = resp.get_json()
        self.assertEqual(data['avg_word_length'], 5.0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_avg_word_length_is_float(self, _):
        """avg_word_length가 float 타입인지 확인"""
        resp = self.client.post('/api/content/stats',
                                json={'content': '가나다 라마바사'},
                                headers=_HEADERS)
        data = resp.get_json()
        self.assertIsInstance(data['avg_word_length'], float)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_avg_word_length_mixed_language(self, _):
        """한영 혼합 텍스트에서도 정상 계산"""
        # "AI 기술은 발전합니다" → 4단어
        resp = self.client.post('/api/content/stats',
                                json={'content': 'AI 기술은 발전합니다'},
                                headers=_HEADERS)
        data = resp.get_json()
        self.assertGreater(data['avg_word_length'], 0)


if __name__ == '__main__':
    unittest.main()
