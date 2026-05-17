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
