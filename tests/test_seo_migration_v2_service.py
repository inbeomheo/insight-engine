"""SEO 마이그레이션 v2 서비스 테스트"""
import unittest
from services.seo_migration_v2_service import (
    create_plan, apply_rules, validate_plan, generate_htaccess,
    MigrationPlan, MigrationRule
)


class TestSeoMigrationV2Service(unittest.TestCase):

    def setUp(self):
        self.rules_config = [
            {'old_pattern': '/blog/old-post', 'new_pattern': '/blog/new-post', 'rule_type': 'exact', 'priority': 10},
            {'old_pattern': '/docs/', 'new_pattern': '/documentation/', 'rule_type': 'prefix', 'priority': 5},
        ]
        self.plan = create_plan(self.rules_config)

    def test_create_plan(self):
        self.assertIsInstance(self.plan, MigrationPlan)
        self.assertEqual(len(self.plan.rules), 2)
        self.assertFalse(self.plan.validated)

    def test_create_plan_sorted_by_priority(self):
        self.assertEqual(self.plan.rules[0].priority, 10)

    def test_apply_rules_exact(self):
        urls = ['/blog/old-post', '/blog/other']
        mappings = apply_rules(self.plan, urls)
        self.assertEqual(mappings['/blog/old-post'], '/blog/new-post')
        self.assertEqual(mappings['/blog/other'], '/blog/other')

    def test_apply_rules_prefix(self):
        urls = ['/docs/api/v1']
        mappings = apply_rules(self.plan, urls)
        self.assertEqual(mappings['/docs/api/v1'], '/documentation/api/v1')

    def test_apply_rules_regex(self):
        plan = create_plan([
            {'old_pattern': r'/post/(\d+)', 'new_pattern': r'/article/\1', 'rule_type': 'regex', 'priority': 1}
        ])
        mappings = apply_rules(plan, ['/post/123'])
        self.assertEqual(mappings['/post/123'], '/article/123')

    def test_apply_rules_no_match(self):
        mappings = apply_rules(self.plan, ['/contact'])
        self.assertEqual(mappings['/contact'], '/contact')

    def test_validate_plan_valid(self):
        errors = validate_plan(self.plan)
        self.assertEqual(len(errors), 0)

    def test_validate_plan_duplicate(self):
        plan = create_plan([
            {'old_pattern': '/a', 'new_pattern': '/b', 'rule_type': 'exact', 'priority': 1},
            {'old_pattern': '/a', 'new_pattern': '/c', 'rule_type': 'exact', 'priority': 2},
        ])
        errors = validate_plan(plan)
        dup_errors = [e for e in errors if '중복' in e]
        self.assertGreater(len(dup_errors), 0)

    def test_validate_plan_circular(self):
        plan = create_plan([
            {'old_pattern': '/a', 'new_pattern': '/b', 'rule_type': 'exact', 'priority': 1},
            {'old_pattern': '/b', 'new_pattern': '/a', 'rule_type': 'exact', 'priority': 2},
        ])
        errors = validate_plan(plan)
        circular_errors = [e for e in errors if '순환' in e]
        self.assertGreater(len(circular_errors), 0)

    def test_generate_htaccess(self):
        mappings = {'/old': '/new', '/same': '/same'}
        htaccess = generate_htaccess(mappings)
        self.assertIn('RewriteEngine On', htaccess)
        self.assertIn('old', htaccess)
        # /same은 변경 없으므로 포함 안됨
        self.assertNotIn('same', htaccess)

    def test_apply_rules_invalid_regex(self):
        plan = create_plan([
            {'old_pattern': '[invalid', 'new_pattern': '/x', 'rule_type': 'regex', 'priority': 1}
        ])
        mappings = apply_rules(plan, ['/test'])
        self.assertEqual(mappings['/test'], '/test')


if __name__ == '__main__':
    unittest.main()
