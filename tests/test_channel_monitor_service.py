"""channel_monitor_service 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.platform.channel_monitor_service import get_latest_video, check_monitors


class TestGetLatestVideo(unittest.TestCase):

    @patch.dict('os.environ', {'YOUTUBE_API_KEY': ''}, clear=False)
    def test_no_api_key(self):
        """API 키 없음 → None"""
        result = get_latest_video('UC_test')
        self.assertIsNone(result)

    @patch.dict('os.environ', {'YOUTUBE_API_KEY': 'test-key'}, clear=False)
    @patch('requests.get')
    def test_success(self, mock_get):
        """정상 응답 → video_id, title, published_at"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'items': [{
                'id': {'videoId': 'abc123'},
                'snippet': {
                    'title': '테스트 영상',
                    'publishedAt': '2026-03-01T00:00:00Z',
                },
            }]
        }
        mock_get.return_value = mock_resp

        result = get_latest_video('UC_test')
        self.assertEqual(result['video_id'], 'abc123')
        self.assertEqual(result['title'], '테스트 영상')
        self.assertEqual(result['published_at'], '2026-03-01T00:00:00Z')

    @patch.dict('os.environ', {'YOUTUBE_API_KEY': 'test-key'}, clear=False)
    @patch('requests.get')
    def test_empty_items(self, mock_get):
        """빈 결과 → None"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {'items': []}
        mock_get.return_value = mock_resp

        result = get_latest_video('UC_empty')
        self.assertIsNone(result)

    @patch.dict('os.environ', {'YOUTUBE_API_KEY': 'test-key'}, clear=False)
    @patch('requests.get')
    def test_request_error(self, mock_get):
        """네트워크 오류 → None"""
        mock_get.side_effect = Exception('timeout')
        result = get_latest_video('UC_fail')
        self.assertIsNone(result)


class TestCheckMonitors(unittest.TestCase):

    def test_no_client(self):
        """supabase_client 없음 → 빈 리스트"""
        self.assertEqual(check_monitors(None), [])

    def test_no_client_default(self):
        """기본 인자 → 빈 리스트"""
        self.assertEqual(check_monitors(), [])

    @patch('services.channel_monitor_service.get_latest_video')
    def test_new_video_detected(self, mock_latest):
        """신규 영상 감지"""
        mock_latest.return_value = {
            'video_id': 'new_vid',
            'title': '신규 영상',
            'published_at': '2026-03-08T00:00:00Z',
        }

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                'id': 'mon1',
                'user_id': 'user1',
                'channel_id': 'UC_ch1',
                'last_video_id': 'old_vid',
                'style_id': 'blog_seo',
                'modifiers': {'length': 'medium'},
                'is_active': True,
            }]
        )

        result = check_monitors(mock_client)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['video_id'], 'new_vid')
        self.assertEqual(result[0]['channel_id'], 'UC_ch1')
        self.assertEqual(result[0]['style_id'], 'blog_seo')

    @patch('services.channel_monitor_service.get_latest_video')
    def test_same_video_skipped(self, mock_latest):
        """동일 영상 → 스킵"""
        mock_latest.return_value = {
            'video_id': 'same_vid',
            'title': '기존 영상',
            'published_at': '2026-03-01T00:00:00Z',
        }

        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                'id': 'mon1',
                'user_id': 'user1',
                'channel_id': 'UC_ch1',
                'last_video_id': 'same_vid',
                'style_id': 'blog_seo',
                'modifiers': {},
                'is_active': True,
            }]
        )

        result = check_monitors(mock_client)
        self.assertEqual(len(result), 0)

    @patch('services.channel_monitor_service.get_latest_video', return_value=None)
    def test_latest_video_none(self, mock_latest):
        """최신 영상 조회 실패 → 스킵"""
        mock_client = MagicMock()
        mock_client.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{
                'id': 'mon1',
                'user_id': 'user1',
                'channel_id': 'UC_ch1',
                'last_video_id': 'old',
                'is_active': True,
            }]
        )

        result = check_monitors(mock_client)
        self.assertEqual(len(result), 0)

    def test_client_exception(self):
        """클라이언트 예외 → 빈 리스트"""
        mock_client = MagicMock()
        mock_client.table.side_effect = Exception('db error')
        result = check_monitors(mock_client)
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
