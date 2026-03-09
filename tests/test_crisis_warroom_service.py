"""위기 워룸 서비스 테스트."""

import unittest
from services.crisis_warroom_service import (
    CrisisEvent,
    Warroom,
    detect_crisis,
    escalate,
    add_response,
    resolve_crisis,
    get_active_crises,
)


class TestCrisisWarroomService(unittest.TestCase):
    """CrisisWarroomService 단위 테스트."""

    def test_detect_crisis_basic(self):
        """위기가 탐지된다."""
        event = detect_crisis("content_1", "콘텐츠에 오류가 발견되었습니다")
        self.assertIsInstance(event, CrisisEvent)
        self.assertEqual(event.status, "detected")
        self.assertIn("content_1", event.affected_content)
        self.assertTrue(event.event_id.startswith("ce_"))

    def test_detect_crisis_auto_severity_critical(self):
        """critical 키워드 자동 분류."""
        event = detect_crisis("c1", "데이터 유출 사고 발생")
        self.assertEqual(event.severity, "critical")

    def test_detect_crisis_auto_severity_high(self):
        """high 키워드 자동 분류."""
        event = detect_crisis("c1", "저작권 위반 신고 접수")
        self.assertEqual(event.severity, "high")

    def test_detect_crisis_auto_severity_medium(self):
        """medium 키워드 자동 분류."""
        event = detect_crisis("c1", "콘텐츠 품질 저하 보고")
        self.assertEqual(event.severity, "medium")

    def test_detect_crisis_auto_severity_low(self):
        """키워드 없으면 low."""
        event = detect_crisis("c1", "사소한 이슈")
        self.assertEqual(event.severity, "low")

    def test_detect_crisis_timeline(self):
        """타임라인에 탐지 기록이 포함된다."""
        event = detect_crisis("c1", "이슈 발생")
        self.assertEqual(len(event.timeline), 1)
        self.assertEqual(event.timeline[0]["action"], "detected")

    def test_escalate_changes_severity(self):
        """에스컬레이션으로 심각도가 변경된다."""
        event = detect_crisis("c1", "이슈")
        escalated = escalate(event, "critical")
        self.assertEqual(escalated.severity, "critical")
        self.assertEqual(escalated.status, "assessing")

    def test_escalate_adds_timeline(self):
        """에스컬레이션이 타임라인에 기록된다."""
        event = detect_crisis("c1", "이슈")
        escalated = escalate(event, "high")
        self.assertEqual(len(escalated.timeline), 2)
        self.assertEqual(escalated.timeline[1]["action"], "escalated")

    def test_escalate_invalid_severity(self):
        """유효하지 않은 심각도는 에러."""
        event = detect_crisis("c1", "이슈")
        with self.assertRaises(ValueError):
            escalate(event, "ultra")

    def test_add_response_records(self):
        """대응 기록이 추가된다."""
        event = detect_crisis("c1", "이슈")
        responded = add_response(event, "김철수", "콘텐츠 비공개 처리")
        self.assertEqual(responded.status, "responding")
        self.assertEqual(len(responded.timeline), 2)
        self.assertEqual(responded.timeline[1]["actor"], "김철수")

    def test_add_response_multiple(self):
        """여러 대응을 추가할 수 있다."""
        event = detect_crisis("c1", "이슈")
        e2 = add_response(event, "김철수", "1차 대응")
        e3 = add_response(e2, "이영희", "2차 대응")
        self.assertEqual(len(e3.timeline), 3)

    def test_resolve_crisis(self):
        """위기가 해결된다."""
        event = detect_crisis("c1", "이슈")
        resolved = resolve_crisis(event, "콘텐츠 수정 완료")
        self.assertEqual(resolved.status, "resolved")
        self.assertEqual(resolved.timeline[-1]["action"], "resolved")

    def test_resolve_crisis_preserves_info(self):
        """해결 후 기존 정보가 보존된다."""
        event = detect_crisis("c1", "이슈")
        event = add_response(event, "홍길동", "조치")
        resolved = resolve_crisis(event, "해결됨")
        self.assertEqual(resolved.event_id, event.event_id)
        self.assertIn("c1", resolved.affected_content)

    def test_get_active_crises(self):
        """미해결 위기만 반환한다."""
        e1 = detect_crisis("c1", "이슈 1")
        e2 = detect_crisis("c2", "이슈 2")
        e3 = resolve_crisis(detect_crisis("c3", "이슈 3"), "해결됨")

        warroom = Warroom(warroom_id="wr1", events=[e1, e2, e3], responders=["admin"])
        active = get_active_crises(warroom)
        self.assertEqual(len(active), 2)
        self.assertTrue(all(e.status != "resolved" for e in active))

    def test_get_active_crises_all_resolved(self):
        """모두 해결되면 빈 리스트."""
        e1 = resolve_crisis(detect_crisis("c1", "이슈"), "해결")
        warroom = Warroom(warroom_id="wr1", events=[e1], responders=[])
        self.assertEqual(get_active_crises(warroom), [])

    def test_get_active_crises_empty_warroom(self):
        """빈 워룸은 빈 리스트."""
        warroom = Warroom(warroom_id="wr1", events=[], responders=[])
        self.assertEqual(get_active_crises(warroom), [])

    def test_full_lifecycle(self):
        """전체 생명주기: 탐지 → 에스컬레이션 → 대응 → 해결."""
        event = detect_crisis("c1", "데이터 유출 가능성")
        self.assertEqual(event.status, "detected")

        event = escalate(event, "critical")
        self.assertEqual(event.status, "assessing")

        event = add_response(event, "보안팀", "긴급 조치 착수")
        self.assertEqual(event.status, "responding")

        event = resolve_crisis(event, "유출 차단 완료")
        self.assertEqual(event.status, "resolved")
        self.assertEqual(len(event.timeline), 4)

    def test_escalate_preserves_event_id(self):
        """에스컬레이션 후 이벤트 ID가 유지된다."""
        event = detect_crisis("c1", "이슈")
        original_id = event.event_id
        escalated = escalate(event, "high")
        self.assertEqual(escalated.event_id, original_id)


if __name__ == "__main__":
    unittest.main()
