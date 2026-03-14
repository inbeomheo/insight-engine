"""expiry_service 단위 테스트"""
import time
import unittest
from unittest.mock import patch

from services.data import expiry_service


class TestExpiryService(unittest.TestCase):

    def setUp(self):
        with expiry_service._lock:
            expiry_service._expiry_rules.clear()

    def test_set_expiry(self):
        """만료 규칙 설정"""
        rule = expiry_service.set_expiry('item1', time.time() + 86400, 'archive')
        self.assertEqual(rule['item_id'], 'item1')
        self.assertEqual(rule['action'], 'archive')
        self.assertFalse(rule['notified'])
        self.assertFalse(rule['executed'])

    def test_get_expiry(self):
        """만료 규칙 조회"""
        expiry_service.set_expiry('item1', time.time() + 3600)
        rule = expiry_service.get_expiry('item1')
        self.assertIsNotNone(rule)
        self.assertEqual(rule['item_id'], 'item1')

    def test_get_expiry_nonexistent(self):
        """없는 규칙 조회 → None"""
        self.assertIsNone(expiry_service.get_expiry('nonexistent'))

    def test_remove_expiry(self):
        """만료 규칙 제거"""
        expiry_service.set_expiry('item1', time.time() + 3600)
        self.assertTrue(expiry_service.remove_expiry('item1'))
        self.assertIsNone(expiry_service.get_expiry('item1'))

    def test_remove_expiry_nonexistent(self):
        """없는 규칙 제거 → False"""
        self.assertFalse(expiry_service.remove_expiry('bad'))

    def test_list_expiring_soon(self):
        """만료 임박 항목 조회"""
        expiry_service.set_expiry('soon', time.time() + 3600)       # 1시간 후
        expiry_service.set_expiry('later', time.time() + 86400 * 30)  # 30일 후
        soon = expiry_service.list_expiring_soon(within_days=1)
        self.assertEqual(len(soon), 1)
        self.assertEqual(soon[0]['item_id'], 'soon')

    def test_get_all_rules(self):
        """전체 규칙 목록"""
        expiry_service.set_expiry('a', time.time() + 100)
        expiry_service.set_expiry('b', time.time() + 200)
        rules = expiry_service.get_all_rules()
        self.assertEqual(len(rules), 2)

    @patch('services.data.content_library_service.delete_item')
    def test_process_expired_delete(self, mock_delete):
        """만료 삭제 처리"""
        expiry_service.set_expiry('del1', time.time() - 100, action='delete')
        result = expiry_service.process_expired()
        self.assertEqual(result['deleted'], 1)
        mock_delete.assert_called_once_with('del1', soft=True)

    @patch('services.data.content_library_service.update_item')
    def test_process_expired_archive(self, mock_update):
        """만료 아카이브 처리"""
        expiry_service.set_expiry('arc1', time.time() - 100, action='archive')
        result = expiry_service.process_expired()
        self.assertEqual(result['archived'], 1)
        mock_update.assert_called_once()

    def test_process_expired_notification(self):
        """만료 전 알림 플래그 설정"""
        # 2일 후 만료, notify_before_days=3 → 알림 대상
        expiry_service.set_expiry('notify1', time.time() + 86400 * 2, notify_before_days=3)
        result = expiry_service.process_expired()
        self.assertEqual(result['notified'], 1)
        rule = expiry_service.get_expiry('notify1')
        self.assertTrue(rule['notified'])

    def test_process_skips_executed(self):
        """이미 처리된 규칙 건너뜀"""
        expiry_service.set_expiry('done', time.time() - 100)
        with expiry_service._lock:
            expiry_service._expiry_rules['done']['executed'] = True
        result = expiry_service.process_expired()
        self.assertEqual(result['archived'], 0)
        self.assertEqual(result['deleted'], 0)


if __name__ == '__main__':
    unittest.main()
