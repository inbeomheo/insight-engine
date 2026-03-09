"""런북 캔버스 서비스 테스트"""

import unittest
from services.runbook_canvas_service import (
    RunbookStep, Runbook,
    create_runbook, add_step, validate_runbook, export_as_checklist,
)


class TestCreateRunbook(unittest.TestCase):
    """create_runbook 테스트"""

    def test_create_basic(self):
        """기본 런북 생성"""
        rb = create_runbook("배포 절차서", "운영팀")
        self.assertTrue(rb.runbook_id.startswith("runbook_"))
        self.assertEqual(rb.title, "배포 절차서")
        self.assertEqual(rb.owner, "운영팀")
        self.assertEqual(rb.version, "1.0")
        self.assertEqual(len(rb.steps), 0)

    def test_empty_title_raises(self):
        """빈 제목은 ValueError"""
        with self.assertRaises(ValueError):
            create_runbook("   ", "owner")

    def test_title_trimmed(self):
        """제목 양쪽 공백 제거"""
        rb = create_runbook("  절차서  ", "팀")
        self.assertEqual(rb.title, "절차서")


class TestAddStep(unittest.TestCase):
    """add_step 테스트"""

    def setUp(self):
        self.rb = create_runbook("테스트 런북", "팀")

    def test_add_manual_step(self):
        """수동 단계 추가"""
        step_cfg = {
            "title": "서버 확인",
            "description": "서버 상태 확인",
            "step_type": "manual",
            "checklist": ["CPU 확인", "메모리 확인"],
        }
        updated = add_step(self.rb, step_cfg)
        self.assertEqual(len(updated.steps), 1)
        self.assertEqual(updated.steps[0].step_type, "manual")

    def test_add_automated_step(self):
        """자동 단계 추가"""
        step_cfg = {
            "title": "배포 스크립트",
            "description": "자동 배포",
            "step_type": "automated",
        }
        updated = add_step(self.rb, step_cfg)
        self.assertEqual(updated.steps[0].step_type, "automated")

    def test_add_decision_step(self):
        """판단 단계 추가"""
        step_cfg = {
            "title": "롤백 여부",
            "description": "롤백할지 결정",
            "step_type": "decision",
            "checklist": ["에러율 확인", "응답 시간 확인"],
        }
        updated = add_step(self.rb, step_cfg)
        self.assertEqual(updated.steps[0].step_type, "decision")

    def test_invalid_step_type_raises(self):
        """유효하지 않은 단계 유형은 ValueError"""
        with self.assertRaises(ValueError):
            add_step(self.rb, {"title": "잘못됨", "step_type": "invalid"})

    def test_add_step_with_next_steps(self):
        """다음 단계 참조 포함"""
        cfg = {
            "step_id": "s1",
            "title": "1단계",
            "step_type": "manual",
            "next_steps": ["s2", "s3"],
        }
        updated = add_step(self.rb, cfg)
        self.assertEqual(updated.steps[0].next_steps, ["s2", "s3"])


class TestValidateRunbook(unittest.TestCase):
    """validate_runbook 테스트"""

    def test_valid_runbook(self):
        """유효한 런북 — 오류 없음"""
        rb = create_runbook("테스트", "팀")
        rb = add_step(rb, {
            "step_id": "s1", "title": "1단계", "step_type": "manual",
            "next_steps": ["s2"],
        })
        rb = add_step(rb, {
            "step_id": "s2", "title": "2단계", "step_type": "automated",
        })
        errors = validate_runbook(rb)
        self.assertEqual(len(errors), 0)

    def test_orphan_reference(self):
        """고아 참조 탐지"""
        rb = create_runbook("테스트", "팀")
        rb = add_step(rb, {
            "step_id": "s1", "title": "1단계", "step_type": "manual",
            "next_steps": ["nonexistent"],
        })
        errors = validate_runbook(rb)
        self.assertTrue(any("고아" in e for e in errors))

    def test_self_cycle(self):
        """자기 순환 탐지"""
        rb = create_runbook("테스트", "팀")
        rb = add_step(rb, {
            "step_id": "s1", "title": "1단계", "step_type": "manual",
            "next_steps": ["s1"],
        })
        errors = validate_runbook(rb)
        self.assertTrue(any("순환" in e for e in errors))

    def test_decision_without_checklist(self):
        """decision 단계에 체크리스트 없으면 경고"""
        rb = create_runbook("테스트", "팀")
        rb = add_step(rb, {
            "step_id": "s1", "title": "판단", "step_type": "decision",
            "checklist": [],
        })
        errors = validate_runbook(rb)
        self.assertTrue(any("체크리스트" in e for e in errors))

    def test_empty_runbook_valid(self):
        """빈 런북은 유효"""
        rb = create_runbook("빈 런북", "팀")
        errors = validate_runbook(rb)
        self.assertEqual(len(errors), 0)


class TestExportAsChecklist(unittest.TestCase):
    """export_as_checklist 테스트"""

    def test_export_basic(self):
        """기본 체크리스트 내보내기"""
        rb = create_runbook("배포 절차", "운영팀")
        rb = add_step(rb, {
            "title": "서버 확인", "description": "상태 점검",
            "step_type": "manual",
            "checklist": ["CPU", "메모리"],
        })

        text = export_as_checklist(rb)
        self.assertIn("배포 절차", text)
        self.assertIn("운영팀", text)
        self.assertIn("서버 확인", text)
        self.assertIn("[ ] CPU", text)

    def test_export_contains_step_types(self):
        """단계 유형 표시"""
        rb = create_runbook("테스트", "팀")
        rb = add_step(rb, {"title": "자동화", "step_type": "automated", "description": ""})

        text = export_as_checklist(rb)
        self.assertIn("자동", text)

    def test_export_empty_runbook(self):
        """빈 런북 내보내기"""
        rb = create_runbook("빈 절차", "팀")
        text = export_as_checklist(rb)
        self.assertIn("빈 절차", text)


if __name__ == "__main__":
    unittest.main()
