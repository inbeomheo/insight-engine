"""Title Tag Length Checker 서비스 테스트."""
import unittest
from services.seo.title_tag_length_service import check_title_tag_length


class TestTitleTagLength(unittest.TestCase):

    def test_empty_content(self):
        result = check_title_tag_length('')
        self.assertEqual(result['score'], 0.0)

    def test_none_content(self):
        result = check_title_tag_length(None)
        self.assertEqual(result['score'], 0.0)

    def test_no_title(self):
        content = '제목 없는 평문입니다. 헤딩이 없습니다.'
        result = check_title_tag_length(content)
        self.assertEqual(result['title'], '')

    def test_h1_extraction(self):
        content = '# SEO 최적화 가이드\n\n본문 내용입니다.'
        result = check_title_tag_length(content)
        self.assertIn('SEO', result['title'])

    def test_html_title_extraction(self):
        content = '<title>10가지 효과적인 마케팅 전략</title>'
        result = check_title_tag_length(content)
        self.assertIn('마케팅', result['title'])

    def test_frontmatter_title(self):
        content = """---
title: "완벽한 SEO 가이드"
---
본문입니다."""
        result = check_title_tag_length(content)
        self.assertIn('SEO', result['title'])

    def test_optimal_korean_length(self):
        content = '# 효과적인 콘텐츠 마케팅 전략 가이드'  # ~17자
        result = check_title_tag_length(content)
        self.assertTrue(result['checks']['optimal_length'])

    def test_short_title(self):
        content = '# 짧음'
        result = check_title_tag_length(content)
        self.assertFalse(result['checks']['not_too_short'])

    def test_long_title(self):
        long_title = '아' * 45
        content = f'# {long_title}'
        result = check_title_tag_length(content)
        self.assertFalse(result['checks']['not_too_long'])

    def test_english_title_optimal(self):
        content = '# The Complete Guide to Content Marketing Strategies'  # ~50자
        result = check_title_tag_length(content)
        self.assertEqual(result['summary']['language'], 'en')

    def test_separator_abuse(self):
        content = '# A | B | C | D - E - F - G'
        result = check_title_tag_length(content)
        self.assertFalse(result['checks']['no_separator_abuse'])

    def test_score_range(self):
        content = '# 테스트 제목입니다'
        result = check_title_tag_length(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_suggestions_exist(self):
        content = '# 짧'
        result = check_title_tag_length(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_return_structure(self):
        content = '# 테스트'
        result = check_title_tag_length(content)
        self.assertIn('title', result)
        self.assertIn('checks', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('length', result['summary'])
        self.assertIn('language', result['summary'])
        self.assertIn('quality_level', result['summary'])


if __name__ == '__main__':
    unittest.main()
