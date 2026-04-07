"""핵심 라우트 통합 테스트 (Flask test_client 기반)."""
import unittest
from unittest.mock import patch

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestHealthRoute(unittest.TestCase):
    """헬스체크 엔드포인트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_health_returns_200(self):
        resp = self.client.get('/health', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)


class TestCacheRouteAuth(unittest.TestCase):
    """캐시 삭제 엔드포인트 인증 테스트 (C-3)."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=True)
    def test_cache_delete_requires_auth(self, _mock_sb):
        """인증 없이 캐시 삭제 시 401 반환."""
        resp = self.client.delete('/api/cache',
                                  json={},
                                  headers=_HEADERS)
        self.assertEqual(resp.status_code, 401)


class TestFactCheckRouteAuth(unittest.TestCase):
    """팩트체크 엔드포인트 인증 테스트 (H-16)."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=True)
    def test_fact_check_requires_auth(self, _mock_sb):
        """인증 없이 팩트체크 시 401 반환."""
        resp = self.client.post('/api/fact-check',
                                json={'content': 'test'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 401)


class TestProvidersRoute(unittest.TestCase):
    """프로바이더 목록 엔드포인트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_providers_returns_200(self, _mock_sb):
        resp = self.client.get('/api/providers', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertIn('providers', data)


class TestExportRoutes(unittest.TestCase):
    """내보내기 엔드포인트 기본 검증."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_docx_export_requires_content(self):
        """콘텐츠 없이 DOCX 내보내기 시 400 반환."""
        resp = self.client.post('/api/export/docx',
                                json={},
                                headers=_HEADERS)
        self.assertIn(resp.status_code, [400, 422])


if __name__ == '__main__':
    unittest.main()
