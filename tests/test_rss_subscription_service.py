"""rss_subscription_service 단위 테스트 (파일 기반)"""
import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import services.rss_subscription_service as rss_sub_mod


class TestRssSubscriptionService(unittest.TestCase):

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp()
        self._orig_subs_file = rss_sub_mod._SUBS_FILE
        self._orig_data_dir = rss_sub_mod._DATA_DIR
        rss_sub_mod._DATA_DIR = self._tmpdir
        rss_sub_mod._SUBS_FILE = os.path.join(self._tmpdir, 'rss_subscriptions.json')

    def tearDown(self):
        rss_sub_mod._SUBS_FILE = self._orig_subs_file
        rss_sub_mod._DATA_DIR = self._orig_data_dir
        tmp_file = os.path.join(self._tmpdir, 'rss_subscriptions.json')
        if os.path.exists(tmp_file):
            os.unlink(tmp_file)
        os.rmdir(self._tmpdir)

    def test_load_all_empty(self):
        """파일 없으면 빈 dict"""
        data = rss_sub_mod._load_all()
        self.assertEqual(data, {})

    def test_save_and_load(self):
        """저장 후 로드"""
        test_data = {'user1': [{'id': 'sub1', 'feed_url': 'https://example.com/feed'}]}
        rss_sub_mod._save_all(test_data)
        loaded = rss_sub_mod._load_all()
        self.assertEqual(loaded['user1'][0]['id'], 'sub1')

    @patch('services.rss_subscription_service.parse_feed', return_value=[{'title': 'T'}])
    @patch('services.rss_subscription_service._feedparser')
    def test_subscribe(self, mock_fp, mock_parse):
        """구독 추가"""
        mock_fp.parse.return_value = MagicMock(feed=MagicMock(title='Test Feed'))
        result = rss_sub_mod.subscribe('user1', 'https://example.com/feed')
        self.assertIn('id', result)
        self.assertEqual(result['feed_url'], 'https://example.com/feed')
        self.assertEqual(result['title'], 'Test Feed')

    @patch('services.rss_subscription_service.parse_feed', return_value=[{'title': 'T'}])
    @patch('services.rss_subscription_service._feedparser')
    def test_subscribe_duplicate(self, mock_fp, mock_parse):
        """중복 구독 → ValueError"""
        mock_fp.parse.return_value = MagicMock(feed=MagicMock(title='Feed'))
        rss_sub_mod.subscribe('user1', 'https://dup.com/feed')
        with self.assertRaises(ValueError) as ctx:
            rss_sub_mod.subscribe('user1', 'https://dup.com/feed')
        self.assertIn('이미 구독', str(ctx.exception))

    @patch('services.rss_subscription_service.parse_feed', return_value=[{'title': 'T'}])
    @patch('services.rss_subscription_service._feedparser')
    def test_unsubscribe(self, mock_fp, mock_parse):
        """구독 해제"""
        mock_fp.parse.return_value = MagicMock(feed=MagicMock(title='Feed'))
        sub = rss_sub_mod.subscribe('user1', 'https://unsub.com/feed')
        result = rss_sub_mod.unsubscribe('user1', sub['id'])
        self.assertTrue(result)

    def test_unsubscribe_not_found(self):
        """없는 구독 해제 → False"""
        result = rss_sub_mod.unsubscribe('user1', 'nonexistent')
        self.assertFalse(result)

    def test_list_subscriptions_empty(self):
        """구독 없는 사용자 → 빈 리스트"""
        result = rss_sub_mod.list_subscriptions('nobody')
        self.assertEqual(result, [])

    @patch('services.rss_subscription_service.parse_feed', return_value=[{'title': 'T'}])
    @patch('services.rss_subscription_service._feedparser')
    def test_list_subscriptions(self, mock_fp, mock_parse):
        """구독 목록 조회"""
        mock_fp.parse.return_value = MagicMock(feed=MagicMock(title='Feed'))
        rss_sub_mod.subscribe('user2', 'https://list.com/feed')
        subs = rss_sub_mod.list_subscriptions('user2')
        self.assertEqual(len(subs), 1)

    def test_check_new_entries_first_time(self):
        """처음 확인 → 최신 1개"""
        sub = {'feed_url': 'https://x.com/feed', 'last_entry_url': None}
        with patch('services.rss_subscription_service.parse_feed') as mock_parse:
            mock_parse.return_value = [
                {'url': 'https://x.com/1', 'title': 'A'},
                {'url': 'https://x.com/2', 'title': 'B'},
            ]
            result = rss_sub_mod.check_new_entries(sub)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['url'], 'https://x.com/1')

    def test_check_new_entries_with_last(self):
        """마지막 URL 이후 새 글만"""
        sub = {'feed_url': 'https://x.com/feed', 'last_entry_url': 'https://x.com/2'}
        with patch('services.rss_subscription_service.parse_feed') as mock_parse:
            mock_parse.return_value = [
                {'url': 'https://x.com/3', 'title': 'New'},
                {'url': 'https://x.com/2', 'title': 'Old'},
            ]
            result = rss_sub_mod.check_new_entries(sub)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'New')

    @patch('services.rss_subscription_service.parse_feed', return_value=[{'title': 'T'}])
    @patch('services.rss_subscription_service._feedparser')
    def test_update_last_checked(self, mock_fp, mock_parse):
        """마지막 확인 시간 업데이트"""
        mock_fp.parse.return_value = MagicMock(feed=MagicMock(title='Feed'))
        sub = rss_sub_mod.subscribe('user3', 'https://update.com/feed')
        rss_sub_mod.update_last_checked('user3', sub['id'], 'https://update.com/latest')
        subs = rss_sub_mod.list_subscriptions('user3')
        self.assertEqual(subs[0]['last_entry_url'], 'https://update.com/latest')
        self.assertIsNotNone(subs[0]['last_checked_at'])


if __name__ == '__main__':
    unittest.main()
