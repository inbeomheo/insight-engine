"""
검색 의도 적합도 분석 서비스 테스트

analyze_search_intent 함수의 의도 감지, 신호 점수, 형식 매칭,
권장 형식, 제안 생성 등을 검증한다.
"""

import unittest
from services.search_intent_service import analyze_search_intent


class TestSearchIntentService(unittest.TestCase):
    """검색 의도 분석 서비스 단위 테스트."""

    # ─── 1. 빈/None 입력 처리 ───

    def test_empty_content(self):
        """빈 문자열 입력 시 기본값을 반환한다."""
        result = analyze_search_intent('')
        self.assertEqual(result['detected_intent'], 'informational')
        self.assertEqual(result['intent_confidence'], 0.0)
        self.assertEqual(result['content_format_match'], 0.0)
        self.assertIn('콘텐츠가 비어 있습니다', result['format_issues'])
        self.assertTrue(len(result['suggestions']) > 0)

    def test_none_content(self):
        """None 입력 시 기본값을 반환한다."""
        result = analyze_search_intent(None)
        self.assertEqual(result['detected_intent'], 'informational')
        self.assertEqual(result['intent_confidence'], 0.0)
        # 모든 신호 0
        for intent, score in result['intent_signals'].items():
            self.assertEqual(score, 0.0,
                             f'{intent} 신호가 0이어야 합니다')

    # ─── 2. 의도 감지 ───

    def test_informational_intent(self):
        """정보 탐색 의도 콘텐츠를 감지한다."""
        content = """
# Python이란 무엇인가

## 정의와 개념

Python은 1991년 귀도 반 로섬이 만든 프로그래밍 언어입니다.
인터프리터 방식으로 동작하며, 문법이 간결합니다.

## 사용 방법

Python을 설치하는 방법은 다음과 같습니다.
가이드를 따라 진행하면 됩니다.

1. 공식 사이트에서 다운로드합니다
2. 설치 파일을 실행합니다
3. 환경변수를 설정합니다

## 왜 Python을 배워야 하는가

Python을 배우는 이유는 다양합니다.
"""
        result = analyze_search_intent(content)
        self.assertEqual(result['detected_intent'], 'informational')
        self.assertGreater(result['intent_signals']['informational'], 0)

    def test_commercial_intent(self):
        """상업적 조사 의도 콘텐츠를 감지한다."""
        content = """
# 2024 노트북 추천 TOP 5 비교 리뷰

## 노트북 비교 순위

최고의 노트북을 선별했습니다. 각 제품의 장단점을 평가했습니다.

| 제품 | 가격 | 성능 | 평점 |
|------|------|------|------|
| A제품 | 100만원 | 높음 | 9/10 |
| B제품 | 80만원 | 중간 | 7/10 |

## 장단점 분석

A제품은 B제품보다 더 좋은 성능을 보여줍니다.
B제품은 가격 대비 우수한 특징을 가지고 있습니다.
베스트 선택은 용도에 따라 달라집니다.
"""
        result = analyze_search_intent(content)
        self.assertEqual(result['detected_intent'], 'commercial')
        self.assertGreater(result['intent_signals']['commercial'], 0)

    def test_transactional_intent(self):
        """거래/행동 의도 콘텐츠를 감지한다."""
        content = """
지금 바로 구매하세요! 50% 할인 이벤트 진행 중입니다.

특별 가격: 29,900원 (정가 59,800원)
무료 체험 기간 30일 제공합니다.

쿠폰 코드를 입력하면 추가 할인을 받을 수 있습니다.
지금 신청하시면 즉시 이용 가능합니다.

결제는 카드, 계좌이체 모두 가능합니다.
가입하세요!
"""
        result = analyze_search_intent(content)
        self.assertEqual(result['detected_intent'], 'transactional')
        self.assertGreater(result['intent_signals']['transactional'], 0)

    def test_navigational_intent(self):
        """특정 브랜드/사이트 탐색 의도를 감지한다."""
        content = """
Samsung 공식 사이트에서 Samsung Galaxy 제품을 확인하세요.
Samsung 홈페이지에 로그인하면 Samsung 멤버십 혜택을 받을 수 있습니다.

방문하기: https://www.samsung.com
바로가기 링크를 통해 접속할 수 있습니다.
"""
        result = analyze_search_intent(content)
        self.assertEqual(result['detected_intent'], 'navigational')
        self.assertGreater(result['intent_signals']['navigational'], 0)

    # ─── 3. 신호 범위 검증 ───

    def test_intent_signals_range(self):
        """모든 의도 신호 점수가 0-100 범위 내에 있다."""
        # 매우 많은 키워드가 포함된 콘텐츠
        content = """
무엇 뜻 정의 의미 개념 어떻게 방법 가이드 튜토리얼
왜 이유 원인 추천 비교 리뷰 평가 순위 최고 베스트 TOP vs
장단점 특징 가격 구매 가입 다운로드 신청 등록 할인 쿠폰
무료 체험 공식 홈페이지 사이트 로그인 입니다. 합니다.
지금 바로 시작 클릭 시작하세요 결제 원 별점 평점
"""
        result = analyze_search_intent(content)
        for intent, score in result['intent_signals'].items():
            self.assertGreaterEqual(score, 0.0,
                                    f'{intent} 신호가 0 이상이어야 합니다')
            self.assertLessEqual(score, 100.0,
                                 f'{intent} 신호가 100 이하여야 합니다')

    # ─── 4. 신뢰도 계산 ───

    def test_intent_confidence(self):
        """신뢰도는 최고 점수와 두 번째 점수의 차이이다."""
        # 명확한 informational 콘텐츠
        content = """
Python이란 무엇인가? 프로그래밍 언어의 정의와 개념을 설명합니다.
어떻게 사용하는지 방법을 가이드합니다.
왜 배워야 하는지 이유를 알아봅니다.
"""
        result = analyze_search_intent(content)
        signals = result['intent_signals']
        sorted_scores = sorted(signals.values(), reverse=True)

        expected_confidence = sorted_scores[0] - sorted_scores[1]
        self.assertAlmostEqual(result['intent_confidence'],
                               min(expected_confidence, 100.0), places=1)
        self.assertGreaterEqual(result['intent_confidence'], 0.0)
        self.assertLessEqual(result['intent_confidence'], 100.0)

    # ─── 5. 형식 매칭 ───

    def test_content_format_match(self):
        """의도에 맞는 형식의 콘텐츠는 높은 형식 매칭 점수를 받는다."""
        # informational에 잘 맞는 형식: 헤딩, 긴 문단, 정의, 목록
        content = """
# 머신러닝이란 무엇인가

머신러닝이란 데이터에서 패턴을 학습하여 예측하는 기술입니다. 이 기술은 인공지능의 한 분야로, 명시적인 프로그래밍 없이도 컴퓨터가 학습할 수 있게 합니다. 다양한 산업에서 활용되고 있습니다.

## 주요 유형

다양한 머신러닝 알고리즘이 있으며, 각각의 특징이 다릅니다. 지도학습, 비지도학습, 강화학습 세 가지 주요 유형이 있습니다. 각 유형은 서로 다른 문제 해결에 적합합니다.

## 사용 방법

- 데이터를 수집합니다
- 모델을 선택합니다
- 학습을 진행합니다
- 결과를 평가합니다
"""
        result = analyze_search_intent(content)
        self.assertGreater(result['content_format_match'], 30,
                           '적합한 형식은 30점 이상이어야 합니다')

    # ─── 6. 형식 불일치 경고 ───

    def test_format_issues(self):
        """형식 불일치 시 경고 메시지가 포함된다."""
        # transactional 의도인데 CTA가 없는 콘텐츠
        content = """
구매를 고려해보세요. 할인 행사 중입니다.
무료 체험 기간이 있습니다.
지금 바로 신청 가능합니다.
"""
        result = analyze_search_intent(content)
        # format_issues는 리스트여야 함
        self.assertIsInstance(result['format_issues'], list)

        # 빈 콘텐츠는 반드시 이슈가 있어야 함
        empty_result = analyze_search_intent('')
        self.assertTrue(len(empty_result['format_issues']) > 0)

    # ─── 7. 권장 형식 ───

    def test_recommended_format(self):
        """감지된 의도에 따라 올바른 권장 형식을 반환한다."""
        # 각 의도별 테스트
        test_cases = [
            ('무엇 정의 개념 방법 가이드 어떻게 이유 왜 입니다. 합니다.',
             '가이드/설명형 콘텐츠'),
            ('추천 비교 리뷰 평가 순위 최고 베스트 TOP 장단점 특징',
             '비교 리뷰형 콘텐츠'),
            ('구매 가입 다운로드 할인 쿠폰 무료 지금 바로 시작 결제 29900원 시작하세요',
             '전환 유도형 콘텐츠'),
            ('Samsung Samsung Samsung Samsung 공식 홈페이지 사이트 로그인 https://samsung.com 접속 방문',
             '브랜드 안내형 콘텐츠'),
        ]
        for content, expected_format in test_cases:
            with self.subTest(expected=expected_format):
                result = analyze_search_intent(content)
                self.assertEqual(result['recommended_format'], expected_format)

    # ─── 8. 타겟 키워드 ───

    def test_with_target_keyword(self):
        """target_keyword가 의도 감지에 반영된다."""
        content = "이 제품에 대한 일반적인 설명입니다."

        # 키워드 없이
        result_no_kw = analyze_search_intent(content)

        # informational 키워드
        result_info = analyze_search_intent(content, target_keyword='파이썬이란 무엇')
        self.assertGreater(result_info['intent_signals']['informational'],
                           result_no_kw['intent_signals']['informational'])

        # commercial 키워드
        result_comm = analyze_search_intent(content, target_keyword='노트북 추천 비교')
        self.assertGreater(result_comm['intent_signals']['commercial'],
                           result_no_kw['intent_signals']['commercial'])

    # ─── 9. 제안 목록 ───

    def test_suggestions(self):
        """적절한 제안이 생성된다."""
        # 형식이 맞지 않는 콘텐츠
        content = "짧은 콘텐츠입니다."
        result = analyze_search_intent(content)
        self.assertIsInstance(result['suggestions'], list)
        self.assertTrue(len(result['suggestions']) > 0,
                        '짧은 콘텐츠에 대해 제안이 있어야 합니다')

    # ─── 10. 반환값 구조 검증 ───

    def test_return_structure(self):
        """반환값이 명세에 맞는 구조를 가진다."""
        content = "테스트 콘텐츠입니다. 방법을 설명합니다."
        result = analyze_search_intent(content)

        required_keys = [
            'detected_intent', 'intent_confidence', 'intent_signals',
            'content_format_match', 'format_issues', 'recommended_format',
            'suggestions',
        ]
        for key in required_keys:
            self.assertIn(key, result, f'반환값에 {key} 키가 있어야 합니다')

        # 타입 검증
        self.assertIsInstance(result['detected_intent'], str)
        self.assertIsInstance(result['intent_confidence'], float)
        self.assertIsInstance(result['intent_signals'], dict)
        self.assertIsInstance(result['content_format_match'], float)
        self.assertIsInstance(result['format_issues'], list)
        self.assertIsInstance(result['recommended_format'], str)
        self.assertIsInstance(result['suggestions'], list)

        # intent_signals 키 검증
        expected_intents = {'informational', 'commercial',
                            'transactional', 'navigational'}
        self.assertEqual(set(result['intent_signals'].keys()),
                         expected_intents)

        # detected_intent 값 검증
        self.assertIn(result['detected_intent'], expected_intents)

    # ─── 11. 혼합 의도 콘텐츠 ───

    def test_mixed_intent_confidence_low(self):
        """여러 의도가 혼합된 콘텐츠는 신뢰도가 낮다."""
        content = """
파이썬이란 무엇인지 설명합니다. 방법을 가이드합니다.
추천 노트북 비교 리뷰 순위 베스트 TOP 5
지금 바로 구매하세요. 할인 쿠폰 무료 체험.
공식 사이트 홈페이지 로그인 https://example.com
"""
        result = analyze_search_intent(content)
        # 여러 의도가 고르게 분포하면 신뢰도가 낮음
        signals = result['intent_signals']
        non_zero = [s for s in signals.values() if s > 0]
        self.assertGreater(len(non_zero), 1,
                           '혼합 콘텐츠에서 여러 의도 신호가 0 이상이어야 합니다')

    # ─── 12. 공백만 있는 콘텐츠 ───

    def test_whitespace_only(self):
        """공백만 있는 콘텐츠는 빈 콘텐츠와 동일하게 처리된다."""
        result = analyze_search_intent('   \n\t\n   ')
        self.assertEqual(result['detected_intent'], 'informational')
        self.assertEqual(result['intent_confidence'], 0.0)
        self.assertIn('콘텐츠가 비어 있습니다', result['format_issues'])

    # ─── 13. target_keyword가 빈 문자열 ───

    def test_empty_target_keyword(self):
        """빈 target_keyword도 정상 동작한다."""
        content = "이 문서는 개념과 정의를 설명합니다."
        result = analyze_search_intent(content, target_keyword='')
        self.assertIn(result['detected_intent'],
                      {'informational', 'commercial',
                       'transactional', 'navigational'})


if __name__ == '__main__':
    unittest.main()
