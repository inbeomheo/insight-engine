"""Readiness probe `/ready` 엔드포인트 테스트"""
import unittest
from unittest.mock import patch, MagicMock


class TestReadyEndpoint(unittest.TestCase):
    """`/ready`는 의존성 상태를 종합하여 200 또는 503을 반환"""

    def _get_client(self):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        return app.test_client()

    @patch.dict('os.environ', {'REDIS_URL': '', 'RAG_ENABLED': 'false', 'RUN_SCHEDULER': '0'}, clear=False)
    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_ready_minimal_dev_env(self, _mock_sb):
        """Redis/Supabase/RAG 비활성 환경 → 200 OK"""
        client = self._get_client()
        resp = client.get('/ready')
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data['ready'])
        self.assertEqual(data['checks']['redis'], 'skipped (REDIS_URL unset)')
        self.assertEqual(data['checks']['supabase'], 'disabled')
        self.assertEqual(data['checks']['chroma_db'], 'disabled')

    @patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:9999/0', 'RAG_ENABLED': 'false', 'RUN_SCHEDULER': '0'}, clear=False)
    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_ready_fails_when_redis_unreachable(self, _mock_sb):
        """Redis 설정됐는데 ping 실패 → 503"""
        client = self._get_client()
        resp = client.get('/ready')
        self.assertEqual(resp.status_code, 503)
        data = resp.get_json()
        self.assertFalse(data['ready'])
        self.assertIn('fail', data['checks']['redis'])

    @patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379/0', 'RAG_ENABLED': 'false', 'RUN_SCHEDULER': '0'}, clear=False)
    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_ready_when_redis_reachable(self, _mock_sb):
        """Redis ping 성공 시 200 (모의) — redis 미설치 환경은 skip"""
        try:
            import redis  # noqa: F401
        except ImportError:
            self.skipTest('redis 패키지가 설치되어 있지 않음')
        with patch('redis.from_url') as mock_from_url:
            fake_client = MagicMock()
            fake_client.ping.return_value = True
            mock_from_url.return_value = fake_client
            client = self._get_client()
            resp = client.get('/ready')
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.get_json()['checks']['redis'], 'ok')

    @patch.dict('os.environ', {'REDIS_URL': '', 'RAG_ENABLED': 'true', 'CHROMA_DB_PATH': '/nonexistent/path/xyzz', 'RUN_SCHEDULER': '0'}, clear=False)
    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_ready_fails_when_chroma_path_missing(self, _mock_sb):
        """RAG_ENABLED이면서 ChromaDB 경로 없으면 503"""
        client = self._get_client()
        resp = client.get('/ready')
        self.assertEqual(resp.status_code, 503)
        self.assertIn('fail', resp.get_json()['checks']['chroma_db'])


if __name__ == '__main__':
    unittest.main()
