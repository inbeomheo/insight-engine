"""CoAgent 서비스 테스트"""

import unittest
from services.coagent_service import (
    AgentRole, CoTask, CoSession,
    create_session, assign_task, complete_task, get_session_summary,
    VALID_ROLES,
)


class TestCreateSession(unittest.TestCase):
    """create_session 테스트"""

    def test_create_session_with_agents(self):
        """에이전트 포함 세션 생성"""
        configs = [
            {"name": "연구원", "role": "researcher", "capabilities": ["search"]},
            {"name": "작가", "role": "writer", "capabilities": ["write"]},
        ]
        session = create_session(configs)
        self.assertEqual(len(session.agents), 2)
        self.assertTrue(session.session_id.startswith("session_"))

    def test_create_empty_session(self):
        """빈 에이전트 목록으로 세션 생성"""
        session = create_session([])
        self.assertEqual(len(session.agents), 0)
        self.assertEqual(len(session.tasks), 0)

    def test_invalid_role_raises(self):
        """유효하지 않은 역할은 ValueError"""
        configs = [{"name": "Unknown", "role": "hacker"}]
        with self.assertRaises(ValueError):
            create_session(configs)

    def test_session_has_system_message(self):
        """세션 생성 시 시스템 메시지 포함"""
        configs = [{"name": "Agent", "role": "writer"}]
        session = create_session(configs)
        self.assertEqual(len(session.messages), 1)
        self.assertEqual(session.messages[0]["type"], "system")

    def test_agent_ids_unique(self):
        """에이전트 ID가 고유"""
        configs = [
            {"name": "A", "role": "writer"},
            {"name": "B", "role": "reviewer"},
        ]
        session = create_session(configs)
        ids = [a.agent_id for a in session.agents]
        self.assertEqual(len(ids), len(set(ids)))


class TestAssignTask(unittest.TestCase):
    """assign_task 테스트"""

    def setUp(self):
        self.session = create_session([
            {"name": "연구원", "role": "researcher"},
            {"name": "작가", "role": "writer"},
        ])
        self.agent_id = self.session.agents[0].agent_id

    def test_assign_adds_task(self):
        """태스크 할당 시 목록에 추가"""
        updated = assign_task(self.session, "자료 조사", self.agent_id)
        self.assertEqual(len(updated.tasks), 1)

    def test_assigned_task_is_in_progress(self):
        """할당된 태스크는 in_progress 상태"""
        updated = assign_task(self.session, "자료 조사", self.agent_id)
        self.assertEqual(updated.tasks[0].status, "in_progress")

    def test_assign_to_nonexistent_agent_raises(self):
        """존재하지 않는 에이전트에 할당 시 ValueError"""
        with self.assertRaises(ValueError):
            assign_task(self.session, "태스크", "nonexistent_agent")

    def test_assign_adds_message(self):
        """할당 시 메시지 추가"""
        original_count = len(self.session.messages)
        updated = assign_task(self.session, "작업", self.agent_id)
        self.assertEqual(len(updated.messages), original_count + 1)


class TestCompleteTask(unittest.TestCase):
    """complete_task 테스트"""

    def setUp(self):
        self.session = create_session([
            {"name": "작가", "role": "writer"},
        ])
        agent_id = self.session.agents[0].agent_id
        self.session = assign_task(self.session, "글 작성", agent_id)
        self.task_id = self.session.tasks[0].task_id

    def test_complete_changes_status(self):
        """완료 처리 시 status가 completed"""
        updated = complete_task(self.session, self.task_id, "완료된 결과물")
        self.assertEqual(updated.tasks[0].status, "completed")

    def test_complete_stores_output(self):
        """결과물이 저장됨"""
        updated = complete_task(self.session, self.task_id, "결과물 텍스트")
        self.assertEqual(updated.tasks[0].output, "결과물 텍스트")

    def test_complete_nonexistent_task_raises(self):
        """존재하지 않는 태스크 완료 시 ValueError"""
        with self.assertRaises(ValueError):
            complete_task(self.session, "nonexistent_task", "결과")


class TestGetSessionSummary(unittest.TestCase):
    """get_session_summary 테스트"""

    def test_empty_session_summary(self):
        """빈 세션 요약"""
        session = create_session([{"name": "A", "role": "writer"}])
        summary = get_session_summary(session)
        self.assertEqual(summary["total_tasks"], 0)
        self.assertEqual(summary["completion_rate"], 0.0)

    def test_completion_rate_calculated(self):
        """완료율 계산"""
        session = create_session([{"name": "A", "role": "writer"}])
        agent_id = session.agents[0].agent_id
        session = assign_task(session, "태스크1", agent_id)
        session = assign_task(session, "태스크2", agent_id)
        task_id = session.tasks[0].task_id
        session = complete_task(session, task_id, "완료")

        summary = get_session_summary(session)
        self.assertEqual(summary["total_tasks"], 2)
        self.assertEqual(summary["completed"], 1)
        self.assertAlmostEqual(summary["completion_rate"], 0.5)

    def test_agent_contributions_tracked(self):
        """에이전트별 기여도 추적"""
        session = create_session([
            {"name": "A", "role": "writer"},
            {"name": "B", "role": "reviewer"},
        ])
        a_id = session.agents[0].agent_id
        b_id = session.agents[1].agent_id

        session = assign_task(session, "작업1", a_id)
        session = assign_task(session, "작업2", b_id)

        summary = get_session_summary(session)
        self.assertIn(a_id, summary["agent_contributions"])
        self.assertEqual(summary["agent_contributions"][a_id]["assigned"], 1)


if __name__ == "__main__":
    unittest.main()
