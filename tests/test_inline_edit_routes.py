"""인라인 편집 라우트 테스트 (/api/inline-edit)."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestInlineEditRoutes(unittest.TestCase):
    """POST /api/inline-edit 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.core.ai_service.inline_edit')
    def test_inline_edit_returns_diff(self, mock_edit, _mock_sb):
        """응답에 diff 필드가 포함됨."""
        mock_edit.return_value = {
            'original': '원본 텍스트',
            'edited': '수정된 텍스트',
            'full_content': '앞부분 수정된 텍스트 뒷부분',
            'diff': '--- original\n+++ edited\n@@ -1 +1 @@\n-원본 텍스트\n+수정된 텍스트',
        }
        resp = self.client.post('/api/inline-edit', json={
            'content': '앞부분 원본 텍스트 뒷부분',
            'selection': '원본 텍스트',
            'instruction': '축약해주세요',
        }, headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('diff', data)
        self.assertIn('original', data['diff'])
        self.assertIn('edited', data['diff'])
        self.assertEqual(data['original'], '원본 텍스트')
        self.assertEqual(data['edited'], '수정된 텍스트')

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_missing_content_returns_400(self, _mock_sb):
        """content 없이 요청 시 400."""
        resp = self.client.post('/api/inline-edit', json={
            'selection': '텍스트',
            'instruction': '수정',
        }, headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_missing_instruction_returns_400(self, _mock_sb):
        """instruction 없이 요청 시 400."""
        resp = self.client.post('/api/inline-edit', json={
            'content': '전체 텍스트',
            'selection': '일부',
        }, headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
