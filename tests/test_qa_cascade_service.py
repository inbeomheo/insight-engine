"""qa_cascade_service 단위 테스트"""
import json
import unittest
from unittest.mock import patch, MagicMock

from services.qa_cascade_service import (
    QaPair,
    generate_qa_cascade,
    qa_pairs_to_dicts,
    _parse_qa_response,
    _VALID_CATEGORIES,
)


class TestGenerateQaCascade(unittest.TestCase):
    """generate_qa_cascade 함수 테스트"""

    def test_empty_transcript_raises(self):
        """빈 자막은 ValueError 발생"""
        with self.assertRaises(ValueError):
            generate_qa_cascade("")

    def test_whitespace_transcript_raises(self):
        """공백만 있는 자막은 ValueError 발생"""
        with self.assertRaises(ValueError):
            generate_qa_cascade("   \n\t  ")

    def test_short_transcript_raises(self):
        """30자 미만 자막은 ValueError 발생"""
        with self.assertRaises(ValueError):
            generate_qa_cascade("짧은 텍스트")

    @patch('services.qa_cascade_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.qa_cascade_service._call_llm')
    def test_successful_qa_generation(self, mock_call, mock_model):
        """정상적인 Q&A 생성 — QaPair 리스트 반환"""
        mock_call.return_value = json.dumps({
            "qa_pairs": [
                {"question": "배포 절차는 어떻게 되나요?", "answer": "CI/CD 파이프라인을 통해 자동 배포됩니다.", "category": "process", "confidence": 0.9},
                {"question": "보안 정책은 무엇인가요?", "answer": "모든 데이터는 암호화되어 저장됩니다.", "category": "policy", "confidence": 0.85},
                {"question": "API 성능은 어느 정도인가요?", "answer": "평균 응답 시간 200ms 이하입니다.", "category": "technical", "confidence": 0.8},
                {"question": "팀 회의는 언제 하나요?", "answer": "매주 월요일 오전 10시에 진행합니다.", "category": "general", "confidence": 0.7},
                {"question": "코드 리뷰 기준은?", "answer": "PR 제출 후 2명의 승인이 필요합니다.", "category": "process", "confidence": 0.88},
            ]
        })

        transcript = "이 프로젝트는 CI/CD를 통해 자동 배포되며, 보안 정책에 따라 모든 데이터를 암호화합니다. " * 3
        result = generate_qa_cascade(transcript)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 5)
        self.assertIsInstance(result[0], QaPair)
        self.assertEqual(result[0].category, "process")
        self.assertGreater(result[0].confidence, 0.0)

    @patch('services.qa_cascade_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.qa_cascade_service._call_llm')
    def test_empty_llm_response_returns_empty(self, mock_call, mock_model):
        """LLM 빈 응답 시 빈 리스트 반환"""
        mock_call.return_value = ""
        transcript = "충분히 긴 자막 텍스트입니다. " * 5
        result = generate_qa_cascade(transcript)
        self.assertEqual(result, [])

    @patch('services.qa_cascade_service._get_model', return_value='gemini/gemini-3-flash-preview')
    @patch('services.qa_cascade_service._call_llm')
    def test_llm_exception_returns_empty(self, mock_call, mock_model):
        """LLM 호출 실패 시 빈 리스트 반환 (예외 전파 안 함)"""
        mock_call.side_effect = RuntimeError("API 연결 실패")
        transcript = "충분히 긴 자막 텍스트입니다. " * 5
        result = generate_qa_cascade(transcript)
        self.assertEqual(result, [])


class TestParseQaResponse(unittest.TestCase):
    """_parse_qa_response 파싱 로직 테스트"""

    def test_valid_json_response(self):
        """유효한 JSON 응답 파싱"""
        raw = json.dumps({
            "qa_pairs": [
                {"question": "Q1", "answer": "A1", "category": "technical", "confidence": 0.9}
            ]
        })
        result = _parse_qa_response(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].question, "Q1")
        self.assertEqual(result[0].category, "technical")

    def test_code_block_wrapped_json(self):
        """```json ... ``` 코드블록 감싸진 응답 파싱"""
        raw = '```json\n{"qa_pairs": [{"question": "Q", "answer": "A", "category": "general", "confidence": 0.5}]}\n```'
        result = _parse_qa_response(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].question, "Q")

    def test_invalid_category_fallback_to_general(self):
        """유효하지 않은 카테고리는 'general'로 폴백"""
        raw = json.dumps({
            "qa_pairs": [
                {"question": "Q", "answer": "A", "category": "invalid_type", "confidence": 0.5}
            ]
        })
        result = _parse_qa_response(raw)
        self.assertEqual(result[0].category, "general")

    def test_confidence_clamping(self):
        """confidence 값이 0.0~1.0 범위로 클램핑"""
        raw = json.dumps({
            "qa_pairs": [
                {"question": "Q1", "answer": "A1", "category": "process", "confidence": 2.5},
                {"question": "Q2", "answer": "A2", "category": "process", "confidence": -0.5},
            ]
        })
        result = _parse_qa_response(raw)
        self.assertEqual(result[0].confidence, 1.0)
        self.assertEqual(result[1].confidence, 0.0)

    def test_missing_question_or_answer_skipped(self):
        """question 또는 answer가 없는 항목은 건너뜀"""
        raw = json.dumps({
            "qa_pairs": [
                {"question": "", "answer": "A1", "category": "general", "confidence": 0.5},
                {"question": "Q2", "answer": "", "category": "general", "confidence": 0.5},
                {"question": "Q3", "answer": "A3", "category": "general", "confidence": 0.5},
            ]
        })
        result = _parse_qa_response(raw)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].question, "Q3")

    def test_max_15_pairs(self):
        """최대 15개까지만 반환"""
        pairs = [{"question": f"Q{i}", "answer": f"A{i}", "category": "general", "confidence": 0.5} for i in range(20)]
        raw = json.dumps({"qa_pairs": pairs})
        result = _parse_qa_response(raw)
        self.assertEqual(len(result), 15)

    def test_invalid_json_returns_empty(self):
        """파싱 불가한 텍스트는 빈 리스트 반환"""
        result = _parse_qa_response("이것은 JSON이 아닙니다")
        self.assertEqual(result, [])


class TestQaPairToDict(unittest.TestCase):
    """직렬화 테스트"""

    def test_to_dicts(self):
        """QaPair → dict 변환"""
        pairs = [
            QaPair(question="Q", answer="A", category="process", confidence=0.9),
        ]
        result = qa_pairs_to_dicts(pairs)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["question"], "Q")
        self.assertEqual(result[0]["category"], "process")
        self.assertIsInstance(result[0], dict)


class TestValidCategories(unittest.TestCase):
    """카테고리 상수 테스트"""

    def test_all_categories_present(self):
        """4개 카테고리가 모두 정의되어 있는지 확인"""
        expected = {"process", "policy", "technical", "general"}
        self.assertEqual(_VALID_CATEGORIES, expected)


if __name__ == '__main__':
    unittest.main()
