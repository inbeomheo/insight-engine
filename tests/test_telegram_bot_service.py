"""Telegram Bot Service 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.integrations.telegram_bot_service import TelegramBotService


class TestTelegramBotService(unittest.TestCase):

    def setUp(self):
        self.svc = TelegramBotService()
        self.svc.bot_token = ''

    def test_is_configured_false(self):
        self.assertFalse(self.svc.is_configured)

    def test_is_configured_true(self):
        self.svc.bot_token = '123:ABCdef'
        self.assertTrue(self.svc.is_configured)

    def test_api_url(self):
        self.svc.bot_token = '123:ABCdef'
        self.assertEqual(self.svc.api_url, 'https://api.telegram.org/bot123:ABCdef')

    def test_handle_update_no_message(self):
        result = self.svc.handle_update({})
        self.assertTrue(result['ok'])

    def test_handle_start_command(self):
        result = self.svc.handle_update({
            'message': {
                'text': '/start',
                'chat': {'id': 12345},
            },
        })
        self.assertTrue(result['ok'])

    def test_handle_styles_command(self):
        result = self.svc.handle_update({
            'message': {
                'text': '/styles',
                'chat': {'id': 12345},
            },
        })
        self.assertTrue(result['ok'])

    def test_handle_generate_valid_url(self):
        result = self.svc.handle_update({
            'message': {
                'text': '/generate https://www.youtube.com/watch?v=abc123 summary',
                'chat': {'id': 12345},
            },
        })
        self.assertTrue(result['ok'])
        self.assertEqual(result['url'], 'https://www.youtube.com/watch?v=abc123')
        self.assertEqual(result['style'], 'summary')

    def test_handle_generate_default_style(self):
        result = self.svc.handle_update({
            'message': {
                'text': '/generate https://youtu.be/abc123',
                'chat': {'id': 12345},
            },
        })
        self.assertEqual(result['style'], 'blog_seo')

    def test_handle_generate_invalid_url(self):
        result = self.svc.handle_update({
            'message': {
                'text': '/generate https://example.com',
                'chat': {'id': 12345},
            },
        })
        self.assertTrue(result['ok'])
        self.assertNotIn('url', result)

    def test_handle_youtube_url_in_text(self):
        result = self.svc.handle_update({
            'message': {
                'text': '이 영상 봐봐 https://youtube.com/watch?v=xyz789',
                'chat': {'id': 12345},
            },
        })
        self.assertTrue(result['ok'])

    def test_handle_plain_text(self):
        result = self.svc.handle_update({
            'message': {
                'text': '안녕하세요',
                'chat': {'id': 12345},
            },
        })
        self.assertTrue(result['ok'])

    def test_handle_callback_query_generate(self):
        result = self.svc.handle_callback_query({
            'id': 'cb_123',
            'data': 'gen:blog_seo:https://youtube.com/watch?v=abc',
            'message': {'chat': {'id': 12345}},
        })
        self.assertTrue(result['ok'])
        self.assertEqual(result['style'], 'blog_seo')

    def test_handle_callback_query_unknown(self):
        result = self.svc.handle_callback_query({
            'id': 'cb_123',
            'data': 'unknown_action',
        })
        self.assertTrue(result['ok'])

    def test_handle_no_chat_id(self):
        result = self.svc.handle_update({
            'message': {'text': 'hello', 'chat': {}},
        })
        self.assertTrue(result['ok'])

    def test_set_webhook_no_token(self):
        self.svc.bot_token = ''
        self.assertFalse(self.svc.set_webhook('https://example.com/webhook'))

    @patch('services.integrations.telegram_bot_service.requests.post')
    def test_set_webhook_includes_secret_token_when_configured(self, mock_post):
        self.svc.bot_token = '123:ABCdef'
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        with patch.dict(
            'os.environ',
            {'TELEGRAM_WEBHOOK_SECRET': 'telegram-secret-1234567890abcdef'},
        ):
            self.assertTrue(self.svc.set_webhook('https://example.com/webhook'))

        payload = mock_post.call_args.kwargs['json']
        self.assertEqual(payload['url'], 'https://example.com/webhook')
        self.assertEqual(payload['secret_token'], 'telegram-secret-1234567890abcdef')
        self.assertFalse(mock_post.call_args.kwargs['allow_redirects'])

    @patch('services.integrations.telegram_bot_service.requests.post')
    def test_set_webhook_blocks_redirect_response(self, mock_post):
        self.svc.bot_token = '123:ABCdef'
        mock_post.return_value = MagicMock(status_code=302)

        self.assertFalse(self.svc.set_webhook('https://example.com/webhook'))
        self.assertFalse(mock_post.call_args.kwargs['allow_redirects'])

    @patch('services.integrations.telegram_bot_service.requests.post')
    def test_send_message_disables_redirects(self, mock_post):
        self.svc.bot_token = '123:ABCdef'
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {'ok': True}
        mock_post.return_value = mock_resp

        result = self.svc._send_message(12345, 'hello')

        self.assertTrue(result['ok'])
        self.assertFalse(mock_post.call_args.kwargs['allow_redirects'])

    def test_send_message_no_token(self):
        self.svc.bot_token = ''
        result = self.svc._send_message(12345, 'hello')
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
