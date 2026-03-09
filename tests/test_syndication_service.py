"""syndication_service 단위 테스트"""
import unittest

from services.syndication_service import (
    syndicate_content,
    SyndicationResult,
    _strip_markdown,
    _extract_keywords,
    _truncate_with_ellipsis,
    _PLATFORM_CONFIG,
)


class TestStripMarkdown(unittest.TestCase):

    def test_headers_removed(self):
        result = _strip_markdown('# 제목\n## 부제목')
        self.assertNotIn('#', result)
        self.assertIn('제목', result)

    def test_bold_italic_removed(self):
        result = _strip_markdown('**볼드** *이탤릭* __밑줄__')
        self.assertNotIn('*', result)
        self.assertNotIn('_', result)

    def test_links_converted(self):
        result = _strip_markdown('[링크](https://example.com)')
        self.assertIn('링크', result)
        self.assertIn('example.com', result)

    def test_code_blocks_removed(self):
        result = _strip_markdown('```python\nprint("hello")\n```')
        self.assertNotIn('```', result)

    def test_list_markers_converted(self):
        result = _strip_markdown('- 항목1\n* 항목2')
        self.assertEqual(result.count('•'), 2)


class TestExtractKeywords(unittest.TestCase):

    def test_basic_extraction(self):
        content = 'SEO 최적화 방법 SEO 전략 SEO 도구'
        keywords = _extract_keywords(content, 3)
        self.assertTrue(len(keywords) > 0)
        self.assertTrue(all(k.startswith('#') for k in keywords))

    def test_limit_respected(self):
        content = '파이썬 자바 코틀린 스위프트 러스트'
        keywords = _extract_keywords(content, 2)
        self.assertLessEqual(len(keywords), 2)

    def test_zero_limit(self):
        self.assertEqual(_extract_keywords('content', 0), [])

    def test_stopwords_filtered(self):
        content = 'the and for 중요한 키워드'
        keywords = _extract_keywords(content, 5)
        self.assertFalse(any('#the' == k for k in keywords))


class TestTruncateWithEllipsis(unittest.TestCase):

    def test_short_text_unchanged(self):
        text, status = _truncate_with_ellipsis('짧은 텍스트', 100)
        self.assertEqual(text, '짧은 텍스트')
        self.assertEqual(status, 'ok')

    def test_long_text_truncated(self):
        long = '가' * 300
        text, status = _truncate_with_ellipsis(long, 100)
        self.assertLessEqual(len(text), 103)  # +3 for ...
        self.assertEqual(status, 'truncated')
        self.assertTrue(text.endswith('...'))


class TestSyndicateContent(unittest.TestCase):

    def test_empty_content(self):
        results = syndicate_content('', ['twitter'])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, 'error')
        self.assertEqual(results[0].character_count, 0)

    def test_twitter_char_limit(self):
        long_content = '테스트 ' * 200
        results = syndicate_content(long_content, ['twitter'])
        self.assertEqual(len(results), 1)
        r = results[0]
        self.assertEqual(r.platform, 'twitter')
        # 트위터 제한 + 해시태그 + 스레드 힌트
        self.assertIsInstance(r.adapted_content, str)
        self.assertTrue(len(r.adapted_content) > 0)

    def test_blog_preserves_markdown(self):
        content = '# 제목\n\n**볼드** 텍스트'
        results = syndicate_content(content, ['blog'])
        self.assertEqual(len(results), 1)
        self.assertIn('#', results[0].adapted_content)

    def test_linkedin_strips_markdown(self):
        content = '**볼드** 텍스트'
        results = syndicate_content(content, ['linkedin'])
        self.assertNotIn('**', results[0].adapted_content)

    def test_multiple_platforms(self):
        content = '테스트 콘텐츠입니다.'
        platforms = ['twitter', 'linkedin', 'instagram']
        results = syndicate_content(content, platforms)
        self.assertEqual(len(results), 3)
        platform_names = [r.platform for r in results]
        self.assertIn('twitter', platform_names)
        self.assertIn('linkedin', platform_names)
        self.assertIn('instagram', platform_names)

    def test_unknown_platform(self):
        results = syndicate_content('콘텐츠', ['unknown_platform'])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, 'error')

    def test_character_count_accurate(self):
        content = '정확한 글자수 테스트'
        results = syndicate_content(content, ['blog'])
        r = results[0]
        self.assertEqual(r.character_count, len(r.adapted_content))

    def test_empty_platforms(self):
        results = syndicate_content('콘텐츠', [])
        self.assertEqual(len(results), 0)

    def test_threads_platform(self):
        content = '스레드 테스트 ' * 100
        results = syndicate_content(content, ['threads'])
        self.assertEqual(results[0].platform, 'threads')
        self.assertIsInstance(results[0], SyndicationResult)

    def test_newsletter_no_hashtags(self):
        content = 'SEO SEO SEO 뉴스레터 콘텐츠'
        results = syndicate_content(content, ['newsletter'])
        r = results[0]
        # 뉴스레터는 해시태그 제한 0
        self.assertNotIn('#', r.adapted_content)


if __name__ == '__main__':
    unittest.main()
