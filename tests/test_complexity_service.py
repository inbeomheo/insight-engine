"""complexity_service 단위 테스트"""
import unittest

from services.analysis.complexity_service import ComplexityService


class TestComplexityService(unittest.TestCase):

    def setUp(self):
        self.svc = ComplexityService()

    def test_empty_content(self):
        """빈 콘텐츠"""
        report = self.svc.analyze('')
        self.assertEqual(report.sentence_count, 0)
        self.assertEqual(report.expertise_level, 'beginner')

    def test_simple_content(self):
        """간단한 콘텐츠"""
        report = self.svc.analyze('안녕하세요. 간단한 텍스트입니다. 세 번째 문장입니다.')
        self.assertGreater(report.sentence_count, 0)
        self.assertEqual(report.expertise_level, 'beginner')

    def test_expert_content(self):
        """전문 용어가 많은 콘텐츠"""
        content = (
            '딥러닝 신경망 LLM 파인튜닝 RAG GPT 임베딩 트랜스포머 '
            '알고리즘 복잡도 비동기 아키텍처. ' * 5
        )
        report = self.svc.analyze(content)
        self.assertEqual(report.expertise_level, 'expert')
        self.assertGreater(report.technical_term_count, 5)

    def test_domain_detection(self):
        """도메인 감지"""
        content = '딥러닝 신경망 LLM 파인튜닝 트랜스포머 GPT 임베딩'
        report = self.svc.analyze(content)
        self.assertEqual(report.domain_detected, 'ai')

    def test_heading_depth(self):
        """헤딩 깊이"""
        content = '# H1\n## H2\n### H3\n내용입니다. 충분히 긴 문장입니다.'
        report = self.svc.analyze(content)
        self.assertEqual(report.heading_depth, 3)

    def test_code_blocks_counted(self):
        """코드 블록 수"""
        content = '설명입니다.\n```python\nprint("hi")\n```\n더 있습니다.\n```js\nalert(1)\n```\n'
        report = self.svc.analyze(content)
        self.assertEqual(report.code_block_count, 2)

    def test_readability_score_range(self):
        """가독성 점수 범위"""
        report = self.svc.analyze('보통 길이의 문장으로 구성된 콘텐츠입니다. 두 번째 문장입니다.')
        self.assertGreaterEqual(report.readability_score, 0)
        self.assertLessEqual(report.readability_score, 100)

    def test_to_dict(self):
        """to_dict 변환"""
        report = self.svc.analyze('테스트 콘텐츠입니다.')
        d = report.to_dict()
        self.assertIn('readability_score', d)
        self.assertIn('suggestions', d)

    def test_suggestions_for_long_sentences(self):
        """긴 문장에 대한 제안"""
        long = '아' * 200 + '.'
        report = self.svc.analyze(long)
        suggestions = report._get_suggestions()
        self.assertTrue(any('너무 깁니다' in s for s in suggestions))

    def test_list_items_counted(self):
        """목록 항목 수"""
        content = '- 항목1\n- 항목2\n- 항목3\n내용입니다.'
        report = self.svc.analyze(content)
        self.assertEqual(report.list_count, 3)


if __name__ == '__main__':
    unittest.main()
