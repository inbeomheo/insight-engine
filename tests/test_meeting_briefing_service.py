"""미팅 브리핑 서비스 테스트"""

import unittest

from services.meeting_briefing_service import (
    MeetingInfo,
    Briefing,
    create_briefing,
    extract_action_items,
    generate_summary,
    estimate_time_allocation,
)


class TestCreateBriefing(unittest.TestCase):
    """create_briefing 함수 테스트"""

    def test_기본_브리핑_생성(self):
        meeting = MeetingInfo(
            meeting_id="m1",
            title="주간 회의",
            attendees=["김철수", "이영희"],
            agenda=["프로젝트 진행 상황", "일정 조율"],
            date="2026-03-10",
            duration_min=60,
        )
        briefing = create_briefing(meeting)
        self.assertEqual(briefing.meeting_id, "m1")
        self.assertGreater(len(briefing.executive_summary), 0)
        self.assertEqual(len(briefing.key_topics), 2)

    def test_참조_문서_포함(self):
        meeting = MeetingInfo(
            meeting_id="m1",
            agenda=["진행 상황"],
            attendees=["홍길동"],
        )
        docs = ["- 보고서 작성 필요\n- API 검토 진행"]
        briefing = create_briefing(meeting, context_docs=docs)
        self.assertGreater(len(briefing.preparation_notes), 0)

    def test_빈_안건(self):
        meeting = MeetingInfo(meeting_id="m1")
        briefing = create_briefing(meeting)
        self.assertEqual(briefing.key_topics, ["안건 미정"])

    def test_준비_사항_참석자(self):
        meeting = MeetingInfo(
            meeting_id="m1",
            attendees=["A", "B", "C"],
            agenda=["토픽1"],
        )
        briefing = create_briefing(meeting)
        has_attendee_note = any("참석자" in note for note in briefing.preparation_notes)
        self.assertTrue(has_attendee_note)


class TestExtractActionItems(unittest.TestCase):
    """extract_action_items 함수 테스트"""

    def test_액션_아이템_추출(self):
        notes = "- 보고서 작성 필요\n- 일정 확인 진행\n- 맛있는 점심"
        items = extract_action_items(notes)
        self.assertGreater(len(items), 0)
        # "필요", "확인", "진행" 키워드 포함 항목
        self.assertTrue(any("필요" in item for item in items))

    def test_빈_노트(self):
        items = extract_action_items("")
        self.assertEqual(len(items), 0)

    def test_액션_없는_노트(self):
        notes = "오늘 날씨가 좋다\n커피가 맛있다"
        items = extract_action_items(notes)
        self.assertEqual(len(items), 0)

    def test_번호_목록(self):
        notes = "1. 프로젝트 검토 필요\n2. 문서 작성 완료\n3. 단순 내용"
        items = extract_action_items(notes)
        self.assertGreaterEqual(len(items), 2)

    def test_여러_키워드(self):
        notes = "- 보고서 준비\n- 결과 공유\n- 코드 정리"
        items = extract_action_items(notes)
        self.assertEqual(len(items), 3)


class TestGenerateSummary(unittest.TestCase):
    """generate_summary 함수 테스트"""

    def test_안건_요약(self):
        summary = generate_summary(["프로젝트 리뷰", "일정 조율"])
        self.assertIn("프로젝트 리뷰", summary)
        self.assertIn("일정 조율", summary)

    def test_참조_문서_언급(self):
        summary = generate_summary(["안건1"], context=["문서1", "문서2"])
        self.assertIn("참조 문서", summary)

    def test_빈_안건(self):
        summary = generate_summary([])
        self.assertIn("제공되지 않았습니다", summary)


class TestEstimateTimeAllocation(unittest.TestCase):
    """estimate_time_allocation 함수 테스트"""

    def test_기본_시간_배분(self):
        result = estimate_time_allocation(["안건1", "안건2"], 60)
        self.assertGreater(len(result), 0)
        # 마지막은 마무리/QA
        self.assertIn("마무리", result[-1]["agenda_item"])

    def test_총_시간_일치(self):
        result = estimate_time_allocation(["안건1", "안건2", "안건3"], 90)
        total = sum(item["allocated_min"] for item in result)
        self.assertEqual(total, 90)

    def test_빈_안건(self):
        result = estimate_time_allocation([], 60)
        self.assertEqual(len(result), 0)

    def test_0_시간(self):
        result = estimate_time_allocation(["안건1"], 0)
        self.assertEqual(len(result), 0)

    def test_순서_번호(self):
        result = estimate_time_allocation(["A", "B"], 60)
        self.assertEqual(result[0]["order"], 1)
        self.assertEqual(result[1]["order"], 2)
        self.assertEqual(result[2]["order"], 3)  # 마무리

    def test_단일_안건(self):
        result = estimate_time_allocation(["유일한 안건"], 30)
        self.assertEqual(len(result), 2)  # 안건1 + 마무리
        total = sum(item["allocated_min"] for item in result)
        self.assertEqual(total, 30)


if __name__ == "__main__":
    unittest.main()
