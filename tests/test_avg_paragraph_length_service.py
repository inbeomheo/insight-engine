"""Average Paragraph Length 서비스 테스트."""
import unittest
from services.analysis.avg_paragraph_length_service import analyze_avg_paragraph_length


class TestAvgParagraphLength(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_avg_paragraph_length('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['summary']['total_paragraphs'], 0)

    def test_none_content(self):
        result = analyze_avg_paragraph_length(None)
        self.assertEqual(result['score'], 0.0)

    def test_optimal_paragraphs(self):
        p1 = ' '.join(['단어'] * 80)
        p2 = ' '.join(['내용'] * 70)
        p3 = ' '.join(['설명'] * 90)
        content = f'{p1}\n\n{p2}\n\n{p3}'
        result = analyze_avg_paragraph_length(content)
        self.assertEqual(result['summary']['level'], 'optimal')
        self.assertGreaterEqual(result['score'], 90.0)

    def test_short_paragraphs(self):
        content = '짧은 단락 내용입니다.\n\n또 다른 짧은 단락입니다.\n\n매우 짧은 내용입니다.'
        result = analyze_avg_paragraph_length(content)
        self.assertEqual(result['summary']['level'], 'too_short')

    def test_long_paragraphs(self):
        long_text = ' '.join(['상세한 내용을 포함하는 긴 문장입니다'] * 50)
        content = f'{long_text}\n\n{long_text}'
        result = analyze_avg_paragraph_length(content)
        self.assertEqual(result['summary']['level'], 'too_long')

    def test_paragraph_data_structure(self):
        content = '첫 번째 단락 내용입니다 여러 단어를 포함합니다.\n\n두 번째 단락 내용입니다 역시 여러 단어가 있습니다.'
        result = analyze_avg_paragraph_length(content)
        for p in result['paragraph_data']:
            self.assertIn('preview', p)
            self.assertIn('word_count', p)
            self.assertIn('sentence_count', p)
            self.assertIn('category', p)

    def test_avg_words(self):
        p1 = ' '.join(['테스트'] * 50)
        p2 = ' '.join(['데이터'] * 60)
        content = f'{p1}\n\n{p2}'
        result = analyze_avg_paragraph_length(content)
        self.assertGreater(result['summary']['avg_words'], 0.0)

    def test_avg_sentences(self):
        content = ('문장1입니다. 문장2입니다. 문장3입니다.\n\n'
                   '문장4입니다. 문장5입니다.')
        result = analyze_avg_paragraph_length(content)
        self.assertGreater(result['summary']['avg_sentences'], 0.0)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.\n\n두 번째 단락입니다.'
        result = analyze_avg_paragraph_length(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인입니다.\n\n두 번째 단락입니다.'
        result = analyze_avg_paragraph_length(content)
        self.assertIn('paragraph_data', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_paragraphs', result['summary'])
        self.assertIn('avg_words', result['summary'])
        self.assertIn('avg_sentences', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_exist(self):
        content = '단락1 내용입니다.\n\n단락2 내용입니다.'
        result = analyze_avg_paragraph_length(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_max_20_paragraph_data(self):
        paragraphs = '\n\n'.join([f'단락 번호 {i} 내용입니다 여러 단어 포함.' for i in range(25)])
        result = analyze_avg_paragraph_length(paragraphs)
        self.assertLessEqual(len(result['paragraph_data']), 20)

    def test_mixed_lengths(self):
        short = '짧은 단락 내용입니다.'
        long_text = ' '.join(['상세한 내용'] * 40)
        content = f'{short}\n\n{long_text}\n\n{short}'
        result = analyze_avg_paragraph_length(content)
        self.assertGreater(result['summary'].get('long_paragraphs', 0) +
                          result['summary'].get('short_paragraphs', 0), 0)


if __name__ == '__main__':
    unittest.main()
