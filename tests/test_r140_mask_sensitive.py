"""R140: mask_sensitive 유틸리티 테스트 — API 키/토큰 로그 안전 마스킹"""
import unittest

from utils.responses import mask_sensitive


class TestMaskSensitive(unittest.TestCase):

    def test_typical_api_key(self):
        result = mask_sensitive('sk-abcdefghijklmnop')
        self.assertTrue(result.startswith('sk-a'))
        self.assertTrue(result.endswith('mnop'))
        self.assertIn('*', result)

    def test_short_value_fully_masked(self):
        """visible_chars * 2 이하는 전체 마스킹"""
        result = mask_sensitive('abc')
        self.assertEqual(result, '***')

    def test_exact_boundary(self):
        """visible_chars*2 == len(value)이면 전체 마스킹"""
        result = mask_sensitive('abcdefgh', visible_chars=4)
        self.assertEqual(result, '********')

    def test_empty_string(self):
        self.assertEqual(mask_sensitive(''), '****')

    def test_none_input(self):
        self.assertEqual(mask_sensitive(None), '****')

    def test_long_key_caps_asterisks(self):
        """중간 마스킹 부분은 최대 8개 별표로 제한"""
        result = mask_sensitive('A' * 100, visible_chars=4)
        # 앞4 + 최대8별표 + 뒤4 = 16
        self.assertEqual(len(result), 16)

    def test_custom_visible_chars(self):
        result = mask_sensitive('1234567890', visible_chars=2)
        self.assertTrue(result.startswith('12'))
        self.assertTrue(result.endswith('90'))
        self.assertIn('*', result)

    def test_preserves_prefix_suffix(self):
        key = 'Bearer_token_value_xyz'
        result = mask_sensitive(key, visible_chars=6)
        self.assertEqual(result[:6], 'Bearer')
        self.assertEqual(result[-6:], 'ue_xyz')


if __name__ == '__main__':
    unittest.main()
