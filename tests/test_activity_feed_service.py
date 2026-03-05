"""
활동 피드 서비스 단위 테스트
"""
import unittest
from services.activity_feed_service import ActivityFeedService


class TestActivityFeedService(unittest.TestCase):
    """ActivityFeedService 단위 테스트"""

    def setUp(self):
        self.svc = ActivityFeedService()

    def test_record_returns_item(self):
        """record()가 ActivityItem dict를 반환해야 함"""
        item = self.svc.record(
            workspace_id='ws_1',
            user_id='user_1',
            action='generated',
            target_title='테스트 콘텐츠',
        )
        self.assertEqual(item.workspace_id, 'ws_1')
        self.assertEqual(item.action, 'generated')
        self.assertEqual(item.target_title, '테스트 콘텐츠')
        self.assertTrue(item.id.startswith('act_'))

    def test_get_feed_returns_latest_first(self):
        """get_feed()가 최신 순으로 반환해야 함"""
        self.svc.record('ws_1', 'u1', 'generated', '첫 번째')
        self.svc.record('ws_1', 'u1', 'published', '두 번째')

        feed = self.svc.get_feed('ws_1')
        self.assertEqual(len(feed), 2)
        self.assertEqual(feed[0]['target_title'], '두 번째')
        self.assertEqual(feed[1]['target_title'], '첫 번째')

    def test_get_feed_limit_and_offset(self):
        """limit/offset 페이지네이션 동작 확인"""
        for i in range(10):
            self.svc.record('ws_1', 'u1', 'generated', f'항목 {i}')

        page1 = self.svc.get_feed('ws_1', limit=3, offset=0)
        self.assertEqual(len(page1), 3)

        page2 = self.svc.get_feed('ws_1', limit=3, offset=3)
        self.assertEqual(len(page2), 3)
        self.assertNotEqual(page1[0]['id'], page2[0]['id'])

    def test_get_feed_empty_workspace(self):
        """존재하지 않는 워크스페이스는 빈 리스트 반환"""
        feed = self.svc.get_feed('nonexistent')
        self.assertEqual(feed, [])

    def test_get_user_feed(self):
        """특정 사용자의 활동만 필터링"""
        self.svc.record('ws_1', 'user_a', 'generated', 'A의 콘텐츠')
        self.svc.record('ws_1', 'user_b', 'published', 'B의 콘텐츠')
        self.svc.record('ws_2', 'user_a', 'commented', 'A의 댓글')

        feed = self.svc.get_user_feed('user_a')
        self.assertEqual(len(feed), 2)
        for item in feed:
            self.assertEqual(item['user_id'], 'user_a')

    def test_max_items_per_workspace(self):
        """워크스페이스당 최대 항목 수 제한"""
        self.svc.MAX_ITEMS_PER_WORKSPACE = 5
        for i in range(10):
            self.svc.record('ws_1', 'u1', 'generated', f'항목 {i}')

        feed = self.svc.get_feed('ws_1', limit=100)
        self.assertEqual(len(feed), 5)

    def test_clear_workspace(self):
        """워크스페이스 피드 초기화"""
        self.svc.record('ws_1', 'u1', 'generated', '테스트')
        self.assertEqual(len(self.svc.get_feed('ws_1')), 1)

        self.svc.clear_workspace('ws_1')
        self.assertEqual(len(self.svc.get_feed('ws_1')), 0)

    def test_metadata_stored(self):
        """메타데이터가 올바르게 저장됨"""
        item = self.svc.record(
            'ws_1', 'u1', 'generated', '테스트',
            metadata={'style': 'blog_seo', 'model': 'gemini'},
        )
        self.assertEqual(item.metadata['style'], 'blog_seo')

        feed = self.svc.get_feed('ws_1')
        self.assertEqual(feed[0]['metadata']['model'], 'gemini')


if __name__ == '__main__':
    unittest.main()
