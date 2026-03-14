"""eeat_analyzer_service 단위 테스트"""
import unittest

from services.seo.eeat_analyzer_service import analyze_eeat


class TestAnalyzeEeat(unittest.TestCase):
    """E-E-A-T 신뢰 신호 분석 테스트"""

    # ── 1. 빈 콘텐츠 ──
    def test_empty_content(self):
        """빈 문자열 입력 시 기본 응답 반환"""
        result = analyze_eeat('')
        self.assertEqual(result['eeat_score'], 0.0)
        self.assertEqual(result['grade'], 'F')
        self.assertEqual(result['dimensions']['experience'], 0.0)
        self.assertEqual(result['signals_found'], [])

    # ── 2. None 입력 ──
    def test_none_content(self):
        """None 입력 시 기본 응답 반환"""
        result = analyze_eeat(None)
        self.assertEqual(result['eeat_score'], 0.0)
        self.assertEqual(result['grade'], 'F')

    # ── 3. 기본 분석 구조 ──
    def test_basic_analysis(self):
        """반환값에 필수 키가 모두 존재하는지 확인"""
        result = analyze_eeat('일반적인 텍스트입니다.')
        required_keys = {'eeat_score', 'grade', 'dimensions', 'signals_found', 'signals_missing', 'suggestions'}
        self.assertTrue(required_keys.issubset(result.keys()))
        dim_keys = {'experience', 'expertise', 'authoritativeness', 'trustworthiness'}
        self.assertTrue(dim_keys.issubset(result['dimensions'].keys()))

    # ── 4. 점수 범위 0-100 ──
    def test_score_range(self):
        """모든 점수가 0-100 범위 내인지 확인"""
        # 많은 신호를 포함한 풍부한 콘텐츠
        content = """
        # SEO 최적화 가이드
        ## API 활용 방법
        ### CDN 설정 단계

        제가 직접 3개월간 사용해보니 결과적으로 200% 개선되었습니다.
        구글에 따르면 이 방법이 공식 권장 사항입니다.
        https://example.com 참고하세요.

        - 1단계: 설정
        - 2단계: 배포
        - 3단계: 모니터링

        다만 주의할 점이 있습니다. 반면 다른 의견도 있습니다.
        2025년 최신 업데이트 기준입니다.

        ![스크린샷](image.png)
        """
        result = analyze_eeat(content, author_info='홍길동, SEO 전문가')
        self.assertGreaterEqual(result['eeat_score'], 0)
        self.assertLessEqual(result['eeat_score'], 100)
        for dim, score in result['dimensions'].items():
            self.assertGreaterEqual(score, 0, f'{dim} 점수가 0 미만')
            self.assertLessEqual(score, 100, f'{dim} 점수가 100 초과')

    # ── 5. 등급 매핑 ──
    def test_grade_mapping(self):
        """등급이 A/B/C/D/F 중 하나인지 확인"""
        # 최소 콘텐츠
        result_low = analyze_eeat('짧은 글.')
        self.assertIn(result_low['grade'], ['A', 'B', 'C', 'D', 'F'])

        # 풍부한 콘텐츠 — 높은 등급 기대
        rich = """
        # 가이드
        ## 소개
        ### 결론

        제가 직접 실제로 경험해보니 결과적으로 성과가 있었습니다.
        3개월간 테스트한 결과 50% 향상, 100건 처리, 30명 참여.
        API, SEO, CDN 기술을 활용한 절차를 설명합니다.
        구글에 따르면 이것이 공식 방법입니다. https://example.com

        - 항목 A
        - 항목 B

        다만 한계가 있습니다. 반면 다른 의견도 존재합니다.
        2025년 최신 업데이트입니다. 아래 스크린샷을 참고하세요.
        """
        result_high = analyze_eeat(rich, author_info='전문가')
        self.assertIn(result_high['grade'], ['A', 'B'])

    # ── 6. 경험 신호 감지 ──
    def test_experience_signals(self):
        """1인칭 경험 표현이 감지되는지 확인"""
        content = '제가 직접 사용해보니 실제로 효과가 있었습니다. 3개월간 테스트했고 그 결과 만족스러웠습니다.'
        result = analyze_eeat(content)
        self.assertGreater(result['dimensions']['experience'], 0)
        # 경험 관련 신호가 signals_found에 포함
        exp_signals = {'1인칭 경험 표현', '사례/결과 공유', '구체적 기간/시점'}
        found_set = set(result['signals_found'])
        self.assertTrue(exp_signals & found_set, '경험 신호가 하나도 감지되지 않음')

    # ── 7. 전문성 신호 감지 ──
    def test_expertise_signals(self):
        """전문용어, 데이터 인용 등 전문성 신호 감지"""
        content = """
        API와 SDK를 활용한 SEO 최적화 프로세스를 단계별로 설명합니다.
        이 방법을 적용하면 전환율이 35% 향상되며 월 1000건 이상 처리할 수 있습니다.

        첫 번째 단락입니다. 꽤 긴 설명이 포함됩니다.
        두 번째 단락에서는 더 자세히 설명합니다.
        세 번째 단락에서는 결론을 도출합니다.
        """
        result = analyze_eeat(content)
        self.assertGreater(result['dimensions']['expertise'], 0)

    # ── 8. 권위 신호 감지 ──
    def test_authority_signals(self):
        """출처 인용, 외부 링크 등 권위 신호 감지"""
        content = '구글에 따르면 이 방법이 공식 권장됩니다. 자세한 내용은 https://example.com 을 참고하세요.'
        result = analyze_eeat(content)
        self.assertGreater(result['dimensions']['authoritativeness'], 0)
        found_set = set(result['signals_found'])
        self.assertIn('출처 인용', found_set)
        self.assertIn('외부 링크/참조', found_set)

    # ── 9. 신뢰성 신호 감지 ──
    def test_trust_signals(self):
        """날짜, 면책, 균형 시각 등 신뢰성 신호 감지"""
        content = """
        # 가이드
        ## 방법
        ### 결론

        2025년 기준 최신 정보입니다.
        다만 주의할 점이 있습니다.
        반면 다른 접근법도 고려해볼 수 있습니다.

        - 장점 A
        - 단점 B
        """
        result = analyze_eeat(content)
        self.assertGreater(result['dimensions']['trustworthiness'], 0)

    # ── 10. 저자 정보 제공 시 ──
    def test_with_author_info(self):
        """author_info 제공 시 authoritativeness 점수 상승"""
        content = '일반적인 콘텐츠입니다.'
        result_without = analyze_eeat(content, author_info='')
        result_with = analyze_eeat(content, author_info='홍길동, 10년 경력 개발자')
        # 저자 정보가 있으면 권위 점수가 더 높아야 함
        self.assertGreater(
            result_with['dimensions']['authoritativeness'],
            result_without['dimensions']['authoritativeness'],
        )

    # ── 11. 발견된 신호 목록 ──
    def test_signals_found(self):
        """signals_found가 리스트이며 감지된 신호가 포함되는지 확인"""
        content = '제가 직접 테스트한 결과적으로 효과가 있었습니다.'
        result = analyze_eeat(content)
        self.assertIsInstance(result['signals_found'], list)
        self.assertGreater(len(result['signals_found']), 0)

    # ── 12. 결핍된 신호 목록 ──
    def test_signals_missing(self):
        """signals_missing이 리스트이며 누락 신호가 포함되는지 확인"""
        # 아주 짧은 콘텐츠 — 대부분의 신호 누락
        content = '짧은 글입니다.'
        result = analyze_eeat(content)
        self.assertIsInstance(result['signals_missing'], list)
        self.assertGreater(len(result['signals_missing']), 0)
        # 16개 전체 신호 중 대부분 누락
        self.assertGreater(len(result['signals_missing']), 10)

    # ── 13. 제안 목록 ──
    def test_suggestions(self):
        """suggestions가 리스트이며 개선 제안이 포함되는지 확인"""
        content = '짧은 글입니다.'
        result = analyze_eeat(content)
        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)
        # 제안은 모두 문자열
        for s in result['suggestions']:
            self.assertIsInstance(s, str)


if __name__ == '__main__':
    unittest.main()
