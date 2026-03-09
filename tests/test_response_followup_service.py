"""response_followup_service 단위 테스트"""
import unittest

from services.response_followup_service import (
    generate_followup,
    PersonalizedContent,
    _filter_valid_responses,
    _split_responses,
    _extract_knowledge_gaps,
    _extract_topic_from_question,
    _build_summary,
    _build_recommendations,
    _build_next_steps,
    _get_level,
)


class TestGenerateFollowup(unittest.TestCase):
    """generate_followup 통합 테스트"""

    def test_empty_list(self):
        """빈 응답 리스트 처리"""
        result = generate_followup([])
        self.assertIsInstance(result, PersonalizedContent)
        self.assertEqual(result.summary, "분석할 응답이 없습니다.")
        self.assertEqual(result.recommendations, [])
        self.assertEqual(result.knowledge_gaps, [])
        self.assertEqual(result.next_steps, [])

    def test_none_input(self):
        """None 입력 처리"""
        result = generate_followup(None)
        self.assertEqual(result.summary, "분석할 응답이 없습니다.")

    def test_all_correct_high_score(self):
        """전부 정답 → 우수 레벨"""
        responses = [
            {"question": "파이썬이란 무엇인가요?", "answer": "프로그래밍 언어", "correct": True},
            {"question": "변수는 어떻게 선언하나요?", "answer": "x = 1", "correct": True},
            {"question": "리스트의 특징은?", "answer": "순서 보장", "correct": True},
        ]
        result = generate_followup(responses)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.correct_count, 3)
        self.assertEqual(result.total_questions, 3)
        self.assertEqual(result.knowledge_gaps, [])
        self.assertIn("우수", result.summary)

    def test_all_wrong_low_score(self):
        """전부 오답 → 추가 학습 필요 레벨"""
        responses = [
            {"question": "파이썬이란 무엇인가요?", "answer": "모름", "correct": False},
            {"question": "변수는 어떻게 선언하나요?", "answer": "모름", "correct": False},
        ]
        result = generate_followup(responses)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.correct_count, 0)
        self.assertGreater(len(result.knowledge_gaps), 0)
        self.assertIn("추가 학습", result.summary)

    def test_mixed_responses(self):
        """정답/오답 혼합 → 중간 레벨"""
        responses = [
            {"question": "데이터베이스 정규화란?", "answer": "중복 제거", "correct": True},
            {"question": "인덱스의 역할은 무엇인가요?", "answer": "빠른 검색", "correct": False},
            {"question": "트랜잭션 ACID 속성은?", "answer": "모름", "correct": False},
            {"question": "SQL JOIN 종류를 설명하세요", "answer": "INNER", "correct": True},
        ]
        result = generate_followup(responses)
        self.assertEqual(result.score, 0.5)
        self.assertEqual(result.total_questions, 4)
        self.assertEqual(result.correct_count, 2)

    def test_video_id_included(self):
        """video_id가 응답 ID에 반영됨"""
        responses = [{"question": "Q1?", "answer": "A1", "correct": True}]
        r1 = generate_followup(responses, video_id="abc123")
        r2 = generate_followup(responses, video_id="xyz789")
        self.assertNotEqual(r1.response_id, r2.response_id)

    def test_response_id_deterministic(self):
        """같은 입력 → 같은 response_id"""
        responses = [{"question": "Q1?", "answer": "A1", "correct": True}]
        r1 = generate_followup(responses, video_id="test")
        r2 = generate_followup(responses, video_id="test")
        self.assertEqual(r1.response_id, r2.response_id)

    def test_recommendations_not_empty(self):
        """추천 리스트가 항상 비어있지 않음"""
        responses = [
            {"question": "웹 프레임워크란?", "answer": "Flask", "correct": True},
        ]
        result = generate_followup(responses)
        self.assertGreater(len(result.recommendations), 0)

    def test_next_steps_not_empty(self):
        """다음 단계가 항상 비어있지 않음"""
        responses = [
            {"question": "API 설계 원칙은?", "answer": "REST", "correct": False},
        ]
        result = generate_followup(responses)
        self.assertGreater(len(result.next_steps), 0)


class TestFilterValidResponses(unittest.TestCase):
    """_filter_valid_responses 테스트"""

    def test_filters_missing_question(self):
        """question 키 누락 응답 필터링"""
        data = [{"answer": "A", "correct": True}]
        self.assertEqual(len(_filter_valid_responses(data)), 0)

    def test_filters_missing_correct(self):
        """correct 키 누락 응답 필터링"""
        data = [{"question": "Q?", "answer": "A"}]
        self.assertEqual(len(_filter_valid_responses(data)), 0)

    def test_filters_empty_question(self):
        """빈 question 문자열 필터링"""
        data = [{"question": "  ", "answer": "A", "correct": True}]
        self.assertEqual(len(_filter_valid_responses(data)), 0)

    def test_filters_non_dict(self):
        """dict가 아닌 요소 필터링"""
        data = ["not a dict", 42, None, {"question": "Q?", "correct": True}]
        valid = _filter_valid_responses(data)
        self.assertEqual(len(valid), 1)

    def test_keeps_valid_responses(self):
        """유효 응답은 보존"""
        data = [
            {"question": "Q1?", "answer": "A1", "correct": True},
            {"question": "Q2?", "answer": "A2", "correct": False},
        ]
        self.assertEqual(len(_filter_valid_responses(data)), 2)


