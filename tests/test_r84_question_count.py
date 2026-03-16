"""R84: /api/content/stats에 question_count 필드 추가 테스트."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestQuestionCount(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_question_count_present(self, _mock_sb):
        """question_count 필드가 응답에 포함된다."""
        resp = self.client.post('/api/content/stats',
                                json={'content': '이것은 무엇인가요? 저것은 어떤가요? 그렇습니다.'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('question_count', data)
        self.assertEqual(data['question_count'], 2)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_question_count_zero(self, _mock_sb):
        """물음표가 없으면 0을 반환한다."""
        resp = self.client.post('/api/content/stats',
                                json={'content': '이것은 문장입니다. 다른 문장도 있습니다.'},
                                headers=_HEADERS)
        data = resp.get_json()
        self.assertEqual(data['question_count'], 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_question_count_fullwidth(self, _mock_sb):
        """전각 물음표(？)도 카운트한다."""
        resp = self.client.post('/api/content/stats',
                                json={'content': 'これは何ですか？ はい。'},
                                headers=_HEADERS)
        data = resp.get_json()
        self.assertEqual(data['question_count'], 1)


if __name__ == '__main__':
    unittest.main()
