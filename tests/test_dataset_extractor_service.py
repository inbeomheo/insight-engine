"""데이터셋 추출 서비스 테스트"""
import unittest
from services.dataset_extractor_service import (
    extract_from_text, detect_field_types, validate_dataset, export_as_csv,
    ExtractedField, ExtractedDataset
)


class TestDatasetExtractorService(unittest.TestCase):

    def setUp(self):
        self.text = """이름: 홍길동
나이: 30
직업: 개발자
이름: 김영희
나이: 25
직업: 디자이너"""

    def test_extract_from_text(self):
        dataset = extract_from_text(self.text, ['이름', '나이', '직업'])
        self.assertIsInstance(dataset, ExtractedDataset)
        self.assertGreater(len(dataset.fields), 0)

    def test_extract_field_values(self):
        dataset = extract_from_text(self.text, ['이름'])
        name_field = [f for f in dataset.fields if f.field_name == '이름']
        self.assertEqual(len(name_field), 1)
        self.assertEqual(len(name_field[0].values), 2)
        self.assertIn('홍길동', name_field[0].values)

    def test_extract_no_hints(self):
        dataset = extract_from_text(self.text, [])
        self.assertEqual(len(dataset.fields), 0)

    def test_extract_no_match(self):
        dataset = extract_from_text('아무 내용', ['없는 필드'])
        self.assertEqual(len(dataset.fields), 0)

    def test_detect_field_types_number(self):
        self.assertEqual(detect_field_types(['1', '2.5', '100']), 'number')

    def test_detect_field_types_date(self):
        self.assertEqual(detect_field_types(['2026-01-01', '2026-02-15']), 'date')

    def test_detect_field_types_text(self):
        self.assertEqual(detect_field_types(['hello', 'world', 'test']), 'text')

    def test_detect_field_types_category(self):
        self.assertEqual(detect_field_types(['A', 'B', 'A', 'B', 'A', 'B']), 'category')

    def test_detect_field_types_empty(self):
        self.assertEqual(detect_field_types([]), 'text')

    def test_validate_dataset_valid(self):
        dataset = extract_from_text(self.text, ['이름', '나이'])
        errors = validate_dataset(dataset)
        self.assertEqual(len(errors), 0)

    def test_validate_dataset_no_fields(self):
        dataset = ExtractedDataset('d1', 'src', [], 0)
        errors = validate_dataset(dataset)
        self.assertIn('추출된 필드가 없습니다.', errors)

    def test_validate_dataset_empty_values(self):
        field = ExtractedField('name', 'text', ['홍길동', ''])
        dataset = ExtractedDataset('d1', 'src', [field], 2)
        errors = validate_dataset(dataset)
        self.assertTrue(any('빈 값' in e for e in errors))

    def test_export_as_csv(self):
        dataset = extract_from_text(self.text, ['이름', '나이'])
        csv = export_as_csv(dataset)
        lines = csv.strip().split('\n')
        self.assertIn('이름', lines[0])
        self.assertGreater(len(lines), 1)

    def test_export_as_csv_empty(self):
        dataset = ExtractedDataset('d1', 'src', [], 0)
        csv = export_as_csv(dataset)
        self.assertEqual(csv, '')


if __name__ == '__main__':
    unittest.main()
