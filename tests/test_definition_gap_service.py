"""Definition Gap Detector 서비스 테스트."""
import unittest
from services.definition_gap_service import detect_definition_gaps


class TestDefinitionGap(unittest.TestCase):

    def test_empty_content(self):
        result = detect_definition_gaps('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = detect_definition_gaps(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_technical_terms(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다.'
        result = detect_definition_gaps(content)
        self.assertEqual(result['summary']['total_terms'], 0)

    def test_common_acronym_ignored(self):
        content = 'API를 사용하여 데이터를 가져옵니다. JSON 형식입니다.'
        result = detect_definition_gaps(content)
        # API, JSON은 흔한 약어로 제외
        self.assertEqual(result['summary']['total_terms'], 0)

    def test_undefined_acronym(self):
        content = 'RBAC 정책을 설정합니다. OIDC 인증을 구성합니다.'
        result = detect_definition_gaps(content)
        self.assertGreater(result['summary']['undefined_terms'], 0)

    def test_defined_acronym(self):
        content = 'RBAC(Role-Based Access Control)을 설정합니다.'
        result = detect_definition_gaps(content)
        self.assertGreater(result['summary']['defined_terms'], 0)

    def test_ko_technical_undefined(self):
        content = '레이턴시가 높아서 스루풋이 떨어집니다. 미들웨어를 추가합니다.'
        result = detect_definition_gaps(content)
        self.assertGreater(result['summary']['undefined_terms'], 0)

    def test_ko_technical_defined(self):
        content = '레이턴시란 요청부터 응답까지 걸리는 시간을 의미합니다.'
        result = detect_definition_gaps(content)
        self.assertGreater(result['summary']['defined_terms'], 0)

    def test_en_technical_undefined(self):
        content = 'Implement sharding for better throughput. Add partitioning logic.'
        result = detect_definition_gaps(content)
        self.assertGreater(result['summary']['undefined_terms'], 0)

    def test_all_defined_level(self):
        content = ('RBAC(Role-Based Access Control)을 설정합니다. '
                   '레이턴시란 응답 시간을 의미합니다.')
        result = detect_definition_gaps(content)
        self.assertEqual(result['summary']['level'], 'all_defined')

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = detect_definition_gaps(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = detect_definition_gaps(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('undefined_terms', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_terms', result['summary'])
        self.assertIn('defined_terms', result['summary'])
        self.assertIn('undefined_terms', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_gaps(self):
        content = 'RBAC과 OIDC를 설정하고 SSO를 구성합니다.'
        result = detect_definition_gaps(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_definition_with_ie(self):
        content = 'Sharding, i.e. splitting data across nodes, improves performance.'
        result = detect_definition_gaps(content)
        self.assertGreater(result['summary']['defined_terms'], 0)


if __name__ == '__main__':
    unittest.main()
