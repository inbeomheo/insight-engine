"""
회의록 생성 서비스 테스트
"""
import unittest

from services.meeting_minutes_service import (
    ActionItem,
    Discussion,
    MeetingMinutes,
    extract_action_items,
    transcribe_to_minutes,
    _extract_decisions,
    _extract_deadline,
    _extract_assignee,
    _determine_priority,
    _extract_raw_action_items,
    _split_into_paragraphs,
)


class TestTranscribeToMinutes(unittest.TestCase):
    """transcribe_to_minutes 함수 테스트."""

    def test_basic_transcript(self):
        """기본 전사 텍스트로 회의록 생성."""
        transcript = "프로젝트 킥오프 미팅\n\n이번 프로젝트 일정을 논의했습니다."
        minutes = transcribe_to_minutes(transcript, attendees=["김철수", "이영희"])
        self.assertIsInstance(minutes, MeetingMinutes)
        self.assertIn("프로젝트 킥오프 미팅", minutes.title)
        self.assertEqual(minutes.attendees, ["김철수", "이영희"])

    def test_empty_transcript_raises(self):
        """빈 전사 텍스트 시 ValueError."""
        with self.assertRaises(ValueError):
            transcribe_to_minutes("")
        with self.assertRaises(ValueError):
            transcribe_to_minutes("   ")

    def test_no_attendees(self):
        """참석자 미지정 시 빈 리스트."""
        minutes = transcribe_to_minutes("회의 내용입니다.")
        self.assertEqual(minutes.attendees, [])

    def test_title_truncation(self):
        """긴 첫 줄은 50자로 잘림."""
        long_line = "가" * 100
        minutes = transcribe_to_minutes(long_line)
        # 제목 = 잘린 첫 줄 + " — 회의록"
        self.assertLessEqual(len(minutes.title), 60)

    def test_date_format(self):
        """날짜가 YYYY-MM-DD 형식."""
        minutes = transcribe_to_minutes("테스트 회의")
        self.assertRegex(minutes.date, r'^\d{4}-\d{2}-\d{2}$')

    def test_decisions_extracted(self):
        """의사결정 키워드 포함 문장 추출."""
        transcript = (
            "안건 논의\n\n"
            "디자인 시안 A로 확정했습니다. "
            "일반적인 논의 내용입니다. "
            "다음 스프린트 일정에 합의했습니다."
        )
        minutes = transcribe_to_minutes(transcript)
        self.assertGreaterEqual(len(minutes.decisions), 2)

    def test_action_items_extracted(self):
        """실행 항목 패턴 추출."""
        transcript = (
            "회의 안건\n\n"
            "김철수님이 보고서를 작성해야 합니다. "
            "이영희님이 다음 주까지 디자인을 완료하겠습니다."
        )
        minutes = transcribe_to_minutes(transcript, attendees=["김철수", "이영희"])
        self.assertGreaterEqual(len(minutes.action_items), 2)

    def test_discussions_created(self):
        """문단 기반 Discussion 생성."""
        transcript = (
            "1. 프로젝트 현황\n현재 진행률은 70%입니다.\n\n"
            "2. 예산 논의\n추가 예산이 필요한 상황입니다."
        )
        minutes = transcribe_to_minutes(transcript)
        self.assertGreaterEqual(len(minutes.discussions), 2)

    def test_agenda_extraction(self):
        """안건 패턴 추출."""
        transcript = (
            "주제: 분기 실적 검토\n\n"
            "1. 매출 현황 분석\n세부 내용입니다.\n\n"
            "2. 비용 절감 방안\n세부 내용입니다."
        )
        minutes = transcribe_to_minutes(transcript)
        self.assertGreaterEqual(len(minutes.agenda), 1)

    def test_return_type(self):
        """반환 타입 확인."""
        minutes = transcribe_to_minutes("테스트")
        self.assertIsInstance(minutes, MeetingMinutes)
        self.assertIsInstance(minutes.discussions, list)
        self.assertIsInstance(minutes.action_items, list)
        self.assertIsInstance(minutes.decisions, list)

    def test_whitespace_stripping(self):
        """앞뒤 공백 제거."""
        minutes = transcribe_to_minutes("  회의 내용  \n  ")
        self.assertIn("회의 내용", minutes.title)

    def test_attendee_in_discussion_participants(self):
        """참석자가 Discussion 참가자로 매핑."""
        transcript = (
            "프로젝트 회의\n\n"
            "김철수가 진행 상황을 보고했습니다.\n이에 대해 논의했습니다."
        )
        minutes = transcribe_to_minutes(transcript, attendees=["김철수"])
        # 김철수가 포함된 discussion이 있어야 함
        has_participant = any(
            "김철수" in d.participants for d in minutes.discussions
        )
        self.assertTrue(has_participant)


