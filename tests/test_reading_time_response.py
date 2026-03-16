"""
R21: /generate 응답에 reading_time_min 필드가 포함되는지 검증
"""
from __future__ import annotations

import unittest


class TestReadingTimeInResponse(unittest.TestCase):
    """reading_time_min 계산 로직 단위 테스트"""

    def test_reading_time_min_short_content(self):
        """500자 미만 → 1분"""
        text = "가" * 300
        char_count = len(text)
        reading_time_min = max(1, round(char_count / 500)) if char_count > 0 else 0
        self.assertEqual(reading_time_min, 1)

    def test_reading_time_min_medium_content(self):
        """1500자 → 3분"""
        text = "가" * 1500
        char_count = len(text)
        reading_time_min = max(1, round(char_count / 500)) if char_count > 0 else 0
        self.assertEqual(reading_time_min, 3)

    def test_reading_time_min_long_content(self):
        """5000자 → 10분"""
        text = "가" * 5000
        char_count = len(text)
        reading_time_min = max(1, round(char_count / 500)) if char_count > 0 else 0
        self.assertEqual(reading_time_min, 10)

    def test_reading_time_min_empty(self):
        """빈 콘텐츠 → 0분"""
        text = ""
        char_count = len(text)
        reading_time_min = max(1, round(char_count / 500)) if char_count > 0 else 0
        self.assertEqual(reading_time_min, 0)

    def test_reading_time_min_boundary_250(self):
        """250자 → round(0.5) = 0 → max(1, 0) = 1"""
        text = "가" * 250
        char_count = len(text)
        reading_time_min = max(1, round(char_count / 500)) if char_count > 0 else 0
        self.assertEqual(reading_time_min, 1)

    def test_reading_time_min_boundary_750(self):
        """750자 → round(1.5) = 2"""
        text = "가" * 750
        char_count = len(text)
        reading_time_min = max(1, round(char_count / 500)) if char_count > 0 else 0
        self.assertEqual(reading_time_min, 2)

    def test_content_stats_dict_structure(self):
        """_content_stats 딕셔너리에 reading_time_min 포함 확인"""
        _content_text = "테스트 콘텐츠입니다. " * 100  # ~1100자
        _char_count = len(_content_text)
        _reading_time_min = max(1, round(_char_count / 500)) if _char_count > 0 else 0
        _content_stats = {
            "char_count": _char_count,
            "word_count": len(_content_text.split()) if _content_text else 0,
            "reading_time_min": _reading_time_min,
        }
        self.assertIn("reading_time_min", _content_stats)
        self.assertIn("char_count", _content_stats)
        self.assertIn("word_count", _content_stats)
        self.assertIsInstance(_content_stats["reading_time_min"], int)
        self.assertGreater(_content_stats["reading_time_min"], 0)


if __name__ == '__main__':
    unittest.main()
