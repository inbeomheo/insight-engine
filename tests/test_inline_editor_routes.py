"""인라인 편집 앱 라우트 테스트."""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestInlineEditorRoutes(unittest.TestCase):
    """POST /api/mcp/apps/inline-editor/render, /action 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_render_returns_html(self, _mock_sb):
        """콘텐츠를 제공하면 편집 가능한 HTML 반환."""
        resp = self.client.post('/api/mcp/apps/inline-editor/render',
                                json={
                                    'title': '테스트 제목',
                                    'content': '첫 번째 단락\n\n두 번째 단락',
                                },
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('html', data)
        self.assertIn('actions', data)
        self.assertIn('단락', data['html'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_render_empty_content_returns_400(self, _mock_sb):
        """빈 content로 렌더링 시 400."""
        resp = self.client.post('/api/mcp/apps/inline-editor/render',
                                json={'title': '제목', 'content': ''},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_action_without_action_field_returns_400(self, _mock_sb):
        """action 필드 없이 액션 요청 시 400."""
        resp = self.client.post('/api/mcp/apps/inline-editor/action',
                                json={'session_id': 'abc'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertIn('error', data)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_render_then_action_uses_same_singleton_session(self, _mock_sb):
        rendered = self.client.post(
            '/api/mcp/apps/inline-editor/render',
            json={'title': '제목', 'content': '원본 단락'},
            headers=_HEADERS,
        )
        self.assertEqual(rendered.status_code, 200)
        session_id = rendered.get_json()['session_id']

        edited = self.client.post(
            '/api/mcp/apps/inline-editor/action',
            json={
                'action': 'save_edit',
                'session_id': session_id,
                'section': 0,
                'new_content': '수정된 단락',
            },
            headers=_HEADERS,
        )
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(
            edited.get_json()['updated_content']['sections'][0],
            '수정된 단락',
        )


if __name__ == '__main__':
    unittest.main()
