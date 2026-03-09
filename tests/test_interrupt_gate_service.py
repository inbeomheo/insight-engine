"""인터럽트 게이트 서비스 테스트"""
import unittest
from services.interrupt_gate_service import (
    create_gate,
    get_gate,
    submit_gate_decision,
    list_gates,
    _reset_store,
    GateState,
)


class TestCreateGate(unittest.TestCase):
    """게이트 생성 테스트"""

    def setUp(self):
        _reset_store()

    def test_creates_gate_with_pending_status(self):
        """생성된 게이트는 pending 상태"""
        gate = create_gate("pipeline-1", "review")
        self.assertEqual(gate.status, "pending")
        self.assertEqual(gate.pipeline_id, "pipeline-1")
        self.assertEqual(gate.step, "review")

    def test_generates_unique_gate_id(self):
        """각 게이트에 고유 ID 생성"""
        g1 = create_gate("p1", "s1")
        g2 = create_gate("p1", "s2")
        self.assertNotEqual(g1.gate_id, g2.gate_id)

    def test_decision_is_none_initially(self):
        """초기에는 decision과 edits가 None"""
        gate = create_gate("p1", "step1")
        self.assertIsNone(gate.decision)
        self.assertIsNone(gate.edits)
        self.assertIsNone(gate.decided_at)

    def test_created_at_is_set(self):
        """created_at이 자동 설정됨"""
        gate = create_gate("p1", "step1")
        self.assertIsNotNone(gate.created_at)

    def test_empty_pipeline_id_raises(self):
        """빈 pipeline_id는 ValueError"""
        with self.assertRaises(ValueError):
            create_gate("", "step1")

    def test_empty_step_raises(self):
        """빈 step은 ValueError"""
        with self.assertRaises(ValueError):
            create_gate("pipeline-1", "")

    def test_whitespace_only_pipeline_id_raises(self):
        """공백만 있는 pipeline_id는 ValueError"""
        with self.assertRaises(ValueError):
            create_gate("   ", "step1")

    def test_strips_whitespace(self):
        """앞뒤 공백이 제거됨"""
        gate = create_gate("  p1  ", "  step1  ")
        self.assertEqual(gate.pipeline_id, "p1")
        self.assertEqual(gate.step, "step1")


class TestGetGate(unittest.TestCase):
    """게이트 조회 테스트"""

    def setUp(self):
        _reset_store()

    def test_returns_existing_gate(self):
        """존재하는 게이트 조회"""
        gate = create_gate("p1", "step1")
        found = get_gate(gate.gate_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.gate_id, gate.gate_id)

    def test_returns_none_for_nonexistent(self):
        """없는 게이트는 None 반환"""
        self.assertIsNone(get_gate("nonexistent-id"))


class TestSubmitDecision(unittest.TestCase):
    """게이트 결정 제출 테스트"""

    def setUp(self):
        _reset_store()

    def test_approve_changes_status(self):
        """approve 결정 → approved 상태"""
        gate = create_gate("p1", "step1")
        result = submit_gate_decision(gate.gate_id, "approve")
        self.assertEqual(result.status, "approved")
        self.assertEqual(result.decision, "approve")
        self.assertIsNotNone(result.decided_at)

    def test_reject_changes_status(self):
        """reject 결정 → rejected 상태"""
        gate = create_gate("p1", "step1")
        result = submit_gate_decision(gate.gate_id, "reject")
        self.assertEqual(result.status, "rejected")
        self.assertEqual(result.decision, "reject")

    def test_edit_with_edits(self):
        """edit 결정 + edits dict → edited 상태"""
        gate = create_gate("p1", "step1")
        edits = {"title": "수정된 제목", "content": "수정된 내용"}
        result = submit_gate_decision(gate.gate_id, "edit", edits=edits)
        self.assertEqual(result.status, "edited")
        self.assertEqual(result.decision, "edit")
        self.assertEqual(result.edits, edits)

    def test_edit_without_edits_raises(self):
        """edit 결정 시 edits 누락하면 ValueError"""
        gate = create_gate("p1", "step1")
        with self.assertRaises(ValueError):
            submit_gate_decision(gate.gate_id, "edit")

    def test_double_decision_raises(self):
        """이미 결정된 게이트에 재결정 시 ValueError"""
        gate = create_gate("p1", "step1")
        submit_gate_decision(gate.gate_id, "approve")
        with self.assertRaises(ValueError):
            submit_gate_decision(gate.gate_id, "reject")

    def test_nonexistent_gate_raises(self):
        """없는 게이트에 결정 시 ValueError"""
        with self.assertRaises(ValueError):
            submit_gate_decision("no-such-id", "approve")

    def test_invalid_decision_raises(self):
        """유효하지 않은 결정 값은 ValueError"""
        gate = create_gate("p1", "step1")
        with self.assertRaises(ValueError):
            submit_gate_decision(gate.gate_id, "maybe")

    def test_approve_clears_edits(self):
        """approve 결정 시 edits는 None"""
        gate = create_gate("p1", "step1")
        result = submit_gate_decision(gate.gate_id, "approve")
        self.assertIsNone(result.edits)

    def test_decided_at_is_set(self):
        """결정 시 decided_at이 설정됨"""
        gate = create_gate("p1", "step1")
        result = submit_gate_decision(gate.gate_id, "approve")
        self.assertIsNotNone(result.decided_at)


class TestListGates(unittest.TestCase):
    """게이트 목록 조회 테스트"""

    def setUp(self):
        _reset_store()

    def test_list_all(self):
        """전체 게이트 목록"""
        create_gate("p1", "s1")
        create_gate("p2", "s2")
        self.assertEqual(len(list_gates()), 2)

    def test_filter_by_pipeline_id(self):
        """pipeline_id 필터"""
        create_gate("p1", "s1")
        create_gate("p1", "s2")
        create_gate("p2", "s3")
        result = list_gates(pipeline_id="p1")
        self.assertEqual(len(result), 2)

    def test_filter_by_status(self):
        """status 필터"""
        g1 = create_gate("p1", "s1")
        create_gate("p1", "s2")
        submit_gate_decision(g1.gate_id, "approve")
        pending = list_gates(status="pending")
        approved = list_gates(status="approved")
        self.assertEqual(len(pending), 1)
        self.assertEqual(len(approved), 1)

    def test_filter_combined(self):
        """pipeline_id + status 복합 필터"""
        g1 = create_gate("p1", "s1")
        create_gate("p1", "s2")
        create_gate("p2", "s3")
        submit_gate_decision(g1.gate_id, "approve")
        result = list_gates(pipeline_id="p1", status="pending")
        self.assertEqual(len(result), 1)

    def test_empty_when_no_gates(self):
        """게이트 없을 때 빈 리스트"""
        self.assertEqual(list_gates(), [])


class TestGateStateDataclass(unittest.TestCase):
    """GateState dataclass 기본값 테스트"""

    def test_defaults(self):
        """기본값 확인"""
        g = GateState()
        self.assertIsNotNone(g.gate_id)
        self.assertEqual(g.pipeline_id, "")
        self.assertEqual(g.step, "")
        self.assertEqual(g.status, "pending")
        self.assertIsNone(g.decision)
        self.assertIsNone(g.edits)
        self.assertIsNotNone(g.created_at)
        self.assertIsNone(g.decided_at)


if __name__ == '__main__':
    unittest.main()
