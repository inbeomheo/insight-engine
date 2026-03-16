"""publish_queue_service 단위 테스트"""
import unittest
from unittest.mock import patch

from services.data.publish_queue_service import PublishQueueService


class TestPublishQueueService(unittest.TestCase):

    def setUp(self):
        # 테스트 시 파일 I/O 무효화 (인메모리만 사용)
        with patch.object(PublishQueueService, '_load_queue'), \
             patch.object(PublishQueueService, '_save_queue'):
            self.svc = PublishQueueService()
        self.svc._queue = []
        self.svc._save_queue = lambda: None  # enqueue 등에서 호출 시 무시

    def test_enqueue(self):
        """큐에 항목 추가"""
        item = self.svc.enqueue('c1', '제목', '내용', 'naver_blog', 'user1')
        self.assertEqual(item['status'], 'queued')
        self.assertEqual(item['title'], '제목')
        self.assertEqual(item['plugin_id'], 'naver_blog')

    def test_get_queue_status(self):
        """큐 상태 조회"""
        self.svc.enqueue('c1', '제목1', '내용1', 'plugin1', 'u1')
        self.svc.enqueue('c2', '제목2', '내용2', 'plugin2', 'u2')
        all_items = self.svc.get_queue_status()
        self.assertEqual(len(all_items), 2)

    def test_get_queue_status_filtered(self):
        """사용자별 큐 조회"""
        self.svc.enqueue('c1', '제목1', '내용1', 'p1', 'u1')
        self.svc.enqueue('c2', '제목2', '내용2', 'p2', 'u2')
        items = self.svc.get_queue_status(user_id='u1')
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['user_id'], 'u1')

    def test_cancel_queued_item(self):
        """queued 상태 항목 취소"""
        item = self.svc.enqueue('c1', '제목', '내용', 'p1', 'u1')
        result = self.svc.cancel_item(item['id'])
        self.assertTrue(result['success'])
        self.assertEqual(len(self.svc.get_queue_status()), 0)

    def test_cancel_nonexistent(self):
        """없는 항목 취소"""
        result = self.svc.cancel_item('bad-id')
        self.assertFalse(result['success'])

    def test_cancel_non_queued(self):
        """queued가 아닌 상태에서 취소 → 실패"""
        item = self.svc.enqueue('c1', '제목', '내용', 'p1', 'u1')
        # 수동으로 상태 변경
        self.svc._queue[0]['status'] = 'publishing'
        result = self.svc.cancel_item(item['id'])
        self.assertFalse(result['success'])

    def test_retry_failed_item(self):
        """failed 상태 항목 수동 재시도"""
        item = self.svc.enqueue('c1', '제목', '내용', 'p1', 'u1')
        self.svc._queue[0]['status'] = 'failed'
        self.svc._queue[0]['retry_count'] = 3
        result = self.svc.retry_item(item['id'])
        self.assertTrue(result['success'])
        self.assertEqual(self.svc._queue[0]['status'], 'queued')
        self.assertEqual(self.svc._queue[0]['retry_count'], 0)

    def test_retry_non_failed(self):
        """failed가 아닌 상태에서 재시도 → 실패"""
        item = self.svc.enqueue('c1', '제목', '내용', 'p1', 'u1')
        result = self.svc.retry_item(item['id'])
        self.assertFalse(result['success'])

    def test_handle_failure_with_retry(self):
        """실패 시 재시도 큐 복귀"""
        item = self.svc.enqueue('c1', '제목', '내용', 'p1', 'u1')
        raw = self.svc._queue[0]
        self.svc._handle_failure(raw, '오류')
        self.assertEqual(raw['status'], 'queued')
        self.assertEqual(raw['retry_count'], 1)
        self.assertIsNotNone(raw['next_retry_at'])

    def test_handle_failure_max_retries(self):
        """최대 재시도 초과 → failed"""
        item = self.svc.enqueue('c1', '제목', '내용', 'p1', 'u1')
        raw = self.svc._queue[0]
        raw['retry_count'] = 2  # 이미 2번 시도
        self.svc._handle_failure(raw, '오류')
        self.assertEqual(raw['status'], 'failed')

    def test_sanitize_excludes_content(self):
        """_sanitize는 content 필드 제외"""
        item = self.svc.enqueue('c1', '제목', '큰 본문', 'p1', 'u1')
        self.assertNotIn('content', item)
        self.assertIn('title', item)

    def test_get_status_summary(self):
        """상태별 요약 통계"""
        self.svc.enqueue('c1', '제목1', '내용1', 'p1', 'u1')
        self.svc.enqueue('c2', '제목2', '내용2', 'p1', 'u1')
        self.svc._queue[1]['status'] = 'failed'
        summary = self.svc.get_status_summary()
        self.assertEqual(summary['queued'], 1)
        self.assertEqual(summary['failed'], 1)
        self.assertEqual(summary['total'], 2)
        self.assertEqual(summary['success'], 0)
        self.assertEqual(summary['publishing'], 0)

    def test_get_status_summary_filtered_by_user(self):
        """사용자별 상태 요약"""
        self.svc.enqueue('c1', '제목1', '내용1', 'p1', 'u1')
        self.svc.enqueue('c2', '제목2', '내용2', 'p1', 'u2')
        summary = self.svc.get_status_summary(user_id='u1')
        self.assertEqual(summary['total'], 1)
        self.assertEqual(summary['queued'], 1)

    def test_get_status_summary_empty(self):
        """빈 큐 상태 요약"""
        summary = self.svc.get_status_summary()
        self.assertEqual(summary['total'], 0)
        for state in PublishQueueService.STATES:
            self.assertEqual(summary[state], 0)


if __name__ == '__main__':
    unittest.main()
