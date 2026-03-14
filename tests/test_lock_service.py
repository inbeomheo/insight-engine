"""lock_service 단위 테스트"""
import unittest
from unittest.mock import patch

from services.data import lock_service


class TestLockService(unittest.TestCase):
    """콘텐츠 잠금 서비스 테스트"""

    def setUp(self):
        with lock_service._mutex:
            lock_service._locks.clear()

    def test_acquire_lock(self):
        """잠금 획득 성공"""
        result = lock_service.acquire_lock('item1', 'user1', 'Alice')
        self.assertTrue(result['success'])
        self.assertEqual(result['lock']['user_id'], 'user1')

    def test_acquire_lock_conflict(self):
        """다른 사용자가 잠근 경우 실패"""
        lock_service.acquire_lock('item1', 'user1', 'Alice')
        result = lock_service.acquire_lock('item1', 'user2', 'Bob')
        self.assertFalse(result['success'])
        self.assertIn('locked_by', result)

    def test_acquire_lock_same_user_renews(self):
        """같은 사용자 재획득 시 갱신"""
        lock_service.acquire_lock('item1', 'user1')
        result = lock_service.acquire_lock('item1', 'user1')
        self.assertTrue(result['success'])

    def test_acquire_expired_lock(self):
        """만료된 잠금은 다른 사용자가 획득 가능"""
        with patch.object(lock_service, '_now', return_value=1000.0):
            lock_service.acquire_lock('item1', 'user1', ttl=10)
        with patch.object(lock_service, '_now', return_value=1020.0):
            result = lock_service.acquire_lock('item1', 'user2')
            self.assertTrue(result['success'])

    def test_release_lock(self):
        """잠금 해제"""
        lock_service.acquire_lock('item1', 'user1')
        self.assertTrue(lock_service.release_lock('item1', 'user1'))
        self.assertIsNone(lock_service.get_lock('item1'))

    def test_release_lock_wrong_user(self):
        """다른 사용자의 잠금 해제 불가"""
        lock_service.acquire_lock('item1', 'user1')
        self.assertFalse(lock_service.release_lock('item1', 'user2'))

    def test_release_nonexistent(self):
        """없는 잠금 해제 시 True (이미 없음)"""
        self.assertTrue(lock_service.release_lock('item1', 'user1'))

    def test_heartbeat(self):
        """TTL 갱신"""
        lock_service.acquire_lock('item1', 'user1')
        self.assertTrue(lock_service.heartbeat('item1', 'user1'))

    def test_heartbeat_wrong_user(self):
        """다른 사용자의 heartbeat 실패"""
        lock_service.acquire_lock('item1', 'user1')
        self.assertFalse(lock_service.heartbeat('item1', 'user2'))

    def test_get_lock(self):
        """잠금 상태 조회"""
        lock_service.acquire_lock('item1', 'user1')
        lock = lock_service.get_lock('item1')
        self.assertIsNotNone(lock)
        self.assertEqual(lock['user_id'], 'user1')

    def test_get_lock_expired(self):
        """만료된 잠금 조회 시 None"""
        with patch.object(lock_service, '_now', return_value=1000.0):
            lock_service.acquire_lock('item1', 'user1', ttl=10)
        with patch.object(lock_service, '_now', return_value=1020.0):
            self.assertIsNone(lock_service.get_lock('item1'))

    def test_force_release(self):
        """강제 해제"""
        lock_service.acquire_lock('item1', 'user1')
        self.assertTrue(lock_service.force_release('item1'))
        self.assertIsNone(lock_service.get_lock('item1'))

    def test_cleanup_expired(self):
        """만료 잠금 정리"""
        with patch.object(lock_service, '_now', return_value=1000.0):
            lock_service.acquire_lock('item1', 'u1', ttl=10)
            lock_service.acquire_lock('item2', 'u2', ttl=10)
        with patch.object(lock_service, '_now', return_value=1020.0):
            removed = lock_service.cleanup_expired()
            self.assertEqual(removed, 2)


if __name__ == '__main__':
    unittest.main()
