"""R104: /api/export/markdown에 include_separator 옵션 테스트"""
import unittest
from unittest.mock import patch

from app import create_app


class TestExportMarkdownSeparator(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_separator_adds_hr_between_sections(self, _mock):
        """include_separator=true이면 ## 사이에 --- 구분선이 삽입된다."""
        content = '본문 시작\n\n## 섹션 1\n내용1\n\n## 섹션 2\n내용2'
        resp = self.client.post('/api/export/markdown',
            json={'title': '테스트', 'content': content, 'include_separator': True},
            headers={'Authorization': 'Bearer test'})
        self.assertEqual(resp.status_code, 200)
        text = resp.data.decode('utf-8')
        self.assertIn('---\n\n## 섹션 1', text)
        self.assertIn('---\n\n## 섹션 2', text)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_no_separator_by_default(self, _mock):
        """기본값(include_separator 미전달)이면 구분선이 없다."""
        content = '본문\n\n## 섹션 A\n내용A\n\n## 섹션 B\n내용B'
        resp = self.client.post('/api/export/markdown',
            json={'title': '테스트', 'content': content},
            headers={'Authorization': 'Bearer test'})
        self.assertEqual(resp.status_code, 200)
        text = resp.data.decode('utf-8')
        self.assertNotIn('---\n\n## 섹션 A', text)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_separator_false_no_hr(self, _mock):
        """include_separator=false이면 구분선이 없다."""
        content = '본문\n\n## 첫 번째\n내용'
        resp = self.client.post('/api/export/markdown',
            json={'title': '테스트', 'content': content, 'include_separator': False},
            headers={'Authorization': 'Bearer test'})
        self.assertEqual(resp.status_code, 200)
        text = resp.data.decode('utf-8')
        self.assertNotIn('---\n\n## 첫 번째', text)

    def test_service_function_directly(self):
        """export_service.export_markdown의 include_separator 파라미터 직접 테스트."""
        from services.export.export_service import export_markdown
        content = '서론\n\n## 파트 1\n내용1\n\n## 파트 2\n내용2\n\n## 파트 3\n내용3'
        buf = export_markdown('제목', content, include_separator=True)
        text = buf.read().decode('utf-8')
        self.assertEqual(text.count('---\n\n##'), 3)

    def test_service_no_separator(self):
        """include_separator=False이면 원본 유지."""
        from services.export.export_service import export_markdown
        content = '서론\n\n## 파트 1\n내용'
        buf = export_markdown('제목', content, include_separator=False)
        text = buf.read().decode('utf-8')
        self.assertNotIn('---\n\n## 파트 1', text)


if __name__ == '__main__':
    unittest.main()
