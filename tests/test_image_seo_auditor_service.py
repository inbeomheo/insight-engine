"""Image SEO Auditor 서비스 테스트."""
import unittest
from services.seo.image_seo_auditor_service import audit_image_seo


class TestImageSeoAuditor(unittest.TestCase):
    """audit_image_seo 함수 테스트."""

    def test_empty_content(self):
        result = audit_image_seo('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['total_images'], 0)

    def test_none_content(self):
        result = audit_image_seo(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_images(self):
        result = audit_image_seo('이미지가 없는 텍스트입니다.')
        self.assertEqual(result['summary']['total_images'], 0)
        self.assertGreater(len(result['suggestions']), 0)

    def test_markdown_image_good_alt(self):
        content = '![React 컴포넌트 구조도](https://example.com/react-component.png)'
        result = audit_image_seo(content)
        self.assertEqual(result['summary']['total_images'], 1)
        self.assertEqual(result['images'][0]['alt_status'], 'good')

    def test_markdown_image_missing_alt(self):
        content = '![](https://example.com/image.png)'
        result = audit_image_seo(content)
        self.assertEqual(result['summary']['missing_alt'], 1)

    def test_markdown_image_generic_alt(self):
        content = '![이미지](https://example.com/photo.png)'
        result = audit_image_seo(content)
        self.assertEqual(result['summary']['generic_alt'], 1)

    def test_html_image_good_alt(self):
        content = '<img src="https://example.com/diagram.png" alt="시스템 아키텍처 다이어그램">'
        result = audit_image_seo(content)
        self.assertEqual(result['summary']['total_images'], 1)
        self.assertEqual(result['images'][0]['alt_status'], 'good')

    def test_html_image_missing_alt(self):
        content = '<img src="https://example.com/photo.jpg">'
        result = audit_image_seo(content)
        self.assertEqual(result['summary']['missing_alt'], 1)

    def test_alt_too_short(self):
        content = '![ab](https://example.com/img.png)'
        result = audit_image_seo(content)
        self.assertEqual(result['images'][0]['alt_status'], 'too_short')

    def test_alt_too_long(self):
        long_alt = '가' * 130
        content = f'![{long_alt}](https://example.com/img.png)'
        result = audit_image_seo(content)
        self.assertEqual(result['images'][0]['alt_status'], 'too_long')

    def test_meaningless_filename(self):
        content = '![좋은 설명](https://example.com/abc123def456.png)'
        result = audit_image_seo(content)
        self.assertEqual(result['summary']['meaningless_filename'], 1)

    def test_good_filename(self):
        content = '![좋은 설명](https://example.com/react-hooks-guide.png)'
        result = audit_image_seo(content)
        self.assertEqual(result['images'][0]['filename_status'], 'good')

    def test_multiple_images_mixed(self):
        content = """
![React 아키텍처](https://example.com/architecture.png)
![](https://example.com/screenshot123.jpg)
![사진](https://example.com/photo.webp)
"""
        result = audit_image_seo(content)
        self.assertEqual(result['summary']['total_images'], 3)
        self.assertEqual(result['summary']['good_alt'], 1)

    def test_score_perfect(self):
        content = '![Next.js 라우팅 구조](https://example.com/nextjs-routing.png)'
        result = audit_image_seo(content)
        self.assertGreaterEqual(result['score'], 80.0)

    def test_score_decreases_with_issues(self):
        content = '![](https://example.com/abc123.png)'
        result = audit_image_seo(content)
        self.assertLess(result['score'], 100.0)

    def test_suggestions_for_missing_alt(self):
        content = '![](https://example.com/img.png)'
        result = audit_image_seo(content)
        self.assertTrue(any('alt' in s for s in result['suggestions']))

    def test_return_structure(self):
        content = '![테스트](https://example.com/test.png)'
        result = audit_image_seo(content)
        self.assertIn('images', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_images', result['summary'])
        self.assertIn('missing_alt', result['summary'])


if __name__ == '__main__':
    unittest.main()
