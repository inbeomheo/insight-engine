"""Slack Bot Service 테스트"""
import hashlib
import hmac
import time
import unittest
from unittest.mock import patch, MagicMock

from services.integrations.slack_bot_service import SlackBotService


class TestSlackBotService(unittest.TestCase):

    def setUp(self):
        self.svc = SlackBotService()
        self.svc.bot_token = ''
        self.svc.signing_secret = ''

    def test_is_configured_false(self):
        self.assertFalse(self.svc.is_configured)

    def test_is_configured_true(self):
        self.svc.bot_token = 'xoxb-token'
        self.svc.signing_secret = 'secret'
        self.assertTrue(self.svc.is_configured)

    def test_verify_signature_no_secret(self):
        self.svc.signing_secret = ''
        with patch.dict('os.environ', {'FLASK_ENV': 'development'}):
            self.assertTrue(self.svc.verify_signature(b'body', 'ts', 'sig'))

    def test_verify_signature_no_secret_fails_closed_in_production(self):
        self.svc.signing_secret = ''
        with patch.dict('os.environ', {'FLASK_ENV': 'production'}):
            self.assertFalse(self.svc.verify_signature(b'body', 'ts', 'sig'))

    def test_verify_signature_valid(self):
        self.svc.signing_secret = 'test_secret'
        ts = str(int(time.time()))
        body = b'test_body'
        base_str = f'v0:{ts}:{body.decode("utf-8")}'
        expected = 'v0=' + hmac.new(
            b'test_secret', base_str.encode(), hashlib.sha256
        ).hexdigest()
        self.assertTrue(self.svc.verify_signature(body, ts, expected))

    def test_verify_signature_invalid(self):
        self.svc.signing_secret = 'test_secret'
        ts = str(int(time.time()))
        self.assertFalse(self.svc.verify_signature(b'body', ts, 'v0=bad'))

    def test_verify_signature_replay_attack(self):
        self.svc.signing_secret = 'test_secret'
        old_ts = str(int(time.time()) - 600)
        self.assertFalse(self.svc.verify_signature(b'body', old_ts, 'v0=sig'))

    def test_verify_signature_invalid_timestamp(self):
        self.svc.signing_secret = 'test_secret'
        self.assertFalse(self.svc.verify_signature(b'body', 'not_a_number', 'v0=sig'))

    def test_handle_url_verification(self):
        result = self.svc.handle_event({
            'type': 'url_verification',
            'challenge': 'abc123',
        })
        self.assertEqual(result['challenge'], 'abc123')

    def test_handle_message_with_youtube_url(self):
        result = self.svc.handle_event({
            'type': 'event_callback',
            'event': {
                'type': 'message',
                'text': 'https://www.youtube.com/watch?v=abc123 이거 봐',
                'channel': 'C123',
            },
        })
        self.assertEqual(result['url'], 'https://www.youtube.com/watch?v=abc123')

    def test_handle_message_no_url(self):
        result = self.svc.handle_event({
            'type': 'event_callback',
            'event': {
                'type': 'message',
                'text': '안녕하세요',
                'channel': 'C123',
            },
        })
        self.assertTrue(result['ok'])
        self.assertNotIn('url', result)

    def test_handle_bot_message_ignored(self):
        result = self.svc.handle_event({
            'type': 'event_callback',
            'event': {
                'type': 'message',
                'text': 'https://youtube.com/watch?v=abc',
                'bot_id': 'B123',
                'channel': 'C123',
            },
        })
        self.assertTrue(result['ok'])
        self.assertNotIn('url', result)

    def test_handle_unknown_event(self):
        result = self.svc.handle_event({
            'type': 'event_callback',
            'event': {'type': 'app_mention'},
        })
        self.assertTrue(result['ok'])

    def test_send_message_no_token(self):
        self.svc.bot_token = ''
        result = self.svc._send_message('C123', 'hello')
        self.assertIsNone(result)

    @patch('services.integrations.slack_bot_service.requests.post')
    def test_send_message_disables_redirects(self, mock_post):
        self.svc.bot_token = 'xoxb-token'
        mock_resp = MagicMock(status_code=200)
        mock_resp.json.return_value = {'ok': True}
        mock_post.return_value = mock_resp

        result = self.svc._send_message('C123', 'hello')

        self.assertTrue(result['ok'])
        self.assertFalse(mock_post.call_args.kwargs['allow_redirects'])

    @patch('services.integrations.slack_bot_service.requests.post')
    def test_send_message_blocks_redirect_response(self, mock_post):
        self.svc.bot_token = 'xoxb-token'
        mock_post.return_value = MagicMock(status_code=302)

        result = self.svc._send_message('C123', 'hello')

        self.assertIsNone(result)
        self.assertFalse(mock_post.call_args.kwargs['allow_redirects'])


if __name__ == '__main__':
    unittest.main()