class TestSplitResponses(unittest.TestCase):
    """_split_responses 테스트"""

    def test_split_correct_incorrect(self):
        """정답/오답 분리"""
        data = [
            {"question": "Q1", "correct": True},
            {"question": "Q2", "correct": False},
            {"question": "Q3", "correct": True},
        ]
        correct, incorrect = _split_responses(data)
        self.assertEqual(len(correct), 2)
        self.assertEqual(len(incorrect), 1)


class TestExtractKnowledgeGaps(unittest.TestCase):
    """_extract_knowledge_gaps 테스트"""

    def test_extracts_gaps_from_incorrect(self):
        """오답에서 지식 격차 추출"""
        incorrect = [
            {"question": "데이터베이스 인덱스의 역할은?", "correct": False},
            {"question": "트랜잭션 격리 수준을 설명하세요", "correct": False},
        ]
        gaps = _extract_knowledge_gaps(incorrect)
        self.assertGreater(len(gaps), 0)

    def test_no_duplicates(self):
        """동일 주제 중복 방지"""
        incorrect = [
            {"question": "같은질문을 두번 물어봅니다", "correct": False},
            {"question": "같은질문을 두번 물어봅니다", "correct": False},
        ]
        gaps = _extract_knowledge_gaps(incorrect)
        self.assertEqual(len(gaps), len(set(gaps)))

    def test_empty_incorrect(self):
        """빈 오답 리스트"""
        gaps = _extract_knowledge_gaps([])
        self.assertEqual(gaps, [])


class TestExtractTopic(unittest.TestCase):
    """_extract_topic_from_question 테스트"""

    def test_extracts_topic(self):
        """질문에서 주제 추출"""
        topic = _extract_topic_from_question("파이썬 리스트의 특징은?")
        self.assertTrue(len(topic) >= 3)

    def test_short_returns_empty(self):
        """너무 짧은 입력은 빈 문자열"""
        topic = _extract_topic_from_question("OX")
        self.assertEqual(topic, "")


class TestGetLevel(unittest.TestCase):
    """_get_level 테스트"""

    def test_excellent(self):
        self.assertEqual(_get_level(0.9), "excellent")
        self.assertEqual(_get_level(0.8), "excellent")

    def test_average(self):
        self.assertEqual(_get_level(0.6), "average")
        self.assertEqual(_get_level(0.5), "average")

    def test_needs_work(self):
        self.assertEqual(_get_level(0.3), "needs_work")
        self.assertEqual(_get_level(0.0), "needs_work")


class TestBuildSummary(unittest.TestCase):
    """_build_summary 테스트"""

    def test_includes_percentage(self):
        """요약에 정답률 포함"""
        summary = _build_summary(0.8, 10, 8, [])
        self.assertIn("80%", summary)

    def test_includes_gap_info(self):
        """지식 격차 정보 포함"""
        summary = _build_summary(0.4, 5, 2, ["인덱스", "트랜잭션"])
        self.assertIn("인덱스", summary)


class TestBuildRecommendations(unittest.TestCase):
    """_build_recommendations 테스트"""

    def test_excellent_recommendations(self):
        """우수 레벨 추천"""
        recs = _build_recommendations(0.9, [], [{"question": "Q", "correct": True}])
        self.assertTrue(any("심화" in r for r in recs))

    def test_low_score_recommendations(self):
        """낮은 점수 추천"""
        incorrect = [{"question": "긴 질문 문장이 들어갑니다 여기에 뭔가", "correct": False}]
        recs = _build_recommendations(0.2, incorrect, [])
        self.assertTrue(any("다시 시청" in r for r in recs))


class TestBuildNextSteps(unittest.TestCase):
    """_build_next_steps 테스트"""

    def test_excellent_has_project_step(self):
        """우수 레벨 → 실습 프로젝트 단계 포함"""
        steps = _build_next_steps(0.9, [])
        self.assertTrue(any("프로젝트" in s for s in steps))

    def test_low_score_has_review_step(self):
        """낮은 점수 → 다시 시청 단계 포함"""
        steps = _build_next_steps(0.2, ["주제A"])
        self.assertTrue(any("다시 시청" in s or "다시 도전" in s for s in steps))

    def test_average_includes_gap_review(self):
        """중간 레벨 → 격차 영역 복습 단계 포함"""
        steps = _build_next_steps(0.6, ["인덱스", "조인"])
        self.assertTrue(any("인덱스" in s for s in steps))


if __name__ == '__main__':
    unittest.main()
