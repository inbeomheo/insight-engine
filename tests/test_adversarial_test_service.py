"""적대적 페르소나 테스트 서비스 테스트."""
import unittest
from services.adversarial_test_service import (
    stress_test,
    get_available_personas,
    StressResult,
)


class TestGetAvailablePersonas(unittest.TestCase):
    """get_available_personas 함수 테스트."""

    def test_returns_list(self):
        result = get_available_personas()
        self.assertIsInstance(result, list)

    def test_default_personas_present(self):
        """기본 4개 페르소나가 모두 포함."""
        result = get_available_personas()
        for persona in ['skeptic', 'regulator', 'competitor', 'beginner']:
            self.assertIn(persona, result)


class TestStressTest(unittest.TestCase):
    """stress_test 함수 테스트."""

    def test_empty_content(self):
        """빈 콘텐츠 입력 시 빈 결과."""
        result = stress_test('')
        self.assertEqual(result, [])

    def test_none_content(self):
        """None 입력 시 빈 결과."""
        result = stress_test(None)
        self.assertEqual(result, [])

    def test_all_personas_run(self):
        """기본값(전체 페르소나) 실행 시 4개 결과."""
        result = stress_test('일반적인 콘텐츠입니다.')
        self.assertEqual(len(result), 4)
        personas = {r.persona for r in result}
        self.assertEqual(personas, {'skeptic', 'regulator', 'competitor', 'beginner'})

    def test_single_persona(self):
        """단일 페르소나 지정."""
        result = stress_test('테스트 콘텐츠', personas=['skeptic'])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].persona, 'skeptic')

    def test_unknown_persona_skipped(self):
        """존재하지 않는 페르소나는 건너뛴다."""
        result = stress_test('테스트', personas=['unknown_persona'])
        self.assertEqual(result, [])

    def test_result_dataclass_fields(self):
        """StressResult 필드 확인."""
        results = stress_test('콘텐츠')
        for r in results:
            self.assertIsInstance(r, StressResult)
            self.assertIsInstance(r.persona, str)
            self.assertIsInstance(r.test_name, str)
            self.assertIsInstance(r.passed, bool)
            self.assertIsInstance(r.issues, list)
            self.assertIsInstance(r.suggestions, list)

    # ── Skeptic 테스트 ──

    def test_skeptic_detects_unsubstantiated_claims(self):
        """회의론자: '최고의', '혁신적' 등 근거 없는 주장 탐지."""
        content = '이것은 최고의 혁신적인 제품입니다. 획기적인 기술로 만들었습니다.'
        result = stress_test(content, personas=['skeptic'])[0]
        self.assertFalse(result.passed)
        self.assertGreater(len(result.issues), 0)

    def test_skeptic_passes_clean_content(self):
        """회의론자: 과장 없는 콘텐츠는 통과."""
        content = '이 제품은 2024년 출시되었습니다. 주요 기능은 데이터 분석입니다.'
        result = stress_test(content, personas=['skeptic'])[0]
        self.assertTrue(result.passed)

    def test_skeptic_with_evidence(self):
        """회의론자: 근거(수치)가 있으면 제안이 달라짐."""
        content = '최고의 제품입니다. 연구에 따르면 85% 고객이 만족했습니다.'
        result = stress_test(content, personas=['skeptic'])[0]
        self.assertFalse(result.passed)  # 여전히 과장 표현은 문제
        # 하지만 근거가 있으므로 '근거 자료가 전혀 없다'는 이슈는 없어야 함
        no_evidence_issues = [i for i in result.issues if '근거 자료가 전혀' in i]
        self.assertEqual(len(no_evidence_issues), 0)

    # ── Regulator 테스트 ──

    def test_regulator_detects_misleading(self):
        """규제자: '100% 보장' 등 오해 유발 표현 탐지."""
        content = '100% 안전한 투자입니다. 부작용 없는 건강식품입니다.'
        result = stress_test(content, personas=['regulator'])[0]
        self.assertFalse(result.passed)

    def test_regulator_detects_regulated_without_disclaimer(self):
        """규제자: 의료/금융 분야 + 면책 문구 없음."""
        content = '이 의약품은 치료에 효과적입니다. 투자 수익률 200%를 달성했습니다.'
        result = stress_test(content, personas=['regulator'])[0]
        self.assertFalse(result.passed)
        disclaimer_issues = [i for i in result.issues if '면책' in i or '규제' in i]
        self.assertGreater(len(disclaimer_issues), 0)

    def test_regulator_passes_clean_content(self):
        """규제자: 문제없는 콘텐츠 통과."""
        content = '오늘 점심으로 파스타를 먹었습니다. 맛있었습니다.'
        result = stress_test(content, personas=['regulator'])[0]
        self.assertTrue(result.passed)

    # ── Competitor 테스트 ──

    def test_competitor_detects_disparagement(self):
        """경쟁사: 비방 표현 탐지."""
        content = '경쟁사 제품은 열등하고 불안정합니다. 우리 제품이 훨씬 낫습니다.'
        result = stress_test(content, personas=['competitor'])[0]
        self.assertFalse(result.passed)

    def test_competitor_passes_neutral(self):
        """경쟁사: 경쟁사 언급 없는 콘텐츠 통과."""
        content = '우리 제품의 주요 기능을 소개합니다. 사용이 간편합니다.'
        result = stress_test(content, personas=['competitor'])[0]
        self.assertTrue(result.passed)

    # ── Beginner 테스트 ──

    def test_beginner_detects_jargon_overuse(self):
        """초보자: 전문용어 과다 탐지."""
        content = (
            'API와 SDK를 활용한 REST GraphQL OAuth JWT CORS CI/CD DevOps '
            '마이크로서비스 컨테이너화 오케스트레이션 디커플링 리팩토링 환경을 구축합니다.'
        )
        result = stress_test(content, personas=['beginner'])[0]
        self.assertFalse(result.passed)

    def test_beginner_passes_simple(self):
        """초보자: 쉬운 용어로 작성된 콘텐츠 통과."""
        content = '이 앱을 설치하면 사진을 편집할 수 있습니다. 필터를 적용해보세요.'
        result = stress_test(content, personas=['beginner'])[0]
        self.assertTrue(result.passed)

    def test_beginner_jargon_with_explanation(self):
        """초보자: 전문용어에 설명이 있으면 이슈가 달라짐."""
        content = (
            'API(응용 프로그래밍 인터페이스)와 SDK를 활용합니다. '
            '즉, 개발 도구를 사용한다는 뜻입니다.'
        )
        result = stress_test(content, personas=['beginner'])[0]
        # 설명이 있으므로 '설명이 부족합니다'라는 이슈는 없어야 함
        no_explain_issues = [i for i in result.issues if '설명이 부족' in i]
        self.assertEqual(len(no_explain_issues), 0)

    def test_suggestions_always_present(self):
        """모든 결과에 suggestions가 1개 이상."""
        results = stress_test('아무 콘텐츠')
        for r in results:
            self.assertGreater(len(r.suggestions), 0)


if __name__ == '__main__':
    unittest.main()
