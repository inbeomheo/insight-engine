"""이해관계자 샌드박스 서비스 테스트."""

import unittest
from services.stakeholder_sandbox_service import (
    Stakeholder,
    SandboxView,
    create_sandbox,
    apply_redaction,
    add_annotation,
    compare_views,
)


class TestStakeholderSandboxService(unittest.TestCase):
    """StakeholderSandboxService 단위 테스트."""

    def _make_stakeholder(self, role: str, name: str = "테스트") -> Stakeholder:
        return Stakeholder(
            stakeholder_id=f"sh_{role}",
            name=name,
            role=role,
            view_preferences={},
        )

    def test_apply_redaction_basic(self):
        """민감 패턴이 [REDACTED]로 교체된다."""
        text = "연락처: test@example.com 으로 보내주세요"
        patterns = [r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"]
        result = apply_redaction(text, patterns)
        self.assertIn("[REDACTED]", result)
        self.assertNotIn("test@example.com", result)

    def test_apply_redaction_no_match(self):
        """패턴이 없으면 원본 그대로."""
        text = "깨끗한 텍스트"
        result = apply_redaction(text, [r"\d{10}"])
        self.assertEqual(result, text)

    def test_apply_redaction_multiple_patterns(self):
        """여러 패턴이 모두 적용된다."""
        text = "전화: 010-1234-5678, 이메일: a@b.com"
        patterns = [
            r"\b\d{3}[-.]?\d{4}[-.]?\d{4}\b",
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        ]
        result = apply_redaction(text, patterns)
        self.assertEqual(result.count("[REDACTED]"), 2)

    def test_create_sandbox_external_redacts(self):
        """external 역할은 연락처를 마스킹한다."""
        stakeholder = self._make_stakeholder("external")
        content = {"text": "문의: test@example.com 또는 010-1234-5678"}
        view = create_sandbox(content, stakeholder)
        self.assertNotIn("test@example.com", view.content_filtered)
        self.assertNotIn("010-1234-5678", view.content_filtered)
        self.assertIn("personal_info", view.redacted_fields)

    def test_create_sandbox_executive_no_redact(self):
        """executive 역할은 마스킹하지 않는다."""
        stakeholder = self._make_stakeholder("executive")
        content = {"text": "중요 정보: test@example.com"}
        view = create_sandbox(content, stakeholder)
        self.assertIn("test@example.com", view.content_filtered)
        self.assertEqual(view.redacted_fields, [])

    def test_create_sandbox_legal_no_redact(self):
        """legal 역할은 전체 접근."""
        stakeholder = self._make_stakeholder("legal")
        content = {"text": "010-1234-5678 연락처"}
        view = create_sandbox(content, stakeholder)
        self.assertIn("010-1234-5678", view.content_filtered)

    def test_create_sandbox_has_annotation(self):
        """기본 주석이 포함된다."""
        stakeholder = self._make_stakeholder("marketing")
        view = create_sandbox({"text": "test"}, stakeholder)
        self.assertTrue(len(view.annotations) > 0)
        self.assertTrue(any("마케팅" in a for a in view.annotations))

    def test_create_sandbox_view_id_format(self):
        """뷰 ID가 sv_ 접두사로 시작한다."""
        stakeholder = self._make_stakeholder("technical")
        view = create_sandbox({"text": "test"}, stakeholder)
        self.assertTrue(view.view_id.startswith("sv_"))

    def test_add_annotation(self):
        """주석을 추가한다."""
        stakeholder = self._make_stakeholder("executive")
        view = create_sandbox({"text": "test"}, stakeholder)
        initial_count = len(view.annotations)
        updated = add_annotation(view, "법무팀 검토 필요")
        self.assertEqual(len(updated.annotations), initial_count + 1)
        self.assertIn("법무팀 검토 필요", updated.annotations)

    def test_add_annotation_preserves_original(self):
        """기존 주석이 보존된다."""
        stakeholder = self._make_stakeholder("legal")
        view = create_sandbox({"text": "test"}, stakeholder)
        original_first = view.annotations[0] if view.annotations else None
        updated = add_annotation(view, "추가 메모")
        if original_first:
            self.assertIn(original_first, updated.annotations)

    def test_compare_views_basic(self):
        """2개 이상 뷰를 비교한다."""
        ext = self._make_stakeholder("external")
        exc = self._make_stakeholder("executive")
        content = {"text": "데이터: test@example.com 포함"}

        v1 = create_sandbox(content, ext)
        v2 = create_sandbox(content, exc)

        result = compare_views([v1, v2])
        self.assertTrue(result["compared"])
        self.assertEqual(result["view_count"], 2)
        self.assertIn("max_length_diff", result)

    def test_compare_views_single(self):
        """1개 뷰만으로는 비교 불가."""
        stakeholder = self._make_stakeholder("executive")
        view = create_sandbox({"text": "test"}, stakeholder)
        result = compare_views([view])
        self.assertFalse(result["compared"])

    def test_compare_views_empty(self):
        """빈 목록은 비교 불가."""
        result = compare_views([])
        self.assertFalse(result["compared"])

    def test_compare_views_redaction_diff(self):
        """외부 뷰는 마스킹으로 콘텐츠 길이가 다를 수 있다."""
        ext = self._make_stakeholder("external")
        exc = self._make_stakeholder("executive")
        long_email_content = {"text": "contact: verylongemail@verylongdomain.com here"}

        v_ext = create_sandbox(long_email_content, ext)
        v_exc = create_sandbox(long_email_content, exc)

        result = compare_views([v_ext, v_exc])
        self.assertTrue(result["compared"])


if __name__ == "__main__":
    unittest.main()
