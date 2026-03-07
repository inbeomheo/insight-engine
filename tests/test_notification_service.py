"""notification_service 단위 테스트"""
import unittest

from services import notification_service


class TestNotificationService(unittest.TestCase):
    """알림 센터 서비스 테스트"""

    def setUp(self):
        notification_service._notifications.clear()

    def test_create_notification(self):
        """알림 생성"""
        n = notification_service.create_notification('u1', 'system', '제목', '메시지')
        self.assertEqual(n['type'], 'system')
        self.assertEqual(n['title'], '제목')
        self.assertFalse(n['read'])

    def test_list_notifications(self):
        """알림 목록 조회"""
        notification_service.create_notification('u1', 'system', 'A', 'msg')
        notification_service.create_notification('u1', 'system', 'B', 'msg')
        result = notification_service.list_notifications('u1')
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['unread_count'], 2)

    def test_list_unread_only(self):
        """읽지 않은 알림만 필터링"""
        n = notification_service.create_notification('u1', 'system', 'A', 'msg')
        notification_service.create_notification('u1', 'system', 'B', 'msg')
        notification_service.mark_read('u1', n['id'])
        result = notification_service.list_notifications('u1', unread_only=True)
        self.assertEqual(result['total'], 1)

    def test_pagination(self):
        """페이지네이션"""
        for i in range(5):
            notification_service.create_notification('u1', 'system', f'N{i}', 'msg')
        result = notification_service.list_notifications('u1', limit=2, offset=1)
        self.assertEqual(len(result['notifications']), 2)
        self.assertEqual(result['total'], 5)

    def test_mark_read(self):
        """알림 읽음 표시"""
        n = notification_service.create_notification('u1', 'system', '제목', 'msg')
        self.assertTrue(notification_service.mark_read('u1', n['id']))
        result = notification_service.list_notifications('u1')
        self.assertEqual(result['unread_count'], 0)

    def test_mark_read_not_found(self):
        """없는 알림 읽음 표시 시 False"""
        self.assertFalse(notification_service.mark_read('u1', 'no-id'))

    def test_mark_all_read(self):
        """모든 알림 읽음 표시"""
        notification_service.create_notification('u1', 'system', 'A', 'msg')
        notification_service.create_notification('u1', 'system', 'B', 'msg')
        count = notification_service.mark_all_read('u1')
        self.assertEqual(count, 2)
        self.assertEqual(notification_service.get_unread_count('u1'), 0)

    def test_delete_notification(self):
        """알림 삭제"""
        n = notification_service.create_notification('u1', 'system', '삭제용', 'msg')
        self.assertTrue(notification_service.delete_notification('u1', n['id']))
        result = notification_service.list_notifications('u1')
        self.assertEqual(result['total'], 0)

    def test_delete_not_found(self):
        """없는 알림 삭제 시 False"""
        self.assertFalse(notification_service.delete_notification('u1', 'no-id'))

    def test_get_unread_count(self):
        """읽지 않은 알림 수"""
        notification_service.create_notification('u1', 'system', 'A', 'msg')
        notification_service.create_notification('u1', 'system', 'B', 'msg')
        self.assertEqual(notification_service.get_unread_count('u1'), 2)

    def test_max_notifications_limit(self):
        """최대 알림 수 초과 시 오래된 것 제거"""
        original = notification_service.MAX_NOTIFICATIONS_PER_USER
        notification_service.MAX_NOTIFICATIONS_PER_USER = 3
        try:
            for i in range(5):
                notification_service.create_notification('u1', 'system', f'N{i}', 'msg')
            result = notification_service.list_notifications('u1')
            self.assertEqual(result['total'], 3)
        finally:
            notification_service.MAX_NOTIFICATIONS_PER_USER = original


if __name__ == '__main__':
    unittest.main()
