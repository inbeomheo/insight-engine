"""
Subheading Gap Detector 서비스 단위 테스트
"""
import unittest

from services.subheading_gap_service import detect_subheading_gaps


class TestSubheadingGapService(unittest.TestCase):
    """detect_subheading_gaps 함수 테스트"""

    # --- 기본 케이스 ---

    def test_empty_content(self):
        """빈 콘텐츠 입력 시 기본 응답을 반환한다."""
        result = detect_subheading_gaps('')
        self.assertEqual(result['sections'], [])
        self.assertEqual(result['gaps'], [])
        self.assertEqual(result['balance_score'], 100.0)
        self.assertIn('비어 있습니다', result['suggestions'][0])

        # None 입력도 동일
        result_none = detect_subheading_gaps(None)
        self.assertEqual(result_none['sections'], [])

    def test_no_headings(self):
        """헤딩이 없는 일반 텍스트 입력 시 빈 섹션을 반환한다."""
        content = '이것은 헤딩이 없는 일반 텍스트입니다. 마크다운 문법이 사용되지 않았습니다.'
        result = detect_subheading_gaps(content)
        self.assertEqual(result['sections'], [])
        self.assertEqual(result['gaps'], [])
        self.assertIn('헤딩이 없습니다', result['suggestions'][0])

    def test_single_heading(self):
        """헤딩이 하나뿐인 경우 단일 섹션을 반환한다."""
        content = '# 제목\n\n본문 내용이 여기에 들어갑니다. 적절한 길이의 텍스트입니다.'
        result = detect_subheading_gaps(content)
        self.assertEqual(len(result['sections']), 1)
        self.assertEqual(result['sections'][0]['heading'], '제목')
        self.assertEqual(result['sections'][0]['level'], 1)

    # --- 상태 판정 ---

    def test_well_balanced(self):
        """균형 잡힌 섹션들이면 모두 ok 상태이고 높은 점수를 받는다."""
        # 각 섹션 약 60~80자 (ok 범위)
        body = '가나다라마바사아자차카타파하 ' * 5
        content = (
            f'# 섹션 하나\n\n{body}\n\n'
            f'# 섹션 둘\n\n{body}\n\n'
            f'# 섹션 셋\n\n{body}'
        )
        result = detect_subheading_gaps(content)
        self.assertEqual(len(result['sections']), 3)
        for s in result['sections']:
            self.assertEqual(s['status'], 'ok')
        self.assertGreater(result['balance_score'], 70)
        self.assertEqual(len(result['gaps']), 0)

    def test_too_long_section(self):
        """300자를 초과하는 섹션은 too_long으로 판정된다."""
        long_text = '가나다라마바사' * 60  # 약 420자
        content = f'# 긴 섹션\n\n{long_text}'
        result = detect_subheading_gaps(content)
        self.assertEqual(result['sections'][0]['status'], 'too_long')
        self.assertGreater(result['sections'][0]['char_count'], 300)

    def test_too_short_section(self):
        """50자 미만 섹션은 too_short으로 판정된다."""
        content = '# 짧은 섹션\n\n짧은 본문'
        result = detect_subheading_gaps(content)
        self.assertEqual(result['sections'][0]['status'], 'too_short')
        self.assertLess(result['sections'][0]['char_count'], 50)

    # --- 갭 감지 ---

    def test_gap_detection(self):
        """too_long/too_short 섹션은 gaps 리스트에 추가된다."""
        long_text = '가나다라마바사' * 60
        content = (
            f'# 긴 섹션\n\n{long_text}\n\n'
            '# 짧은 섹션\n\n짧다\n\n'
            '# 정상 섹션\n\n' + '가나다라마바사아자차' * 8
        )
        result = detect_subheading_gaps(content)
        # 긴 섹션 + 짧은 섹션 = 2개 갭
        self.assertEqual(len(result['gaps']), 2)

        issues = [g['issue'] for g in result['gaps']]
        self.assertTrue(any('너무 깁니다' in i for i in issues))
        self.assertTrue(any('너무 짧습니다' in i for i in issues))

    # --- 균형 점수 ---

    def test_balance_score_range(self):
        """균형 점수는 항상 0~100 범위 내에 있다."""
        # 극단적 불균형 테스트
        content = (
            '# 아주 긴 섹션\n\n' + '가나다라마바사아자차' * 100 + '\n\n'
            '# 아주 짧은 섹션\n\n짧'
        )
        result = detect_subheading_gaps(content)
        self.assertGreaterEqual(result['balance_score'], 0)
        self.assertLessEqual(result['balance_score'], 100)

        # 균형 잡힌 경우도 범위 확인
        content_balanced = (
            '# A\n\n' + '테스트텍스트입니다' * 10 + '\n\n'
            '# B\n\n' + '테스트텍스트입니다' * 10
        )
        result_balanced = detect_subheading_gaps(content_balanced)
        self.assertGreaterEqual(result_balanced['balance_score'], 0)
        self.assertLessEqual(result_balanced['balance_score'], 100)

    # --- 다중 헤딩 레벨 ---

    def test_multiple_levels(self):
        """#, ##, ### 등 다양한 레벨의 헤딩을 모두 인식한다."""
        body = '가나다라마바사아자차' * 8  # 약 80자 (ok 범위)
        content = (
            f'# 대제목\n\n{body}\n\n'
            f'## 중제목\n\n{body}\n\n'
            f'### 소제목\n\n{body}'
        )
        result = detect_subheading_gaps(content)
        self.assertEqual(len(result['sections']), 3)
        levels = [s['level'] for s in result['sections']]
        self.assertEqual(levels, [1, 2, 3])

    # --- 섹션 구조 검증 ---

    def test_section_structure(self):
        """반환되는 섹션 딕셔너리에 필수 키가 모두 포함된다."""
        content = '## 테스트\n\n본문 내용이 여기에 있습니다. 충분한 길이의 텍스트.'
        result = detect_subheading_gaps(content)

        required_keys = {'heading', 'level', 'word_count', 'char_count',
                         'paragraph_count', 'status'}
        self.assertEqual(len(result['sections']), 1)
        self.assertEqual(set(result['sections'][0].keys()), required_keys)

        # 최상위 반환값 키 검증
        top_keys = {'sections', 'gaps', 'balance_score', 'suggestions'}
        self.assertEqual(set(result.keys()), top_keys)

    # --- 단락 카운팅 ---

    def test_paragraph_counting(self):
        """빈 줄로 구분된 단락 수를 정확히 센다."""
        content = (
            '# 단락 테스트\n\n'
            '첫 번째 단락입니다.\n\n'
            '두 번째 단락입니다.\n\n'
            '세 번째 단락입니다.'
        )
        result = detect_subheading_gaps(content)
        self.assertEqual(result['sections'][0]['paragraph_count'], 3)

    # --- 제안 ---

    def test_suggestions(self):
        """문제 유형에 맞는 제안을 생성한다."""
        long_text = '가나다라마바사' * 60
        content = (
            f'# 긴 섹션\n\n{long_text}\n\n'
            '# 짧은 섹션\n\n짧'
        )
        result = detect_subheading_gaps(content)
        suggestions_text = ' '.join(result['suggestions'])

        # 긴 섹션 → 분할 권장
        self.assertIn('초과', suggestions_text)
        # 짧은 섹션 → 보강/병합 권장
        self.assertIn('미만', suggestions_text)

    # --- 추가 엣지 케이스 ---

    def test_heading_without_body(self):
        """헤딩만 있고 본문이 없는 경우 too_short로 판정된다."""
        content = '# 빈 섹션\n\n# 다음 섹션\n\n적당한 본문 내용이 여기에 있습니다.'
        result = detect_subheading_gaps(content)
        self.assertEqual(len(result['sections']), 2)
        # 첫 섹션은 본문이 없으므로 too_short
        self.assertEqual(result['sections'][0]['status'], 'too_short')


if __name__ == '__main__':
    unittest.main()
