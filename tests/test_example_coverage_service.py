"""
Example Coverage Analyzer 서비스 단위 테스트
"""
import unittest

from services.example_coverage_service import analyze_example_coverage


class TestExampleCoverageService(unittest.TestCase):
    """analyze_example_coverage 함수 테스트"""

    # --- 빈/무관 입력 ---

    def test_empty_content(self):
        """빈 콘텐츠 입력 시 기본 구조 반환"""
        result = analyze_example_coverage('')
        self.assertEqual(result['claims'], [])
        self.assertEqual(result['summary']['total_claims'], 0)
        self.assertEqual(result['coverage_score'], 0.0)
        self.assertIn('콘텐츠가 비어 있습니다.', result['suggestions'])

        # None 입력도 동일
        result_none = analyze_example_coverage(None)
        self.assertEqual(result_none['claims'], [])

    def test_no_claims(self):
        """주장이 없는 순수 서술 콘텐츠"""
        content = '오늘 날씨가 맑다. 하늘이 파랗다. 바람이 분다.'
        result = analyze_example_coverage(content)
        self.assertEqual(result['summary']['total_claims'], 0)
        self.assertEqual(result['coverage_score'], 100.0)
        self.assertIn('주장/조언 문장이 없습니다', result['suggestions'][0])

    # --- 주장 감지 ---

    def test_claim_detection(self):
        """한국어 주장 패턴 감지"""
        content = (
            '코드 리뷰를 해야 합니다. '
            '테스트를 작성하는 것이 좋습니다. '
            '보안 점검이 중요합니다.'
        )
        result = analyze_example_coverage(content)
        self.assertEqual(result['summary']['total_claims'], 3)

    def test_claim_detection_english(self):
        """영어 주장 패턴 감지"""
        content = (
            'You should write tests. '
            'Documentation is important. '
            'Code review must be done regularly.'
        )
        result = analyze_example_coverage(content)
        self.assertGreaterEqual(result['summary']['total_claims'], 3)

    # --- 근거 감지 ---

    def test_example_evidence(self):
        """'예를 들어' 패턴 감지"""
        content = (
            '테스트를 작성해야 합니다. '
            '예를 들어 단위 테스트는 함수 단위로 검증합니다.'
        )
        result = analyze_example_coverage(content)
        claim = result['claims'][0]
        self.assertTrue(claim['has_evidence'])
        self.assertEqual(claim['evidence_type'], 'example')
        self.assertEqual(claim['status'], 'supported')

    def test_number_evidence(self):
        """수치 데이터 패턴 감지"""
        content = (
            '코드 커버리지를 높이는 것이 중요합니다. '
            '커버리지가 80% 이상이면 버그가 40% 감소합니다.'
        )
        result = analyze_example_coverage(content)
        claim = result['claims'][0]
        self.assertTrue(claim['has_evidence'])
        self.assertEqual(claim['evidence_type'], 'number')

    def test_case_evidence(self):
        """사례/실험 결과 패턴 감지"""
        content = (
            '지속적 배포를 도입해야 합니다. '
            '실제로 대기업 A사는 배포 주기를 주 1회에서 일 3회로 개선했습니다.'
        )
        result = analyze_example_coverage(content)
        claim = result['claims'][0]
        self.assertTrue(claim['has_evidence'])
        self.assertEqual(claim['evidence_type'], 'case')

    def test_quote_evidence(self):
        """인용 패턴 감지"""
        content = (
            '보안 점검이 필수입니다. '
            'OWASP 보고서에 따르면 SQL Injection이 여전히 1위 위협입니다.'
        )
        result = analyze_example_coverage(content)
        claim = result['claims'][0]
        self.assertTrue(claim['has_evidence'])
        self.assertEqual(claim['evidence_type'], 'quote')

    # --- 미지원 주장 ---

    def test_unsupported_claim(self):
        """근거 없는 주장 감지"""
        content = (
            '모든 팀원이 코딩 컨벤션을 따라야 합니다. '
            '그래야 코드 품질이 올라간다.'
        )
        result = analyze_example_coverage(content)
        # 첫 번째 문장이 주장이고, 뒤에 근거 패턴이 없음
        unsupported = [c for c in result['claims'] if not c['has_evidence']]
        self.assertGreater(len(unsupported), 0)
        self.assertEqual(unsupported[0]['status'], 'unsupported')

    def test_supported_claim(self):
        """근거가 있는 주장의 status가 'supported'인지 확인"""
        content = (
            '로깅을 반드시 해야 합니다. '
            '예를 들어 에러 로그를 남기면 디버깅 시간이 절반으로 줄어듭니다.'
        )
        result = analyze_example_coverage(content)
        supported = [c for c in result['claims'] if c['has_evidence']]
        self.assertGreater(len(supported), 0)
        self.assertEqual(supported[0]['status'], 'supported')

    # --- 점수 및 요약 ---

    def test_coverage_score_range(self):
        """커버리지 점수가 0-100 범위인지 확인"""
        # 절반 지원
        content = (
            '테스트가 중요합니다. 예를 들어 회귀 테스트는 필수입니다. '
            '코드 리뷰를 해야 합니다. 보안 점검이 필요합니다.'
        )
        result = analyze_example_coverage(content)
        self.assertGreaterEqual(result['coverage_score'], 0.0)
        self.assertLessEqual(result['coverage_score'], 100.0)

    def test_multiple_claims(self):
        """여러 주장이 각각 분석되는지 확인"""
        content = (
            '문서화를 해야 합니다. '
            '예를 들어 API 문서는 Swagger로 작성합니다. '
            '코드 리뷰가 중요합니다. '
            '실제로 Google은 모든 코드에 리뷰를 적용합니다. '
            '자동화 테스트가 필수입니다.'
        )
        result = analyze_example_coverage(content)
        self.assertGreaterEqual(result['summary']['total_claims'], 3)
        self.assertEqual(
            result['summary']['total_claims'],
            result['summary']['supported'] + result['summary']['unsupported'],
        )

    # --- weak_sections / suggestions ---

    def test_weak_sections(self):
        """근거 없는 주장이 weak_sections에 포함되는지 확인"""
        content = (
            '모니터링이 중요합니다. '
            '알림 설정을 해야 합니다.'
        )
        result = analyze_example_coverage(content)
        self.assertGreater(len(result['weak_sections']), 0)
        # weak_sections의 각 항목이 실제 주장 문장인지
        for ws in result['weak_sections']:
            self.assertTrue(any(ws == c['claim_sentence'] for c in result['claims']))

    def test_suggestions(self):
        """suggestions가 비어 있지 않은지 확인"""
        content = (
            '보안 패치를 적용해야 합니다. '
            '성능 최적화가 필요합니다.'
        )
        result = analyze_example_coverage(content)
        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)

    # --- before/after 근거 ---

    def test_before_after_evidence(self):
        """before/after 패턴 감지"""
        content = (
            '리팩토링을 해야 합니다. '
            '적용 전 응답시간 500ms에서 적용 후 200ms로 개선되었습니다.'
        )
        result = analyze_example_coverage(content)
        claim = result['claims'][0]
        # before_after 또는 number 중 하나 (적용 전/후 + 숫자 둘 다 있음)
        self.assertTrue(claim['has_evidence'])
        self.assertIn(claim['evidence_type'], ['before_after', 'number'])

    # --- 전체 구조 검증 ---

    def test_return_structure(self):
        """반환값의 전체 키 구조 검증"""
        content = '테스트를 작성해야 합니다.'
        result = analyze_example_coverage(content)

        self.assertIn('claims', result)
        self.assertIn('summary', result)
        self.assertIn('coverage_score', result)
        self.assertIn('weak_sections', result)
        self.assertIn('suggestions', result)

        self.assertIn('total_claims', result['summary'])
        self.assertIn('supported', result['summary'])
        self.assertIn('unsupported', result['summary'])

        if result['claims']:
            claim = result['claims'][0]
            self.assertIn('claim_sentence', claim)
            self.assertIn('has_evidence', claim)
            self.assertIn('evidence_type', claim)
            self.assertIn('status', claim)


if __name__ == '__main__':
    unittest.main()
