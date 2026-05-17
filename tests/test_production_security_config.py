"""프로덕션 보안 설정 fail-fast 테스트."""
import os
import unittest
from unittest.mock import patch


class TestProductionSecurityConfig(unittest.TestCase):
    def _production_env(self, **overrides):
        env = {
            'FLASK_ENV': 'production',
            'REDIS_URL': 'redis://localhost:6379/0',
            'RUN_SCHEDULER': '0',
            'SUPABASE_ENABLED': 'false',
            'CORS_ORIGINS': 'https://app.example.com',
            'METRICS_AUTH_TOKEN': 'metrics-secret',
            'ENCRYPTION_SECRET': 'x' * 32,
        }
        env.update(overrides)
        return patch.dict(os.environ, env, clear=False)

    def test_production_rejects_localhost_cors_origin(self):
        from app import create_app

        with self._production_env(CORS_ORIGINS='https://app.example.com,http://localhost:3000'):
            with self.assertRaises(RuntimeError) as ctx:
                create_app({'TESTING': True})

        self.assertIn('CORS_ORIGINS', str(ctx.exception))
        self.assertIn('localhost', str(ctx.exception))

    def test_production_rejects_wildcard_cors_origin(self):
        from app import create_app

        with self._production_env(CORS_ORIGINS='*'):
            with self.assertRaises(RuntimeError) as ctx:
                create_app({'TESTING': True})

        self.assertIn('CORS_ORIGINS', str(ctx.exception))

    def test_production_requires_metrics_auth_token(self):
        from app import create_app

        with self._production_env(METRICS_AUTH_TOKEN=''):
            with self.assertRaises(RuntimeError) as ctx:
                create_app({'TESTING': True})

        self.assertIn('METRICS_AUTH_TOKEN', str(ctx.exception))

    def test_production_requires_strong_encryption_secret(self):
        from app import create_app

        with self._production_env(ENCRYPTION_SECRET='short'):
            with self.assertRaises(RuntimeError) as ctx:
                create_app({'TESTING': True})

        self.assertIn('ENCRYPTION_SECRET', str(ctx.exception))


    def test_production_default_csp_excludes_unsafe_script_sources(self):
        from app import create_app

        with self._production_env():
            os.environ.pop('CONTENT_SECURITY_POLICY', None)
            app = create_app({'TESTING': True})
            response = app.test_client().get('/health')

        csp = response.headers['Content-Security-Policy']
        self.assertIn('script-src', csp)
        self.assertNotIn("'unsafe-inline'", csp)
        self.assertNotIn("'unsafe-eval'", csp)

    def test_production_rejects_unsafe_custom_csp(self):
        from app import create_app

        with self._production_env(
            CONTENT_SECURITY_POLICY="default-src 'self'; script-src 'self' 'unsafe-eval'"
        ):
            with self.assertRaises(RuntimeError) as ctx:
                create_app({'TESTING': True})

        self.assertIn('CONTENT_SECURITY_POLICY', str(ctx.exception))
        self.assertIn('unsafe-eval', str(ctx.exception))


    def test_security_headers_include_browser_isolation_defaults(self):
        from app import create_app

        with self._production_env():
            os.environ.pop('CONTENT_SECURITY_POLICY', None)
            app = create_app({'TESTING': True})
            response = app.test_client().get('/health', base_url='https://app.example.com')

        self.assertEqual(response.headers['Cross-Origin-Opener-Policy'], 'same-origin')
        self.assertEqual(response.headers['Cross-Origin-Resource-Policy'], 'same-origin')
        self.assertEqual(response.headers['X-Permitted-Cross-Domain-Policies'], 'none')
        hsts = response.headers['Strict-Transport-Security']
        self.assertIn('max-age=63072000', hsts)
        self.assertIn('includeSubDomains', hsts)
        self.assertIn('preload', hsts)

    def test_development_allows_localhost_cors_without_metrics_token(self):
        from app import create_app

        with patch.dict(os.environ, {
            'FLASK_ENV': 'development',
            'CORS_ORIGINS': 'http://localhost:3000',
            'METRICS_AUTH_TOKEN': '',
            'RUN_SCHEDULER': '0',
            'SUPABASE_ENABLED': 'false',
        }, clear=False):
            app = create_app({'TESTING': True})

        self.assertTrue(app.testing)


if __name__ == '__main__':
    unittest.main()
