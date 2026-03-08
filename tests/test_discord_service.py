"""Discord Webhook Service 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.integrations.discord_service import DiscordService


class TestDiscordService(unittest.TestCase):

    def test_init_default_url(self):
        with patch('services.integrations.discord_service.DISCORD_WEBHOOK_URL', 'https://discord.com/api/webhooks/123'):
            svc = DiscordService()
            self.assertEqual(svc.webhook_url, 'https://discord.com/api/webhooks/123')

    def test_init_custom_url(self):
        svc = DiscordService(webhook_url='https://custom/webhook')
        self.assertEqual(svc.webhook_url, 'https://custom/webhook')

    def test_is_enabled_true(self):
        svc = DiscordService(webhook_url='https://discord.com/api/webhooks/123')
        self.assertTrue(svc.is_enabled())

    def test_is_enabled_false(self):
        svc = DiscordService(webhook_url='')
        self.assertFalse(svc.is_enabled())

    def test_send_disabled(self):
        svc = DiscordService(webhook_url='')
        result = svc.send('hello')
        self.assertFalse(result['ok'])
        self.assertIn('reason', result)

    @patch('services.integrations.discord_service.requests.post')
    def test_send_success(self, mock_post):
        mock_post.return_value = MagicMock(status_code=204)
        svc = DiscordService(webhook_url='https://discord.com/api/webhooks/123')
        result = svc.send('테스트 메시지')
        self.assertTrue(result['ok'])
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        self.assertEqual(call_kwargs[1]['json']['content'], '테스트 메시지')

    @patch('services.integrations.discord_service.requests.post')
    def test_send_failure_status(self, mock_post):
        mock_post.return_value = MagicMock(status_code=400, text='Bad Request')
        svc = DiscordService(webhook_url='https://discord.com/api/webhooks/123')
        result = svc.send('test')
        self.assertFalse(result['ok'])
        self.assertEqual(result['status'], 400)

    @patch('services.integrations.discord_service.requests.post')
    def test_send_exception(self, mock_post):
        mock_post.side_effect = Exception('Connection error')
        svc = DiscordService(webhook_url='https://discord.com/api/webhooks/123')
        result = svc.send('test')
        self.assertFalse(result['ok'])
        self.assertIn('error', result)

    def test_send_embed_disabled(self):
        svc = DiscordService(webhook_url='')
        result = svc.send_embed('제목', '설명')
        self.assertFalse(result['ok'])

    @patch('services.integrations.discord_service.requests.post')
    def test_send_embed_success(self, mock_post):
        mock_post.return_value = MagicMock(status_code=204)
        svc = DiscordService(webhook_url='https://discord.com/api/webhooks/123')
        result = svc.send_embed('제목', '설명', fields=[{'name': 'k', 'value': 'v'}])
        self.assertTrue(result['ok'])
        payload = mock_post.call_args[1]['json']
        self.assertEqual(len(payload['embeds']), 1)
        self.assertEqual(payload['embeds'][0]['title'], '제목')

    @patch('services.integrations.discord_service.requests.post')
    def test_notify_generation_complete(self, mock_post):
        mock_post.return_value = MagicMock(status_code=204)
        svc = DiscordService(webhook_url='https://discord.com/api/webhooks/123')
        result = svc.notify_generation_complete('글제목', 'blog_seo', 'gemini', 1500)
        self.assertTrue(result['ok'])

    @patch('services.integrations.discord_service.requests.post')
    def test_notify_anomaly(self, mock_post):
        mock_post.return_value = MagicMock(status_code=204)
        svc = DiscordService(webhook_url='https://discord.com/api/webhooks/123')
        result = svc.notify_anomaly('latency', 5.2, 3.1)
        self.assertTrue(result['ok'])


if __name__ == '__main__':
    unittest.main()
