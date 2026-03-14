"""seo_metadata_service 단위 테스트"""
import unittest

from services.seo.seo_metadata_service import (
    _get_video_id, generate_video_object_schema,
    generate_faq_page_schema, generate_article_schema, generate_all_schemas
)


class TestGetVideoId(unittest.TestCase):

    def test_standard_url(self):
        self.assertEqual(_get_video_id('https://www.youtube.com/watch?v=abc12345678'), 'abc12345678')

    def test_short_url(self):
        self.assertEqual(_get_video_id('https://youtu.be/abc12345678'), 'abc12345678')

    def test_empty(self):
        self.assertIsNone(_get_video_id(''))

    def test_invalid(self):
        self.assertIsNone(_get_video_id('https://example.com'))


class TestVideoObjectSchema(unittest.TestCase):

    def test_basic(self):
        schema = generate_video_object_schema('https://youtu.be/abc12345678', '제목')
        self.assertEqual(schema['@type'], 'VideoObject')
        self.assertEqual(schema['name'], '제목')
        self.assertIn('abc12345678', schema['contentUrl'])

    def test_thumbnail(self):
        schema = generate_video_object_schema('https://youtu.be/abc12345678', '제목')
        self.assertIn('thumbnailUrl', schema)

    def test_no_video_id(self):
        schema = generate_video_object_schema('https://example.com', '제목')
        self.assertNotIn('thumbnailUrl', schema)


class TestFaqPageSchema(unittest.TestCase):

    def test_basic(self):
        pairs = [{'question': '질문?', 'answer': '답변'}]
        schema = generate_faq_page_schema(pairs)
        self.assertEqual(schema['@type'], 'FAQPage')
        self.assertEqual(len(schema['mainEntity']), 1)

    def test_skips_empty(self):
        pairs = [{'question': '', 'answer': 'x'}, {'question': 'q', 'answer': ''}]
        schema = generate_faq_page_schema(pairs)
        self.assertEqual(len(schema['mainEntity']), 0)


class TestArticleSchema(unittest.TestCase):

    def test_basic(self):
        schema = generate_article_schema('제목', '설명', ['kw1'])
        self.assertEqual(schema['@type'], 'Article')
        self.assertEqual(schema['keywords'], ['kw1'])

    def test_headline_truncated(self):
        schema = generate_article_schema('A' * 200)
        self.assertLessEqual(len(schema['headline']), 110)


class TestGenerateAllSchemas(unittest.TestCase):

    def test_with_video_and_faq(self):
        schemas = generate_all_schemas(
            'https://youtu.be/abc12345678', '제목', '내용이 충분히 긴 문장입니다 여기에',
            [{'question': 'Q?', 'answer': 'A'}], ['kw']
        )
        types = [s['@type'] for s in schemas]
        self.assertIn('VideoObject', types)
        self.assertIn('FAQPage', types)
        self.assertIn('Article', types)

    def test_no_video(self):
        schemas = generate_all_schemas('', '제목', '내용', [], ['kw'])
        types = [s['@type'] for s in schemas]
        self.assertNotIn('VideoObject', types)
        self.assertIn('Article', types)

    def test_auto_description(self):
        """description 자동 추출"""
        schemas = generate_all_schemas(
            '', '제목', '# 헤딩\n이것은 충분히 긴 자동 추출 설명 문장입니다', [], []
        )
        article = next(s for s in schemas if s['@type'] == 'Article')
        self.assertTrue(len(article['description']) > 0)


if __name__ == '__main__':
    unittest.main()
