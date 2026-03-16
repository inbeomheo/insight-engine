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


class TestGenerateOutlineEdgeCases(unittest.TestCase):
    """generate_outline 엣지 케이스 테스트"""

    def test_whitespace_only_topic(self):
        """공백만 있는 주제"""
        result = generate_outline('   ')
        self.assertEqual(result['outline'], [])

    def test_topic_stripped(self):
        """주제 앞뒤 공백 제거"""
        result = generate_outline('  AI  ')
        self.assertEqual(result['topic'], 'AI')

    def test_no_keywords_no_error(self):
        """keywords=None이어도 에러 없음"""
        result = generate_outline('주제', keywords=None)
        self.assertIsInstance(result['seo_tips'], list)

    def test_empty_keywords_list(self):
        """빈 키워드 리스트"""
        result = generate_outline('주제', keywords=[])
        self.assertIsInstance(result['seo_tips'], list)
        # 키워드 관련 팁은 포함되지 않음
        tips_text = ' '.join(result['seo_tips'])
        self.assertNotIn('타겟 키워드', tips_text)

    def test_comparison_has_option_sections(self):
        """비교 분석 템플릿에 옵션 A/B 섹션 존재"""
        result = generate_outline('프레임워크', 'comparison')
        texts = [s['text'] for s in result['outline']]
        has_option_a = any('옵션 A' in t for t in texts)
        has_option_b = any('옵션 B' in t for t in texts)
        self.assertTrue(has_option_a)
        self.assertTrue(has_option_b)

    def test_tutorial_has_steps(self):
        """튜토리얼 템플릿에 단계 섹션 존재"""
        result = generate_outline('React', 'tutorial')
        texts = [s['text'] for s in result['outline']]
        has_step = any('단계' in t for t in texts)
        self.assertTrue(has_step)

    def test_opinion_has_claim_section(self):
        """의견 템플릿에 주장 섹션 존재"""
        result = generate_outline('원격근무', 'opinion')
        texts = [s['text'] for s in result['outline']]
        has_claim = any('주장' in t for t in texts)
        self.assertTrue(has_claim)

    def test_many_keywords_capped(self):
        """키워드 5개 이상이면 5개만 팁에 포함"""
        keywords = ['키워드1', '키워드2', '키워드3', '키워드4', '키워드5', '키워드6']
        result = generate_outline('주제', keywords=keywords)
        tips_text = ' '.join(result['seo_tips'])
        self.assertNotIn('키워드6', tips_text)


class TestGetTemplatesDetails(unittest.TestCase):
    """get_templates 상세 테스트"""

    def test_all_five_templates(self):
        """5개 템플릿 모두 포함"""
        templates = get_templates()
        ids = {t['id'] for t in templates}
        expected = {'guide', 'listicle', 'comparison', 'tutorial', 'opinion'}
        self.assertEqual(ids, expected)

    def test_sections_count_positive(self):
        """모든 템플릿의 sections 수가 양수"""
        templates = get_templates()
        for t in templates:
            self.assertGreater(t['sections'], 0, f'{t["id"]} has no sections')


if __name__ == '__main__':
    unittest.main()
