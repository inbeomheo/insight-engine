"""watermark_service 단위 테스트"""
import unittest

from services.content.watermark_service import (
    add_invisible_watermark,
    detect_watermark,
    add_attribution,
    _encode_to_zwc,
    _decode_from_zwc,
)


class TestInvisibleWatermark(unittest.TestCase):

    def test_empty_content(self):
        result = add_invisible_watermark('')
        self.assertEqual(result['watermarked'], '')

    def test_basic_watermark(self):
        result = add_invisible_watermark('본문 내용입니다.', identifier='test123')
        self.assertEqual(result['identifier'], 'test123')
        self.assertGreater(result['watermark_length'], 0)
        # 보이는 텍스트는 동일해야 함 (영폭 문자 제외)
        visible = result['watermarked'].replace('\u200b', '').replace('\u200c', '')
        self.assertEqual(visible, '본문 내용입니다.')

    def test_auto_identifier(self):
        result = add_invisible_watermark('테스트')
        self.assertGreater(len(result['identifier']), 0)

    def test_roundtrip(self):
        original = '테스트 콘텐츠입니다.'
        wm_result = add_invisible_watermark(original, identifier='abc123')
        detect_result = detect_watermark(wm_result['watermarked'])
        self.assertTrue(detect_result['has_watermark'])
        self.assertEqual(detect_result['identifier'], 'abc123')

    def test_no_watermark_detected(self):
        result = detect_watermark('일반 텍스트')
        self.assertFalse(result['has_watermark'])

    def test_detect_empty(self):
        result = detect_watermark('')
        self.assertFalse(result['has_watermark'])

    def test_heading_skipped(self):
        result = add_invisible_watermark('# 제목\n본문입니다.', identifier='id')
        # 워터마크는 본문에 삽입, 제목이 아닌 곳
        self.assertIn('id', detect_watermark(result['watermarked'])['identifier'])


class TestAttribution(unittest.TestCase):

    def test_basic_attribution(self):
        result = add_attribution('콘텐츠', author='작성자', source_url='https://example.com')
        self.assertIn('작성자', result['attributed'])
        self.assertIn('example.com', result['attributed'])
        self.assertIn('---', result['attributed'])

    def test_empty_content(self):
        result = add_attribution('')
        self.assertEqual(result['attributed'], '')

    def test_no_params(self):
        result = add_attribution('콘텐츠')
        self.assertEqual(result['attributed'], '콘텐츠')

    def test_license_text(self):
        result = add_attribution('콘텐츠', license_text='CC BY 4.0')
        self.assertIn('CC BY 4.0', result['attributed'])


class TestZwcEncoding(unittest.TestCase):

    def test_encode_decode_roundtrip(self):
        original = 'hello'
        encoded = _encode_to_zwc(original)
        decoded = _decode_from_zwc(encoded)
        self.assertEqual(decoded, original)

    def test_korean_roundtrip(self):
        original = '한글'
        encoded = _encode_to_zwc(original)
        decoded = _decode_from_zwc(encoded)
        self.assertEqual(decoded, original)

    def test_empty_decode(self):
        self.assertEqual(_decode_from_zwc(''), '')


if __name__ == '__main__':
    unittest.main()
