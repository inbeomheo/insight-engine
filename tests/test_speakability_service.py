"""
Speakability Analyzer 서비스 테스트
"""
import unittest

from services.speakability_service import analyze_speakability


class TestSpeakabilityService(unittest.TestCase):
    """음성 적합성 분석 서비스 테스트"""

    # --- 기본 케이스 ---

    def test_empty_content(self):
        """빈 콘텐츠는 기본값 반환"""
        result = analyze_speakability('')
        self.assertEqual(result['speakability_score'], 100.0)
        self.assertEqual(result['problem_sentences'], [])
        self.assertIn('콘텐츠가 비어 있습니다.', result['suggestions'])

        # None 입력도 동일
        result_none = analyze_speakability(None)
        self.assertEqual(result_none['speakability_score'], 100.0)

    def test_clean_speakable_content(self):
        """깨끗한 음성 적합 콘텐츠는 높은 점수"""
        content = (
            '오늘은 날씨가 좋습니다. '
            '산책을 나가면 기분이 좋아집니다. '
            '공원에서 새소리를 들었습니다. '
            '맑은 하늘이 참 예뻤습니다.'
        )
        result = analyze_speakability(content)
        # 짧은 문장, 약어 없음, 숫자 없음 → 높은 점수
        self.assertGreaterEqual(result['speakability_score'], 80.0)
        self.assertEqual(len(result['problem_sentences']), 0)

    # --- 개별 요소 감점 ---

    def test_long_sentences_penalty(self):
        """긴 문장이 많으면 문장 길이 점수 감소"""
        # 각 문장이 80자 이상
        long_sentence = '이것은 매우 길고 복잡한 문장으로서 음성으로 읽기에 적합하지 않은 구조를 가지고 있으며 청취자가 이해하기 어려울 수 있는 내용을 담고 있습니다'
        content = f'{long_sentence}. {long_sentence}. {long_sentence}.'
        result = analyze_speakability(content)

        # 문장 길이 점수가 낮아야 함
        self.assertLess(result['factors']['sentence_length']['score'], 50.0)
        self.assertGreater(result['factors']['sentence_length']['avg_length'], 60.0)

    def test_abbreviation_penalty(self):
        """약어가 많으면 약어 밀도 점수 감소"""
        content = (
            'API와 SDK를 활용한 REST 서비스입니다. '
            'HTTP와 HTTPS를 지원합니다. '
            'JSON과 XML 포맷을 사용합니다. '
            'AWS와 GCP 클라우드입니다. '
            'CPU와 GPU를 활용합니다.'
        )
        result = analyze_speakability(content)

        # 약어 밀도 점수가 낮아야 함
        self.assertLess(result['factors']['abbreviation_density']['score'], 80.0)
        self.assertGreater(result['factors']['abbreviation_density']['count'], 5)

    def test_number_density_penalty(self):
        """숫자가 과다하면 숫자 밀도 점수 감소"""
        content = (
            '매출은 1200만원에서 3500만원으로 증가했습니다. '
            '성장률은 45.2%이고 영업이익은 890만원입니다. '
            '직원 수는 23명에서 67명으로 늘었습니다. '
            '2024년 목표는 5000만원입니다.'
        )
        result = analyze_speakability(content)

        # 숫자 밀도 점수가 낮아야 함
        self.assertLess(result['factors']['number_density']['score'], 80.0)
        self.assertGreater(result['factors']['number_density']['count'], 5)

    def test_parenthetical_penalty(self):
        """괄호 표현이 많으면 괄호 밀도 점수 감소"""
        content = (
            '머신러닝(Machine Learning)은 인공지능(AI)의 한 분야입니다. '
            '딥러닝(Deep Learning)은 신경망(Neural Network)을 사용합니다. '
            '자연어 처리(NLP)도 중요합니다. '
            '컴퓨터 비전(CV)도 활용됩니다.'
        )
        result = analyze_speakability(content)

        # 괄호 밀도 점수가 낮아야 함
        self.assertLess(result['factors']['parenthetical_density']['score'], 80.0)
        self.assertGreaterEqual(result['factors']['parenthetical_density']['count'], 4)

    def test_complex_structure_detection(self):
        """복잡한 구조(표, 코드, 중첩 괄호, 긴 나열)를 탐지"""
        content = (
            '다음은 코드입니다.\n'
            '```python\nprint("hello")\n```\n'
            '표 형식도 있습니다.\n'
            '| 항목 | 값 |\n| A | 1 |\n'
            '중첩 괄호도 있습니다 (이것은 (중첩된) 괄호입니다).\n'
            '항목은 사과, 배, 포도, 딸기, 수박, 참외, 망고가 있습니다.'
        )
        result = analyze_speakability(content)

        issues = result['factors']['complex_structure']['issues']
        self.assertGreater(len(issues), 0)
        self.assertLess(result['factors']['complex_structure']['score'], 80.0)

    # --- 반환 구조 검증 ---

    def test_score_range(self):
        """모든 점수가 0~100 범위 내"""
        test_cases = [
            '',
            '짧은 문장입니다.',
            'API SDK REST HTTP JSON XML AWS GCP CPU GPU' * 10,
            '12345 67890 11111 22222 33333 44444' * 5,
        ]
        for content in test_cases:
            result = analyze_speakability(content)

            self.assertGreaterEqual(result['speakability_score'], 0.0)
            self.assertLessEqual(result['speakability_score'], 100.0)

            for factor_name, factor_data in result['factors'].items():
                self.assertGreaterEqual(
                    factor_data['score'], 0.0,
                    f'{factor_name} 점수가 0 미만: {factor_data["score"]}'
                )
                self.assertLessEqual(
                    factor_data['score'], 100.0,
                    f'{factor_name} 점수가 100 초과: {factor_data["score"]}'
                )

    def test_factors_structure(self):
        """factors 딕셔너리 구조가 올바른지 검증"""
        result = analyze_speakability('테스트 콘텐츠입니다.')

        expected_factors = [
            'sentence_length', 'abbreviation_density',
            'number_density', 'parenthetical_density', 'complex_structure',
        ]
        for factor in expected_factors:
            self.assertIn(factor, result['factors'], f'{factor} 누락')
            self.assertIn('score', result['factors'][factor], f'{factor}에 score 누락')

        # sentence_length 구조
        self.assertIn('avg_length', result['factors']['sentence_length'])

        # abbreviation_density 구조
        self.assertIn('count', result['factors']['abbreviation_density'])
        self.assertIn('density', result['factors']['abbreviation_density'])

        # number_density 구조
        self.assertIn('count', result['factors']['number_density'])
        self.assertIn('density', result['factors']['number_density'])

        # parenthetical_density 구조
        self.assertIn('count', result['factors']['parenthetical_density'])

        # complex_structure 구조
        self.assertIn('issues', result['factors']['complex_structure'])

    def test_problem_sentences(self):
        """문제 문장이 올바르게 식별되는지 검증"""
        content = (
            '이것은 짧은 문장입니다. '
            '이것은 매우 매우 매우 길고 복잡한 문장으로서 다양한 내용을 담고 있어 음성으로 읽기에 적합하지 않은 구조를 가집니다. '
            '약어 API와 SDK와 REST를 포함한 문장입니다. '
            '이것은 괄호(bracket)가 포함된 문장입니다.'
        )
        result = analyze_speakability(content)

        self.assertGreater(len(result['problem_sentences']), 0)

        # 각 문제 문장에 sentence, reason 필드 확인
        for problem in result['problem_sentences']:
            self.assertIn('sentence', problem)
            self.assertIn('reason', problem)
            self.assertIsInstance(problem['sentence'], str)
            self.assertIsInstance(problem['reason'], str)

    def test_suggestions(self):
        """개선 제안이 생성되는지 검증"""
        # 문제가 많은 콘텐츠
        content = (
            '이것은 매우 길고 복잡한 문장으로서 음성으로 읽기에 적합하지 않은 구조를 가지고 있으며 청취자가 이해하기 어려울 수 있는 내용입니다. '
            'API와 SDK를 사용합니다. '
            '수치는 1234만원이고 성장률 56.7%입니다. '
            '머신러닝(ML)과 딥러닝(DL)이 있습니다.'
        )
        result = analyze_speakability(content)

        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)

        # 깨끗한 콘텐츠에도 최소 1개 제안
        clean_result = analyze_speakability('오늘 날씨가 좋습니다. 기분도 좋습니다.')
        self.assertGreater(len(clean_result['suggestions']), 0)

    def test_mixed_content(self):
        """혼합 콘텐츠에서 종합 점수가 적절히 계산되는지 검증"""
        # 일부 문제가 있는 혼합 콘텐츠
        content = (
            '인공지능 기술이 발전하고 있습니다. '           # 깨끗
            '자연어 처리(NLP)는 텍스트를 분석합니다. '       # 괄호 1개
            'API를 통해 서비스를 제공합니다. '              # 약어 1개
            '매출이 120% 증가했습니다. '                    # 숫자 1개
            '클라우드 서비스를 활용합니다. '                 # 깨끗
            '데이터 분석이 중요합니다.'                      # 깨끗
        )
        result = analyze_speakability(content)

        # 혼합 콘텐츠이므로 중간 점수대
        self.assertGreaterEqual(result['speakability_score'], 40.0)
        self.assertLessEqual(result['speakability_score'], 100.0)

        # 모든 반환 키 존재
        self.assertIn('factors', result)
        self.assertIn('speakability_score', result)
        self.assertIn('problem_sentences', result)
        self.assertIn('suggestions', result)


if __name__ == '__main__':
    unittest.main()
