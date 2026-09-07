"""NotebookLM 라우트 테스트."""
import unittest
from unittest.mock import patch, MagicMock
import json
from flask import g


class TestNotebookLmRoutes(unittest.TestCase):
    """NotebookLM API 엔드포인트 테스트."""

    def setUp(self):
        self.auth_patcher = patch(
            'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
            return_value=False,
        )
        self.auth_patcher.start()
        # NotebookLmService를 mock으로 교체
        self.svc_patcher = patch('routes.notebooklm_routes._service')
        self.mock_svc = self.svc_patcher.start()

        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        self.client = app.test_client()

    def tearDown(self):
        self.svc_patcher.stop()
        self.auth_patcher.stop()

    def test_all_endpoints_require_app_auth_when_supabase_is_enabled(self):
        endpoints = [
            ('get', '/api/notebooklm/auth-check'),
            ('post', '/api/notebooklm/generate'),
            ('get', '/api/notebooklm/status/test-id'),
            ('get', '/api/notebooklm/download/test-id'),
        ]
        with patch(
            'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
            return_value=True,
        ):
            for method, path in endpoints:
                with self.subTest(path=path):
                    resp = getattr(self.client, method)(path)
                    self.assertEqual(resp.status_code, 401)
                    self.assertEqual(resp.get_json()['code'], 'AUTH_REQUIRED')

    def test_auth_check_valid(self):
        self.mock_svc.check_auth.return_value = {'valid': True, 'email': 'test@gmail.com'}
        resp = self.client.get('/api/notebooklm/auth-check')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['valid'])

    def test_auth_check_invalid(self):
        self.mock_svc.check_auth.return_value = {'valid': False, 'message': 'nlm login 필요'}
        resp = self.client.get('/api/notebooklm/auth-check')
        self.assertEqual(resp.status_code, 424)
        self.assertEqual(resp.get_json()['code'], 'NOTEBOOKLM_AUTH_REQUIRED')

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
        self.mock_svc.generate.assert_called_once_with(
            'audio',
            'https://youtube.com/watch?v=test',
            '자막 텍스트',
            user_id=None,
            on_cost_start=None,
        )

    def test_generate_unauthenticated(self):
        self.mock_svc.check_auth.return_value = {'valid': False, 'message': 'nlm login 필요'}
        resp = self.client.post('/api/notebooklm/generate',
                                data=json.dumps({
                                    'type': 'audio',
                                    'url': 'https://youtube.com/watch?v=test',
                                    'source_text': '자막'
                                }),
                                content_type='application/json')
        self.assertEqual(resp.status_code, 424)
        self.assertEqual(resp.get_json()['code'], 'NOTEBOOKLM_AUTH_REQUIRED')

    def test_status_endpoint(self):
        self.mock_svc.check_status.return_value = {'status': 'completed', 'type': 'audio'}
        resp = self.client.get('/api/notebooklm/status/test-id')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['status'], 'completed')
        self.mock_svc.check_status.assert_called_once_with('test-id', user_id=None)

    def test_authenticated_user_id_is_forwarded_for_ownership_check(self):
        self.mock_svc.check_status.return_value = {'status': 'completed', 'type': 'audio'}

        def validate_token(_token):
            g.user_id = 'user-a'
            return {'valid': True, 'error': None, 'code': None}

        with (
            patch(
                'src.contexts.identity.interface.auth_decorators.is_supabase_enabled',
                return_value=True,
            ),
            patch(
                'src.contexts.identity.interface.auth_decorators._validate_token',
                side_effect=validate_token,
            ),
        ):
            resp = self.client.get(
                '/api/notebooklm/status/artifact-a',
                headers={'Authorization': 'Bearer test-token'},
            )

        self.assertEqual(resp.status_code, 200)
        self.mock_svc.check_status.assert_called_once_with(
            'artifact-a',
            user_id='user-a',
        )

    def test_download_error_when_not_ready(self):
        self.mock_svc.download.side_effect = RuntimeError('아직 완료되지 않은 artifact입니다.')
        resp = self.client.get('/api/notebooklm/download/test-id')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('완료되지 않은', resp.get_json()['error'])

    def test_download_returns_not_found_for_unowned_artifact(self):
        self.mock_svc.download.side_effect = RuntimeError('artifact를 찾을 수 없습니다.')

        resp = self.client.get('/api/notebooklm/download/other-users-id')

        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.get_json()['error'], 'artifact를 찾을 수 없습니다.')


if __name__ == '__main__':
    unittest.main()
