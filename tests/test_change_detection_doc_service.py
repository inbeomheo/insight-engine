"""변경 감지 문서 서비스 테스트"""

import unittest

from services.change_detection_doc_service import (
    DocVersion,
    ChangeReport,
    detect_changes,
    highlight_changes,
    is_significant_change,
    summarize_changes,
)


class TestDetectChanges(unittest.TestCase):
    """detect_changes 함수 테스트"""

    def test_동일_텍스트(self):
        report = detect_changes("hello\nworld", "hello\nworld")
        self.assertEqual(len(report.added_lines), 0)
        self.assertEqual(len(report.removed_lines), 0)
        self.assertEqual(report.change_ratio, 0.0)

    def test_라인_추가(self):
        report = detect_changes("hello", "hello\nnew line")
        self.assertIn("new line", report.added_lines)
        self.assertGreater(report.change_ratio, 0)

    def test_라인_삭제(self):
        report = detect_changes("hello\nold line", "hello")
        self.assertIn("old line", report.removed_lines)

    def test_라인_수정(self):
        report = detect_changes("hello world", "hello universe")
        self.assertIn("hello world", report.removed_lines)
        self.assertIn("hello universe", report.added_lines)

    def test_빈_텍스트_비교(self):
        report = detect_changes("", "")
        self.assertEqual(report.change_ratio, 0.0)

    def test_change_ratio_범위(self):
        report = detect_changes("a\nb\nc", "x\ny\nz")
        self.assertGreaterEqual(report.change_ratio, 0)
        self.assertLessEqual(report.change_ratio, 1.0)

    def test_modified_count(self):
        report = detect_changes("line1\nline2", "line1\nline3\nline4")
        self.assertEqual(report.modified_count, len(report.added_lines) + len(report.removed_lines))


class TestHighlightChanges(unittest.TestCase):
    """highlight_changes 함수 테스트"""

    def test_추가_삭제_표시(self):
        report = ChangeReport(
            added_lines=["new line"],
            removed_lines=["old line"],
            modified_count=2,
            change_ratio=0.5,
        )
        result = highlight_changes(report)
        self.assertIn("+ new line", result)
        self.assertIn("- old line", result)

    def test_변경_없음(self):
        report = ChangeReport()
        result = highlight_changes(report)
        self.assertEqual(result, "")


class TestIsSignificantChange(unittest.TestCase):
    """is_significant_change 함수 테스트"""

    def test_유의미_변경(self):
        report = ChangeReport(change_ratio=0.5)
        self.assertTrue(is_significant_change(report, 0.1))

    def test_사소한_변경(self):
        report = ChangeReport(change_ratio=0.05)
        self.assertFalse(is_significant_change(report, 0.1))

    def test_경계값(self):
        report = ChangeReport(change_ratio=0.1)
        self.assertFalse(is_significant_change(report, 0.1))  # > 이므로 동일값은 False


class TestSummarizeChanges(unittest.TestCase):
    """summarize_changes 함수 테스트"""

    def test_추가_삭제_요약(self):
        report = ChangeReport(
            added_lines=["a", "b"],
            removed_lines=["c"],
            change_ratio=0.5,
        )
        summary = summarize_changes(report)
        self.assertIn("2개 라인 추가", summary)
        self.assertIn("1개 라인 삭제", summary)
        self.assertIn("변경률", summary)

    def test_변경_없음_요약(self):
        report = ChangeReport()
        summary = summarize_changes(report)
        self.assertEqual(summary, "변경 사항 없음")


if __name__ == "__main__":
    unittest.main()
