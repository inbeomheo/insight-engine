"""SEO 마이그레이션 서비스 테스트"""
import unittest
from services.seo_migration_service import (
    plan_migration,
    validate_redirects,
    MigrationPlan,
    URLMapping,
    RedirectIssue,
    _is_valid_url,
    _determine_priority,
)


class TestIsValidUrl(unittest.TestCase):
    """URL 유효성 검사 테스트"""

    def test_valid_url(self):
        self.assertTrue(_is_valid_url("https://example.com"))

    def test_invalid_url(self):
        self.assertFalse(_is_valid_url("not-a-url"))

    def test_path_only(self):
        self.assertFalse(_is_valid_url("/path/to/page"))


class TestDeterminePriority(unittest.TestCase):
    """우선순위 결정 테스트"""

    def test_root_high(self):
        self.assertEqual(_determine_priority("https://example.com/"), "high")

    def test_shallow_path_high(self):
        self.assertEqual(_determine_priority("https://example.com/about"), "high")

    def test_medium_depth(self):
        self.assertEqual(_determine_priority("https://example.com/blog/post"), "medium")

    def test_deep_path_low(self):
        self.assertEqual(_determine_priority("https://example.com/a/b/c/d"), "low")


class TestPlanMigration(unittest.TestCase):
    """마이그레이션 계획 테스트"""

    def test_empty_urls(self):
        result = plan_migration([], [])
        self.assertIsInstance(result, MigrationPlan)
        self.assertEqual(result.total_redirects, 0)

    def test_basic_migration(self):
        old = ["https://old.com/page1", "https://old.com/page2"]
        new = ["https://new.com/page1", "https://new.com/page2"]
        result = plan_migration(old, new)
        self.assertEqual(result.total_redirects, 2)
        self.assertEqual(len(result.mappings), 2)

    def test_mapping_fields(self):
        old = ["https://old.com/about"]
        new = ["https://new.com/about"]
        result = plan_migration(old, new)
        m = result.mappings[0]
        self.assertIsInstance(m, URLMapping)
        self.assertEqual(m.redirect_type, 301)

    def test_missing_new_url(self):
        """새 URL이 부족하면 동일 URL 유지"""
        old = ["https://old.com/a", "https://old.com/b"]
        new = ["https://new.com/a"]
        result = plan_migration(old, new)
        self.assertEqual(result.mappings[1].new_url, "https://old.com/b")

    def test_risk_level_low(self):
        old = ["https://old.com/a"]
        new = ["https://new.com/a"]
        result = plan_migration(old, new)
        self.assertEqual(result.risk_level, "low")

    def test_risk_level_scales(self):
        old = [f"https://old.com/{i}" for i in range(60)]
        new = [f"https://new.com/{i}" for i in range(60)]
        result = plan_migration(old, new)
        self.assertIn(result.risk_level, ("high", "critical"))

    def test_empty_old_url_skipped(self):
        old = ["", "https://old.com/b"]
        new = ["https://new.com/a", "https://new.com/b"]
        result = plan_migration(old, new)
        self.assertEqual(result.total_redirects, 1)

    def test_priority_assignment(self):
        old = ["https://old.com/", "https://old.com/a/b/c/d"]
        new = ["https://new.com/", "https://new.com/a/b/c/d"]
        result = plan_migration(old, new)
        self.assertEqual(result.mappings[0].priority, "high")
        self.assertEqual(result.mappings[1].priority, "low")


class TestValidateRedirects(unittest.TestCase):
    """리다이렉트 검증 테스트"""

    def test_empty_mapping(self):
        result = validate_redirects([])
        self.assertEqual(result, [])

    def test_self_redirect(self):
        mapping = [{"old_url": "https://a.com", "new_url": "https://a.com"}]
        result = validate_redirects(mapping)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].issue_type, "self_redirect")

    def test_chain_redirect(self):
        mapping = [
            {"old_url": "https://a.com", "new_url": "https://b.com"},
            {"old_url": "https://b.com", "new_url": "https://c.com"},
        ]
        result = validate_redirects(mapping)
        chain_issues = [i for i in result if i.issue_type == "chain_redirect"]
        self.assertGreater(len(chain_issues), 0)

    def test_missing_target(self):
        mapping = [{"old_url": "https://a.com", "new_url": ""}]
        result = validate_redirects(mapping)
        missing = [i for i in result if i.issue_type == "missing_target"]
        self.assertGreater(len(missing), 0)

    def test_valid_mapping(self):
        mapping = [{"old_url": "https://a.com", "new_url": "https://b.com"}]
        result = validate_redirects(mapping)
        self.assertEqual(len(result), 0)

    def test_issue_fields(self):
        mapping = [{"old_url": "https://a.com", "new_url": "https://a.com"}]
        result = validate_redirects(mapping)
        issue = result[0]
        self.assertIsInstance(issue, RedirectIssue)
        self.assertTrue(issue.description)


if __name__ == "__main__":
    unittest.main()
