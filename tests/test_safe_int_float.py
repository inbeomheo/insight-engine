"""safe_int / safe_float 유틸리티 테스트"""
import pytest

from utils.responses import safe_int, safe_float


class TestSafeInt:
    """safe_int 함수 테스트"""

    def test_normal_int(self):
        assert safe_int(42) == 42

    def test_string_number(self):
        assert safe_int('123') == 123

    def test_float_to_int(self):
        assert safe_int(3.7) == 3

    def test_none_returns_default(self):
        assert safe_int(None) == 0
        assert safe_int(None, 99) == 99

    def test_invalid_string_returns_default(self):
        assert safe_int('abc') == 0
        assert safe_int('abc', 10) == 10

    def test_empty_string_returns_default(self):
        assert safe_int('') == 0

    def test_list_returns_default(self):
        assert safe_int([1, 2]) == 0

    def test_bool_works(self):
        """bool은 int 서브클래스이므로 변환 가능"""
        assert safe_int(True) == 1
        assert safe_int(False) == 0


class TestSafeFloat:
    """safe_float 함수 테스트"""

    def test_normal_float(self):
        assert safe_float(3.14) == 3.14

    def test_string_number(self):
        assert safe_float('2.5') == 2.5

    def test_int_to_float(self):
        assert safe_float(10) == 10.0

    def test_none_returns_default(self):
        assert safe_float(None) == 0.0
        assert safe_float(None, 1.5) == 1.5

    def test_invalid_string_returns_default(self):
        assert safe_float('xyz') == 0.0
        assert safe_float('xyz', 9.9) == 9.9

    def test_empty_string_returns_default(self):
        assert safe_float('') == 0.0

    def test_dict_returns_default(self):
        assert safe_float({}) == 0.0

    def test_negative_values(self):
        assert safe_float('-3.5') == -3.5
        assert safe_int('-7') == -7
