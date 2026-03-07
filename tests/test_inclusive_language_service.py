"""
포용적 언어 검사 서비스 테스트
"""
import unittest

from services.inclusive_language_service import check_inclusive_language


class TestInclusiveLanguageService(unittest.TestCase):
    """check_inclusive_language 함수 테스트."""

    # ── 기본 동작 ──

    def test_empty_content(self):
        """빈 콘텐츠 입력 시 기본 응답을 반환한다."""
        result = check_inclusive_language('')
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['summary']['total'], 0)
        self.assertEqual(result['inclusivity_score'], 100.0)
        self.assertIn('비어 있습니다', result['suggestions'][0])

        # None 입력
        result_none = check_inclusive_language(None)
        self.assertEqual(result_none['inclusivity_score'], 100.0)

    def test_clean_content(self):
        """편향 없는 텍스트는 이슈 없이 높은 점수를 반환한다."""
        content = '모든 사람은 평등합니다. 팀원 간 협력이 중요합니다.'
        result = check_inclusive_language(content)
        self.assertEqual(result['summary']['total'], 0)
        self.assertEqual(result['inclusivity_score'], 100.0)
        self.assertTrue(any('감지되지 않았습니다' in s for s in result['suggestions']))

    # ── 카테고리별 감지 ──

    def test_gender_bias_detection(self):
        """성별 편향 표현을 감지한다."""
        content = '그녀는 chairman으로 선출되었습니다. manpower가 부족합니다.'
        result = check_inclusive_language(content)
        gender_issues = [i for i in result['issues'] if i['category'] == 'gender']
        self.assertGreaterEqual(len(gender_issues), 3)
        phrases = [i['phrase'] for i in gender_issues]
        self.assertIn('그녀', phrases)
        self.assertIn('chairman', phrases)
        self.assertIn('manpower', phrases)

    def test_disability_detection(self):
        """장애 관련 편향 표현을 감지한다."""
        content = '이 방법은 정상인 기준으로 설계되었고, blind spot이 있습니다.'
        result = check_inclusive_language(content)
        disability_issues = [i for i in result['issues'] if i['category'] == 'disability']
        self.assertGreaterEqual(len(disability_issues), 2)
        phrases = [i['phrase'] for i in disability_issues]
        self.assertIn('정상인', phrases)
        self.assertIn('blind spot', phrases)

    def test_age_bias_detection(self):
        """나이 편향 표현을 감지한다."""
        content = '꼰대 같은 생각은 old-fashioned한 발상입니다.'
        result = check_inclusive_language(content)
        age_issues = [i for i in result['issues'] if i['category'] == 'age']
        self.assertGreaterEqual(len(age_issues), 2)
        phrases = [i['phrase'] for i in age_issues]
        self.assertIn('꼰대', phrases)
        self.assertIn('old-fashioned', phrases)

    def test_cultural_detection(self):
        """문화/인종 편향 표현을 감지한다."""
        content = '후진국 출신 외국인 노동자들이 증가하고 있다.'
        result = check_inclusive_language(content)
        cultural_issues = [i for i in result['issues'] if i['category'] == 'cultural']
        self.assertGreaterEqual(len(cultural_issues), 1)
        phrases = [i['phrase'] for i in cultural_issues]
        self.assertIn('후진국', phrases)

    def test_ability_detection(self):
        """능력주의 편향 표현을 감지한다."""
        content = '이런 멍청한 코드를 쓰다니. dummy 데이터를 사용하세요.'
        result = check_inclusive_language(content)
        ability_issues = [i for i in result['issues'] if i['category'] == 'ability']
        self.assertGreaterEqual(len(ability_issues), 2)
        phrases = [i['phrase'] for i in ability_issues]
        self.assertIn('멍청한', phrases)
        self.assertIn('dummy', phrases)

    # ── 대체 표현 ──

    def test_alternative_provided(self):
        """모든 감지 항목에 대체 표현이 제공된다."""
        content = 'fireman이 불구인 사람을 구했다. 바보 같은 실수다.'
        result = check_inclusive_language(content)
        for issue in result['issues']:
            self.assertIsInstance(issue['alternative'], str)
            self.assertGreater(len(issue['alternative']), 0)

        # 특정 대체 표현 확인
        fire_issue = next((i for i in result['issues'] if i['phrase'] == 'fireman'), None)
        self.assertIsNotNone(fire_issue)
        self.assertEqual(fire_issue['alternative'], 'firefighter')

    # ── 심각도 ──

    def test_severity_levels(self):
        """심각도가 low/medium/high 중 하나로 분류된다."""
        content = '불구인 사람을 chairman이 도왔다. blind spot이 있었다.'
        result = check_inclusive_language(content)
        valid_levels = {'low', 'medium', 'high'}
        for issue in result['issues']:
            self.assertIn(issue['severity'], valid_levels)

        # high 심각도 확인 (불구)
        high_issues = [i for i in result['issues'] if i['severity'] == 'high']
        self.assertGreaterEqual(len(high_issues), 1)

        # summary의 by_severity 확인
        self.assertIn('by_severity', result['summary'])

    # ── 점수 ──

    def test_inclusivity_score_range(self):
        """포용성 점수가 0-100 범위 내에 있다."""
        # 깨끗한 콘텐츠: 100점
        clean = check_inclusive_language('좋은 콘텐츠입니다.')
        self.assertEqual(clean['inclusivity_score'], 100.0)

        # 문제 있는 콘텐츠: 100 미만
        bad = check_inclusive_language('멍청한 꼰대가 chairman으로 불구인 사람을 무시했다.')
        self.assertGreaterEqual(bad['inclusivity_score'], 0.0)
        self.assertLess(bad['inclusivity_score'], 100.0)

    # ── 영어 감지 ──

    def test_english_detection(self):
        """영어 표현도 감지한다 (대소문자 무관)."""
        content = 'The Chairman decided to hire more Manpower.'
        result = check_inclusive_language(content)
        phrases_lower = [i['phrase'].lower() for i in result['issues']]
        # 대소문자 무관 감지 확인
        self.assertIn('chairman', phrases_lower)
        self.assertIn('manpower', phrases_lower)

    # ── 혼합 콘텐츠 ──

    def test_mixed_content(self):
        """한국어+영어 혼합 콘텐츠에서 여러 카테고리를 동시에 감지한다."""
        content = (
            '그녀는 chairman으로 일하고 있다. '
            '정상인 기준으로 설계된 시스템은 blind spot이 많다. '
            '꼰대 문화를 바꿔야 한다. '
            '후진국 출신이라고 차별하면 안 된다. '
            '멍청한 실수를 하지 마세요.'
        )
        result = check_inclusive_language(content)

        # 최소 5개 이상 이슈
        self.assertGreaterEqual(result['summary']['total'], 5)

        # 5개 카테고리 모두 감지
        detected_cats = set(result['summary']['by_category'].keys())
        self.assertEqual(detected_cats, {'gender', 'disability', 'age', 'cultural', 'ability'})

        # 점수가 크게 감소
        self.assertLess(result['inclusivity_score'], 70.0)

        # 제안이 여러 개
        self.assertGreaterEqual(len(result['suggestions']), 3)


if __name__ == '__main__':
    unittest.main()
