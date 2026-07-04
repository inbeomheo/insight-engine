"""
ScheduleService 단위 테스트
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone, timedelta

from services.data.schedule_service import ScheduleService, _memory_store


class TestScheduleServiceMemory(unittest.TestCase):
    """메모리 fallback 모드 (Supabase 비활성화) 테스트"""

    def setUp(self):
        _memory_store.clear()
        self.svc = ScheduleService()
        self.user_id = 'test-user-001'

    @patch('services.data.schedule_service.is_supabase_enabled', return_value=False)
    def test_create(self, _):
        post = self.svc.create(
            user_id=self.user_id,
            title='테스트 제목',
            content='테스트 내용',
            html='<p>테스트</p>',
            target_plugin='wordpress',
            scheduled_at='2026-03-02T09:00:00+00:00',
        )
        self.assertIsNotNone(post)
        self.assertEqual(post['title'], '테스트 제목')
        self.assertEqual(post['status'], 'pending')
        self.assertEqual(post['user_id'], self.user_id)

    @patch('services.data.schedule_service.is_supabase_enabled', return_value=False)
    def test_list_by_user(self, _):
        self.svc.create(self.user_id, '제목1', '내용1', None, 'wp', '2026-03-01T09:00:00+00:00')
        self.svc.create(self.user_id, '제목2', '내용2', None, 'wp', '2026-03-02T09:00:00+00:00')
        self.svc.create('other-user', '남의 것', '내용', None, 'wp', '2026-03-01T09:00:00+00:00')

        posts = self.svc.list_by_user(self.user_id)
        self.assertEqual(len(posts), 2)
        # 다른 사용자 것은 포함 안 됨
        self.assertTrue(all(p['user_id'] == self.user_id for p in posts))

    @patch('services.data.schedule_service.is_supabase_enabled', return_value=False)
    def test_delete_own_post(self, _):
        post = self.svc.create(self.user_id, '삭제할 것', '내용', None, 'wp', '2026-03-01T09:00:00+00:00')
        result = self.svc.delete(post['id'], self.user_id)
        self.assertTrue(result)
        self.assertEqual(len(self.svc.list_by_user(self.user_id)), 0)

    @patch('services.data.schedule_service.is_supabase_enabled', return_value=False)
    def test_delete_other_user_post_fails(self, _):
        post = self.svc.create(self.user_id, '내 것', '내용', None, 'wp', '2026-03-01T09:00:00+00:00')
        result = self.svc.delete(post['id'], 'other-user')
        self.assertFalse(result)
        # 삭제 안 됨
        self.assertEqual(len(self.svc.list_by_user(self.user_id)), 1)

    @patch('services.data.schedule_service.is_supabase_enabled', return_value=False)
    def test_get_due_posts(self, _):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        self.svc.create(self.user_id, '과거', '내용', None, 'wp', past)
        self.svc.create(self.user_id, '미래', '내용', None, 'wp', future)

        due = self.svc.get_due_posts()
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]['title'], '과거')

    @patch('services.data.schedule_service.is_supabase_enabled', return_value=False)
    def test_update_status(self, _):
        post = self.svc.create(self.user_id, '제목', '내용', None, 'wp', '2026-03-01T09:00:00+00:00')
        self.svc.update_status(post['id'], 'published', published_url='https://blog.example.com/1')

        updated = _memory_store[post['id']]
        self.assertEqual(updated['status'], 'published')
        self.assertEqual(updated['published_url'], 'https://blog.example.com/1')

    @patch('services.data.schedule_service.is_supabase_enabled', return_value=False)
    def test_update_status_failed(self, _):
        post = self.svc.create(self.user_id, '제목', '내용', None, 'wp', '2026-03-01T09:00:00+00:00')
        self.svc.update_status(post['id'], 'failed', error_message='연결 실패')

        updated = _memory_store[post['id']]
        self.assertEqual(updated['status'], 'failed')
        self.assertEqual(updated['error_message'], '연결 실패')


    @patch('services.data.schedule_service.is_supabase_enabled', return_value=False)
    def test_create_invalid_scheduled_at(self, _):
        """잘못된 ISO 형식 scheduled_at → 빈 dict 반환 (크래시 방지)"""
        result = self.svc.create(
            self.user_id, '제목', '내용', None, 'wp', 'not-a-date'
        )
        self.assertEqual(result, {})

    @patch('services.data.schedule_service.is_supabase_enabled', return_value=False)
    def test_create_empty_scheduled_at(self, _):
        """빈 문자열 scheduled_at → 빈 dict 반환"""
        result = self.svc.create(
            self.user_id, '제목', '내용', None, 'wp', ''
        )
        self.assertEqual(result, {})


class TestCheckAndPublish(unittest.TestCase):
    """워커 check_and_publish 테스트 — 발행 플러그인 제거(Dep-5) 후 대기 포스트는 실패 처리"""

    def setUp(self):
        _memory_store.clear()

    @patch('services.data.schedule_service.is_supabase_enabled', return_value=False)
    def test_check_and_publish_marks_due_posts_failed(self, _):
        from services.data.scheduler_worker import check_and_publish
        from services.data.schedule_service import schedule_service

        # 과거 시간으로 예약 생성
        past = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        post = schedule_service.create('user1', '제목', '내용', None, 'wp', past)

        check_and_publish()

        self.assertEqual(_memory_store[post['id']]['status'], 'failed')
        self.assertEqual(_memory_store[post['id']]['error_message'], '발행 기능이 종료되었습니다.')


if __name__ == '__main__':
    unittest.main()
