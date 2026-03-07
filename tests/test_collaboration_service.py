"""collaboration_service 단위 테스트"""
import unittest
from unittest.mock import patch

from services import collaboration_service


class TestCollaborationService(unittest.TestCase):
    """실시간 협업 편집 서비스 테스트"""

    def setUp(self):
        with collaboration_service._lock:
            collaboration_service._sessions.clear()

    def test_create_session(self):
        """세션 생성"""
        result = collaboration_service.create_session('c1', 'u1', 'Alice')
        self.assertIn('session_id', result)
        self.assertEqual(result['version'], 0)
        self.assertEqual(len(result['participants']), 1)

    def test_join_existing_session(self):
        """같은 콘텐츠에 두 번째 참가자 참여"""
        r1 = collaboration_service.create_session('c1', 'u1', 'Alice')
        r2 = collaboration_service.create_session('c1', 'u2', 'Bob')
        self.assertEqual(r1['session_id'], r2['session_id'])
        self.assertEqual(len(r2['participants']), 2)

    def test_update_content(self):
        """콘텐츠 업데이트"""
        r = collaboration_service.create_session('c1', 'u1')
        result = collaboration_service.update_content(r['session_id'], 'u1', '새 내용', 5)
        self.assertEqual(result['version'], 1)

    def test_update_nonexistent_session(self):
        """없는 세션 업데이트 시 None"""
        self.assertIsNone(collaboration_service.update_content('bad', 'u1', 'x'))

    def test_get_session(self):
        """세션 조회"""
        r = collaboration_service.create_session('c1', 'u1')
        session = collaboration_service.get_session(r['session_id'])
        self.assertIsNotNone(session)
        self.assertEqual(session['content'], '')

    def test_get_nonexistent_session(self):
        """없는 세션 조회 시 None"""
        self.assertIsNone(collaboration_service.get_session('bad'))

    def test_inactive_participants_removed(self):
        """30초 이상 비활성 참가자 제거"""
        r = collaboration_service.create_session('c1', 'u1')
        sid = r['session_id']
        # last_seen을 40초 전으로 설정
        with collaboration_service._lock:
            import time
            collaboration_service._sessions[sid]['participants']['u1']['last_seen'] = time.time() - 40
        session = collaboration_service.get_session(sid)
        self.assertEqual(len(session['participants']), 0)

    def test_heartbeat_success(self):
        """하트비트 성공"""
        r = collaboration_service.create_session('c1', 'u1')
        self.assertTrue(collaboration_service.heartbeat(r['session_id'], 'u1', 10))

    def test_heartbeat_wrong_session(self):
        """없는 세션 하트비트 실패"""
        self.assertFalse(collaboration_service.heartbeat('bad', 'u1'))

    def test_heartbeat_wrong_user(self):
        """없는 사용자 하트비트 실패"""
        r = collaboration_service.create_session('c1', 'u1')
        self.assertFalse(collaboration_service.heartbeat(r['session_id'], 'u2'))

    def test_leave_session(self):
        """세션 떠나기"""
        r = collaboration_service.create_session('c1', 'u1')
        self.assertTrue(collaboration_service.leave_session(r['session_id'], 'u1'))
        # 마지막 참가자가 나가면 세션 삭제
        self.assertIsNone(collaboration_service.get_session(r['session_id']))

    def test_leave_nonexistent_session(self):
        """없는 세션 떠나기"""
        self.assertFalse(collaboration_service.leave_session('bad', 'u1'))

    def test_participant_color_assigned(self):
        """참가자에 색상 할당"""
        r = collaboration_service.create_session('c1', 'u1')
        self.assertIn('color', r['participants'][0])


if __name__ == '__main__':
    unittest.main()
