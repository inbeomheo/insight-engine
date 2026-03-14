"""
RSS 구독 서비스 단위 테스트
"""
import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from services.platform.rss_subscription_service import (
    subscribe,
    unsubscribe,
    list_subscriptions,
    check_new_entries,
    check_all_subscriptions,
    _SUBS_FILE,
)


class TestRssSubscriptionService(unittest.TestCase):
    """RSS 구독 CRUD + 새 글 감지 테스트"""

    def setUp(self):
        """임시 파일로 구독 데이터 격리"""
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_file = os.path.join(self.tmp_dir, 'rss_subscriptions.json')
        self._patcher_file = patch(
            'services.rss_subscription_service._SUBS_FILE', self.tmp_file,
        )
        self._patcher_dir = patch(
            'services.rss_subscription_service._DATA_DIR', self.tmp_dir,
        )
        self._patcher_file.start()
        self._patcher_dir.start()

    def tearDown(self):
        self._patcher_file.stop()
        self._patcher_dir.stop()
        if os.path.exists(self.tmp_file):
            os.remove(self.tmp_file)
        os.rmdir(self.tmp_dir)

    @patch('services.rss_subscription_service.parse_feed')
    @patch('services.rss_subscription_service._feedparser')
    def test_subscribe_success(self, mock_feedparser, mock_parse):
        """구독 추가 성공"""
        mock_parse.return_value = [{'title': 'Test', 'url': 'http://example.com/1'}]
        mock_feed = MagicMock()
        mock_feed.feed.title = 'Test Blog'
        mock_feedparser.parse.return_value = mock_feed

        result = subscribe('user1', 'http://example.com/feed')

        self.assertEqual(result['feed_url'], 'http://example.com/feed')
        self.assertEqual(result['title'], 'Test Blog')
        self.assertIn('id', result)

    @patch('services.rss_subscription_service.parse_feed')
    @patch('services.rss_subscription_service._feedparser')
    def test_subscribe_duplicate(self, mock_feedparser, mock_parse):
        """중복 구독 시 ValueError"""
        mock_parse.return_value = [{'title': 'Test'}]
        mock_feed = MagicMock()
        mock_feed.feed.title = 'Test'
        mock_feedparser.parse.return_value = mock_feed

        subscribe('user1', 'http://example.com/feed')

        with self.assertRaises(ValueError) as ctx:
            subscribe('user1', 'http://example.com/feed')
        self.assertIn('이미 구독 중', str(ctx.exception))

    @patch('services.rss_subscription_service.parse_feed')
    def test_subscribe_invalid_feed(self, mock_parse):
        """유효하지 않은 피드 URL"""
        mock_parse.side_effect = ValueError("파싱 실패")

        with self.assertRaises(ValueError):
            subscribe('user1', 'http://invalid.example.com/feed')

    @patch('services.rss_subscription_service.parse_feed')
    @patch('services.rss_subscription_service._feedparser')
    def test_unsubscribe(self, mock_feedparser, mock_parse):
        """구독 해제"""
        mock_parse.return_value = [{'title': 'Test'}]
        mock_feed = MagicMock()
        mock_feed.feed.title = 'Test'
        mock_feedparser.parse.return_value = mock_feed

        sub = subscribe('user1', 'http://example.com/feed')
        result = unsubscribe('user1', sub['id'])
        self.assertTrue(result)

        # 목록에서 사라졌는지 확인
        subs = list_subscriptions('user1')
        self.assertEqual(len(subs), 0)

    def test_unsubscribe_not_found(self):
        """존재하지 않는 구독 해제"""
        result = unsubscribe('user1', 'nonexistent-id')
        self.assertFalse(result)

    def test_list_empty(self):
        """빈 목록"""
        subs = list_subscriptions('user1')
        self.assertEqual(subs, [])

    @patch('services.rss_subscription_service.parse_feed')
    def test_check_new_entries_first_time(self, mock_parse):
        """처음 확인 시 최신 1개만 반환"""
        mock_parse.return_value = [
            {'title': 'Entry 1', 'url': 'http://example.com/1'},
            {'title': 'Entry 2', 'url': 'http://example.com/2'},
        ]

        sub = {'feed_url': 'http://example.com/feed', 'last_entry_url': None}
        entries = check_new_entries(sub)
        self.assertEqual(len(entries), 1)

    @patch('services.rss_subscription_service.parse_feed')
    def test_check_new_entries_with_last(self, mock_parse):
        """마지막 URL 이후 새 글만 반환"""
        mock_parse.return_value = [
            {'title': 'New Entry', 'url': 'http://example.com/3'},
            {'title': 'Seen Entry', 'url': 'http://example.com/2'},
            {'title': 'Old Entry', 'url': 'http://example.com/1'},
        ]

        sub = {'feed_url': 'http://example.com/feed', 'last_entry_url': 'http://example.com/2'}
        entries = check_new_entries(sub)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]['url'], 'http://example.com/3')

    @patch('services.rss_subscription_service.parse_feed')
    def test_check_new_entries_no_new(self, mock_parse):
        """새 글 없음"""
        mock_parse.return_value = [
            {'title': 'Seen', 'url': 'http://example.com/1'},
        ]

        sub = {'feed_url': 'http://example.com/feed', 'last_entry_url': 'http://example.com/1'}
        entries = check_new_entries(sub)
        self.assertEqual(len(entries), 0)


if __name__ == '__main__':
    unittest.main()
