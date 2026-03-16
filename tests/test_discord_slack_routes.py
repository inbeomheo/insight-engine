"""Discord / Slack 알림 라우트 단위 테스트."""
import unittest
from unittest.mock import patch, MagicMock

from app import create_app

_HEADERS = {'Origin': 'http://localhost:3000'}


class TestDiscordRoutes(unittest.TestCase):
    """Discord 알림 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.integrations.discord_service.DiscordService.is_enabled', return_value=True)
    def test_discord_status(self, _mock_enabled, _mock_sb):
        """Discord 상태 조회 성공."""
        resp = self.client.get('/api/integrations/discord/status', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['enabled'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.integrations.discord_service.DiscordService.send', return_value={'ok': True})
    def test_discord_send_success(self, _mock_send, _mock_sb):
        """Discord 메시지 전송 성공."""
        resp = self.client.post('/api/integrations/discord/send',
                                json={'content': '테스트 메시지'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['ok'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_discord_send_empty_content(self, _mock_sb):
        """빈 내용 전송 시 400."""
        resp = self.client.post('/api/integrations/discord/send',
                                json={'content': ''},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.integrations.discord_service.DiscordService.send_embed', return_value={'ok': True})
    def test_discord_send_embed_success(self, _mock_embed, _mock_sb):
        """Discord Embed 전송 성공."""
        resp = self.client.post('/api/integrations/discord/send-embed',
                                json={'title': '제목', 'description': '설명'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['ok'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_discord_send_embed_missing_fields(self, _mock_sb):
        """Embed 필수 필드 누락 시 400."""
        resp = self.client.post('/api/integrations/discord/send-embed',
                                json={'title': '제목'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)


class TestSlackRoutes(unittest.TestCase):
    """Slack 알림 API 테스트."""

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.integrations.slack_service.SlackService.is_enabled', return_value=False)
    def test_slack_status_disabled(self, _mock_enabled, _mock_sb):
        """Slack 비활성 상태 조회."""
        resp = self.client.get('/api/integrations/slack/status', headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.get_json()['enabled'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.integrations.slack_service.SlackService.send', return_value={'ok': True})
    def test_slack_send_success(self, _mock_send, _mock_sb):
        """Slack 메시지 전송 성공."""
        resp = self.client.post('/api/integrations/slack/send',
                                json={'text': '알림 테스트'},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['ok'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_slack_send_empty_text(self, _mock_sb):
        """빈 텍스트 전송 시 400."""
        resp = self.client.post('/api/integrations/slack/send',
                                json={'text': ''},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    @patch('services.integrations.slack_service.SlackService.send_blocks', return_value={'ok': True})
    def test_slack_send_blocks_success(self, _mock_blocks, _mock_sb):
        """Slack Block Kit 전송 성공."""
        resp = self.client.post('/api/integrations/slack/send-blocks',
                                json={'blocks': [{'type': 'section', 'text': {'type': 'mrkdwn', 'text': 'hello'}}]},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()['ok'])

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_slack_send_blocks_empty(self, _mock_sb):
        """빈 blocks 전송 시 400."""
        resp = self.client.post('/api/integrations/slack/send-blocks',
                                json={'blocks': []},
                                headers=_HEADERS)
        self.assertEqual(resp.status_code, 400)


if __name__ == '__main__':
    unittest.main()
