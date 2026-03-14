"""Sentence Complexity Scorer 서비스 테스트."""
import unittest
from services.analysis.sentence_analysis_service import score_sentence_complexity


class TestSentenceComplexityScorer(unittest.TestCase):

    def test_empty_content(self):
        result = score_sentence_complexity('')
        self.assertEqual(result['score'], 0.0)
        self.assertEqual(result['summary']['total_sentences'], 0)

    def test_none_content(self):
        result = score_sentence_complexity(None)
        self.assertEqual(result['score'], 0.0)

    def test_simple_sentences(self):
        content = '날씨가 좋습니다. 산책을 합니다. 기분이 좋습니다.'
        result = score_sentence_complexity(content)
        self.assertGreater(result['summary']['total_sentences'], 0)
        dist = result['summary']['distribution']
        self.assertGreater(dist['simple'], 0)

    def test_complex_sentences(self):
        content = ('비록 날씨가 좋지 않았지만, 우리는 계획대로 진행했으며, '
                   '결과적으로 (예상과는 달리) 성공적인 결과를 얻었는데, '
                   '이는 팀원들의 헌신적인 노력 덕분이었습니다.')
        result = score_sentence_complexity(content)
        if result['sentences']:
            max_complexity = max(s['complexity'] for s in result['sentences'])
            self.assertGreater(max_complexity, 30.0)

    def test_clause_count(self):
        content = '비가 오지만 우리는 나갔으며 즐거운 시간을 보냈습니다.'
        result = score_sentence_complexity(content)
        if result['sentences']:
            self.assertGreater(result['sentences'][0]['clause_count'], 1)

    def test_nesting_depth(self):
        content = '그는 (전문가들의 (일부는 반대했던) 의견에도) 결정을 내렸습니다.'
        result = score_sentence_complexity(content)
        if result['sentences']:
            self.assertGreater(result['sentences'][0]['nesting_depth'], 0)

    def test_comma_count(self):
        content = '사과, 배, 포도, 딸기, 수박을 샀습니다.'
        result = score_sentence_complexity(content)
        if result['sentences']:
            self.assertGreater(result['sentences'][0]['comma_count'], 0)

    def test_category_simple(self):
        content = '좋은 날입니다. 감사합니다.'
        result = score_sentence_complexity(content)
        categories = [s['category'] for s in result['sentences']]
        self.assertIn('simple', categories)

    def test_avg_complexity(self):
        content = '간단한 문장입니다. 복잡하지 않습니다. 읽기 쉽습니다.'
        result = score_sentence_complexity(content)
        self.assertGreaterEqual(result['summary']['avg_complexity'], 0.0)

    def test_level_balanced(self):
        # 적절한 복잡도의 문장
        content = ('프로젝트 관리에서 가장 중요한 것은 일정 관리입니다. '
                   '팀원들과 소통하며 진행 상황을 공유하는 것이 필수적입니다. '
                   '문제가 발생하면 빠르게 대응하는 것이 좋습니다.')
        result = score_sentence_complexity(content)
        self.assertIn(result['summary']['level'], ('easy', 'balanced'))

    def test_score_range(self):
        content = '일반적인 문장입니다.'
        result = score_sentence_complexity(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 문장입니다.'
        result = score_sentence_complexity(content)
        self.assertIn('sentences', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sentences', result['summary'])
        self.assertIn('avg_complexity', result['summary'])
        self.assertIn('distribution', result['summary'])
        self.assertIn('level', result['summary'])

    def test_sentence_structure(self):
        content = '테스트 문장입니다.'
        result = score_sentence_complexity(content)
        for s in result['sentences']:
            self.assertIn('text', s)
            self.assertIn('word_count', s)
            self.assertIn('clause_count', s)
            self.assertIn('complexity', s)
            self.assertIn('category', s)

    def test_max_30_sentences(self):
        sentences = '. '.join([f'이것은 테스트 문장 번호 {i}입니다' for i in range(40)])
        content = sentences + '.'
        result = score_sentence_complexity(content)
        self.assertLessEqual(len(result['sentences']), 30)

    def test_suggestions_exist(self):
        content = '간단한 문장입니다. 복잡하지 않습니다.'
        result = score_sentence_complexity(content)
        self.assertGreater(len(result['suggestions']), 0)


if __name__ == '__main__':
    unittest.main()
