"""
팩트체크 에이전트 단위 테스트 (F3-07)
"""
import json
import unittest
from unittest.mock import patch, MagicMock


class TestFactCheckAgent(unittest.TestCase):
    """fact_check_agent 테스트"""

    MOCK_RESPONSE = json.dumps([
        {
            "claim": "GPT-4는 2023년 3월에 출시되었다",
            "category": "date",
            "verifiable": True,
            "confidence": 0.9,
            "reasoning": "공식 발표일 확인 가능"
        },
        {
            "claim": "AI가 인간의 모든 직업을 대체할 것이다",
            "category": "other",
            "verifiable": False,
            "confidence": 0.2,
            "reasoning": "미래 예측으로 검증 불가"
        },
    ])

    def _mock_completion(self, content: str):
        mock = MagicMock()
        mock.choices[0].message.content = content
        return mock

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion')
    def test_returns_claims(self, mock_llm, mock_model):
        """정상 응답 시 claims 목록 반환"""
        mock_llm.return_value = self._mock_completion(self.MOCK_RESPONSE)

        from services.agents.fact_check_agent import fact_check
        result = fact_check("GPT-4는 2023년 3월에 출시되었다. AI가 인간의 모든 직업을 대체할 것이다.")

        self.assertIn('claims', result)
        self.assertIn('summary', result)
        self.assertEqual(len(result['claims']), 2)

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion')
    def test_summary_counts(self, mock_llm, mock_model):
        """요약 통계 정확성"""
        mock_llm.return_value = self._mock_completion(self.MOCK_RESPONSE)

        from services.agents.fact_check_agent import fact_check
        result = fact_check("테스트 내용")

        summary = result['summary']
        self.assertEqual(summary['total'], 2)
        self.assertEqual(summary['verified'], 1)  # confidence >= 0.7
        self.assertEqual(summary['suspicious'], 1)  # confidence < 0.3

    def test_empty_content(self):
        """빈 콘텐츠 입력 시 빈 결과"""
        from services.agents.fact_check_agent import fact_check
        result = fact_check("")
        self.assertEqual(result['claims'], [])

    @patch('services.agents.base_agent.BaseAgent._get_default_model',
           return_value='gemini/gemini-3-flash-preview')
    @patch('litellm.completion', side_effect=Exception("API 오류"))
    def test_llm_failure_graceful(self, mock_llm, mock_model):
        """LLM 실패 시 빈 결과 반환"""
        from services.agents.fact_check_agent import fact_check
        result = fact_check("테스트")
        self.assertEqual(result['claims'], [])


class TestParseClaims(unittest.TestCase):
    """_parse_claims 상세 테스트"""

    def setUp(self):
        from services.agents.fact_check_agent import _parse_claims
        self._parse = _parse_claims

    def test_valid_json_array(self):
        """유효한 JSON 배열 파싱"""
        data = [{"claim": "테스트", "category": "other", "verifiable": True,
                 "confidence": 0.8, "reasoning": "근거"}]
        result = self._parse(json.dumps(data))
        self.assertEqual(len(result), 1)

    def test_code_block_wrapped(self):
        """```json 코드블록 래핑된 경우"""
        data = [{"claim": "A", "category": "date", "confidence": 0.5}]
        raw = f"```json\n{json.dumps(data)}\n```"
        result = self._parse(raw)
        self.assertEqual(len(result), 1)

    def test_invalid_json_returns_empty(self):
        """잘못된 JSON은 빈 목록"""
        result = self._parse("이것은 JSON이 아닙니다")
        self.assertEqual(result, [])

    def test_confidence_clamped(self):
        """confidence 범위 0-1 클램핑"""
        data = [{"claim": "A", "confidence": 5.0}]
        result = self._parse(json.dumps(data))
        self.assertLessEqual(result[0]['confidence'], 1.0)

    def test_max_10_claims(self):
        """최대 10개 제한"""
        data = [{"claim": f"C{i}", "confidence": 0.5} for i in range(15)]
        result = self._parse(json.dumps(data))
        self.assertLessEqual(len(result), 10)


if __name__ == '__main__':
    unittest.main()
