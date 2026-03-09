"""WCAG 프리플라이트 서비스 테스트"""

import unittest

from services.wcag_preflight_service import (
    WCAGIssue,
    PreflightReport,
    check_alt_text,
    check_heading_hierarchy,
    check_color_contrast,
    run_preflight,
)


class TestCheckAltText(unittest.TestCase):
    """check_alt_text 함수 테스트"""

    def test_alt_누락_감지(self):
        html = '<img src="test.jpg">'
        issues = check_alt_text(html)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].criterion, "1.1.1")

    def test_alt_빈값_감지(self):
        html = '<img src="test.jpg" alt="">'
        issues = check_alt_text(html)
        self.assertEqual(len(issues), 1)

    def test_alt_정상(self):
        html = '<img src="test.jpg" alt="테스트 이미지">'
        issues = check_alt_text(html)
        self.assertEqual(len(issues), 0)

    def test_여러_img_태그(self):
        html = '<img src="a.jpg"><img src="b.jpg" alt="ok"><img src="c.jpg">'
        issues = check_alt_text(html)
        self.assertEqual(len(issues), 2)  # a.jpg, c.jpg 누락

    def test_img_없음(self):
        html = '<div>텍스트만 있는 HTML</div>'
        issues = check_alt_text(html)
        self.assertEqual(len(issues), 0)

    def test_자기닫힘_태그(self):
        html = '<img src="test.jpg" />'
        issues = check_alt_text(html)
        self.assertEqual(len(issues), 1)


class TestCheckHeadingHierarchy(unittest.TestCase):
    """check_heading_hierarchy 함수 테스트"""

    def test_정상_순서(self):
        html = '<h1>제목</h1><h2>소제목</h2><h3>하위</h3>'
        issues = check_heading_hierarchy(html)
        self.assertEqual(len(issues), 0)

    def test_h1_누락(self):
        html = '<h2>소제목</h2>'
        issues = check_heading_hierarchy(html)
        self.assertGreater(len(issues), 0)

    def test_레벨_건너뛰기(self):
        html = '<h1>제목</h1><h3>건너뛴 헤딩</h3>'
        issues = check_heading_hierarchy(html)
        has_skip_issue = any("건너뛰" in i.description for i in issues)
        self.assertTrue(has_skip_issue)

    def test_헤딩_없음(self):
        html = '<p>헤딩 없는 문서</p>'
        issues = check_heading_hierarchy(html)
        self.assertEqual(len(issues), 0)


class TestCheckColorContrast(unittest.TestCase):
    """check_color_contrast 함수 테스트"""

    def test_충분한_대비(self):
        # 검정 (#000000) 대 흰색 (#FFFFFF): 21:1
        issue = check_color_contrast("#000000", "#FFFFFF")
        self.assertIsNone(issue)

    def test_불충분한_대비(self):
        # 밝은 회색 대 흰색: 낮은 대비
        issue = check_color_contrast("#CCCCCC", "#FFFFFF")
        self.assertIsNotNone(issue)
        self.assertEqual(issue.criterion, "1.4.3")

    def test_단축_헥스(self):
        issue = check_color_contrast("#000", "#FFF")
        self.assertIsNone(issue)

    def test_잘못된_색상_형식(self):
        issue = check_color_contrast("invalid", "#FFFFFF")
        self.assertIsNotNone(issue)


class TestRunPreflight(unittest.TestCase):
    """run_preflight 함수 테스트"""

    def test_깨끗한_HTML(self):
        html = '<h1>제목</h1><h2>소제목</h2><img src="a.jpg" alt="설명">'
        report = run_preflight(html)
        self.assertEqual(len(report.issues), 0)
        self.assertEqual(report.score, 100.0)

    def test_이슈_있는_HTML(self):
        html = '<h2>건너뛴 헤딩</h2><img src="a.jpg">'
        report = run_preflight(html)
        self.assertGreater(len(report.issues), 0)
        self.assertLess(report.score, 100.0)

    def test_빈_HTML(self):
        report = run_preflight("")
        self.assertEqual(len(report.issues), 0)

    def test_보고서_구조(self):
        report = run_preflight("<h1>Test</h1>")
        self.assertIsInstance(report.issues, list)
        self.assertGreaterEqual(report.pass_count, 0)
        self.assertGreaterEqual(report.fail_count, 0)


if __name__ == "__main__":
    unittest.main()
