"""comparison_service 단위 테스트"""
import unittest

from services.comparison_service import generate_comparison


class TestGenerateComparison(unittest.TestCase):

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            generate_comparison([])

    def test_single_item_raises(self):
        with self.assertRaises(ValueError):
            generate_comparison([{'name': 'A'}])

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            generate_comparison(['a', 'b'])

    def test_basic_table(self):
        items = [
            {'name': 'Python', 'speed': 'slow', 'ease': 'easy'},
            {'name': 'Rust', 'speed': 'fast', 'ease': 'hard'},
        ]
        md = generate_comparison(items)
        self.assertIn('Python', md)
        self.assertIn('Rust', md)
        self.assertIn('speed', md)
        self.assertIn('|', md)
        self.assertIn('---', md)

    def test_missing_values_filled(self):
        items = [
            {'name': 'A', 'x': '1'},
            {'name': 'B', 'y': '2'},
        ]
        md = generate_comparison(items)
        self.assertIn('-', md)  # 누락 값은 '-'으로 채워짐

    def test_no_name_key(self):
        items = [
            {'price': '10', 'weight': '1kg'},
            {'price': '20', 'weight': '2kg'},
        ]
        md = generate_comparison(items)
        self.assertIn('항목 1', md)
        self.assertIn('항목 2', md)


if __name__ == '__main__':
    unittest.main()
