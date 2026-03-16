"""debate_service 단위 테스트"""
import unittest

from services.content.debate_service import (
    generate_debate,
    analyze_debate_balance,
    _extract_points,
    _generate_questions,
)


class TestGenerateDebate(unittest.TestCase):

    def test_empty_topic(self):
        result = generate_debate('')
        self.assertEqual(result['topic'], '')
        self.assertEqual(result['perspectives'], [])

    def test_none_topic(self):
        result = generate_debate(None)
        self.assertEqual(result['perspectives'], [])

    def test_basic_debate(self):
        result = generate_debate('인공지능 도입')
        self.assertEqual(result['topic'], '인공지능 도입')
        self.assertEqual(len(result['perspectives']), 3)

        stances = [p['stance'] for p in result['perspectives']]
        self.assertIn('pro', stances)
        self.assertIn('con', stances)
        self.assertIn('neutral', stances)

    def test_perspective_structure(self):
        result = generate_debate('원격 근무')
        for p in result['perspectives']:
            self.assertIn('stance', p)
            self.assertIn('label', p)
            self.assertIn('summary', p)
            self.assertIn('key_points', p)
            self.assertIn('considerations', p)
            self.assertIsInstance(p['key_points'], list)
            self.assertGreater(len(p['key_points']), 0)

    def test_discussion_questions(self):
        result = generate_debate('AI 규제')
        self.assertIsInstance(result['discussion_questions'], list)
        self.assertGreater(len(result['discussion_questions']), 0)

    def test_conclusion_exists(self):
        result = generate_debate('기후 변화')
        self.assertIsInstance(result['conclusion'], str)
        self.assertGreater(len(result['conclusion']), 0)

    def test_with_content(self):
        result = generate_debate(
            'AI 교육',
            content='AI를 활용한 맞춤형 학습이 학생들의 성취도를 높였습니다. 그러나 교사의 역할이 축소될 우려도 있습니다.',
        )
        self.assertEqual(len(result['perspectives']), 3)
        # 콘텐츠 포인트가 반영되었는지
        pro = next(p for p in result['perspectives'] if p['stance'] == 'pro')
        self.assertTrue(any('본문' in point for point in pro['key_points']))

    def test_labels_korean(self):
        result = generate_debate('디지털 전환')
        labels = [p['label'] for p in result['perspectives']]
        self.assertIn('찬성', labels)
        self.assertIn('반대', labels)
        self.assertIn('중립/균형', labels)


class TestExtractPoints(unittest.TestCase):

    def test_extracts_sentences(self):
        content = 'AI는 생산성을 높입니다. 하지만 일자리를 줄일 수 있습니다. 균형이 필요합니다.'
        points = _extract_points(content)
        self.assertGreater(len(points), 0)

    def test_empty_content(self):
        self.assertEqual(_extract_points(''), [])
        self.assertEqual(_extract_points(None), [])

    def test_max_points(self):
        content = '긴 문장입니다 내용이 풍부합니다. ' * 20
        points = _extract_points(content)
        self.assertLessEqual(len(points), 5)


class TestGenerateQuestions(unittest.TestCase):

    def test_generates_questions(self):
        questions = _generate_questions('블록체인')
        self.assertEqual(len(questions), 3)
        self.assertTrue(all('블록체인' in q for q in questions))


class TestAnalyzeDebateBalance(unittest.TestCase):
    """analyze_debate_balance 테스트"""

    def test_balanced_debate(self):
        """균형 잡힌 토론 결과 분석"""
        result = generate_debate('인공지능 도입')
        analysis = analyze_debate_balance(result)
        self.assertIn('balance_score', analysis)
        self.assertIn('intensity_score', analysis)
        self.assertIn('per_stance', analysis)
        self.assertIn('verdict', analysis)

    def test_balance_score_range(self):
        """균형 점수는 0~100 범위"""
        result = generate_debate('원격 근무')
        analysis = analyze_debate_balance(result)
        self.assertGreaterEqual(analysis['balance_score'], 0.0)
        self.assertLessEqual(analysis['balance_score'], 100.0)

    def test_intensity_score_range(self):
        """강도 점수는 0~100 범위"""
        result = generate_debate('AI 규제')
        analysis = analyze_debate_balance(result)
        self.assertGreaterEqual(analysis['intensity_score'], 0.0)
        self.assertLessEqual(analysis['intensity_score'], 100.0)

    def test_per_stance_includes_all(self):
        """per_stance에 3개 관점 모두 포함"""
        result = generate_debate('블록체인')
        analysis = analyze_debate_balance(result)
        self.assertIn('pro', analysis['per_stance'])
        self.assertIn('con', analysis['per_stance'])
        self.assertIn('neutral', analysis['per_stance'])

    def test_empty_perspectives(self):
        """빈 관점 목록 처리"""
        analysis = analyze_debate_balance({'perspectives': []})
        self.assertEqual(analysis['balance_score'], 0.0)
        self.assertEqual(analysis['intensity_score'], 0.0)

    def test_verdict_is_string(self):
        """verdict는 비어있지 않은 문자열"""
        result = generate_debate('기후 변화')
        analysis = analyze_debate_balance(result)
        self.assertIsInstance(analysis['verdict'], str)
        self.assertGreater(len(analysis['verdict']), 0)

    def test_per_stance_has_counts(self):
        """per_stance 항목에 point_count, char_count 포함"""
        result = generate_debate('교육 혁신')
        analysis = analyze_debate_balance(result)
        for stance_data in analysis['per_stance'].values():
            self.assertIn('point_count', stance_data)
            self.assertIn('char_count', stance_data)


if __name__ == '__main__':
    unittest.main()
