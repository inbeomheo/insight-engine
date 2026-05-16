"""content_diff_service 단위 테스트"""
import unittest

from services.content.content_diff_service import (
    compare_content,
    generate_unified_diff,
    _split_into_lines,
    _word_count,
)


class TestCompareContent(unittest.TestCase):

    def test_identical_content(self):
        result = compare_content('동일한 내용', '동일한 내용')
        self.assertEqual(result['similarity'], 1.0)
        self.assertEqual(result['stats']['additions'], 0)
        self.assertEqual(result['stats']['deletions'], 0)
        self.assertEqual(result['stats']['modifications'], 0)

    def test_completely_different(self):
        result = compare_content('원본 텍스트', 'completely different text')
        self.assertLess(result['similarity'], 0.5)

    def test_empty_original(self):
        result = compare_content('', '새 내용')
        self.assertGreater(result['stats']['additions'], 0)

    def test_empty_revised(self):
        result = compare_content('기존 내용', '')
        self.assertGreater(result['stats']['deletions'], 0)

    def test_both_empty(self):
        result = compare_content('', '')
        self.assertEqual(result['similarity'], 1.0)
        self.assertEqual(len(result['changes']), 0)

    def test_none_inputs(self):
        result = compare_content(None, None)
        self.assertEqual(result['similarity'], 1.0)

    def test_none_original(self):
        result = compare_content(None, '내용')
        self.assertIn('additions', result['stats'])

    def test_additions_detected(self):
        original = '첫 줄\n둘째 줄'
        revised = '첫 줄\n새 줄\n둘째 줄'
        result = compare_content(original, revised)
        add_changes = [c for c in result['changes'] if c['type'] == 'add']
        self.assertGreater(len(add_changes), 0)

    def test_deletions_detected(self):
        original = '첫 줄\n삭제할 줄\n셋째 줄'
        revised = '첫 줄\n셋째 줄'
        result = compare_content(original, revised)
        del_changes = [c for c in result['changes'] if c['type'] == 'delete']
        self.assertGreater(len(del_changes), 0)

    def test_modifications_detected(self):
        original = '원래 문장입니다'
        revised = '수정된 문장입니다'
        result = compare_content(original, revised)
        self.assertGreater(result['stats']['modifications'], 0)

    def test_word_diff(self):
        result = compare_content('세 개 단어', '네 개의 다른 단어')
        self.assertEqual(result['word_diff']['original'], 3)
        self.assertEqual(result['word_diff']['revised'], 4)

    def test_char_diff(self):
        result = compare_content('짧은', '긴 텍스트입니다')
        self.assertGreater(result['char_diff']['delta'], 0)

    def test_similarity_range(self):
        result = compare_content('테스트', '테스트 변형')
        self.assertGreaterEqual(result['similarity'], 0.0)
        self.assertLessEqual(result['similarity'], 1.0)

    def test_change_line_numbers(self):
        original = '첫째\n둘째\n셋째'
        revised = '첫째\n변경됨\n셋째'
        result = compare_content(original, revised)
        for change in result['changes']:
            self.assertIn('line', change)
            self.assertGreater(change['line'], 0)


class TestGenerateUnifiedDiff(unittest.TestCase):

    def test_basic_diff(self):
        diff = generate_unified_diff('원본\n내용', '수정\n내용')
        self.assertIn('---', diff)
        self.assertIn('+++', diff)

    def test_no_diff(self):
        diff = generate_unified_diff('동일', '동일')
        self.assertEqual(diff, '')

    def test_custom_labels(self):
        diff = generate_unified_diff('a', 'b', label_a='v1', label_b='v2')
        self.assertIn('v1', diff)
        self.assertIn('v2', diff)

    def test_none_inputs(self):
        diff = generate_unified_diff(None, '내용')
        self.assertIsInstance(diff, str)


class TestWordCount(unittest.TestCase):

    def test_korean(self):
        self.assertGreater(_word_count('한국어 문장 테스트'), 0)

    def test_english(self):
        self.assertEqual(_word_count('three english words'), 3)

    def test_mixed(self):
        count = _word_count('한국어와 english mixed')
        self.assertGreaterEqual(count, 3)

    def test_empty(self):
        self.assertEqual(_word_count(''), 0)


class TestSplitIntoLines(unittest.TestCase):

    def test_basic_split(self):
        lines = _split_into_lines('첫째\n둘째\n셋째')
        self.assertEqual(len(lines), 3)

    def test_single_line(self):
        lines = _split_into_lines('한 줄')
        self.assertEqual(len(lines), 1)

    def test_empty(self):
        lines = _split_into_lines('')
        # 빈 문자열의 splitlines()는 빈 리스트 반환
        self.assertEqual(len(lines), 0)


if __name__ == '__main__':
    unittest.main()
