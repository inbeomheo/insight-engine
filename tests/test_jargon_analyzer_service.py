"""
전문 용어 정의 커버리지 분석 서비스 테스트
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.analysis.jargon_analyzer_service import analyze_jargon_coverage


class TestJargonAnalyzerService(unittest.TestCase):
    """analyze_jargon_coverage 함수 단위 테스트"""

    def test_empty_content(self):
        """빈 콘텐츠 입력 시 기본 응답 반환"""
        result = analyze_jargon_coverage('')
        self.assertEqual(result['terms'], [])
        self.assertEqual(result['summary']['total'], 0)
        self.assertEqual(result['coverage_score'], 100.0)
        self.assertIn('콘텐츠가 비어 있습니다.', result['suggestions'])

        # None 입력
        result_none = analyze_jargon_coverage(None)
        self.assertEqual(result_none['terms'], [])

    def test_no_jargon(self):
        """전문 용어가 없는 일반 텍스트"""
        result = analyze_jargon_coverage('오늘 날씨가 참 좋습니다. 산책을 가야겠어요.')
        self.assertEqual(result['summary']['total'], 0)
        self.assertEqual(result['coverage_score'], 100.0)
        self.assertIn('전문 용어가 감지되지 않았습니다.', result['suggestions'])

    def test_abbreviation_detection(self):
        """영문 약어(대문자 2~6자) 감지"""
        content = 'API를 사용하여 데이터를 가져옵니다. REST API가 일반적입니다.'
        result = analyze_jargon_coverage(content)

        terms = [t['term'] for t in result['terms']]
        self.assertIn('API', terms)

        api_term = next(t for t in result['terms'] if t['term'] == 'API')
        self.assertEqual(api_term['type'], 'abbreviation')

    def test_technical_term_detection(self):
        """카멜케이스/파스칼케이스 기술 용어 감지"""
        content = 'JavaScript와 TypeScript는 현대 웹 개발에서 많이 사용됩니다.'
        result = analyze_jargon_coverage(content)

        terms = [t['term'] for t in result['terms']]
        self.assertIn('JavaScript', terms)
        self.assertIn('TypeScript', terms)

        js_term = next(t for t in result['terms'] if t['term'] == 'JavaScript')
        self.assertEqual(js_term['type'], 'technical')

    def test_korean_jargon_detection(self):
        """한국어 전문 용어 사전 기반 감지"""
        content = '머신러닝 모델을 학습시키고 블록체인 네트워크에 배포합니다.'
        result = analyze_jargon_coverage(content)

        terms = [t['term'] for t in result['terms']]
        self.assertIn('머신러닝', terms)
        self.assertIn('블록체인', terms)

        ml_term = next(t for t in result['terms'] if t['term'] == '머신러닝')
        self.assertEqual(ml_term['type'], 'korean_jargon')

    def test_defined_with_parenthesis(self):
        """괄호 설명이 있는 용어는 defined로 판정"""
        content = 'SEO(검색엔진최적화)를 적용하면 검색 노출이 향상됩니다.'
        result = analyze_jargon_coverage(content)

        seo_term = next(t for t in result['terms'] if t['term'] == 'SEO')
        self.assertTrue(seo_term['has_definition'])
        self.assertEqual(seo_term['status'], 'defined')
        self.assertIn('SEO(검색엔진최적화)', seo_term['definition_text'])

    def test_defined_with_pattern(self):
        """정의 패턴(~란, ~를 의미한다, 콜론 등)으로 정의된 용어"""
        # "~란" 패턴
        content1 = 'API란 프로그램 간의 인터페이스를 제공하는 규약입니다.'
        result1 = analyze_jargon_coverage(content1)
        api_term = next(t for t in result1['terms'] if t['term'] == 'API')
        self.assertTrue(api_term['has_definition'])

        # 콜론 패턴
        content2 = 'ROI: 투자 대비 수익률을 계산하는 지표입니다.'
        result2 = analyze_jargon_coverage(content2)
        roi_term = next(t for t in result2['terms'] if t['term'] == 'ROI')
        self.assertTrue(roi_term['has_definition'])

    def test_undefined_term(self):
        """정의 없이 등장하는 용어는 undefined로 판정"""
        content = '이 시스템은 KPI 달성을 위해 최적화되었습니다.'
        result = analyze_jargon_coverage(content)

        kpi_term = next(t for t in result['terms'] if t['term'] == 'KPI')
        self.assertFalse(kpi_term['has_definition'])
        self.assertEqual(kpi_term['status'], 'undefined')
        self.assertEqual(kpi_term['definition_text'], '')

    def test_coverage_score_range(self):
        """커버리지 점수가 0~100 범위 내"""
        # 모두 미정의
        content_low = 'API와 SDK를 활용한 SaaS 솔루션 개발'
        result_low = analyze_jargon_coverage(content_low)
        self.assertGreaterEqual(result_low['coverage_score'], 0)
        self.assertLessEqual(result_low['coverage_score'], 100)

        # 모두 정의됨
        content_high = 'API(응용 프로그래밍 인터페이스)를 사용합니다.'
        result_high = analyze_jargon_coverage(content_high)
        self.assertGreaterEqual(result_high['coverage_score'], 0)
        self.assertLessEqual(result_high['coverage_score'], 100)

    def test_first_occurrence_tracking(self):
        """첫 등장 위치가 정확히 추적되는지 확인"""
        content = '여기서 API를 사용합니다.'
        result = analyze_jargon_coverage(content)

        api_term = next(t for t in result['terms'] if t['term'] == 'API')
        actual_pos = content.index('API')
        self.assertEqual(api_term['first_occurrence'], actual_pos)

    def test_multiple_terms(self):
        """여러 용어가 동시에 감지되고 결과 구조가 올바른지 확인"""
        content = (
            'REST API를 통해 데이터를 조회합니다. '
            'SDK를 사용하면 개발이 편리합니다. '
            'JavaScript로 프론트엔드를 구현합니다.'
        )
        result = analyze_jargon_coverage(content)

        self.assertGreaterEqual(result['summary']['total'], 3)
        self.assertEqual(
            result['summary']['total'],
            result['summary']['defined'] + result['summary']['undefined'],
        )

        # 첫 등장 위치 순 정렬 확인
        positions = [t['first_occurrence'] for t in result['terms']]
        self.assertEqual(positions, sorted(positions))

    def test_suggestions(self):
        """미정의 용어가 있을 때 제안이 생성되는지 확인"""
        content = 'KPI 달성을 위해 ROI를 분석합니다. API 연동도 필요합니다.'
        result = analyze_jargon_coverage(content)

        self.assertIsInstance(result['suggestions'], list)
        self.assertTrue(len(result['suggestions']) > 0)

        # 미정의 용어 이름이 제안에 포함
        suggestion_text = ' '.join(result['suggestions'])
        undefined_terms = [t['term'] for t in result['terms'] if not t['has_definition']]
        for term in undefined_terms[:5]:
            self.assertIn(term, suggestion_text)

    def test_common_abbreviations_excluded(self):
        """일반 약어(TV, OK 등)는 전문 용어에서 제외"""
        content = 'TV를 보면서 OK 사인을 보냈습니다. PC 게임도 했습니다.'
        result = analyze_jargon_coverage(content)

        terms = [t['term'] for t in result['terms']]
        self.assertNotIn('TV', terms)
        self.assertNotIn('OK', terms)

    def test_dash_definition(self):
        """대시(—, -) 설명 패턴 인식"""
        content = 'CMS — 콘텐츠 관리 시스템으로 웹사이트를 관리합니다.'
        result = analyze_jargon_coverage(content)

        cms_term = next(t for t in result['terms'] if t['term'] == 'CMS')
        self.assertTrue(cms_term['has_definition'])
        self.assertEqual(cms_term['status'], 'defined')

    def test_all_defined_coverage_100(self):
        """모든 용어에 정의가 있으면 커버리지 100%"""
        content = 'API(응용 프로그래밍 인터페이스)와 SDK(소프트웨어 개발 키트)를 사용합니다.'
        result = analyze_jargon_coverage(content)

        self.assertEqual(result['coverage_score'], 100.0)
        self.assertEqual(result['summary']['undefined'], 0)


if __name__ == '__main__':
    unittest.main()
