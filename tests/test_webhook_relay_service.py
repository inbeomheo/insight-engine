"""webhook_relay_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.platform.webhook_relay_service import WebhookRelayService


class TestWebhookRelayService(unittest.TestCase):
    """다중 웹훅 릴레이 서비스 테스트"""

    def setUp(self):
        self.svc = WebhookRelayService()

    def test_empty_urls(self):
        """빈 URL 목록"""
        result = self.svc.send_all([], {'event': 'test'})
        self.assertEqual(result['total'], 0)
        self.assertEqual(result['results'], [])

    @patch('socket.getaddrinfo')
    @patch('services.platform.webhook_relay_service.requests.post')
    def test_success(self, mock_post, mock_getaddrinfo):
        """전송 성공"""
        mock_getaddrinfo.return_value = [(2, 1, 6, '', ('93.184.216.34', 443))]
        mock_post.return_value = MagicMock(status_code=200)

        result = self.svc.send_all(['https://hook.example.com'], {'data': 1})
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['success'], 1)
        self.assertEqual(result['failed'], 0)
        self.assertFalse(mock_post.call_args.kwargs['allow_redirects'])

    @patch('socket.getaddrinfo')
    @patch('services.platform.webhook_relay_service.requests.post')
    def test_failure(self, mock_post, mock_getaddrinfo):
        """전송 실패"""
        mock_getaddrinfo.return_value = [(2, 1, 6, '', ('93.184.216.34', 443))]
        mock_post.return_value = MagicMock(status_code=404)
        result = self.svc.send_all(['https://hook.example.com'], {'data': 1})
        self.assertEqual(result['failed'], 1)
        self.assertFalse(result['results'][0]['success'])

    @patch('socket.getaddrinfo')
    @patch('services.platform.webhook_relay_service.requests.post')
    def test_multiple_urls(self, mock_post, mock_getaddrinfo):
        """다중 URL 전송"""
        mock_getaddrinfo.return_value = [(2, 1, 6, '', ('93.184.216.34', 443))]
        mock_post.return_value = MagicMock(status_code=200)

        urls = [f'https://hook{i}.example.com' for i in range(5)]
        result = self.svc.send_all(urls, {'data': 1})
        self.assertEqual(result['total'], 5)
        self.assertEqual(result['success'], 5)

    @patch('socket.getaddrinfo')
    @patch('services.platform.webhook_relay_service.requests.post')
    def test_relay_content_generated(self, mock_post, mock_getaddrinfo):
        """콘텐츠 생성 이벤트 릴레이"""
        mock_getaddrinfo.return_value = [(2, 1, 6, '', ('93.184.216.34', 443))]
        mock_post.return_value = MagicMock(status_code=200)

        result = self.svc.relay_content_generated(
            ['https://hook.example.com'], '제목', '내용', 'blog_seo'
        )
        self.assertEqual(result['success'], 1)

    @patch('socket.getaddrinfo')
    @patch('services.platform.webhook_relay_service.requests.post')
    def test_connection_error(self, mock_post, mock_getaddrinfo):
        """연결 오류"""
        mock_getaddrinfo.return_value = [(2, 1, 6, '', ('93.184.216.34', 443))]
        mock_post.side_effect = ConnectionError('refused')
        result = self.svc.send_all(['https://hook.example.com'], {'data': 1})
        self.assertEqual(result['failed'], 1)

    @patch('services.platform.webhook_relay_service.requests.post')
    def test_blocks_unsafe_url_without_posting(self, mock_post):
        """unsafe URL은 HTTP 요청 없이 차단"""
        result = self.svc.send_all(['https://169.254.169.254/latest/meta-data/'], {'data': 1})

        self.assertEqual(result['failed'], 1)
        self.assertIn('안전하지 않아 차단', result['results'][0]['error'])
        mock_post.assert_not_called()

    @patch.dict('os.environ', {'FLASK_ENV': 'production'})
    @patch('services.platform.webhook_relay_service.requests.post')
    def test_blocks_plain_http_in_production(self, mock_post):
        """production에서는 HTTP relay URL을 차단"""
        result = self.svc.send_all(['http://example.com/hook'], {'data': 1})

        self.assertEqual(result['failed'], 1)
        self.assertIn('HTTPS', result['results'][0]['error'])
        mock_post.assert_not_called()

    @patch('socket.getaddrinfo')
    @patch('services.platform.webhook_relay_service.requests.post')
    def test_blocks_redirect_response(self, mock_post, mock_getaddrinfo):
        """redirect 응답은 따라가지 않고 실패 처리"""
        mock_getaddrinfo.return_value = [(2, 1, 6, '', ('93.184.216.34', 443))]
        mock_post.return_value = MagicMock(status_code=302)

        result = self.svc.send_all(['https://hook.example.com'], {'data': 1})

        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['results'][0]['status'], 302)
        self.assertFalse(mock_post.call_args.kwargs['allow_redirects'])


if __name__ == '__main__':
    unittest.main()
