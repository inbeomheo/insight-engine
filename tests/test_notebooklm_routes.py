"""NotebookLM 라우트 테스트."""
import unittest
from unittest.mock import patch, MagicMock
import json


class TestNotebookLmRoutes(unittest.TestCase):
    """NotebookLM API 엔드포인트 테스트."""

    def setUp(self):
        # NotebookLmService를 mock으로 교체
        self.svc_patcher = patch('routes.notebooklm_routes._service')
        self.mock_svc = self.svc_patcher.start()

        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        self.svc_patcher.stop()

    def test_auth_check_valid(self):
        self.mock_svc.check_auth.return_value = {'valid': True, 'email': 'test@gmail.com'}
        resp = self.client.get('/api/notebooklm/auth-check')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['valid'])

    def test_auth_check_invalid(self):
        self.mock_svc.check_auth.return_value = {'valid': False, 'message': 'nlm login 필요'}
        resp = self.client.get('/api/notebooklm/auth-check')
        self.assertEqual(resp.status_code, 401)

    def test_generate_missing_fields(self):
        self.mock_svc.check_auth.return_value = {'valid': True}
        resp = self.client.post('/api/notebooklm/generate',
                                data=json.dumps({'type': 'audio'}),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 400)

    def test_generate_success(self):
        self.mock_svc.check_auth.return_value = {'valid': True}
        self.mock_svc.generate.return_value = {
            'artifact_id': 'test-artifact-id',
            'status': 'in_progress',
            'content_type': 'audio',
        }
        resp = self.client.post('/api/notebooklm/generate',
                                data=json.dumps({
                                    'type': 'audio',
                                    'url': 'https://youtube.com/watch?v=test',
                                    'source_text': '자막 텍스트'
                                }),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 202)
        data = resp.get_json()
        self.assertEqual(data['artifact_id'], 'test-artifact-id')

    def test_generate_unauthenticated(self):
        self.mock_svc.check_auth.return_value = {'valid': False, 'message': 'nlm login 필요'}
        resp = self.client.post('/api/notebooklm/generate',
                                data=json.dumps({
                                    'type': 'audio',
                                    'url': 'https://youtube.com/watch?v=test',
                                    'source_text': '자막'
                                }),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 401)

    def test_status_endpoint(self):
        self.mock_svc.check_status.return_value = {'status': 'completed', 'type': 'audio'}
        resp = self.client.get('/api/notebooklm/status/test-id')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'completed')

    def test_download_error_when_not_ready(self):
        self.mock_svc.download.side_effect = RuntimeError('아직 완료되지 않은 artifact입니다.')
        resp = self.client.get('/api/notebooklm/download/test-id')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('완료되지 않은', resp.get_json()['error'])

    def test_view_markdown_renders_html_inline(self):
        import os
        import tempfile

        fd, path = tempfile.mkstemp(suffix='.md')
        os.close(fd)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('# NotebookLM 결과\n\n본문입니다.')

        self.mock_svc.download.return_value = path
        try:
            resp = self.client.get('/api/notebooklm/view/test-id')
            self.assertEqual(resp.status_code, 200)
            self.assertIn('text/html', resp.content_type)
            self.assertNotIn('attachment', resp.headers.get('Content-Disposition', ''))
            self.assertIn('NotebookLM 결과', resp.get_data(as_text=True))
        finally:
            os.remove(path)


if __name__ == '__main__':
    unittest.main()
