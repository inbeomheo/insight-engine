"""
ZapierWebhookService 단위 테스트 (F6-22)
"""
import unittest
from unittest.mock import patch, MagicMock
from services.zapier_webhook_service import ZapierWebhookService, SUPPORTED_EVENTS


class TestZapierWebhookService(unittest.TestCase):

    def setUp(self):
        self.svc = ZapierWebhookService()

    def test_register_valid_event(self):
        result = self.svc.register('content.generated', 'https://hooks.zapier.com/hooks/catch/12345')
        self.assertTrue(result)

    def test_register_invalid_event(self):
        result = self.svc.register('unknown.event', 'https://hooks.zapier.com/hooks/catch/12345')
        self.assertFalse(result)

    def test_register_invalid_url(self):
        result = self.svc.register('content.generated', 'http://localhost/malicious')
        self.assertFalse(result)

    def test_get_supported_events(self):
        events = self.svc.get_supported_events()
        self.assertIn('content.generated', events)
        self.assertIn('anomaly.detected', events)
        self.assertEqual(events, SUPPORTED_EVENTS)

    def test_list_registered(self):
        self.svc.register('content.generated', 'https://hooks.zapier.com/hooks/catch/abc123xyz')
        listed = self.svc.list_registered()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]['event'], 'content.generated')
        self.assertTrue(listed[0]['enabled'])

    def test_emit_calls_webhook(self):
        self.svc.register('content.generated', 'https://hooks.zapier.com/hooks/catch/abc')
        with patch.object(self.svc._webhooks['content.generated'], 'send') as mock_send:
            self.svc.emit_content_generated('제목', 'blog_seo', 'gemini', 1000, 0.001)
            mock_send.assert_called_once()
            call_args = mock_send.call_args
            self.assertEqual(call_args[0][0], 'content.generated')

    def test_fallback_used_when_no_specific(self):
        self.svc.register_fallback('https://hooks.zapier.com/hooks/catch/fallback')
        with patch.object(self.svc._fallback, 'send') as mock_send:
            self.svc.emit('content.failed', {'error': 'test'})
            mock_send.assert_called_once()

    def test_no_emit_when_not_registered(self):
        """등록 안 된 이벤트는 조용히 무시"""
        # 예외 없이 실행되면 성공
        self.svc.emit('content.generated', {'title': 'test'})

    def test_register_fallback_invalid_url(self):
        # 사설 IP는 차단되어야 함
        result = self.svc.register_fallback('http://192.168.1.1/path')
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()
