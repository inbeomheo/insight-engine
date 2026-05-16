"""routes/marketplace_routes — 마켓플레이스 라우트 단위 테스트

marketplace_service를 모의하여 각 엔드포인트의 상태 코드/응답 검증.
인증 라우트는 Supabase 비활성 모드(로컬)에서 우회되므로 _service만 모의하면 됨.
"""
import unittest
from unittest.mock import patch, MagicMock

from flask import Flask

from routes.marketplace_routes import marketplace_bp


def _build_client():
    app = Flask(__name__)
    app.register_blueprint(marketplace_bp)
    app.config['TESTING'] = True
    return app.test_client()


class TestListTemplates(unittest.TestCase):

    def test_returns_list(self):
        svc = MagicMock()
        svc.list_templates.return_value = [
            {'id': 't1', 'title': '템플릿 1'},
            {'id': 't2', 'title': '템플릿 2'},
        ]
        with patch('services.platform.marketplace_service.marketplace_service', svc):
            client = _build_client()
            resp = client.get('/api/marketplace')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()['templates']), 2)

    def test_passes_query_filter(self):
        svc = MagicMock()
        svc.list_templates.return_value = []
        with patch('services.platform.marketplace_service.marketplace_service', svc):
            client = _build_client()
            client.get('/api/marketplace?category=seo&q=블로그')
        svc.list_templates.assert_called_once_with(category='seo', query='블로그')


class TestGetTemplate(unittest.TestCase):

    def test_found_returns_200(self):
        svc = MagicMock()
        svc.get_template.return_value = {'id': 't1', 'title': 'T'}
        with patch('services.platform.marketplace_service.marketplace_service', svc):
            client = _build_client()
            resp = client.get('/api/marketplace/t1')
        self.assertEqual(resp.status_code, 200)

    def test_not_found_returns_404(self):
        svc = MagicMock()
        svc.get_template.return_value = None
        with patch('services.platform.marketplace_service.marketplace_service', svc):
            client = _build_client()
            resp = client.get('/api/marketplace/nope')
        self.assertEqual(resp.status_code, 404)


class TestPublishTemplate(unittest.TestCase):

    def test_success_returns_201(self):
        svc = MagicMock()
        svc.publish_template.return_value = {'id': 'new-id', 'title': 'T'}
        with patch('services.platform.marketplace_service.marketplace_service', svc):
            client = _build_client()
            resp = client.post('/api/marketplace', json={
                'title': 'T', 'description': 'D', 'prompt_text': 'P',
            })
        self.assertEqual(resp.status_code, 201)

    def test_service_error_returns_400(self):
        svc = MagicMock()
        svc.publish_template.return_value = {'error': '입력 검증 실패'}
        with patch('services.platform.marketplace_service.marketplace_service', svc):
            client = _build_client()
            resp = client.post('/api/marketplace', json={'title': 'T'})
        self.assertEqual(resp.status_code, 400)

    def test_unexpected_exception_returns_500(self):
        svc = MagicMock()
        svc.publish_template.side_effect = RuntimeError('DB down')
        with patch('services.platform.marketplace_service.marketplace_service', svc):
            client = _build_client()
            resp = client.post('/api/marketplace', json={'title': 'T'})
        self.assertEqual(resp.status_code, 500)
        # 내부 정보(DB down) 노출 안 됨
        self.assertNotIn('DB down', resp.get_json()['error'])


class TestDownloadTemplate(unittest.TestCase):

    def test_success(self):
        svc = MagicMock()
        svc.download_template.return_value = {'success': True, 'content': 'prompt'}
        with patch('services.platform.marketplace_service.marketplace_service', svc):
            client = _build_client()
            resp = client.post('/api/marketplace/t1/download')
        self.assertEqual(resp.status_code, 200)

    def test_service_error_returns_404(self):
        svc = MagicMock()
        svc.download_template.return_value = {'error': '템플릿 없음'}
        with patch('services.platform.marketplace_service.marketplace_service', svc):
            client = _build_client()
            resp = client.post('/api/marketplace/nope/download')
        self.assertEqual(resp.status_code, 404)


class TestRateTemplate(unittest.TestCase):

    def test_success(self):
        svc = MagicMock()
        svc.rate_template.return_value = {'success': True, 'avg_rating': 4.5}
        with patch('services.platform.marketplace_service.marketplace_service', svc):
            client = _build_client()
            resp = client.post('/api/marketplace/t1/rate', json={'rating': 5.0})
        self.assertEqual(resp.status_code, 200)

    def test_service_error_returns_400(self):
        svc = MagicMock()
        svc.rate_template.return_value = {'error': '평점 범위 초과'}
        with patch('services.platform.marketplace_service.marketplace_service', svc):
            client = _build_client()
            resp = client.post('/api/marketplace/t1/rate', json={'rating': 10})
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
