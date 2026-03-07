"""
대명사/지시어 명확성 검사 서비스 테스트
"""
import unittest

from services.pronoun_clarity_service import check_pronoun_clarity


class TestPronounClarityService(unittest.TestCase):
    """check_pronoun_clarity 함수 단위 테스트"""

    # --- 기본 케이스 ---

    def test_empty_content(self):
        """빈 콘텐츠 입력 시 기본 결과 반환"""
        result = check_pronoun_clarity('')
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['summary']['total'], 0)
        self.assertEqual(result['clarity_score'], 100.0)
        self.assertTrue(len(result['suggestions']) > 0)

        # None 입력도 동일 동작
        result_none = check_pronoun_clarity(None)
        self.assertEqual(result_none['issues'], [])

    def test_clean_content(self):
        """모호한 지시어가 없는 깨끗한 콘텐츠"""
        content = '파이썬은 인기 있는 프로그래밍 언어입니다. 파이썬으로 웹 개발을 할 수 있습니다.'
        result = check_pronoun_clarity(content)
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['summary']['total'], 0)
        self.assertEqual(result['clarity_score'], 100.0)
        # 깨끗한 글에 대한 긍정 제안 포함
        self.assertTrue(any('명확한' in s for s in result['suggestions']))

    # --- 한국어 지시어 감지 ---

    def test_korean_pronoun_detection(self):
        """한국어 지시어(이것, 그것, 그들 등) 감지"""
        content = '이것은 매우 중요합니다. 그것이 핵심입니다.'
        result = check_pronoun_clarity(content)
        self.assertGreater(len(result['issues']), 0)
        pronouns_found = {issue['pronoun'] for issue in result['issues']}
        # '이것'과 '그것' 모두 감지
        self.assertIn('이것', pronouns_found)
        self.assertIn('그것', pronouns_found)

    # --- 영어 지시어 감지 ---

    def test_english_pronoun_detection(self):
        """영어 지시어(it, this, they 등) 감지"""
        content = 'It is very important. They should know about this.'
        result = check_pronoun_clarity(content)
        self.assertGreater(len(result['issues']), 0)
        pronouns_found = {issue['pronoun'] for issue in result['issues']}
        self.assertTrue('it' in pronouns_found or 'they' in pronouns_found or 'this' in pronouns_found)

    # --- 문장 시작 심각도 ---

    def test_sentence_start_severity(self):
        """문장 시작 위치의 지시어는 high 심각도"""
        content = '이것은 문제입니다. 다른 내용이 있습니다.'
        result = check_pronoun_clarity(content)
        high_issues = [i for i in result['issues'] if i['severity'] == 'high']
        self.assertGreater(len(high_issues), 0)
        # 문장 시작 위치
        self.assertEqual(high_issues[0]['position'], 'start')

    # --- 문장 중간 지시어 ---

    def test_mid_sentence_pronoun(self):
        """문장 중간의 지시어는 medium 심각도"""
        content = '중요한 점은 바로 이것이 핵심이라는 사실입니다.'
        result = check_pronoun_clarity(content)
        # '이것'이 감지되어야 함
        issues_with_pronoun = [i for i in result['issues'] if i['pronoun'] == '이것']
        self.assertGreater(len(issues_with_pronoun), 0)
        # 중간 위치이므로 medium
        mid_issues = [i for i in issues_with_pronoun if i['position'] == 'middle']
        if mid_issues:
            self.assertEqual(mid_issues[0]['severity'], 'medium')

    # --- 점수 범위 ---

    def test_clarity_score_range(self):
        """명확성 점수는 0~100 범위"""
        # 이슈 없는 경우
        clean = check_pronoun_clarity('명확한 문장입니다.')
        self.assertGreaterEqual(clean['clarity_score'], 0.0)
        self.assertLessEqual(clean['clarity_score'], 100.0)

        # 이슈 많은 경우
        messy = check_pronoun_clarity(
            '이것은 문제입니다. 그것이 핵심입니다. '
            '그들은 동의합니다. 이러한 상황입니다. '
            '그런 결과가 나왔습니다. 저것도 중요합니다. '
            'It is critical. They should act.'
        )
        self.assertGreaterEqual(messy['clarity_score'], 0.0)
        self.assertLessEqual(messy['clarity_score'], 100.0)

    # --- 제안 제공 ---

    def test_suggestion_provided(self):
        """모호한 지시어 발견 시 제안 포함"""
        content = '이것은 중요합니다.'
        result = check_pronoun_clarity(content)
        # 이슈가 있으면 제안도 있어야 함
        self.assertGreater(len(result['issues']), 0)
        self.assertGreater(len(result['suggestions']), 0)
        # 각 이슈에 suggestion 필드 존재
        for issue in result['issues']:
            self.assertIn('suggestion', issue)
            self.assertTrue(len(issue['suggestion']) > 0)

    # --- 다중 지시어 ---

    def test_multiple_pronouns(self):
        """여러 지시어가 동시에 감지"""
        content = '이것은 중요합니다. 그들은 반대합니다. It is unclear. They disagree.'
        result = check_pronoun_clarity(content)
        self.assertGreater(result['summary']['total'], 2)

    # --- 명사 동반 시 비모호 판정 ---

    def test_pronoun_with_noun(self):
        """지시어 + 명사 결합은 모호하지 않음 (이런 방법, this method)"""
        content = '이런 방법으로 해결할 수 있습니다. This method works well.'
        result = check_pronoun_clarity(content)
        # "이런 방법" → 명사 동반이므로 이슈 아님
        # "this method" → 명사 동반이므로 이슈 아님
        ko_issues = [i for i in result['issues'] if i['pronoun'] == '이런']
        en_issues = [i for i in result['issues'] if i['pronoun'] == 'this']
        self.assertEqual(len(ko_issues), 0, '"이런 방법"은 명확하므로 이슈가 아님')
        self.assertEqual(len(en_issues), 0, '"this method"는 명확하므로 이슈가 아님')

    # --- 혼합 콘텐츠 ---

    def test_mixed_content(self):
        """한국어 + 영어 혼합 콘텐츠"""
        content = (
            '이것은 새로운 기술입니다. '
            'It is revolutionary. '
            '그러한 혁신이 필요합니다.'
        )
        result = check_pronoun_clarity(content)
        self.assertGreater(result['summary']['total'], 0)
        # 한국어 + 영어 지시어 모두 감지
        pronouns = {i['pronoun'] for i in result['issues']}
        has_ko = any(p in _ko_set() for p in pronouns)
        has_en = any(p in _en_set() for p in pronouns)
        self.assertTrue(has_ko, '한국어 지시어가 감지되어야 함')
        self.assertTrue(has_en, '영어 지시어가 감지되어야 함')

    # --- 요약 구조 ---

    def test_summary_structure(self):
        """summary 필드의 구조 검증"""
        content = '이것은 중요합니다. 그것이 핵심입니다. It matters.'
        result = check_pronoun_clarity(content)
        summary = result['summary']

        # 필수 키 존재
        self.assertIn('total', summary)
        self.assertIn('by_severity', summary)

        # total은 issues 길이와 일치
        self.assertEqual(summary['total'], len(result['issues']))

        # by_severity 합계도 total과 일치
        sev_sum = sum(summary['by_severity'].values())
        self.assertEqual(sev_sum, summary['total'])


def _ko_set():
    """한국어 지시어 집합 (테스트 헬퍼)"""
    return {'이것', '그것', '저것', '이들', '그들', '이런', '그런', '이러한', '그러한'}


def _en_set():
    """영어 지시어 집합 (테스트 헬퍼)"""
    return {'it', 'this', 'that', 'they', 'them', 'these', 'those'}


if __name__ == '__main__':
    unittest.main()
