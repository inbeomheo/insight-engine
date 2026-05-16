"""content_template_service 단위 테스트"""
import unittest

from services.content.content_template_service import (
    extract_template,
    apply_template,
    list_templates,
    BUILTIN_TEMPLATES,
)


class TestExtractTemplate(unittest.TestCase):

    def test_empty(self):
        result = extract_template('')
        self.assertEqual(result['section_count'], 0)

    def test_basic_extraction(self):
        content = '# 제목\n## 서론\n내용\n## 본론\n내용\n## 결론\n내용'
        result = extract_template(content, template_name='테스트')
        self.assertEqual(result['name'], '테스트')
        self.assertEqual(result['section_count'], 4)

    def test_section_levels(self):
        content = '# H1\n## H2\n### H3'
        result = extract_template(content)
        levels = [s['level'] for s in result['sections']]
        self.assertEqual(levels, [1, 2, 3])

    def test_auto_name(self):
        content = '# 제목\n## 섹션'
        result = extract_template(content)
        self.assertEqual(result['name'], '커스텀 템플릿')


class TestApplyTemplate(unittest.TestCase):

    def test_builtin_blog(self):
        result = apply_template(template_id='blog_post')
        self.assertIn('# {제목}', result['markdown'])
        self.assertEqual(result['template_name'], '블로그 포스트')
        self.assertGreater(result['section_count'], 0)

    def test_builtin_tutorial(self):
        result = apply_template(template_id='tutorial')
        self.assertIn('단계', result['markdown'])

    def test_all_builtins_valid(self):
        for tid in BUILTIN_TEMPLATES:
            result = apply_template(template_id=tid)
            self.assertGreater(len(result['markdown']), 0)

    def test_placeholder_substitution(self):
        result = apply_template(template_id='blog_post', placeholders={'제목': '인공지능 가이드'})
        self.assertIn('인공지능 가이드', result['markdown'])
        self.assertNotIn('{제목}', result['markdown'])

    def test_custom_sections(self):
        sections = [
            {'level': 1, 'title': '커스텀 제목'},
            {'level': 2, 'title': '커스텀 섹션'},
        ]
        result = apply_template(custom_sections=sections)
        self.assertIn('# 커스텀 제목', result['markdown'])
        self.assertEqual(result['section_count'], 2)

    def test_empty_params(self):
        result = apply_template()
        self.assertEqual(result['markdown'], '')

    def test_invalid_template_id(self):
        result = apply_template(template_id='nonexistent')
        self.assertEqual(result['markdown'], '')


class TestListTemplates(unittest.TestCase):

    def test_returns_all(self):
        templates = list_templates()
        self.assertEqual(len(templates), len(BUILTIN_TEMPLATES))

    def test_template_structure(self):
        templates = list_templates()
        for t in templates:
            self.assertIn('id', t)
            self.assertIn('name', t)
            self.assertIn('section_count', t)
            self.assertIn('sections', t)

    def test_blog_post_exists(self):
        templates = list_templates()
        ids = [t['id'] for t in templates]
        self.assertIn('blog_post', ids)


if __name__ == '__main__':
    unittest.main()
