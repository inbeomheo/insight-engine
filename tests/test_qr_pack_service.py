"""qr_pack_service 단위 테스트"""
import unittest

from services.qr_pack_service import (
    generate_qr_pack,
    QRPack,
    QRCode,
    _is_valid_url,
    _normalize_url,
    _generate_label,
    _generate_qr_data,
)


class TestIsValidUrl(unittest.TestCase):

    def test_valid_https(self):
        self.assertTrue(_is_valid_url('https://example.com'))

    def test_valid_http(self):
        self.assertTrue(_is_valid_url('http://example.com'))

    def test_with_path(self):
        self.assertTrue(_is_valid_url('https://example.com/page/sub'))

    def test_with_query(self):
        self.assertTrue(_is_valid_url('https://example.com?q=test'))

    def test_localhost(self):
        self.assertTrue(_is_valid_url('http://localhost:3000'))

    def test_invalid_empty(self):
        self.assertFalse(_is_valid_url(''))

    def test_invalid_none(self):
        self.assertFalse(_is_valid_url(None))

    def test_invalid_no_scheme(self):
        self.assertFalse(_is_valid_url('not-a-url'))


class TestNormalizeUrl(unittest.TestCase):

    def test_adds_https(self):
        self.assertEqual(_normalize_url('example.com'), 'https://example.com')

    def test_preserves_http(self):
        self.assertEqual(_normalize_url('http://example.com'), 'http://example.com')

    def test_strips_whitespace(self):
        self.assertEqual(_normalize_url('  https://example.com  '), 'https://example.com')


class TestGenerateLabel(unittest.TestCase):

    def test_domain_only(self):
        label = _generate_label('https://example.com')
        self.assertEqual(label, 'example.com')

    def test_www_stripped(self):
        label = _generate_label('https://www.example.com')
        self.assertEqual(label, 'example.com')

    def test_with_path(self):
        label = _generate_label('https://example.com/blog/my-post')
        self.assertIn('my post', label)  # 하이픈 → 공백

    def test_file_extension_removed(self):
        label = _generate_label('https://example.com/page.html')
        self.assertNotIn('.html', label)


class TestGenerateQrData(unittest.TestCase):

    def test_contains_url(self):
        data = _generate_qr_data('https://example.com', 'standard')
        self.assertIn('https://example.com', data)

    def test_contains_style(self):
        data = _generate_qr_data('https://example.com', 'branded')
        self.assertIn('branded', data)

    def test_json_format(self):
        import json
        data = _generate_qr_data('https://example.com', 'standard')
        parsed = json.loads(data)
        self.assertEqual(parsed['url'], 'https://example.com')
        self.assertEqual(parsed['style'], 'standard')

    def test_unique_id_per_url(self):
        data1 = _generate_qr_data('https://a.com', 'standard')
        data2 = _generate_qr_data('https://b.com', 'standard')
        import json
        id1 = json.loads(data1)['id']
        id2 = json.loads(data2)['id']
        self.assertNotEqual(id1, id2)


class TestGenerateQrPack(unittest.TestCase):

    def test_empty_urls(self):
        result = generate_qr_pack([])
        self.assertIsInstance(result, QRPack)
        self.assertEqual(result.total, 0)
        self.assertEqual(len(result.codes), 0)

    def test_single_url(self):
        result = generate_qr_pack(['https://example.com'])
        self.assertEqual(result.total, 1)
        self.assertEqual(len(result.codes), 1)
        self.assertIsInstance(result.codes[0], QRCode)
        self.assertEqual(result.codes[0].url, 'https://example.com')

    def test_multiple_urls(self):
        urls = ['https://a.com', 'https://b.com', 'https://c.com']
        result = generate_qr_pack(urls)
        self.assertEqual(result.total, 3)

    def test_duplicate_urls_deduplicated(self):
        urls = ['https://example.com', 'https://example.com', 'https://example.com']
        result = generate_qr_pack(urls)
        self.assertEqual(result.total, 1)

    def test_invalid_urls_skipped(self):
        urls = ['https://valid.com', 'not-a-url', 'another-bad']
        result = generate_qr_pack(urls)
        self.assertEqual(result.total, 1)

    def test_style_applied(self):
        result = generate_qr_pack(['https://example.com'], style='branded')
        self.assertEqual(result.codes[0].style, 'branded')

    def test_unknown_style_fallback(self):
        result = generate_qr_pack(['https://example.com'], style='unknown')
        self.assertEqual(result.codes[0].style, 'standard')

    def test_format_is_png(self):
        result = generate_qr_pack(['https://example.com'])
        self.assertEqual(result.format, 'png')

    def test_auto_scheme_addition(self):
        """스키마 없는 URL에 https:// 자동 추가"""
        result = generate_qr_pack(['example.com'])
        self.assertEqual(result.total, 1)
        self.assertTrue(result.codes[0].url.startswith('https://'))

    def test_non_string_urls_skipped(self):
        urls = ['https://valid.com', 123, None, True]
        result = generate_qr_pack(urls)
        self.assertEqual(result.total, 1)

    def test_label_generated(self):
        result = generate_qr_pack(['https://example.com/blog/test-post'])
        self.assertTrue(len(result.codes[0].label) > 0)


if __name__ == '__main__':
    unittest.main()
