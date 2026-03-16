"""R71: /api/export/docx 응답에 X-Page-Count 헤더 (페이지 수 추정치) 포함 검증."""
from __future__ import annotations

import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestDocxPageCount(unittest.TestCase):
    """DOCX 내보내기 응답의 X-Page-Count 헤더 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_page_count_header_present(self, _mock_sb):
        """X-Page-Count 헤더가 응답에 포함되어야 함."""
        resp = self.client.post('/api/export/docx',
                                json={'title': '테스트', 'content': '# 제목\n\n본문입니다.'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertIn('X-Page-Count', resp.headers)
        page_count = int(resp.headers['X-Page-Count'])
        self.assertGreaterEqual(page_count, 1)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_short_content_is_one_page(self, _mock_sb):
        """짧은 콘텐츠는 1페이지."""
        resp = self.client.post('/api/export/docx',
                                json={'title': '짧은 글', 'content': '짧은 본문'},
                                headers=_HEADERS)
        self.assertEqual(int(resp.headers['X-Page-Count']), 1)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_long_content_multiple_pages(self, _mock_sb):
        """긴 콘텐츠는 여러 페이지로 추정."""
        long_content = '가나다라마바사 ' * 500  # 약 3500자
        resp = self.client.post('/api/export/docx',
                                json={'title': '긴 글', 'content': long_content},
                                headers=_HEADERS)
        page_count = int(resp.headers['X-Page-Count'])
        self.assertGreater(page_count, 1)


if __name__ == '__main__':
    unittest.main()
