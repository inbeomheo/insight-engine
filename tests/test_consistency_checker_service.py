"""
Consistency & Contradiction Checker 서비스 테스트
"""
import unittest
from services.consistency_checker_service import check_consistency


class TestConsistencyCheckerService(unittest.TestCase):
    """check_consistency 함수에 대한 단위 테스트."""

    # --- 1. 빈 콘텐츠 ---
    def test_empty_content(self):
        """빈 문자열 입력 시 빈 결과와 만점을 반환한다."""
        result = check_consistency('')
        self.assertEqual(result['conflicts'], [])
        self.assertEqual(result['consistency_score'], 100.0)
        self.assertIsInstance(result['suggestions'], list)
        self.assertTrue(len(result['suggestions']) > 0)

        # None 입력도 안전하게 처리
        result_none = check_consistency(None)
        self.assertEqual(result_none['conflicts'], [])

    # --- 2. 모순 없는 콘텐츠 ---
    def test_consistent_content(self):
        """일관된 콘텐츠에서는 모순이 발견되지 않는다."""
        content = (
            '한국 시장 규모는 100억 원입니다. '
            '한국 시장 규모는 100억 원으로 추정됩니다. '
            '이 서비스는 2024년에 출시되었습니다. '
            '이 서비스는 2024년에 글로벌 시장에 진출했습니다.'
        )
        result = check_consistency(content)
        # 같은 수치/날짜이므로 모순 없음
        self.assertEqual(len(result['conflicts']), 0)
        self.assertEqual(result['consistency_score'], 100.0)

    # --- 3. 수치 모순 ---
    def test_number_conflict(self):
        """같은 주제에 대해 서로 다른 수치가 있으면 number_conflict를 감지한다."""
        content = (
            '국내 AI 시장 규모는 100억 원이다.\n'
            '국내 AI 시장 규모는 200억 원으로 추산된다.'
        )
        result = check_consistency(content)
        number_conflicts = [c for c in result['conflicts'] if c['type'] == 'number_conflict']
        self.assertTrue(len(number_conflicts) > 0, '수치 모순이 감지되어야 합니다')

        # 감지된 충돌의 구조 확인
        conflict = number_conflicts[0]
        self.assertIn('100', conflict['text1'] + conflict['text2'])
        self.assertIn('200', conflict['text1'] + conflict['text2'])

    # --- 4. 날짜 모순 ---
    def test_date_conflict(self):
        """같은 이벤트에 대해 서로 다른 날짜가 있으면 date_conflict를 감지한다."""
        content = (
            '이 제품은 2023년에 출시되었습니다.\n'
            '이 제품은 2024년에 출시되었습니다.'
        )
        result = check_consistency(content)
        date_conflicts = [c for c in result['conflicts'] if c['type'] == 'date_conflict']
        self.assertTrue(len(date_conflicts) > 0, '날짜 모순이 감지되어야 합니다')
        self.assertEqual(date_conflicts[0]['severity'], 'high')

    # --- 5. 비교 방향 모순 ---
    def test_comparison_conflict(self):
        """비교 방향이 모순되면 comparison_conflict를 감지한다."""
        content = (
            'Python이 Java보다 빠르다.\n'
            'Java가 Python보다 빠르다.'
        )
        result = check_consistency(content)
        comp_conflicts = [c for c in result['conflicts'] if c['type'] == 'comparison_conflict']
        self.assertTrue(len(comp_conflicts) > 0, '비교 모순이 감지되어야 합니다')
        self.assertEqual(comp_conflicts[0]['severity'], 'high')

    # --- 6. 심각도 수준 ---
    def test_severity_levels(self):
        """수치 차이에 따라 심각도가 구분된다."""
        # 2배 이상 차이 → high
        content_high = (
            '매출은 100억 원이다.\n'
            '매출은 300억 원이다.'
        )
        result_high = check_consistency(content_high)
        num_conflicts = [c for c in result_high['conflicts'] if c['type'] == 'number_conflict']
        self.assertTrue(any(c['severity'] == 'high' for c in num_conflicts))

        # 1.3배~2배 차이 → medium
        content_medium = (
            '이용자 수는 100만 명이다.\n'
            '이용자 수는 150만 명이다.'
        )
        result_medium = check_consistency(content_medium)
        num_conflicts_med = [c for c in result_medium['conflicts'] if c['type'] == 'number_conflict']
        if num_conflicts_med:
            self.assertIn(num_conflicts_med[0]['severity'], ['medium', 'high'])

    # --- 7. 일관성 점수 범위 ---
    def test_consistency_score_range(self):
        """일관성 점수는 0~100 사이여야 한다."""
        # 모순이 많은 콘텐츠
        content = (
            '시장 규모는 100억 원이다.\n'
            '시장 규모는 500억 원이다.\n'
            '출시 연도는 2020년이다.\n'
            '출시 연도는 2023년이다.\n'
            'A가 B보다 빠르다.\n'
            'B가 A보다 빠르다.\n'
            '성장률은 10%이다.\n'
            '성장률은 50%이다.'
        )
        result = check_consistency(content)
        self.assertGreaterEqual(result['consistency_score'], 0.0)
        self.assertLessEqual(result['consistency_score'], 100.0)

    # --- 8. 모순 없으면 만점 ---
    def test_no_conflicts_perfect_score(self):
        """모순이 없으면 일관성 점수가 100이다."""
        content = '오늘 날씨가 좋습니다. 산책하기 좋은 날입니다.'
        result = check_consistency(content)
        self.assertEqual(result['consistency_score'], 100.0)
        self.assertEqual(len(result['conflicts']), 0)

    # --- 9. 다중 모순 ---
    def test_multiple_conflicts(self):
        """여러 유형의 모순이 동시에 감지된다."""
        content = (
            '매출은 100억 원이다.\n'
            '매출은 200억 원이다.\n'
            '서비스 출시는 2022년이다.\n'
            '서비스 출시는 2024년이다.'
        )
        result = check_consistency(content)
        types = {c['type'] for c in result['conflicts']}
        # 수치 + 날짜 두 가지 이상 유형
        self.assertTrue(len(types) >= 2, f'2개 이상 유형이 감지되어야 합니다: {types}')
        self.assertIn('number_conflict', types)
        self.assertIn('date_conflict', types)

    # --- 10. 같은 수치는 모순 아님 ---
    def test_same_number_no_conflict(self):
        """같은 수치가 반복되면 모순으로 감지하지 않는다."""
        content = (
            '사용자 수는 500만 명입니다.\n'
            '사용자 수는 500만 명으로 집계됩니다.'
        )
        result = check_consistency(content)
        number_conflicts = [c for c in result['conflicts'] if c['type'] == 'number_conflict']
        self.assertEqual(len(number_conflicts), 0)

    # --- 11. 제안 생성 ---
    def test_suggestions(self):
        """모순이 있을 때 유형에 맞는 제안을 반환한다."""
        content = (
            '매출은 100억 원이다.\n'
            '매출은 200억 원이다.'
        )
        result = check_consistency(content)
        self.assertIsInstance(result['suggestions'], list)
        self.assertTrue(len(result['suggestions']) > 0)
        # 수치 관련 제안이 포함되어야 함
        joined = ' '.join(result['suggestions'])
        self.assertTrue('수치' in joined or '숫자' in joined or '불일치' in joined)

    # --- 12. 충돌 구조 검증 ---
    def test_conflict_structure(self):
        """각 충돌 항목은 올바른 필드를 가져야 한다."""
        content = (
            '투자액은 50억 원이다.\n'
            '투자액은 80억 원이다.'
        )
        result = check_consistency(content)
        required_keys = {'type', 'text1', 'text2', 'sentence1', 'sentence2', 'severity'}

        for conflict in result['conflicts']:
            self.assertTrue(
                required_keys.issubset(conflict.keys()),
                f'필드 누락: {required_keys - conflict.keys()}'
            )
            self.assertIn(conflict['type'], [
                'number_conflict', 'date_conflict',
                'comparison_conflict', 'name_conflict',
            ])
            self.assertIn(conflict['severity'], ['low', 'medium', 'high'])
            self.assertIsInstance(conflict['text1'], str)
            self.assertIsInstance(conflict['text2'], str)
            self.assertIsInstance(conflict['sentence1'], str)
            self.assertIsInstance(conflict['sentence2'], str)

    # --- 13. 고유명사 모순 ---
    def test_name_conflict(self):
        """같은 약어가 다른 전체명으로 사용되면 name_conflict를 감지한다."""
        content = (
            'AI는 인공지능 (AI) 기술의 핵심입니다.\n'
            'AI는 자동 검사 (AI) 시스템으로 활용됩니다.'
        )
        result = check_consistency(content)
        name_conflicts = [c for c in result['conflicts'] if c['type'] == 'name_conflict']
        self.assertTrue(len(name_conflicts) > 0, '고유명사 모순이 감지되어야 합니다')

    # --- 14. 모순 없는 제안 메시지 ---
    def test_no_conflict_suggestion_message(self):
        """모순이 없을 때 일관성 양호 메시지를 반환한다."""
        content = '오늘은 회의가 있습니다. 내일은 출장입니다.'
        result = check_consistency(content)
        self.assertTrue(any('양호' in s or '모순' in s for s in result['suggestions']))


if __name__ == '__main__':
    unittest.main()
