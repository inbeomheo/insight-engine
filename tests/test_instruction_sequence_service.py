"""Instruction Sequence Validator 서비스 테스트."""
import unittest
from services.instruction_sequence_service import validate_instruction_sequence


class TestInstructionSequenceValidator(unittest.TestCase):

    def test_empty_content(self):
        result = validate_instruction_sequence('')
        self.assertEqual(result['score'], 100.0)
        self.assertFalse(result['summary']['has_instructions'])

    def test_none_content(self):
        result = validate_instruction_sequence(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_instructions(self):
        content = '일반 텍스트입니다. 절차가 없습니다.'
        result = validate_instruction_sequence(content)
        self.assertFalse(result['summary']['has_instructions'])

    def test_correct_numbered_sequence(self):
        content = '1. 환경 설정\n2. 코드 작성\n3. 테스트 실행'
        result = validate_instruction_sequence(content)
        self.assertTrue(result['summary']['has_instructions'])
        self.assertEqual(result['summary']['total_issues'], 0)
        self.assertEqual(result['score'], 100.0)

    def test_skipped_number(self):
        content = '1. 환경 설정\n2. 코드 작성\n4. 테스트 실행'
        result = validate_instruction_sequence(content)
        self.assertGreater(result['summary']['total_issues'], 0)

    def test_duplicate_number(self):
        content = '1. 환경 설정\n2. 코드 작성\n2. 테스트 실행'
        result = validate_instruction_sequence(content)
        self.assertGreater(result['summary']['total_issues'], 0)

    def test_wrong_start(self):
        content = '2. 코드 작성\n3. 테스트 실행\n4. 배포'
        result = validate_instruction_sequence(content)
        self.assertGreater(result['summary']['total_issues'], 0)

    def test_step_n_pattern(self):
        content = 'Step 1: 설치\nStep 2: 설정\nStep 3: 실행'
        result = validate_instruction_sequence(content)
        self.assertTrue(result['summary']['has_instructions'])
        self.assertEqual(result['summary']['total_issues'], 0)

    def test_step_n_skip(self):
        content = 'Step 1: 설치\nStep 3: 실행'
        result = validate_instruction_sequence(content)
        self.assertGreater(result['summary']['total_issues'], 0)

    def test_korean_ordinals(self):
        content = '첫째 환경을 설정합니다. 둘째 코드를 작성합니다. 셋째 테스트합니다.'
        result = validate_instruction_sequence(content)
        self.assertTrue(result['summary']['has_instructions'])

    def test_english_ordinals(self):
        content = 'First install the package. Second configure it. Third run tests.'
        result = validate_instruction_sequence(content)
        self.assertTrue(result['summary']['has_instructions'])

    def test_score_decreases_with_issues(self):
        content = '1. 설치\n3. 실행\n5. 배포'
        result = validate_instruction_sequence(content)
        self.assertLess(result['score'], 100.0)

    def test_suggestions_for_issues(self):
        content = '1. 설치\n3. 실행'
        result = validate_instruction_sequence(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_suggestions_correct(self):
        content = '1. 설치\n2. 설정\n3. 실행'
        result = validate_instruction_sequence(content)
        self.assertTrue(any('올바르게' in s for s in result['suggestions']))

    def test_return_structure(self):
        content = '1. 테스트'
        result = validate_instruction_sequence(content)
        self.assertIn('sequences', result)
        self.assertIn('ordinals', result)
        self.assertIn('issues', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sequences', result['summary'])
        self.assertIn('total_steps', result['summary'])


if __name__ == '__main__':
    unittest.main()
