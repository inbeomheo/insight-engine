"""R150: citation_service 타임스탬프 범위 검증 테스트."""
import unittest
from services.content.citation_service import _timestamp_to_seconds, parse_citations


class TestTimestampRangeValidation(unittest.TestCase):
    """_timestamp_to_seconds에서 분/초 범위 초과 시 0 반환 검증."""

    def test_valid_mm_ss(self):
        """정상 MM:SS 변환."""
        self.assertEqual(_timestamp_to_seconds('03:25'), 205)

    def test_valid_hh_mm_ss(self):
        """정상 HH:MM:SS 변환."""
        self.assertEqual(_timestamp_to_seconds('1:30:00'), 5400)

    def test_seconds_over_59_mm_ss(self):
        """MM:SS에서 초가 60 이상이면 0 반환."""
        self.assertEqual(_timestamp_to_seconds('03:60'), 0)
        self.assertEqual(_timestamp_to_seconds('03:99'), 0)

    def test_seconds_over_59_hh_mm_ss(self):
        """HH:MM:SS에서 초가 60 이상이면 0 반환."""
        self.assertEqual(_timestamp_to_seconds('1:30:60'), 0)

    def test_minutes_over_59_hh_mm_ss(self):
        """HH:MM:SS에서 분이 60 이상이면 0 반환."""
        self.assertEqual(_timestamp_to_seconds('1:60:00'), 0)

    def test_zero_timestamp(self):
        """0:00은 유효 (0초)."""
        self.assertEqual(_timestamp_to_seconds('0:00'), 0)

    def test_max_valid_mm_ss(self):
        """59:59는 유효."""
        self.assertEqual(_timestamp_to_seconds('59:59'), 59 * 60 + 59)

    def test_parse_citations_with_invalid_seconds(self):
        """parse_citations에서 잘못된 타임스탬프가 0초로 처리."""
        content = "텍스트 [03:60] 이후 내용"
        results = parse_citations(content)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['seconds'], 0)


if __name__ == '__main__':
    unittest.main()
