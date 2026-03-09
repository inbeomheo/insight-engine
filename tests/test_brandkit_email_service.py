"""brandkit_email_service 단위 테스트"""
import unittest

from services.brandkit_email_service import (
    generate_branded_email,
    BrandedEmail,
    _extract_colors,
    _generate_subject,
    _generate_preview,
    _content_to_html,
    _content_to_plain,
    _DEFAULT_COLORS,
)


class TestExtractColors(unittest.TestCase):

    def test_default_colors(self):
        colors = _extract_colors({})
        self.assertEqual(colors, _DEFAULT_COLORS)

    def test_custom_colors(self):
        brand = {'colors': {'primary': '#FF0000', 'text': '#000000'}}
        colors = _extract_colors(brand)
        self.assertEqual(colors['primary'], '#FF0000')
        self.assertEqual(colors['text'], '#000000')
        # 기본값 유지
        self.assertEqual(colors['secondary'], _DEFAULT_COLORS['secondary'])

    def test_direct_color_keys(self):
        brand = {'primary_color': '#123456', 'text_color': '#654321'}
        colors = _extract_colors(brand)
        self.assertEqual(colors['primary'], '#123456')
        self.assertEqual(colors['text'], '#654321')


class TestGenerateSubject(unittest.TestCase):

    def test_with_brand_name(self):
        subject = _generate_subject('본문입니다', {'name': 'MyBrand'})
        self.assertIn('[MyBrand]', subject)

    def test_without_brand_name(self):
        subject = _generate_subject('첫 줄 제목\n나머지 본문', {})
        self.assertEqual(subject, '첫 줄 제목')

    def test_long_title_truncated(self):
        long = 'A' * 100
        subject = _generate_subject(long, {})
        self.assertLessEqual(len(subject), 65)
        self.assertTrue(subject.endswith('...'))

    def test_markdown_header_stripped(self):
        subject = _generate_subject('## 제목 텍스트\n본문', {})
        self.assertNotIn('#', subject)
        self.assertIn('제목 텍스트', subject)


class TestGeneratePreview(unittest.TestCase):

    def test_short_content(self):
        preview = _generate_preview('짧은 내용')
        self.assertEqual(preview, '짧은 내용')

    def test_long_content_truncated(self):
        long = '가' * 200
        preview = _generate_preview(long)
        self.assertLessEqual(len(preview), 90)
        self.assertTrue(preview.endswith('...'))

    def test_markdown_removed(self):
        preview = _generate_preview('**볼드** *이탤릭* `코드`')
        self.assertNotIn('*', preview)
        self.assertNotIn('`', preview)


class TestContentToHtml(unittest.TestCase):

    def test_heading_conversion(self):
        html = _content_to_html('# 제목')
        self.assertIn('<h2', html)
        self.assertIn('제목', html)

    def test_list_conversion(self):
        html = _content_to_html('- 항목1\n- 항목2')
        self.assertEqual(html.count('&bull;'), 2)

    def test_bold_conversion(self):
        html = _content_to_html('**볼드 텍스트**')
        self.assertIn('<strong>볼드 텍스트</strong>', html)

    def test_empty_lines_skipped(self):
        html = _content_to_html('줄1\n\n\n줄2')
        self.assertIn('줄1', html)
        self.assertIn('줄2', html)


class TestContentToPlain(unittest.TestCase):

    def test_markdown_stripped(self):
        plain = _content_to_plain('**볼드** # 제목 `코드`')
        self.assertNotIn('*', plain)
        self.assertNotIn('#', plain)
        self.assertNotIn('`', plain)

    def test_link_text_only(self):
        plain = _content_to_plain('[링크 텍스트](https://example.com)')
        self.assertIn('링크 텍스트', plain)
        self.assertNotIn('](', plain)


class TestGenerateBrandedEmail(unittest.TestCase):

    def test_empty_content(self):
        result = generate_branded_email('', {})
        self.assertIsInstance(result, BrandedEmail)
        self.assertEqual(result.subject, '(제목 없음)')
        self.assertEqual(result.body_html, '')

    def test_basic_generation(self):
        result = generate_branded_email(
            '# 뉴스레터\n\n안녕하세요!',
            {'name': 'TestBrand'},
        )
        self.assertIn('[TestBrand]', result.subject)
        self.assertIn('안녕하세요', result.body_html)
        self.assertIn('안녕하세요', result.body_plain)
        self.assertTrue(len(result.preview_text) > 0)

    def test_brand_colors_applied(self):
        brand = {'colors': {'primary': '#FF5500'}}
        result = generate_branded_email('콘텐츠', brand)
        self.assertEqual(result.brand_colors['primary'], '#FF5500')
        self.assertIn('#FF5500', result.body_html)

    def test_logo_included(self):
        brand = {'logo_url': 'https://example.com/logo.png', 'name': 'Logo'}
        result = generate_branded_email('콘텐츠', brand)
        self.assertIn('logo.png', result.body_html)
        self.assertIn('<img', result.body_html)

    def test_footer_included(self):
        brand = {'footer': '저작권 2026'}
        result = generate_branded_email('콘텐츠', brand)
        self.assertIn('저작권 2026', result.body_html)

    def test_none_brand_handled(self):
        result = generate_branded_email('콘텐츠', None)
        self.assertIsInstance(result, BrandedEmail)
        self.assertTrue(len(result.body_html) > 0)

    def test_html_structure(self):
        result = generate_branded_email('테스트', {'name': 'T'})
        self.assertIn('<!DOCTYPE html>', result.body_html)
        self.assertIn('</html>', result.body_html)
        self.assertIn('<table', result.body_html)


if __name__ == '__main__':
    unittest.main()
