"""베이스 프레임워크 에이전트 + 리서치 에이전트 단위 테스트"""
import unittest
from unittest.mock import patch, MagicMock

from services.agents.base_framework import BaseAgent as FrameworkBaseAgent, AgentEvent, MAX_ITERATIONS
from services.agents.research_agent import ResearchAgent


class ConcreteAgent(FrameworkBaseAgent):
    """테스트용 구체 에이전트 (plan/execute/reflect 루프)"""

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
    """FrameworkBaseAgent (plan/execute/reflect 루프) 단위 테스트"""

    def test_run_single_iteration(self):
        """단일 반복으로 완료되는 에이전트"""
        agent = ConcreteAgent()
        result = agent.run("test task")
        self.assertEqual(result["data"], "test result")

    def test_run_multiple_iterations(self):
        """여러 반복 후 완료되는 에이전트"""
        call_count = {"n": 0}

        class MultiIterAgent(FrameworkBaseAgent):
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
    """ResearchAgent (파이프라인 패턴: execute(context)) 단위 테스트"""

    @patch.object(ResearchAgent, '_call_ai')
    def test_execute_parses_ai_response(self, mock_call_ai):
        """execute()가 AI 응답을 올바르게 파싱하는지 확인"""
        mock_call_ai.return_value = '''{
            "main_topic": "인공지능 트렌드",
            "key_points": ["GPT 발전", "로컬 LLM 부상", "멀티모달 확산"],
            "target_audience": "개발자",
            "tone": "교육적",
            "search_query": "AI trends 2026",
            "summary": "AI 기술의 최신 트렌드를 다룹니다"
        }'''

        agent = ResearchAgent(model="test-model")
        result = agent.execute({
            'transcript': '인공지능의 발전은 놀라울 정도입니다...',
            'style': 'blog_seo',
        })

        self.assertEqual(result['agent'], 'research')
        self.assertEqual(result['main_topic'], '인공지능 트렌드')
        self.assertEqual(len(result['key_points']), 3)

    @patch.object(ResearchAgent, '_call_ai')
    def test_execute_handles_empty_transcript(self, mock_call_ai):
        """자막이 비어있으면 빈 결과 반환"""
        agent = ResearchAgent(model="test-model")
        result = agent.execute({'transcript': '', 'style': 'blog_seo'})

        self.assertEqual(result['agent'], 'research')
        self.assertEqual(result['main_topic'], '')
        self.assertEqual(result['key_points'], [])
        # AI 호출이 없어야 함
        mock_call_ai.assert_not_called()

    @patch.object(ResearchAgent, '_call_ai')
    def test_execute_handles_ai_failure(self, mock_call_ai):
        """AI 호출 실패 시 폴백 결과 반환"""
        mock_call_ai.side_effect = Exception("API 오류")

        agent = ResearchAgent(model="test-model")
        result = agent.execute({
            'transcript': '테스트 자막 내용입니다',
            'style': 'summary',
        })

        self.assertEqual(result['agent'], 'research')
        self.assertEqual(result['main_topic'], '알 수 없음')

    @patch.object(ResearchAgent, '_call_ai')
    def test_execute_returns_empty_web_results_without_search_query(self, mock_call_ai):
        """검색 쿼리가 없으면 웹 검색 결과가 비어있음"""
        mock_call_ai.return_value = '{"main_topic": "테스트", "key_points": [], "target_audience": "", "tone": "", "search_query": "", "summary": "요약"}'

        agent = ResearchAgent(model="test-model")
        result = agent.execute({
            'transcript': '테스트 자막',
            'style': 'blog_seo',
        })

        self.assertEqual(result['web_results'], [])
        self.assertEqual(result['web_context'], '')


if __name__ == '__main__':
    unittest.main()
