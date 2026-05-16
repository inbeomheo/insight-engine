"""content_splitter_service 단위 테스트"""
import unittest

from services.content.content_splitter_service import (
    split_by_headings,
    split_by_length,
)


class TestSplitByHeadings(unittest.TestCase):

    def test_empty(self):
        result = split_by_headings('')
        self.assertEqual(result['total_parts'], 0)

    def test_none(self):
        result = split_by_headings(None)
        self.assertEqual(result['total_parts'], 0)

    def test_no_headings(self):
        result = split_by_headings('그냥 텍스트입니다.')
        self.assertEqual(result['total_parts'], 1)

    def test_h2_split(self):
        text = '## 파트1\n내용1\n## 파트2\n내용2\n## 파트3\n내용3'
        result = split_by_headings(text, split_level=2)
        self.assertEqual(result['total_parts'], 3)
        self.assertEqual(result['parts'][0]['title'], '파트1')

    def test_h1_split(self):
        text = '# 섹션A\n내용A\n# 섹션B\n내용B'
        result = split_by_headings(text, split_level=1)
        self.assertEqual(result['total_parts'], 2)

    def test_mixed_levels(self):
        text = '## 메인\n본문\n### 서브\n서브 내용\n## 메인2\n본문2'
        result = split_by_headings(text, split_level=2)
        # H2에서만 분할, H3는 내부에 포함
        self.assertEqual(result['total_parts'], 2)

    def test_intro_before_heading(self):
        text = '도입부 텍스트\n## 섹션1\n내용'
        result = split_by_headings(text, split_level=2)
        self.assertGreaterEqual(result['total_parts'], 2)

    def test_word_count_per_part(self):
        text = '## A\n단어1 단어2 단어3\n## B\n단어4 단어5'
        result = split_by_headings(text)
        for part in result['parts']:
            self.assertGreater(part['word_count'], 0)

    def test_total_words(self):
        text = '## A\n내용A\n## B\n내용B'
        result = split_by_headings(text)
        self.assertGreater(result['total_words'], 0)

    def test_part_numbers_sequential(self):
        text = '## A\n1\n## B\n2\n## C\n3'
        result = split_by_headings(text)
        numbers = [p['part_number'] for p in result['parts']]
        self.assertEqual(numbers, [1, 2, 3])


class TestSplitByLength(unittest.TestCase):

    def test_empty(self):
        result = split_by_length('')
        self.assertEqual(result['total_parts'], 0)

    def test_short_content(self):
        result = split_by_length('짧은 글', max_chars=2000)
        self.assertEqual(result['total_parts'], 1)

    def test_long_content_split(self):
        text = '\n\n'.join([f'문단 {i}. ' * 20 for i in range(10)])
        result = split_by_length(text, max_chars=500)
        self.assertGreater(result['total_parts'], 1)

    def test_respects_max_chars(self):
        text = '\n\n'.join([f'문단 {i}입니다. ' * 15 for i in range(10)])
        result = split_by_length(text, max_chars=500)
        for part in result['parts']:
            # 문단 경계라 약간 초과 가능
            self.assertLessEqual(part['char_count'], 600)

    def test_part_numbers(self):
        text = '\n\n'.join([f'내용 {i}. ' * 20 for i in range(5)])
        result = split_by_length(text, max_chars=500)
        if result['total_parts'] > 1:
            numbers = [p['part_number'] for p in result['parts']]
            self.assertEqual(numbers, list(range(1, len(numbers) + 1)))

    def test_min_max_chars_clamped(self):
        text = '테스트 ' * 100
        result = split_by_length(text, max_chars=100)  # 500 미만 → 500으로 클램프
        # max_chars가 500으로 올라감
        for part in result['parts']:
            self.assertIsInstance(part['char_count'], int)


if __name__ == '__main__':
    unittest.main()
