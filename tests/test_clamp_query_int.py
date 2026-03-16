"""clamp_query_int 유틸 테스트."""
import unittest

from utils.responses import clamp_query_int


class TestClampQueryInt(unittest.TestCase):

    def test_default_value(self):
        """None 입력 시 기본값 반환."""
        self.assertEqual(clamp_query_int(None, default=10), 10)

    def test_valid_string(self):
        """유효한 문자열 정수 파싱."""
        self.assertEqual(clamp_query_int('25', default=10), 25)

    def test_clamped_max(self):
        """최대값 초과 시 클램핑."""
        self.assertEqual(clamp_query_int('9999', default=10, max_val=100), 100)

    def test_clamped_min(self):
        """최소값 미만 시 클램핑."""
        self.assertEqual(clamp_query_int('0', default=10, min_val=1), 1)
        self.assertEqual(clamp_query_int('-5', default=10, min_val=1), 1)

    def test_invalid_string(self):
        """비숫자 문자열은 기본값."""
        self.assertEqual(clamp_query_int('abc', default=10), 10)

    def test_empty_string(self):
        """빈 문자열은 기본값."""
        self.assertEqual(clamp_query_int('', default=10), 10)

    def test_boundary_values(self):
        """경계값 정확히 통과."""
        self.assertEqual(clamp_query_int('1', default=10, min_val=1, max_val=100), 1)
        self.assertEqual(clamp_query_int('100', default=10, min_val=1, max_val=100), 100)


if __name__ == '__main__':
    unittest.main()
