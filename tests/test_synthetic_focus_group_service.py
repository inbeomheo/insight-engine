"""합성 포커스그룹 서비스 테스트"""
import unittest
from services.synthetic_focus_group_service import (
    create_personas, simulate_response, run_focus_group, extract_themes,
    Persona, FocusGroupResponse, FocusGroupReport
)


class TestSyntheticFocusGroupService(unittest.TestCase):

    def setUp(self):
        self.profiles = [
            {'name': '김철수', 'age': 30, 'occupation': '개발자', 'interests': ['AI', '기술'], 'communication_style': 'technical'},
            {'name': '이영희', 'age': 25, 'occupation': '디자이너', 'interests': ['디자인', 'UX'], 'communication_style': 'casual'},
            {'name': '박민수', 'age': 45, 'occupation': '매니저', 'interests': ['AI', '관리'], 'communication_style': 'formal'},
        ]
        self.personas = create_personas(self.profiles)

    def test_create_personas_count(self):
        self.assertEqual(len(self.personas), 3)

    def test_create_personas_fields(self):
        p = self.personas[0]
        self.assertIsInstance(p, Persona)
        self.assertEqual(p.name, '김철수')
        self.assertEqual(p.age, 30)

    def test_simulate_response_returns_correct_type(self):
        response = simulate_response(self.personas[0], 'AI의 미래는?', 'AI 기술이 발전하고 있습니다.')
        self.assertIsInstance(response, FocusGroupResponse)
        self.assertIn(response.sentiment, ['positive', 'neutral', 'negative'])

    def test_simulate_response_uses_style(self):
        tech = simulate_response(self.personas[0], '질문', '기술 콘텐츠')
        self.assertIn('기술 분석', tech.response)

    def test_simulate_response_deterministic(self):
        r1 = simulate_response(self.personas[0], '같은 질문', '같은 콘텐츠')
        r2 = simulate_response(self.personas[0], '같은 질문', '같은 콘텐츠')
        self.assertEqual(r1.sentiment, r2.sentiment)

    def test_run_focus_group_returns_report(self):
        report = run_focus_group(self.personas, '이 제품 어때요?', 'AI 기반 제품입니다.')
        self.assertIsInstance(report, FocusGroupReport)
        self.assertEqual(len(report.responses), 3)

    def test_run_focus_group_consensus(self):
        report = run_focus_group(self.personas, '테스트', '콘텐츠')
        self.assertIn(report.consensus, ['긍정적 합의', '중립적 의견', '부정적 합의', '의견 분산'])

    def test_extract_themes_from_concerns(self):
        responses = [
            FocusGroupResponse('p1', 'q', 'r', 'positive', ['AI', '기술']),
            FocusGroupResponse('p2', 'q', 'r', 'neutral', ['AI', 'UX']),
        ]
        report = FocusGroupReport(question='q', responses=responses, consensus='', key_themes=[])
        themes = extract_themes(report)
        self.assertEqual(themes[0], 'AI')  # 빈도 최다

    def test_extract_themes_empty(self):
        report = FocusGroupReport(question='q', responses=[], consensus='', key_themes=[])
        themes = extract_themes(report)
        self.assertEqual(themes, [])

    def test_create_personas_defaults(self):
        personas = create_personas([{}])
        self.assertEqual(personas[0].name, 'Unknown')
        self.assertEqual(personas[0].age, 30)


if __name__ == '__main__':
    unittest.main()
