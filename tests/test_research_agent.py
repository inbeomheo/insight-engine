"""리서치 에이전트 + 베이스 에이전트 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.agent import BaseAgent, AgentEvent, MAX_ITERATIONS


class ConcreteAgent(BaseAgent):
    """테스트용 구체 에이전트"""

    def __init__(self, plan_result=None, exec_result=None, reflect_result=None):
        super().__init__(name="TestAgent", model="test-model")
        self._plan_result = plan_result or {"summary": "test plan"}
        self._exec_result = exec_result or {"data": "test result"}
        self._reflect_result = reflect_result or {"done": True, "feedback": ""}

    def plan(self, task, context):
        return self._plan_result

    def execute(self, plan):
        return self._exec_result

    def reflect(self, result):
        return self._reflect_result


class TestBaseAgent(unittest.TestCase):
    """BaseAgent 단위 테스트"""

    def test_run_single_iteration(self):
        """단일 반복으로 완료되는 에이전트"""
        agent = ConcreteAgent()
        result = agent.run("test task")
        self.assertEqual(result["data"], "test result")

    def test_run_multiple_iterations(self):
        """여러 반복 후 완료되는 에이전트"""
        call_count = {"n": 0}
        original_reflect = {"done": False, "feedback": "need more"}

        class MultiIterAgent(BaseAgent):
            def plan(self, task, context):
                return {"summary": "plan"}

            def execute(self, plan):
                call_count["n"] += 1
                return {"count": call_count["n"]}

            def reflect(self, result):
                if call_count["n"] >= 2:
                    return {"done": True, "feedback": ""}
                return {"done": False, "feedback": "retry"}

        agent = MultiIterAgent(name="Multi", model="test")
        result = agent.run("task")
        self.assertEqual(result["count"], 2)

    def test_max_iterations_limit(self):
        """최대 반복 횟수 제한"""
        agent = ConcreteAgent(reflect_result={"done": False, "feedback": "never done"})
        agent.max_iterations = 3
        result = agent.run("task")
        self.assertEqual(result["data"], "test result")

    def test_event_emission(self):
        """이벤트 발생 확인"""
        events = []
        agent = ConcreteAgent()
        agent.on_event(lambda e: events.append(e))
        agent.run("task")

        phases = [e.phase for e in events]
        self.assertIn("plan", phases)
        self.assertIn("execute", phases)
        self.assertIn("reflect", phases)
        self.assertIn("done", phases)


class TestResearchAgent(unittest.TestCase):
    """ResearchAgent 단위 테스트"""

    @patch('services.agent.research_agent.ai_service')
    @patch('services.agent.research_agent.search_web')
    @patch('services.agent.research_agent.crawl_article')
    def test_plan_generates_queries(self, mock_crawl, mock_search, mock_ai):
        """plan()이 검색 쿼리를 생성하는지 확인"""
        mock_ai.create_content.return_value = {"content": "AI, 머신러닝, 딥러닝"}

        from services.agent.research_agent import ResearchAgent
        agent = ResearchAgent(model="test-model")
        plan = agent.plan("인공지능 트렌드", {"task": "인공지능 트렌드"})

        self.assertIn("queries", plan)
        self.assertTrue(len(plan["queries"]) > 0)

    @patch('services.agent.research_agent.ai_service')
    @patch('services.agent.research_agent.search_web')
    @patch('services.agent.research_agent.crawl_article')
    def test_execute_collects_sources(self, mock_crawl, mock_search, mock_ai):
        """execute()가 소스를 수집하는지 확인"""
        mock_search.return_value = [
            {"title": "Test Article", "url": "https://example.com/1"},
        ]
        mock_crawl.return_value = "Test article content..."
        mock_ai.create_content.return_value = {"content": "요약된 내용"}

        from services.agent.research_agent import ResearchAgent
        agent = ResearchAgent(model="test-model")
        result = agent.execute({"queries": ["AI trend"]})

        self.assertTrue(len(result["sources"]) > 0)
        self.assertEqual(result["sources"][0]["title"], "Test Article")

    def test_reflect_good_quality(self):
        """소스가 충분하면 done=True"""
        from services.agent.research_agent import ResearchAgent
        agent = ResearchAgent(model="test-model")
        result = agent.reflect({"sources": [{"a": 1}, {"b": 2}, {"c": 3}]})
        self.assertTrue(result["done"])

    def test_reflect_poor_quality(self):
        """소스가 없으면 done=False"""
        from services.agent.research_agent import ResearchAgent
        agent = ResearchAgent(model="test-model")
        result = agent.reflect({"sources": []})
        self.assertFalse(result["done"])


if __name__ == '__main__':
    unittest.main()
