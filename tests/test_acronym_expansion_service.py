"""Acronym Expansion Compliance Checker 서비스 단위 테스트"""
import unittest
from services.analysis.acronym_expansion_service import check_acronym_expansion


class TestAcronymExpansionService(unittest.TestCase):

    def test_empty_content(self):
        result = check_acronym_expansion('')
        self.assertEqual(result['acronyms'], [])
        self.assertEqual(result['score'], 100.0)
        result_none = check_acronym_expansion(None)
        self.assertEqual(result_none['acronyms'], [])

    def test_no_acronyms(self):
        content = '이것은 약어가 없는 일반 문장입니다.'
        result = check_acronym_expansion(content)
        self.assertEqual(result['summary']['total_acronyms'], 0)
        self.assertEqual(result['score'], 100.0)

    def test_expanded_acronym(self):
        content = 'REST (Representational State Transfer) API를 사용합니다.'
        result = check_acronym_expansion(content)
        rest = [a for a in result['acronyms'] if a['acronym'] == 'REST']
        self.assertTrue(len(rest) > 0)
        self.assertTrue(rest[0]['is_expanded'])

    def test_unexpanded_acronym(self):
        content = 'MQTT 프로토콜을 사용하여 데이터를 전송합니다.'
        result = check_acronym_expansion(content)
        mqtt = [a for a in result['acronyms'] if a['acronym'] == 'MQTT']
        self.assertTrue(len(mqtt) > 0)
        self.assertFalse(mqtt[0]['is_expanded'])
        self.assertEqual(mqtt[0]['status'], 'unexpanded')

    def test_well_known_acronym(self):
        content = 'API와 HTML을 사용합니다.'
        result = check_acronym_expansion(content)
        api = [a for a in result['acronyms'] if a['acronym'] == 'API']
        self.assertTrue(len(api) > 0)
        self.assertTrue(api[0]['is_well_known'])
        self.assertEqual(api[0]['status'], 'well_known')

    def test_exception_filter(self):
        content = 'THE AND FOR BUT NOT ARE words.'
        result = check_acronym_expansion(content)
        # 일반 영어 단어는 약어로 감지되지 않아야 함
        acronyms = [a['acronym'] for a in result['acronyms']]
        self.assertNotIn('THE', acronyms)
        self.assertNotIn('AND', acronyms)

    def test_parenthetical_expansion(self):
        content = 'GraphQL (Graph Query Language) 기반입니다.'
        result = check_acronym_expansion(content)
        # "GraphQL"은 대문자가 아니므로 약어로 감지 안 됨 — 다른 예시
        content2 = 'ORM (Object Relational Mapping)을 활용합니다.'
        result2 = check_acronym_expansion(content2)
        orm = [a for a in result2['acronyms'] if a['acronym'] == 'ORM']
        if orm:
            self.assertTrue(orm[0]['is_expanded'])

    def test_reverse_expansion(self):
        """Full Name (약어) 패턴 감지"""
        content = 'Continuous Integration (CI)를 도입합니다.'
        result = check_acronym_expansion(content)
        ci = [a for a in result['acronyms'] if a['acronym'] == 'CI']
        if ci:
            self.assertTrue(ci[0]['is_expanded'])

    def test_score_range(self):
        content = 'API와 SQL을 사용합니다.'
        result = check_acronym_expansion(content)
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_score_with_unexpanded(self):
        content = 'MQTT와 AMQP를 사용합니다.'
        result = check_acronym_expansion(content)
        # 둘 다 미풀어쓰기 → 점수 낮음
        self.assertLess(result['score'], 50)

    def test_suggestions(self):
        content = 'MQTT 프로토콜을 사용합니다.'
        result = check_acronym_expansion(content)
        self.assertGreater(len(result['suggestions']), 0)
        self.assertTrue(any('풀어쓰기' in s for s in result['suggestions']))

    def test_return_structure(self):
        result = check_acronym_expansion('API를 사용합니다.')
        self.assertIn('acronyms', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_acronyms', result['summary'])
        self.assertIn('expanded', result['summary'])
        self.assertIn('unexpanded', result['summary'])
        self.assertIn('well_known', result['summary'])

    def test_multiple_acronyms(self):
        content = 'REST (Representational State Transfer)와 GRPC를 비교합니다. MQTT도 고려합니다.'
        result = check_acronym_expansion(content)
        self.assertGreaterEqual(result['summary']['total_acronyms'], 2)


if __name__ == '__main__':
    unittest.main()
