"""안전 패치 큐 서비스 테스트"""
import unittest
from services.safety_patch_service import (
    queue_safety_patches,
    SafetyPatch,
    _generate_patch,
    _scan_patterns,
)


class TestGeneratePatch(unittest.TestCase):
    """패치 생성 테스트"""

    def test_outdated_link(self):
        result = _generate_patch("http://example.com", "outdated_link")
        self.assertEqual(result, "https://example.com")

    def test_deprecated_info(self):
        result = _generate_patch("Python 2", "deprecated_info")
        self.assertIn("[지원 종료]", result)

    def test_policy_change(self):
        result = _generate_patch("무료 SSL", "policy_change")
        self.assertIn("[정책 변경]", result)

    def test_factual_error(self):
        result = _generate_patch("지구는 평평", "factual_error")
        self.assertIn("[사실 확인 필요]", result)

    def test_unknown_type(self):
        result = _generate_patch("text", "unknown")
        self.assertEqual(result, "text")


class TestQueueSafetyPatches(unittest.TestCase):
    """안전 패치 큐 테스트"""

    def test_empty_contents(self):
        result = queue_safety_patches([])
        self.assertEqual(result, [])

    def test_http_link_detected(self):
        contents = [{"id": "p1", "text": "Visit http://example.com for info."}]
        result = queue_safety_patches(contents)
        self.assertGreater(len(result), 0)
        self.assertEqual(result[0].patch_type, "outdated_link")
        self.assertEqual(result[0].content_id, "p1")

    def test_deprecated_python2(self):
        contents = [{"id": "p2", "text": "Use Python 2 for scripting."}]
        result = queue_safety_patches(contents)
        dep_patches = [p for p in result if p.patch_type == "deprecated_info"]
        self.assertGreater(len(dep_patches), 0)

    def test_ie11_deprecated(self):
        contents = [{"id": "p3", "text": "IE 11 support is important."}]
        result = queue_safety_patches(contents)
        dep_patches = [p for p in result if p.patch_type == "deprecated_info"]
        self.assertGreater(len(dep_patches), 0)

    def test_flash_deprecated(self):
        contents = [{"id": "p4", "text": "Install Adobe Flash for videos."}]
        result = queue_safety_patches(contents)
        dep_patches = [p for p in result if p.patch_type == "deprecated_info"]
        self.assertGreater(len(dep_patches), 0)

    def test_no_issues_clean_content(self):
        contents = [{"id": "p5", "text": "Python 3 is modern and fast."}]
        result = queue_safety_patches(contents)
        self.assertEqual(len(result), 0)

    def test_multiple_contents(self):
        contents = [
            {"id": "p6", "text": "Visit http://old.com"},
            {"id": "p7", "text": "Use Python 2"},
        ]
        result = queue_safety_patches(contents)
        ids = {p.content_id for p in result}
        self.assertIn("p6", ids)
        self.assertIn("p7", ids)

    def test_empty_text_skipped(self):
        contents = [{"id": "p8", "text": ""}]
        result = queue_safety_patches(contents)
        self.assertEqual(len(result), 0)

    def test_patch_fields(self):
        contents = [{"id": "p9", "text": "http://test.com is unsafe."}]
        result = queue_safety_patches(contents)
        patch = result[0]
        self.assertIsInstance(patch, SafetyPatch)
        self.assertTrue(patch.original_text)
        self.assertTrue(patch.patched_text)
        self.assertTrue(patch.reason)

    def test_factual_error_detected(self):
        contents = [{"id": "p10", "text": "만리장성은 우주에서 보인다."}]
        result = queue_safety_patches(contents)
        fact_patches = [p for p in result if p.patch_type == "factual_error"]
        self.assertGreater(len(fact_patches), 0)


if __name__ == "__main__":
    unittest.main()
