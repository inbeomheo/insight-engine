"""
인라인 승인 서비스 테스트
"""

import unittest
import time

from services.inline_approval_service import (
    InlineApprovalService,
    Action,
    ActionResult,
)


class TestCreateAction(unittest.TestCase):
    """create_action 테스트"""

    def setUp(self):
        self.svc = InlineApprovalService()

    def test_기본_액션_생성(self):
        """액션이 pending 상태로 생성되어야 한다"""
        action = self.svc.create_action("pipe_1", "generate", "미리보기 텍스트")
        self.assertIsInstance(action, Action)
        self.assertTrue(action.action_id.startswith("act_"))
        self.assertEqual(action.pipeline_id, "pipe_1")
        self.assertEqual(action.step_name, "generate")
        self.assertEqual(action.content_preview, "미리보기 텍스트")
        self.assertEqual(action.status, "pending")

    def test_빈_pipeline_id_거부(self):
        """빈 pipeline_id는 ValueError"""
        with self.assertRaises(ValueError):
            self.svc.create_action("", "step", "preview")

    def test_공백_pipeline_id_거부(self):
        """공백만 있는 pipeline_id는 ValueError"""
        with self.assertRaises(ValueError):
            self.svc.create_action("   ", "step", "preview")

    def test_빈_step_name_거부(self):
        """빈 step_name은 ValueError"""
        with self.assertRaises(ValueError):
            self.svc.create_action("pipe_1", "", "preview")

    def test_빈_content_preview_허용(self):
        """content_preview는 빈 문자열 허용"""
        action = self.svc.create_action("pipe_1", "step", "")
        self.assertEqual(action.content_preview, "")

    def test_고유_action_id(self):
        """각 액션은 고유 ID를 가져야 한다"""
        a1 = self.svc.create_action("pipe_1", "step_a", "p1")
        a2 = self.svc.create_action("pipe_1", "step_b", "p2")
        self.assertNotEqual(a1.action_id, a2.action_id)

    def test_created_at_자동설정(self):
        """created_at이 현재 시간 근처여야 한다"""
        before = time.time()
        action = self.svc.create_action("pipe_1", "step", "preview")
        after = time.time()
        self.assertGreaterEqual(action.created_at, before)
        self.assertLessEqual(action.created_at, after)


class TestSubmitAction(unittest.TestCase):
    """submit_action 테스트"""

    def setUp(self):
        self.svc = InlineApprovalService()

    def test_승인_처리(self):
        """approve 시 status='approved', next_step 자동 계산"""
        action = self.svc.create_action("pipe_1", "generate", "preview")
        result = self.svc.submit_action(action.action_id, "approve")
        self.assertIsInstance(result, ActionResult)
        self.assertEqual(result.decision, "approve")
        self.assertEqual(result.next_step, "generate_next")
        # 원본 액션 상태도 변경됨
        self.assertEqual(action.status, "approved")

    def test_거절_처리(self):
        """reject 시 status='rejected', next_step=None"""
        action = self.svc.create_action("pipe_1", "publish", "preview")
        result = self.svc.submit_action(action.action_id, "reject")
        self.assertEqual(result.decision, "reject")
        self.assertIsNone(result.next_step)
        self.assertEqual(action.status, "rejected")

    def test_존재하지_않는_액션(self):
        """없는 action_id는 KeyError"""
        with self.assertRaises(KeyError):
            self.svc.submit_action("nonexistent", "approve")

    def test_이미_결정된_액션_재결정_불가(self):
        """이미 승인/거절된 액션은 ValueError"""
        action = self.svc.create_action("pipe_1", "step", "preview")
        self.svc.submit_action(action.action_id, "approve")
        with self.assertRaises(ValueError) as ctx:
            self.svc.submit_action(action.action_id, "reject")
        self.assertIn("이미 결정된", str(ctx.exception))

    def test_잘못된_decision_값(self):
        """approve/reject 외의 값은 ValueError"""
        action = self.svc.create_action("pipe_1", "step", "preview")
        with self.assertRaises(ValueError) as ctx:
            self.svc.submit_action(action.action_id, "maybe")
        self.assertIn("잘못된 결정", str(ctx.exception))

    def test_decided_at_자동설정(self):
        """decided_at이 현재 시간 근처여야 한다"""
        action = self.svc.create_action("pipe_1", "step", "preview")
        before = time.time()
        result = self.svc.submit_action(action.action_id, "approve")
        after = time.time()
        self.assertGreaterEqual(result.decided_at, before)
        self.assertLessEqual(result.decided_at, after)


class TestListPendingActions(unittest.TestCase):
    """list_pending_actions 테스트"""

    def setUp(self):
        self.svc = InlineApprovalService()

    def test_빈_목록(self):
        """액션이 없으면 빈 리스트"""
        self.assertEqual(self.svc.list_pending_actions(), [])

    def test_pending만_반환(self):
        """approved/rejected 제외, pending만 반환"""
        a1 = self.svc.create_action("pipe_1", "step_a", "p1")
        a2 = self.svc.create_action("pipe_1", "step_b", "p2")
        a3 = self.svc.create_action("pipe_1", "step_c", "p3")
        self.svc.submit_action(a1.action_id, "approve")
        self.svc.submit_action(a3.action_id, "reject")
        pending = self.svc.list_pending_actions()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0].action_id, a2.action_id)

    def test_pipeline_id_필터(self):
        """특정 pipeline_id만 필터링"""
        self.svc.create_action("pipe_1", "step_a", "p1")
        self.svc.create_action("pipe_2", "step_b", "p2")
        self.svc.create_action("pipe_1", "step_c", "p3")
        pending = self.svc.list_pending_actions(pipeline_id="pipe_1")
        self.assertEqual(len(pending), 2)
        for a in pending:
            self.assertEqual(a.pipeline_id, "pipe_1")

    def test_pipeline_id_None이면_전체(self):
        """pipeline_id=None이면 모든 파이프라인의 pending 반환"""
        self.svc.create_action("pipe_1", "s1", "p1")
        self.svc.create_action("pipe_2", "s2", "p2")
        pending = self.svc.list_pending_actions(pipeline_id=None)
        self.assertEqual(len(pending), 2)

    def test_생성_시간순_정렬(self):
        """created_at 오름차순 정렬"""
        a1 = self.svc.create_action("pipe_1", "first", "p1")
        a2 = self.svc.create_action("pipe_1", "second", "p2")
        pending = self.svc.list_pending_actions()
        self.assertEqual(pending[0].step_name, "first")
        self.assertEqual(pending[1].step_name, "second")


if __name__ == "__main__":
    unittest.main()
