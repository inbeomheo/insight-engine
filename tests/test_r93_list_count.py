"""R93: /api/content/stats에 list_count (불렛/번호 리스트 항목 수) 필드 테스트."""
import unittest
from unittest.mock import patch

from app import create_app


class TestListCount(unittest.TestCase):
    """list_count 필드가 마크다운 리스트 항목 수를 정확히 반환하는지 검증."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_list_count_present(self, _):
        """응답에 list_count 필드가 존재한다."""
        resp = self.client.post(
            '/api/content/stats',
            json={'content': '일반 텍스트입니다. 특별한 내용 없이 작성합니다.'},
            headers={'Origin': 'http://localhost:3000'},
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('list_count', data)
        self.assertEqual(data['list_count'], 0)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_list_count_bullet(self, _):
        """불렛 리스트 (-, *, +) 항목을 정확히 카운트한다."""
        content = "## 목록\n- 첫 번째\n- 두 번째\n* 세 번째\n+ 네 번째"
        resp = self.client.post(
            '/api/content/stats',
            json={'content': content},
            headers={'Origin': 'http://localhost:3000'},
        )
        data = resp.get_json()
        self.assertEqual(data['list_count'], 4)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_list_count_numbered(self, _):
        """번호 리스트 (1. 2. 3.) 항목을 정확히 카운트한다."""
        content = "## 순서\n1. 첫 번째\n2. 두 번째\n3. 세 번째"
        resp = self.client.post(
            '/api/content/stats',
            json={'content': content},
            headers={'Origin': 'http://localhost:3000'},
        )
        data = resp.get_json()
        self.assertEqual(data['list_count'], 3)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_list_count_mixed(self, _):
        """불렛 + 번호 혼합 리스트를 정확히 카운트한다."""
        content = "- 불렛 1\n- 불렛 2\n1. 번호 1\n2. 번호 2"
        resp = self.client.post(
            '/api/content/stats',
            json={'content': content},
            headers={'Origin': 'http://localhost:3000'},
        )
        data = resp.get_json()
        self.assertEqual(data['list_count'], 4)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_list_count_type(self, _):
        """list_count는 정수형이다."""
        resp = self.client.post(
            '/api/content/stats',
            json={'content': '- 항목 하나'},
            headers={'Origin': 'http://localhost:3000'},
        )
        data = resp.get_json()
        self.assertIsInstance(data['list_count'], int)


if __name__ == '__main__':
    unittest.main()
