"""extensions.py — Flask Limiter 초기화 모듈 단위 테스트

핵심 동작:
- 프로덕션 환경 + REDIS_URL 미설정 → RuntimeError (fail-fast)
- 개발 환경 + REDIS_URL 미설정 → 인메모리 fallback + 경고
- REDIS_URL 설정 시 그대로 storage_uri 사용
- RATE_LIMIT_ENABLED env 로 전체 on/off

reimport를 위해 importlib.reload 사용.
"""
import importlib
import os
import unittest
from unittest.mock import patch


class TestExtensionsConfiguration(unittest.TestCase):

    def _reload_extensions(self):
        """환경변수 변경 후 모듈 재import"""
        import extensions
        return importlib.reload(extensions)

    def test_dev_mode_no_redis_falls_back_to_memory(self):
        with patch.dict(os.environ, {'FLASK_ENV': 'development'}, clear=False):
            # REDIS_URL 명시적 삭제
            os.environ.pop('REDIS_URL', None)
            ext = self._reload_extensions()
            self.assertEqual(ext._storage_uri, 'memory://')
            self.assertIsNotNone(ext.limiter)

    def test_prod_mode_no_redis_raises_runtime_error(self):
        with patch.dict(os.environ, {'FLASK_ENV': 'production'}, clear=False):
            os.environ.pop('REDIS_URL', None)
            with self.assertRaises(RuntimeError) as ctx:
                self._reload_extensions()
            self.assertIn('REDIS_URL', str(ctx.exception))

    def test_redis_url_set_uses_redis_storage(self):
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'REDIS_URL': 'redis://localhost:6379/0',
        }, clear=False):
            ext = self._reload_extensions()
            self.assertEqual(ext._storage_uri, 'redis://localhost:6379/0')

    def test_redis_url_strips_whitespace(self):
        with patch.dict(os.environ, {
            'FLASK_ENV': 'development',
            'REDIS_URL': '  redis://localhost:6379/0  ',
        }, clear=False):
            ext = self._reload_extensions()
            self.assertEqual(ext._storage_uri, 'redis://localhost:6379/0')

    def test_flask_env_case_insensitive(self):
        """FLASK_ENV=PRODUCTION (대문자) 도 production으로 인식"""
        with patch.dict(os.environ, {'FLASK_ENV': 'PRODUCTION'}, clear=False):
            os.environ.pop('REDIS_URL', None)
            with self.assertRaises(RuntimeError):
                self._reload_extensions()

    def test_rate_limit_enabled_default_true(self):
        """RATE_LIMIT_ENABLED 미설정 시 활성화"""
        with patch.dict(os.environ, {'FLASK_ENV': 'development'}, clear=False):
            os.environ.pop('REDIS_URL', None)
            os.environ.pop('RATE_LIMIT_ENABLED', None)
            ext = self._reload_extensions()
            self.assertTrue(ext.limiter.enabled)

    def test_rate_limit_disable_via_env(self):
        with patch.dict(os.environ, {
            'FLASK_ENV': 'development',
            'RATE_LIMIT_ENABLED': 'false',
        }, clear=False):
            os.environ.pop('REDIS_URL', None)
            ext = self._reload_extensions()
            self.assertFalse(ext.limiter.enabled)

    def test_testing_env_treated_as_non_prod(self):
        """FLASK_ENV=testing 일 때 REDIS_URL 없어도 통과 (인메모리)"""
        with patch.dict(os.environ, {'FLASK_ENV': 'testing'}, clear=False):
            os.environ.pop('REDIS_URL', None)
            ext = self._reload_extensions()
            self.assertEqual(ext._storage_uri, 'memory://')

    def tearDown(self):
        """다른 테스트에 영향 주지 않도록 환경 복원"""
        # 일반적으로 patch.dict가 복원하지만 reload 후 모듈 상태는 남으므로 다시 reload
        with patch.dict(os.environ, {'FLASK_ENV': 'testing'}, clear=False):
            os.environ.pop('REDIS_URL', None)
            try:
                self._reload_extensions()
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main()
