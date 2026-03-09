"""
CSV 데이터 × 템플릿 대량 생성 오케스트레이션 서비스 테스트
"""
import unittest

from services.bulk_orchestration_service import (
    OrchestrationResult,
    orchestrate_bulk,
    get_template_vars,
    validate_csv_data,
)


class TestOrchestrateBulkSuccess(unittest.TestCase):
    """정상 치환 검증."""

    def test_single_row(self):
        csv_data = [{'name': '홍길동', 'product': '노트북'}]
        template = '안녕하세요 {{name}}님, {{product}} 구매를 환영합니다.'
        results = orchestrate_bulk(csv_data, template)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, 'success')
        self.assertIn('홍길동', results[0].output)
        self.assertIn('노트북', results[0].output)
        self.assertIsNone(results[0].error)

    def test_multiple_rows(self):
        csv_data = [
            {'name': 'Alice', 'city': 'Seoul'},
            {'name': 'Bob', 'city': 'Busan'},
            {'name': 'Charlie', 'city': 'Daegu'},
        ]
        template = '{{name}} lives in {{city}}.'
        results = orchestrate_bulk(csv_data, template)

        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.status == 'success' for r in results))
        self.assertIn('Alice', results[0].output)
        self.assertIn('Busan', results[1].output)
        self.assertEqual(results[2].row_index, 2)


class TestOrchestrateBulkMissingVar(unittest.TestCase):
    """누락 변수 에러 처리."""

    def test_missing_variable(self):
        csv_data = [{'name': '홍길동'}]  # 'product' 누락
        template = '{{name}}님, {{product}}를 추천합니다.'
        results = orchestrate_bulk(csv_data, template)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, 'error')
        self.assertIn('누락 변수', results[0].error)
        self.assertIn('product', results[0].error)
        self.assertEqual(results[0].output, '')

    def test_partial_missing(self):
        """일부 행만 변수 누락."""
        csv_data = [
            {'name': 'A', 'email': 'a@test.com'},
            {'name': 'B'},  # email 누락
        ]
        template = '{{name}} ({{email}})'
        results = orchestrate_bulk(csv_data, template)

        self.assertEqual(results[0].status, 'success')
        self.assertEqual(results[1].status, 'error')


class TestOrchestrateBulkEmptyInput(unittest.TestCase):
    """빈 입력 처리."""

    def test_empty_csv(self):
        results = orchestrate_bulk([], '{{name}} 안녕하세요')
        self.assertEqual(results, [])

    def test_empty_template(self):
        csv_data = [{'name': '홍길동'}]
        results = orchestrate_bulk(csv_data, '')

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, 'error')
        self.assertIn('빈 템플릿', results[0].error)

    def test_whitespace_template(self):
        csv_data = [{'name': '홍길동'}]
        results = orchestrate_bulk(csv_data, '   ')

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, 'error')


class TestOrchestrateBulkRowIndex(unittest.TestCase):
    """row_index가 입력 순서와 일치하는지 검증."""

    def test_row_index_order(self):
        csv_data = [{'x': str(i)} for i in range(5)]
        template = '값: {{x}}'
        results = orchestrate_bulk(csv_data, template)

        for i, r in enumerate(results):
            self.assertEqual(r.row_index, i)


class TestOrchestrateBulkInputDataPreserved(unittest.TestCase):
    """input_data가 원본 dict를 보존하는지 검증."""

    def test_input_data(self):
        original = {'name': '테스트', 'age': '30'}
        results = orchestrate_bulk([original], '{{name}} {{age}}')

        self.assertEqual(results[0].input_data, original)


class TestOrchestrateBulkSpecialChars(unittest.TestCase):
    """특수 문자 포함 치환 검증."""

    def test_html_in_data(self):
        csv_data = [{'content': '<b>Bold</b>'}]
        template = '내용: {{content}}'
        results = orchestrate_bulk(csv_data, template)

        self.assertEqual(results[0].status, 'success')
        self.assertIn('<b>Bold</b>', results[0].output)

    def test_curly_braces_in_output(self):
        """중괄호가 아닌 일반 텍스트는 그대로 유지."""
        csv_data = [{'name': 'test'}]
        template = 'JSON: {"key": "{{name}}"}'
        results = orchestrate_bulk(csv_data, template)

        self.assertEqual(results[0].status, 'success')
        self.assertIn('"key": "test"', results[0].output)


class TestOrchestrateBulkDuplicateVars(unittest.TestCase):
    """같은 변수가 여러 번 등장하는 경우."""

    def test_duplicate_vars(self):
        csv_data = [{'name': '홍길동'}]
        template = '{{name}}님, {{name}}님 환영합니다!'
        results = orchestrate_bulk(csv_data, template)

        self.assertEqual(results[0].status, 'success')
        self.assertEqual(results[0].output.count('홍길동'), 2)


class TestGetTemplateVars(unittest.TestCase):
    """템플릿 변수 추출."""

    def test_extract_vars(self):
        template = '{{name}}님, {{product}}를 {{count}}개 주문했습니다.'
        vars_list = get_template_vars(template)

        self.assertEqual(len(vars_list), 3)
        self.assertIn('name', vars_list)
        self.assertIn('product', vars_list)
        self.assertIn('count', vars_list)

    def test_no_vars(self):
        self.assertEqual(get_template_vars('변수 없는 텍스트'), [])

    def test_duplicate_vars_deduped(self):
        template = '{{name}} {{name}} {{name}}'
        self.assertEqual(len(get_template_vars(template)), 1)


class TestValidateCsvData(unittest.TestCase):
    """CSV 데이터 검증."""

    def test_all_valid(self):
        csv_data = [
            {'name': 'A', 'email': 'a@test.com'},
            {'name': 'B', 'email': 'b@test.com'},
        ]
        template = '{{name}} ({{email}})'
        result = validate_csv_data(csv_data, template)

        self.assertTrue(result['valid'])
        self.assertEqual(result['total_rows'], 2)
        self.assertEqual(result['valid_rows'], 2)
        self.assertEqual(result['invalid_rows'], 0)

    def test_some_invalid(self):
        csv_data = [
            {'name': 'A', 'email': 'a@test.com'},
            {'name': 'B'},  # email 누락
        ]
        template = '{{name}} ({{email}})'
        result = validate_csv_data(csv_data, template)

        self.assertFalse(result['valid'])
        self.assertEqual(result['valid_rows'], 1)
        self.assertEqual(result['invalid_rows'], 1)
        self.assertIn(1, result['missing_vars_per_row'])
        self.assertIn('email', result['missing_vars_per_row'][1])


class TestOrchestrateBulkNoVarsTemplate(unittest.TestCase):
    """변수 없는 템플릿 — 모든 행에 동일 출력."""

    def test_static_template(self):
        csv_data = [{'a': '1'}, {'b': '2'}]
        template = '고정 텍스트입니다.'
        results = orchestrate_bulk(csv_data, template)

        self.assertEqual(len(results), 2)
        self.assertTrue(all(r.status == 'success' for r in results))
        self.assertTrue(all(r.output == '고정 텍스트입니다.' for r in results))


if __name__ == '__main__':
    unittest.main()
