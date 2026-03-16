"""
web_research_agent (ResearchAgent — plan/execute/reflect 패턴) 단위 테스트
"""
import unittest
from unittest.mock import patch, MagicMock


class TestWebResearchAgent(unittest.TestCase):
    """services.agents.web_research_agent.ResearchAgent 테스트"""

    def _make_agent(self, max_sources=3, max_iterations=2):
        from services.agents.web_research_agent import ResearchAgent
        return ResearchAgent(model='gemini/test', max_sources=max_sources, max_iterations=max_iterations)

    # --- 초기화 ---

    def test_init(self):
        agent = self._make_agent(max_sources=5, max_iterations=3)
        self.assertEqual(agent.name, "ResearchAgent")
        self.assertEqual(agent.max_sources, 5)
        self.assertEqual(agent.max_iterations, 3)

    # --- plan ---

    @patch('services.agents.web_research_agent.ai_service.create_content',
           return_value={"content": "쿼리1, 쿼리2, 쿼리3"})
    def test_plan_generates_queries(self, mock_ai):
        agent = self._make_agent()
        result = agent.plan("AI 기술 동향", {"task": "AI 기술 동향"})

        self.assertIn("queries", result)
        self.assertEqual(len(result["queries"]), 3)
        mock_ai.assert_called_once()

    @patch('services.agents.web_research_agent.ai_service.create_content',
           return_value={"content": "보완 쿼리1, 보완 쿼리2"})
    def test_plan_with_feedback(self, mock_ai):
        agent = self._make_agent()
        result = agent.plan("AI", {"task": "AI", "feedback": "소스 부족"})

        self.assertEqual(len(result["queries"]), 2)
        # 피드백 포함 프롬프트 확인
        call_args = mock_ai.call_args
        self.assertIn("부족", call_args[1]["content"])

    @patch('services.agents.web_research_agent.ai_service.create_content',
           side_effect=Exception("API 오류"))
    def test_plan_failure_uses_task_as_query(self, mock_ai):
        agent = self._make_agent()
        result = agent.plan("AI 기술", {"task": "AI 기술"})

        self.assertEqual(result["queries"], ["AI 기술"])

    # --- execute ---

    @patch('services.agents.web_research_agent.ai_service.create_content',
           return_value={"content": "기사 요약 결과"})
    @patch('services.agents.web_research_agent.crawl_article',
           return_value="기사 본문 텍스트")
    @patch('services.agents.web_research_agent.search_web',
           return_value=[{"url": "https://example.com", "title": "예시"}])
    def test_execute_collects_sources(self, mock_search, mock_crawl, mock_ai):
        agent = self._make_agent()
        result = agent.execute({"queries": ["AI 검색"]})

        self.assertEqual(result["source_count"], 1)
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(result["sources"][0]["title"], "예시")

    @patch('services.agents.web_research_agent.search_web', return_value=[])
    def test_execute_no_results(self, mock_search):
        agent = self._make_agent()
        result = agent.execute({"queries": ["존재하지 않는 주제"]})

        self.assertEqual(result["sources"], [])
        self.assertIn("없음", result["summary"])

    def test_execute_empty_queries(self):
        agent = self._make_agent()
        result = agent.execute({"queries": []})
        self.assertEqual(result["sources"], [])

    @patch('services.agents.web_research_agent.search_web',
           return_value=[{"url": "https://a.com", "title": "A"}])
    @patch('services.agents.web_research_agent.crawl_article', return_value="")
    def test_execute_crawl_empty_skips(self, mock_crawl, mock_search):
        """크롤링 결과가 빈 문자열이면 skip"""
        agent = self._make_agent()
        result = agent.execute({"queries": ["test"]})
        self.assertEqual(len(result["sources"]), 0)

    # --- reflect ---

    def test_reflect_enough_sources(self):
        agent = self._make_agent()
        result = agent.reflect({"sources": [1, 2, 3]})
        self.assertTrue(result["done"])
        self.assertEqual(result["quality"], "good")

    def test_reflect_partial_sources(self):
        agent = self._make_agent()
        result = agent.reflect({"sources": [1]})
        self.assertFalse(result["done"])
        self.assertEqual(result["quality"], "partial")

    def test_reflect_no_sources(self):
        agent = self._make_agent()
        result = agent.reflect({"sources": []})
        self.assertFalse(result["done"])
        self.assertEqual(result["quality"], "poor")


if __name__ == '__main__':
    unittest.main()
