"""Content Symmetry Analyzer 서비스 테스트."""
import unittest
from services.content_symmetry_analyzer_service import analyze_content_symmetry


class TestContentSymmetryAnalyzer(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_content_symmetry('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['summary']['total_sections'], 0)

    def test_none_content(self):
        result = analyze_content_symmetry(None)
        self.assertEqual(result['score'], 0.0)

    def test_single_section(self):
        content = '이것은 단일 섹션의 콘텐츠입니다. 헤딩이 없습니다.'
        result = analyze_content_symmetry(content)
        self.assertEqual(result['summary']['level'], 'single')
        self.assertEqual(result['score'], 50.0)

    def test_symmetric_sections(self):
        # 비슷한 길이의 섹션들
        section1 = ' '.join(['단어'] * 20)
        section2 = ' '.join(['내용'] * 20)
        section3 = ' '.join(['설명'] * 20)
        content = f'# 섹션1\n{section1}\n# 섹션2\n{section2}\n# 섹션3\n{section3}'
        result = analyze_content_symmetry(content)
        self.assertEqual(result['summary']['level'], 'symmetric')
        self.assertGreaterEqual(result['score'], 90.0)

    def test_asymmetric_sections(self):
        # 길이가 매우 다른 섹션들
        short = '짧은 섹션입니다.'
        long_text = ' '.join(['상세한 내용을 포함하는 긴 문장입니다'] * 30)
        content = f'# 짧은 섹션\n{short}\n# 긴 섹션\n{long_text}'
        result = analyze_content_symmetry(content)
        self.assertIn(result['summary']['level'], ('asymmetric', 'very_asymmetric'))

    def test_sections_data(self):
        content = ('# 서론\n서론 내용입니다 여러 단어를 포함합니다.\n'
                   '# 본론\n본론 내용입니다 더 많은 단어가 있습니다.')
        result = analyze_content_symmetry(content)
        self.assertGreater(len(result['sections']), 0)
        for s in result['sections']:
            self.assertIn('title', s)
            self.assertIn('word_count', s)
            self.assertIn('ratio', s)

    def test_balance_info(self):
        content = ('# 파트1\n내용1 단어 여러개 포함.\n'
                   '# 파트2\n내용2 단어 여러개 포함.')
        result = analyze_content_symmetry(content)
        balance = result['balance']
        self.assertIn('mean_words', balance)
        self.assertIn('min_words', balance)
        self.assertIn('max_words', balance)
        self.assertIn('cv', balance)

    def test_cv_symmetric(self):
        # 동일한 길이의 섹션
        words = ' '.join(['테스트'] * 15)
        content = f'# A\n{words}\n# B\n{words}\n# C\n{words}'
        result = analyze_content_symmetry(content)
        self.assertLessEqual(result['summary']['cv'], 0.1)

    def test_cv_asymmetric(self):
        short = '짧음'
        long_text = ' '.join(['길다'] * 50)
        content = f'# 짧은\n{short}\n# 긴\n{long_text}'
        result = analyze_content_symmetry(content)
        self.assertGreater(result['summary']['cv'], 0.5)

    def test_score_range(self):
        content = '# 제목\n내용입니다.\n# 제목2\n내용2입니다.'
        result = analyze_content_symmetry(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '# A\n내용1.\n# B\n내용2.'
        result = analyze_content_symmetry(content)
        self.assertIn('sections', result)
        self.assertIn('balance', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sections', result['summary'])
        self.assertIn('cv', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_asymmetric(self):
        short = '짧은 내용'
        long_text = ' '.join(['상세한 내용'] * 30)
        content = f'# 짧은 섹션\n{short}\n# 긴 섹션\n{long_text}'
        result = analyze_content_symmetry(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_max_20_sections(self):
        sections = '\n'.join([f'# 섹션{i}\n내용 {i} 여러 단어 포함합니다.' for i in range(25)])
        result = analyze_content_symmetry(sections)
        self.assertLessEqual(len(result['sections']), 20)

    def test_intro_section_before_heading(self):
        content = ('서론 부분입니다 헤딩 전에 나옵니다.\n'
                   '# 본문\n본문 내용입니다 여러 단어가 있습니다.')
        result = analyze_content_symmetry(content)
        # 서론 섹션이 "(서론)"으로 캡처되어야 함
        titles = [s['title'] for s in result['sections']]
        self.assertIn('(서론)', titles)


if __name__ == '__main__':
    unittest.main()
