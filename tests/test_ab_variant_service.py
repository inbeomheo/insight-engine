"""ab_variant_service 단위 테스트"""
import unittest

from services.content.ab_variant_service import (
    generate_variants,
    get_variant_types,
    _extract_topic,
    _TITLE_PATTERNS,
    _INTRO_PATTERNS,
    _CTA_PATTERNS,
)


class TestGenerateVariants(unittest.TestCase):

    def test_empty_content(self):
        result = generate_variants('')
        self.assertEqual(result['total'], 0)

    def test_none_content(self):
        result = generate_variants(None)
        self.assertEqual(result['total'], 0)

    def test_basic_generation(self):
        result = generate_variants('인공지능에 대한 글입니다.', title='인공지능 입문')
        self.assertGreater(result['total'], 0)
        self.assertEqual(result['topic'], '인공지능 입문')

    def test_all_variant_types(self):
        result = generate_variants('콘텐츠 내용', title='제목')
        self.assertGreater(len(result['title_variants']), 0)
        self.assertGreater(len(result['intro_variants']), 0)
        self.assertGreater(len(result['cta_variants']), 0)

    def test_title_variants_count(self):
        result = generate_variants('콘텐츠', title='AI')
        self.assertEqual(len(result['title_variants']), len(_TITLE_PATTERNS))

    def test_intro_variants_count(self):
        result = generate_variants('콘텐츠', title='AI')
        self.assertEqual(len(result['intro_variants']), len(_INTRO_PATTERNS))

    def test_cta_variants_count(self):
        result = generate_variants('콘텐츠', title='AI')
        self.assertEqual(len(result['cta_variants']), len(_CTA_PATTERNS))

    def test_selective_types_title_only(self):
        result = generate_variants('콘텐츠', title='제목', variant_types=['title'])
        self.assertGreater(len(result['title_variants']), 0)
        self.assertEqual(len(result['intro_variants']), 0)
        self.assertEqual(len(result['cta_variants']), 0)

    def test_selective_types_cta_only(self):
        result = generate_variants('콘텐츠', title='제목', variant_types=['cta'])
        self.assertEqual(len(result['title_variants']), 0)
        self.assertGreater(len(result['cta_variants']), 0)

    def test_topic_in_title_variants(self):
        result = generate_variants('내용', title='머신러닝')
        for v in result['title_variants']:
            self.assertIn('머신러닝', v['text'])

    def test_variant_structure(self):
        result = generate_variants('콘텐츠', title='제목')
        for v in result['title_variants']:
            self.assertIn('type', v)
            self.assertIn('text', v)

    def test_total_count_correct(self):
        result = generate_variants('콘텐츠', title='제목')
        expected = (len(result['title_variants']) +
                    len(result['intro_variants']) +
                    len(result['cta_variants']))
        self.assertEqual(result['total'], expected)


class TestExtractTopic(unittest.TestCase):

    def test_from_title(self):
        topic = _extract_topic('인공지능 입문', '본문 내용')
        self.assertEqual(topic, '인공지능 입문')

    def test_from_heading(self):
        topic = _extract_topic('', '# 딥러닝 가이드\n본문')
        self.assertEqual(topic, '딥러닝 가이드')

    def test_from_first_sentence(self):
        topic = _extract_topic('', '자연어 처리는 중요합니다. 두 번째 문장.')
        self.assertIn('자연어', topic)

    def test_empty_fallback(self):
        topic = _extract_topic('', '')
        self.assertEqual(topic, '이 주제')

    def test_strips_heading_prefix(self):
        topic = _extract_topic('# 제목 텍스트', '')
        self.assertNotIn('#', topic)


class TestGetVariantTypes(unittest.TestCase):

    def test_returns_all_types(self):
        types = get_variant_types()
        self.assertIn('title', types)
        self.assertIn('intro', types)
        self.assertIn('cta', types)

    def test_title_types(self):
        types = get_variant_types()
        self.assertEqual(set(types['title']), set(_TITLE_PATTERNS.keys()))


if __name__ == '__main__':
    unittest.main()
