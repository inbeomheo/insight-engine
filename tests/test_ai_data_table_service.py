"""AI 데이터 테이블 서비스 테스트"""
import unittest
from services.ai_data_table_service import (
    TableColumn, TableRow, DataTable,
    extract_table, filter_rows, sort_table,
    aggregate, export_csv, _infer_data_type,
)


class TestInferDataType(unittest.TestCase):
    """데이터 타입 추론 테스트"""

    def test_number_integer(self):
        self.assertEqual(_infer_data_type('42'), 'number')

    def test_number_decimal(self):
        self.assertEqual(_infer_data_type('3.14'), 'number')

    def test_number_negative(self):
        self.assertEqual(_infer_data_type('-100'), 'number')

    def test_number_with_comma(self):
        self.assertEqual(_infer_data_type('1,000'), 'number')

    def test_date(self):
        self.assertEqual(_infer_data_type('2024-01-15'), 'date')

    def test_boolean_true(self):
        self.assertEqual(_infer_data_type('true'), 'boolean')

    def test_boolean_korean(self):
        self.assertEqual(_infer_data_type('예'), 'boolean')

    def test_text(self):
        self.assertEqual(_infer_data_type('hello world'), 'text')


class TestExtractTable(unittest.TestCase):
    """테이블 추출 테스트"""

    def test_pipe_table(self):
        """마크다운 파이프 테이블 추출"""
        text = """
| 이름 | 나이 | 도시 |
|------|------|------|
| 김철수 | 30 | 서울 |
| 이영희 | 25 | 부산 |
"""
        result = extract_table(text, '사용자 목록')
        self.assertEqual(result.title, '사용자 목록')
        self.assertEqual(len(result.columns), 3)
        self.assertEqual(len(result.rows), 2)
        self.assertEqual(result.rows[0].values['이름'], '김철수')

    def test_kv_table(self):
        """key: value 패턴 테이블 추출"""
        text = """이름: 김철수
나이: 30
도시: 서울

이름: 이영희
나이: 25
도시: 부산
"""
        result = extract_table(text, '인원 정보')
        self.assertEqual(result.title, '인원 정보')
        self.assertGreater(len(result.rows), 0)

    def test_empty_text(self):
        """빈 텍스트"""
        result = extract_table('', '빈 테이블')
        self.assertEqual(result.title, '빈 테이블')
        self.assertEqual(len(result.rows), 0)

    def test_no_structure(self):
        """구조 없는 일반 텍스트"""
        result = extract_table('그냥 평범한 문장입니다.')
        self.assertEqual(len(result.rows), 0)

    def test_pipe_table_type_inference(self):
        """파이프 테이블 컬럼 타입 추론"""
        text = """
| 항목 | 가격 | 날짜 |
|------|------|------|
| 사과 | 1000 | 2024-01-01 |
| 배 | 2000 | 2024-02-01 |
"""
        result = extract_table(text)
        types = {col.name: col.data_type for col in result.columns}
        self.assertEqual(types['가격'], 'number')
        self.assertEqual(types['날짜'], 'date')


class TestFilterRows(unittest.TestCase):
    """행 필터링 테스트"""

    def setUp(self):
        self.table = DataTable(
            table_id='t1',
            title='테스트',
            columns=[
                TableColumn('이름', 'text', '이름'),
                TableColumn('나이', 'number', '나이'),
                TableColumn('도시', 'text', '도시'),
            ],
            rows=[
                TableRow('r1', {'이름': '김철수', '나이': '30', '도시': '서울'}),
                TableRow('r2', {'이름': '이영희', '나이': '25', '도시': '부산'}),
                TableRow('r3', {'이름': '박지민', '나이': '35', '도시': '서울'}),
            ],
        )

    def test_eq_filter(self):
        result = filter_rows(self.table, '도시', 'eq', '서울')
        self.assertEqual(len(result.rows), 2)

    def test_contains_filter(self):
        result = filter_rows(self.table, '이름', 'contains', '영')
        self.assertEqual(len(result.rows), 1)
        self.assertEqual(result.rows[0].values['이름'], '이영희')

    def test_gt_filter(self):
        result = filter_rows(self.table, '나이', 'gt', '28')
        self.assertEqual(len(result.rows), 2)

    def test_lt_filter(self):
        result = filter_rows(self.table, '나이', 'lt', '30')
        self.assertEqual(len(result.rows), 1)

    def test_no_match(self):
        result = filter_rows(self.table, '도시', 'eq', '대전')
        self.assertEqual(len(result.rows), 0)


