"""Discord Bot Service 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.integrations.discord_bot_service import (
    DiscordBotService,
    INTERACTION_PING, INTERACTION_APPLICATION_COMMAND,
    RESPONSE_PONG, RESPONSE_CHANNEL_MESSAGE,
)


class TestDiscordBotService(unittest.TestCase):

    def setUp(self):
        self.svc = DiscordBotService()
        self.svc.bot_token = ''
        self.svc.public_key = ''

    def test_is_configured_false(self):
        self.assertFalse(self.svc.is_configured)

    def test_is_configured_true(self):
        self.svc.bot_token = 'token'
        self.svc.public_key = 'pubkey'
        self.assertTrue(self.svc.is_configured)

    def test_handle_ping(self):
        result = self.svc.handle_interaction({'type': INTERACTION_PING})
        self.assertEqual(result['type'], RESPONSE_PONG)

    def test_handle_unknown_type(self):
        result = self.svc.handle_interaction({'type': 999})
        self.assertEqual(result['type'], RESPONSE_CHANNEL_MESSAGE)
        self.assertIn('알 수 없는', result['data']['content'])

    def test_generate_command_valid_url(self):
        payload = {
            'type': INTERACTION_APPLICATION_COMMAND,
            'data': {
                'name': 'generate',
                'options': [
                    {'name': 'url', 'value': 'https://www.youtube.com/watch?v=abc123'},
                    {'name': 'style', 'value': 'summary'},
                ],
            },
        }
        result = self.svc.handle_interaction(payload)
        self.assertEqual(result['type'], RESPONSE_CHANNEL_MESSAGE)
        self.assertIn('콘텐츠 생성을 요청', result['data']['content'])
        self.assertIn('summary', result['data']['content'])

    def test_generate_command_invalid_url(self):
        payload = {
            'type': INTERACTION_APPLICATION_COMMAND,
            'data': {
                'name': 'generate',
                'options': [{'name': 'url', 'value': 'https://example.com'}],
            },
        }
        result = self.svc.handle_interaction(payload)
        self.assertIn('YouTube URL', result['data']['content'])

    def test_generate_command_default_style(self):
        payload = {
            'type': INTERACTION_APPLICATION_COMMAND,
            'data': {
                'name': 'generate',
                'options': [
                    {'name': 'url', 'value': 'https://youtu.be/abc123'},
                ],
            },
        }
        result = self.svc.handle_interaction(payload)
        self.assertIn('blog_seo', result['data']['content'])

    def test_unknown_command(self):
        payload = {
            'type': INTERACTION_APPLICATION_COMMAND,
            'data': {'name': 'unknown_cmd', 'options': []},
        }
        result = self.svc.handle_interaction(payload)
        self.assertIn('알 수 없는 명령어', result['data']['content'])

    def test_verify_signature_no_public_key(self):
        self.svc.public_key = ''
        with patch.dict('os.environ', {'FLASK_ENV': 'development'}):
            self.assertTrue(self.svc.verify_signature(b'body', 'ts', 'sig'))

    def test_verify_signature_no_public_key_fails_closed_in_production(self):
        self.svc.public_key = ''
        with patch.dict('os.environ', {'FLASK_ENV': 'production'}):
            self.assertFalse(self.svc.verify_signature(b'body', 'ts', 'sig'))

    def test_register_commands_no_token(self):
        self.svc.bot_token = ''
        self.assertFalse(self.svc.register_commands('app_id'))

    @patch('services.integrations.discord_bot_service.requests.put')
    def test_register_commands_disables_redirects(self, mock_put):
        self.svc.bot_token = 'token'
        mock_put.return_value = MagicMock(status_code=200)

        self.assertTrue(self.svc.register_commands('app_id'))
        self.assertFalse(mock_put.call_args.kwargs['allow_redirects'])

    @patch('services.integrations.discord_bot_service.requests.put')
    def test_register_commands_blocks_redirect_response(self, mock_put):
        self.svc.bot_token = 'token'
        mock_put.return_value = MagicMock(status_code=302)

        self.assertFalse(self.svc.register_commands('app_id'))
        self.assertFalse(mock_put.call_args.kwargs['allow_redirects'])

    def test_youtu_be_short_url(self):
        payload = {
            'type': INTERACTION_APPLICATION_COMMAND,
            'data': {
                'name': 'generate',
                'options': [{'name': 'url', 'value': 'https://youtu.be/dQw4w9WgXcQ'}],
            },
        }
        result = self.svc.handle_interaction(payload)
        self.assertIn('콘텐츠 생성을 요청', result['data']['content'])


if __name__ == '__main__':
    unittest.main()
