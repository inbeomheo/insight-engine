"""social_card_service 단위 테스트"""
import unittest

from services.content.social_card_service import (
    generate_social_card,
    get_card_presets,
    CARD_PRESETS,
)


class TestGenerateSocialCard(unittest.TestCase):

    def test_empty(self):
        result = generate_social_card('')
        self.assertEqual(result['og_tags'], {})

    def test_basic_generation(self):
        result = generate_social_card('콘텐츠 내용입니다.', title='테스트 제목')
        self.assertIn('og:title', result['og_tags'])
        self.assertEqual(result['og_tags']['og:title'], '테스트 제목')
        self.assertIn('twitter:card', result['twitter_tags'])

    def test_title_extracted_from_content(self):
        result = generate_social_card('# 자동 추출 제목\n본문 내용')
        self.assertEqual(result['og_tags']['og:title'], '자동 추출 제목')

    def test_description_generated(self):
        result = generate_social_card('본문 내용이 여기 있습니다.', title='제목')
        self.assertGreater(len(result['description']), 0)

    def test_url_included(self):
        result = generate_social_card('내용', title='제목', url='https://example.com')
        self.assertEqual(result['og_tags']['og:url'], 'https://example.com')

    def test_image_url(self):
        result = generate_social_card('내용', title='제목', image_url='https://img.com/a.png')
        self.assertEqual(result['og_tags']['og:image'], 'https://img.com/a.png')
        self.assertEqual(result['twitter_tags']['twitter:image'], 'https://img.com/a.png')

    def test_image_extracted_from_content(self):
        result = generate_social_card('![alt](https://img.com/auto.png)\n본문', title='제목')
        self.assertIn('og:image', result['og_tags'])

    def test_author(self):
        result = generate_social_card('내용', title='제목', author='홍길동')
        self.assertEqual(result['og_tags']['article:author'], '홍길동')

    def test_meta_html_generated(self):
        result = generate_social_card('내용', title='제목')
        self.assertIn('<meta property="og:title"', result['meta_html'])
        self.assertIn('<meta name="twitter:card"', result['meta_html'])

    def test_preset_blog(self):
        result = generate_social_card('내용', title='제목', preset='blog')
        self.assertEqual(result['og_tags']['og:type'], 'article')

    def test_preset_video(self):
        result = generate_social_card('내용', title='제목', preset='video')
        self.assertEqual(result['og_tags']['og:type'], 'video.other')

    def test_html_escaped(self):
        result = generate_social_card('내용', title='<script>XSS</script>')
        self.assertNotIn('<script>', result['meta_html'])
        self.assertIn('&lt;script&gt;', result['meta_html'])

    def test_description_max_length(self):
        long_content = '긴 내용입니다. ' * 100
        result = generate_social_card(long_content, title='제목')
        self.assertLessEqual(len(result['description']), 163)  # 160 + '...'


class TestGetCardPresets(unittest.TestCase):

    def test_returns_list(self):
        presets = get_card_presets()
        self.assertIsInstance(presets, list)
        self.assertEqual(len(presets), len(CARD_PRESETS))

    def test_preset_structure(self):
        presets = get_card_presets()
        for p in presets:
            self.assertIn('id', p)
            self.assertIn('og_type', p)
            self.assertIn('twitter_card', p)


if __name__ == '__main__':
    unittest.main()
