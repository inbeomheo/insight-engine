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

    @patch('services.platform.webhook_relay_service.urllib.request.urlopen')
    def test_success(self, mock_urlopen):
        """전송 성공"""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.svc.send_all(['https://hook.example.com'], {'data': 1})
        self.assertEqual(result['total'], 1)
        self.assertEqual(result['success'], 1)
        self.assertEqual(result['failed'], 0)

    @patch('services.platform.webhook_relay_service.urllib.request.urlopen')
    def test_failure(self, mock_urlopen):
        """전송 실패"""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            'https://hook.example.com', 404, 'Not Found', {}, None
        )
        result = self.svc.send_all(['https://hook.example.com'], {'data': 1})
        self.assertEqual(result['failed'], 1)
        self.assertFalse(result['results'][0]['success'])

    @patch('services.platform.webhook_relay_service.urllib.request.urlopen')
    def test_multiple_urls(self, mock_urlopen):
        """다중 URL 전송"""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        urls = [f'https://hook{i}.example.com' for i in range(5)]
        result = self.svc.send_all(urls, {'data': 1})
        self.assertEqual(result['total'], 5)
        self.assertEqual(result['success'], 5)

    @patch('services.platform.webhook_relay_service.urllib.request.urlopen')
    def test_relay_content_generated(self, mock_urlopen):
        """콘텐츠 생성 이벤트 릴레이"""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = self.svc.relay_content_generated(
            ['https://hook.example.com'], '제목', '내용', 'blog_seo'
        )
        self.assertEqual(result['success'], 1)

    @patch('services.platform.webhook_relay_service.urllib.request.urlopen')
    def test_connection_error(self, mock_urlopen):
        """연결 오류"""
        mock_urlopen.side_effect = ConnectionError('refused')
        result = self.svc.send_all(['https://hook.example.com'], {'data': 1})
        self.assertEqual(result['failed'], 1)


if __name__ == '__main__':
    unittest.main()