class TestExtractActionItems(unittest.TestCase):
    """extract_action_items 함수 테스트."""

    def test_returns_existing_items(self):
        """회의록의 기존 action_items 반환."""
        item = ActionItem(task="보고서 작성해야 합니다", assignee="김철수")
        minutes = MeetingMinutes(
            title="테스트", date="2026-03-09", action_items=[item]
        )
        result = extract_action_items(minutes)
        self.assertIn(item, result)

    def test_extracts_from_discussions(self):
        """discussions에서 추가 실행 항목 탐색."""
        discussion = Discussion(
            topic="개발 계획",
            summary="API 문서를 작성해야 합니다",
            participants=["이영희"],
        )
        minutes = MeetingMinutes(
            title="테스트", date="2026-03-09", discussions=[discussion]
        )
        result = extract_action_items(minutes)
        self.assertGreaterEqual(len(result), 1)

    def test_no_duplicates(self):
        """중복 항목 제거."""
        task = "테스트 코드를 작성해야 합니다"
        item = ActionItem(task=task, assignee="김철수")
        discussion = Discussion(
            topic="QA", summary=task, participants=["김철수"]
        )
        minutes = MeetingMinutes(
            title="테스트", date="2026-03-09",
            action_items=[item], discussions=[discussion],
        )
        result = extract_action_items(minutes)
        tasks = [r.task for r in result]
        self.assertEqual(len(tasks), len(set(tasks)))

    def test_empty_minutes(self):
        """빈 회의록 시 빈 리스트."""
        minutes = MeetingMinutes(title="빈 회의", date="2026-03-09")
        result = extract_action_items(minutes)
        self.assertEqual(result, [])


class TestHelperFunctions(unittest.TestCase):
    """내부 헬퍼 함수 테스트."""

    def test_extract_decisions_with_keywords(self):
        """의사결정 키워드 포함 문장 추출."""
        text = "디자인을 확정했습니다. 일반 내용입니다. 일정에 합의했습니다."
        decisions = _extract_decisions(text)
        self.assertGreaterEqual(len(decisions), 2)

    def test_extract_decisions_no_keywords(self):
        """의사결정 키워드 없으면 빈 리스트."""
        text = "일반적인 논의를 진행했습니다."
        decisions = _extract_decisions(text)
        self.assertEqual(len(decisions), 0)

    def test_extract_deadline_date_format(self):
        """날짜 형식 마감일 추출."""
        self.assertEqual(_extract_deadline("3월 15일까지 완료"), "3월 15일")
        self.assertIn("다음 주", _extract_deadline("다음 주까지 제출"))

    def test_extract_deadline_none(self):
        """마감일 없으면 '미정'."""
        self.assertEqual(_extract_deadline("일반 텍스트"), "미정")

    def test_extract_assignee_pattern(self):
        """'담당: 이름' 패턴 추출."""
        self.assertEqual(_extract_assignee("담당: 홍길동", []), "홍길동")

    def test_extract_assignee_from_attendees(self):
        """참석자 이름 매칭."""
        self.assertEqual(
            _extract_assignee("김철수가 진행합니다", ["김철수", "이영희"]),
            "김철수"
        )

    def test_extract_assignee_default(self):
        """매칭 없으면 '미정'."""
        self.assertEqual(_extract_assignee("아무도 없음", []), "미정")

    def test_determine_priority_high(self):
        """긴급 키워드 → high."""
        self.assertEqual(_determine_priority("긴급하게 처리"), "high")
        self.assertEqual(_determine_priority("즉시 대응 필요"), "high")

    def test_determine_priority_low(self):
        """여유 키워드 → low."""
        self.assertEqual(_determine_priority("시간 될 때 처리"), "low")

    def test_determine_priority_default(self):
        """키워드 없으면 medium."""
        self.assertEqual(_determine_priority("일반 업무"), "medium")

    def test_extract_raw_action_items(self):
        """실행 항목 패턴 추출."""
        text = "보고서를 작성해야 합니다. 일정을 조정하겠습니다."
        items = _extract_raw_action_items(text)
        self.assertGreaterEqual(len(items), 2)

    def test_split_into_paragraphs(self):
        """빈 줄 기준 문단 분리."""
        text = "첫 번째 문단\n\n두 번째 문단\n\n세 번째 문단"
        paragraphs = _split_into_paragraphs(text)
        self.assertEqual(len(paragraphs), 3)

    def test_split_into_paragraphs_single(self):
        """단일 문단."""
        paragraphs = _split_into_paragraphs("하나의 문단입니다")
        self.assertEqual(len(paragraphs), 1)


if __name__ == "__main__":
    unittest.main()
