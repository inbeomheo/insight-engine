"""관리자 라우트 권한 강제 검증

`@require_admin` 데코레이터가 인증된 일반 사용자에게는 403을 반환하고
관리자에게만 200을 반환하는지 검증.
"""
import unittest
from unittest.mock import patch, MagicMock


class TestRequireAdminDecorator(unittest.TestCase):
    """require_admin 데코레이터 동작 단위 테스트"""

    def test_local_mode_bypasses(self):
        """Supabase 비활성(로컬 모드) → 데코레이터 우회 통과 (개발 편의)"""
        from flask import Flask, jsonify
        from services.data.supabase_service import require_admin

        app = Flask(__name__)

        @app.route('/x')
        @require_admin
        def endpoint():
            return jsonify({'ok': True})

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=False):
            resp = app.test_client().get('/x')
        self.assertEqual(resp.status_code, 200)

    def test_no_token_returns_401(self):
        """Supabase 활성 + 토큰 없음 → 401"""
        from flask import Flask, jsonify
        from services.data.supabase_service import require_admin

        app = Flask(__name__)

        @app.route('/x')
        @require_admin
        def endpoint():
            return jsonify({'ok': True})

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=True):
            resp = app.test_client().get('/x')
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.get_json()['code'], 'AUTH_REQUIRED')

    def test_authenticated_non_admin_returns_403(self):
        """인증은 됐지만 관리자가 아님 → 403"""
        from flask import Flask, jsonify, g
        from services.data.supabase_service import require_admin

        app = Flask(__name__)

        @app.route('/x')
        @require_admin
        def endpoint():
            return jsonify({'ok': True})

        def _fake_validate(token):
            g.user_id = 'user-123'
            g.user_email = 'user@example.com'
            g.access_token = token
            return {'valid': True, 'error': None, 'code': None}

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=True), \
             patch('services.data.supabase_service._validate_token', side_effect=_fake_validate), \
             patch('services.data.supabase_service.is_admin', return_value=False):
            resp = app.test_client().get('/x', headers={'Authorization': 'Bearer faketoken'})
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(resp.get_json()['code'], 'ADMIN_REQUIRED')

    def test_admin_passes(self):
        """관리자 사용자 → 200 통과"""
        from flask import Flask, jsonify, g
        from services.data.supabase_service import require_admin

        app = Flask(__name__)

        @app.route('/x')
        @require_admin
        def endpoint():
            return jsonify({'ok': True})

        def _fake_validate(token):
            g.user_id = 'admin-1'
            g.user_email = 'admin@example.com'
            g.access_token = token
            return {'valid': True, 'error': None, 'code': None}

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=True), \
             patch('services.data.supabase_service._validate_token', side_effect=_fake_validate), \
             patch('services.data.supabase_service.is_admin', return_value=True):
            resp = app.test_client().get('/x', headers={'Authorization': 'Bearer admintoken'})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['ok'])


class TestAdminRoutesAreProtected(unittest.TestCase):
    """실제 라우트 등록 검증 — /api/admin/* 엔드포인트가 require_admin으로 보호됨"""

    SAMPLE_ADMIN_GET_ROUTES = [
        '/api/admin/dashboard',
        '/api/admin/dashboard/extended',
        '/api/admin/users',
        '/api/admin/costs',
        '/api/admin/audit-logs',
        '/api/admin/anomalies',
        '/api/admin/segments/counts',
    ]

    def test_admin_get_routes_reject_non_admin(self):
        """샘플 admin GET 라우트가 일반 사용자에게 403을 반환하는지"""
        from flask import g
        from app import create_app

        def _fake_validate(token):
            g.user_id = 'user-456'
            g.user_email = 'user@example.com'
            g.access_token = token
            return {'valid': True, 'error': None, 'code': None}

        with patch('services.data.supabase_service.is_supabase_enabled', return_value=True), \
             patch('services.data.supabase_service._validate_token', side_effect=_fake_validate), \
             patch('services.data.supabase_service.is_admin', return_value=False):
            app = create_app()
            app.config['TESTING'] = True
            client = app.test_client()
            for path in self.SAMPLE_ADMIN_GET_ROUTES:
                resp = client.get(
                    path,
                    headers={
                        'Authorization': 'Bearer fake',
                        'Origin': 'http://localhost:3000',
                    },
                )
                self.assertEqual(
                    resp.status_code, 403,
                    f"{path} 가 일반 사용자에게 403을 반환하지 않음 (실제 {resp.status_code})"
                )


if __name__ == '__main__':
    unittest.main()
