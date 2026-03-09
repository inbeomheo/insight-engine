"""SEO 감사 서비스 테스트"""
import unittest
from services.seo_audit_service import (
    run_seo_audit,
    SEOAuditReport,
    SEOIssue,
    _check_title,
    _check_headings,
    _check_content_length,
    _calculate_grade,
)


class TestCalculateGrade(unittest.TestCase):
    """등급 계산 테스트"""

    def test_grade_a(self):
        self.assertEqual(_calculate_grade(95), "A")

    def test_grade_b(self):
        self.assertEqual(_calculate_grade(85), "B")

    def test_grade_c(self):
        self.assertEqual(_calculate_grade(75), "C")

    def test_grade_d(self):
        self.assertEqual(_calculate_grade(55), "D")

    def test_grade_f(self):
        self.assertEqual(_calculate_grade(30), "F")


class TestCheckTitle(unittest.TestCase):
    """제목 검사 테스트"""

    def test_no_title(self):
        issues, passed = _check_title("No heading here.")
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].severity, "error")

    def test_good_title(self):
        issues, passed = _check_title("# SEO 최적화를 위한 완벽 가이드\n\nBody text.")
        self.assertEqual(len(issues), 0)
        self.assertGreater(len(passed), 0)

    def test_multiple_h1(self):
        content = "# Title One\n\n# Title Two\n\nBody."
        issues, _ = _check_title(content)
        self.assertTrue(any(i.severity == "warning" for i in issues))


class TestCheckHeadings(unittest.TestCase):
    """헤딩 구조 테스트"""

    def test_insufficient_headings(self):
        issues, _ = _check_headings("# Only one heading")
        self.assertEqual(len(issues), 1)

    def test_skipped_heading_level(self):
        content = "# H1\n\n### H3 skipped H2"
        issues, _ = _check_headings(content)
        self.assertTrue(any("건너뛰" in i.description for i in issues))


class TestRunSeoAudit(unittest.TestCase):
    """SEO 감사 통합 테스트"""

    def test_empty_content(self):
        result = run_seo_audit("")
        self.assertIsInstance(result, SEOAuditReport)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.grade, "F")

    def test_well_structured_content(self):
        content = """# 완벽한 SEO 가이드: 검색 엔진 최적화 마스터하기

이 글은 SEO의 기본부터 고급 기술까지 다루는 종합 가이드입니다. 검색 엔진 최적화는 웹사이트의 가시성을 높이는 핵심 전략입니다.

## 1. SEO 기본 개념

검색 엔진 최적화(SEO)는 검색 결과에서 더 높은 순위를 차지하기 위한 프로세스입니다.
이를 통해 더 많은 유기적 트래픽을 확보할 수 있습니다.

## 2. 키워드 연구

키워드 연구는 SEO의 출발점입니다. 적절한 키워드를 선정하면 타겟 고객에게 효과적으로 도달할 수 있습니다.

## 3. 콘텐츠 최적화

고품질 콘텐츠는 SEO의 핵심입니다. [Google 가이드](https://google.com/seo) 참조.

## 4. 기술적 SEO

사이트 속도, 모바일 최적화, 구조화된 데이터는 기술적 SEO의 핵심 요소입니다.
이러한 요소들을 개선하면 검색 순위가 크게 향상됩니다. 정기적인 기술적 SEO 감사를 통해
문제점을 파악하고 개선하는 것이 중요합니다.
"""
        result = run_seo_audit(content, url="https://example.com/seo-guide")
        self.assertGreater(result.score, 50)
        self.assertEqual(result.url, "https://example.com/seo-guide")
        self.assertIn(result.grade, ("A", "B", "C"))

    def test_poor_content(self):
        content = "Short."
        result = run_seo_audit(content)
        self.assertLess(result.score, 50)

    def test_issues_are_seo_issues(self):
        content = "No structure."
        result = run_seo_audit(content)
        for issue in result.issues:
            self.assertIsInstance(issue, SEOIssue)
            self.assertIn(issue.severity, ("info", "warning", "error"))

    def test_score_range(self):
        content = "# Test\n\n" + "word " * 200
        result = run_seo_audit(content)
        self.assertGreaterEqual(result.score, 0.0)
        self.assertLessEqual(result.score, 100.0)

    def test_link_check(self):
        content = "# Good Title Here\n\n" + "Body text " * 50 + "\n[](https://empty-text.com)"
        result = run_seo_audit(content)
        link_issues = [i for i in result.issues if i.category == "links"]
        self.assertGreater(len(link_issues), 0)

    def test_image_alt_check(self):
        content = "# Image Test Title\n\n" + "Content " * 50 + "\n![](image.png)"
        result = run_seo_audit(content)
        img_issues = [i for i in result.issues if i.category == "images"]
        self.assertGreater(len(img_issues), 0)

    def test_whitespace_only(self):
        result = run_seo_audit("   \n\t  ")
        self.assertEqual(result.grade, "F")


if __name__ == "__main__":
    unittest.main()
