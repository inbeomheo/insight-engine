"""outline_generator_service 단위 테스트"""
import unittest

from services.content.outline_generator_service import (
    generate_outline,
    get_templates,
)


class TestGenerateOutline(unittest.TestCase):

    def test_empty_topic(self):
        result = generate_outline('')
        self.assertEqual(result['topic'], '')
        self.assertEqual(result['outline'], [])

    def test_none_topic(self):
        result = generate_outline(None)
        self.assertEqual(result['outline'], [])

    def test_guide_template(self):
        result = generate_outline('파이썬 프로그래밍', 'guide')
        self.assertEqual(result['template'], 'guide')
        self.assertEqual(result['template_label'], '가이드')
        self.assertGreater(len(result['outline']), 0)
        # H2 섹션 확인
        for section in result['outline']:
            self.assertEqual(section['level'], 2)
            self.assertIn('파이썬 프로그래밍', section['text'])
            break  # 첫 번째만

    def test_listicle_template(self):
        result = generate_outline('생산성 팁', 'listicle')
        self.assertEqual(result['template'], 'listicle')
        self.assertGreater(len(result['outline']), 3)

    def test_all_templates(self):
        for tmpl in ('guide', 'listicle', 'comparison', 'tutorial', 'opinion'):
            result = generate_outline('테스트 주제', tmpl)
            self.assertEqual(result['template'], tmpl)
            self.assertGreater(len(result['outline']), 0)

    def test_invalid_template_defaults_to_guide(self):
        result = generate_outline('주제', 'invalid')
        self.assertEqual(result['template'], 'guide')

    def test_markdown_output(self):
        result = generate_outline('AI 기술')
        self.assertIn('# AI 기술', result['markdown'])
        self.assertIn('##', result['markdown'])

    def test_estimated_word_count(self):
        result = generate_outline('블로그 작성')
        self.assertGreater(result['estimated_word_count'], 0)

    def test_seo_tips(self):
        result = generate_outline('SEO 전략', keywords=['검색엔진', '키워드'])
        self.assertGreater(len(result['seo_tips']), 0)
        # 키워드가 팁에 포함
        tips_text = ' '.join(result['seo_tips'])
        self.assertIn('검색엔진', tips_text)

    def test_children_structure(self):
        result = generate_outline('주제', 'guide')
        has_children = any(len(s['children']) > 0 for s in result['outline'])
        self.assertTrue(has_children)


class TestGetTemplates(unittest.TestCase):

    def test_returns_templates(self):
        templates = get_templates()
        self.assertGreater(len(templates), 0)
        self.assertTrue(all('id' in t and 'label' in t for t in templates))
        ids = [t['id'] for t in templates]
        self.assertIn('guide', ids)
        self.assertIn('listicle', ids)


if __name__ == '__main__':
    unittest.main()
