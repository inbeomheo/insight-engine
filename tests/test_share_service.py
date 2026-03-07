"""share_service 단위 테스트"""
import unittest
from unittest.mock import patch

from services import share_service


class TestShareService(unittest.TestCase):
    """공유 링크 서비스 테스트"""

    def setUp(self):
        with share_service._lock:
            share_service._shares.clear()

    def test_create_share_link(self):
        """공유 링크 생성"""
        s = share_service.create_share_link('item1', user_id='u1')
        self.assertIn('token', s)
        self.assertEqual(s['item_id'], 'item1')
        self.assertEqual(s['view_count'], 0)
        self.assertFalse(s['is_revoked'])

    def test_get_share(self):
        """토큰으로 공유 링크 조회"""
        s = share_service.create_share_link('item1')
        found = share_service.get_share(s['token'])
        self.assertIsNotNone(found)
        self.assertEqual(found['item_id'], 'item1')

    def test_get_share_not_found(self):
        """없는 토큰 조회 시 None"""
        self.assertIsNone(share_service.get_share('invalid-token'))

    def test_get_share_revoked(self):
        """취소된 링크 조회 시 None"""
        s = share_service.create_share_link('item1', user_id='u1')
        share_service.revoke_share(s['token'])
        self.assertIsNone(share_service.get_share(s['token']))

    def test_get_share_expired(self):
        """만료된 링크 조회 시 None"""
        with patch.object(share_service, '_now', return_value=1000.0):
            s = share_service.create_share_link('item1', expires_in_hours=1)
        with patch.object(share_service, '_now', return_value=5000.0):
            self.assertIsNone(share_service.get_share(s['token']))

    def test_verify_and_access_success(self):
        """접근 성공 + 조회수 증가"""
        s = share_service.create_share_link('item1')
        result = share_service.verify_and_access(s['token'])
        self.assertTrue(result['success'])
        self.assertEqual(result['item_id'], 'item1')
        # 조회수 확인
        self.assertEqual(share_service._shares[s['token']]['view_count'], 1)

    def test_verify_with_password(self):
        """비밀번호 보호 링크 접근"""
        s = share_service.create_share_link('item1', password='secret')
        fail = share_service.verify_and_access(s['token'], password='wrong')
        self.assertFalse(fail['success'])
        ok = share_service.verify_and_access(s['token'], password='secret')
        self.assertTrue(ok['success'])

    def test_revoke_share(self):
        """공유 링크 취소"""
        s = share_service.create_share_link('item1', user_id='u1')
        self.assertTrue(share_service.revoke_share(s['token']))

    def test_revoke_wrong_user(self):
        """다른 사용자의 링크 취소 불가"""
        s = share_service.create_share_link('item1', user_id='u1')
        self.assertFalse(share_service.revoke_share(s['token'], user_id='u2'))

    def test_list_shares(self):
        """공유 링크 목록"""
        share_service.create_share_link('item1', user_id='u1')
        share_service.create_share_link('item2', user_id='u1')
        share_service.create_share_link('item1', user_id='u2')
        by_item = share_service.list_shares(item_id='item1')
        self.assertEqual(len(by_item), 2)
        by_user = share_service.list_shares(user_id='u1')
        self.assertEqual(len(by_user), 2)


if __name__ == '__main__':
    unittest.main()
