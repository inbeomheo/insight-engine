"""Slack Webhook Service 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.integrations.slack_service import SlackService


class TestSlackService(unittest.TestCase):

    def test_init_default_url(self):
        with patch('services.integrations.slack_service.SLACK_WEBHOOK_URL', 'https://hooks.slack.com/services/T/B/X'):
            svc = SlackService()
            self.assertEqual(svc.webhook_url, 'https://hooks.slack.com/services/T/B/X')

    def test_init_custom_url(self):
        svc = SlackService(webhook_url='https://custom/webhook')
        self.assertEqual(svc.webhook_url, 'https://custom/webhook')

    def test_is_enabled_true(self):
        svc = SlackService(webhook_url='https://hooks.slack.com/services/T/B/X')
        self.assertTrue(svc.is_enabled())

    def test_is_enabled_false(self):
        svc = SlackService(webhook_url='')
        self.assertFalse(svc.is_enabled())

    def test_send_disabled(self):
        svc = SlackService(webhook_url='')
        result = svc.send('hello')
        self.assertFalse(result['ok'])

    @patch('services.integrations.slack_service.requests.post')
    def test_send_success(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        svc = SlackService(webhook_url='https://hooks.slack.com/services/T/B/X')
        result = svc.send('테스트 메시지')
        self.assertTrue(result['ok'])
        payload = mock_post.call_args[1]['json']
        self.assertEqual(payload['text'], '테스트 메시지')

    @patch('services.integrations.slack_service.requests.post')
    def test_send_with_channel(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        svc = SlackService(webhook_url='https://hooks.slack.com/services/T/B/X')
        svc.send('msg', channel='#general')
        payload = mock_post.call_args[1]['json']
        self.assertEqual(payload['channel'], '#general')

    @patch('services.integrations.slack_service.requests.post')
    def test_send_failure_status(self, mock_post):
        mock_post.return_value = MagicMock(status_code=403, text='Forbidden')
        svc = SlackService(webhook_url='https://hooks.slack.com/services/T/B/X')
        result = svc.send('test')
        self.assertFalse(result['ok'])
        self.assertEqual(result['status'], 403)

    @patch('services.integrations.slack_service.requests.post')
    def test_send_exception(self, mock_post):
        mock_post.side_effect = Exception('Timeout')
        svc = SlackService(webhook_url='https://hooks.slack.com/services/T/B/X')
        result = svc.send('test')
        self.assertFalse(result['ok'])
        self.assertIn('error', result)

    def test_send_blocks_disabled(self):
        svc = SlackService(webhook_url='')
        result = svc.send_blocks([{'type': 'section'}])
        self.assertFalse(result['ok'])

    @patch('services.integrations.slack_service.requests.post')
    def test_send_blocks_success(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        svc = SlackService(webhook_url='https://hooks.slack.com/services/T/B/X')
        blocks = [{'type': 'section', 'text': {'type': 'mrkdwn', 'text': 'hi'}}]
        result = svc.send_blocks(blocks, text='fallback')
        self.assertTrue(result['ok'])
        payload = mock_post.call_args[1]['json']
        self.assertEqual(payload['blocks'], blocks)
        self.assertEqual(payload['text'], 'fallback')

    @patch('services.integrations.slack_service.requests.post')
    def test_notify_generation_complete(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        svc = SlackService(webhook_url='https://hooks.slack.com/services/T/B/X')
        result = svc.notify_generation_complete('글제목', 'blog_seo', 'gemini', 1500)
        self.assertTrue(result['ok'])

    @patch('services.integrations.slack_service.requests.post')
    def test_notify_anomaly(self, mock_post):
        mock_post.return_value = MagicMock(status_code=200)
        svc = SlackService(webhook_url='https://hooks.slack.com/services/T/B/X')
        result = svc.notify_anomaly('latency', 5.2, 3.1)
        self.assertTrue(result['ok'])


if __name__ == '__main__':
    unittest.main()