class TestSortTable(unittest.TestCase):
    """테이블 정렬 테스트"""

    def setUp(self):
        self.table = DataTable(
            table_id='t1',
            title='테스트',
            columns=[
                TableColumn('이름', 'text', '이름'),
                TableColumn('점수', 'number', '점수'),
            ],
            rows=[
                TableRow('r1', {'이름': '김철수', '점수': '85'}),
                TableRow('r2', {'이름': '이영희', '점수': '92'}),
                TableRow('r3', {'이름': '박지민', '점수': '78'}),
            ],
        )

    def test_sort_number_ascending(self):
        result = sort_table(self.table, '점수', ascending=True)
        scores = [r.values['점수'] for r in result.rows]
        self.assertEqual(scores, ['78', '85', '92'])

    def test_sort_number_descending(self):
        result = sort_table(self.table, '점수', ascending=False)
        scores = [r.values['점수'] for r in result.rows]
        self.assertEqual(scores, ['92', '85', '78'])

    def test_sort_text(self):
        result = sort_table(self.table, '이름', ascending=True)
        self.assertIsNotNone(result)
        self.assertEqual(len(result.rows), 3)


class TestAggregate(unittest.TestCase):
    """집계 테스트"""

    def setUp(self):
        self.table = DataTable(
            table_id='t1',
            title='테스트',
            columns=[TableColumn('값', 'number', '값')],
            rows=[
                TableRow('r1', {'값': '10'}),
                TableRow('r2', {'값': '20'}),
                TableRow('r3', {'값': '30'}),
            ],
        )

    def test_count(self):
        self.assertEqual(aggregate(self.table, '값', 'count'), 3.0)

    def test_sum(self):
        self.assertEqual(aggregate(self.table, '값', 'sum'), 60.0)

    def test_avg(self):
        self.assertEqual(aggregate(self.table, '값', 'avg'), 20.0)

    def test_min(self):
        self.assertEqual(aggregate(self.table, '값', 'min'), 10.0)

    def test_max(self):
        self.assertEqual(aggregate(self.table, '값', 'max'), 30.0)

    def test_empty_table(self):
        empty = DataTable(table_id='e', title='빈', columns=[], rows=[])
        self.assertEqual(aggregate(empty, '값', 'count'), 0.0)


class TestExportCsv(unittest.TestCase):
    """CSV 내보내기 테스트"""

    def test_basic_export(self):
        table = DataTable(
            table_id='t1',
            title='테스트',
            columns=[
                TableColumn('이름', 'text', '이름'),
                TableColumn('나이', 'number', '나이'),
            ],
            rows=[
                TableRow('r1', {'이름': '김철수', '나이': '30'}),
                TableRow('r2', {'이름': '이영희', '나이': '25'}),
            ],
        )
        csv_str = export_csv(table)
        lines = csv_str.strip().split('\n')
        self.assertEqual(len(lines), 3)  # 헤더 + 2행
        self.assertIn('이름', lines[0])
        self.assertIn('김철수', lines[1])

    def test_empty_export(self):
        table = DataTable(table_id='e', title='빈', columns=[], rows=[])
        csv_str = export_csv(table)
        # 빈 테이블은 빈 헤더 행만
        self.assertIsInstance(csv_str, str)


if __name__ == '__main__':
    unittest.main()
