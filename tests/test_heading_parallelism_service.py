"""
헤딩 병렬 구조 검사 서비스 테스트

동일 레벨 헤딩의 문법 형태 일관성 검사 로직을 검증합니다.
"""
import unittest

from services.analysis.heading_parallelism_service import check_heading_parallelism


class TestHeadingParallelism(unittest.TestCase):
    """check_heading_parallelism 함수 테스트."""

    # --- 빈 입력 / 헤딩 없음 ---

    def test_empty_content(self):
        """빈 문자열 입력 시 기본 반환값."""
        result = check_heading_parallelism('')
        self.assertEqual(result['headings'], [])
        self.assertEqual(result['groups'], {})
        self.assertEqual(result['parallelism_score'], 100.0)
        self.assertEqual(result['issues'], [])
        self.assertEqual(result['suggestions'], [])

    def test_no_headings(self):
        """헤딩이 없는 일반 텍스트."""
        content = '이것은 일반 텍스트입니다.\n아무 헤딩도 없습니다.'
        result = check_heading_parallelism(content)
        self.assertEqual(result['headings'], [])
        self.assertEqual(result['groups'], {})
        self.assertEqual(result['parallelism_score'], 100.0)

    # --- 일관된 헤딩 ---

    def test_parallel_headings(self):
        """동일 레벨에서 모든 헤딩이 같은 형태일 때 is_parallel=True."""
        content = '\n'.join([
            '## 콘텐츠 분석',
            '## SEO 최적화',
            '## 데이터 시각화',
        ])
        result = check_heading_parallelism(content)
        self.assertEqual(len(result['headings']), 3)
        self.assertTrue(result['groups'][2]['is_parallel'])
        self.assertEqual(result['groups'][2]['dominant_form'], 'noun_phrase')
        self.assertEqual(result['parallelism_score'], 100.0)
        self.assertEqual(result['issues'], [])

    # --- 비일관 헤딩 ---

    def test_mixed_forms(self):
        """동일 레벨에서 형태가 혼합되면 이슈가 발생합니다."""
        content = '\n'.join([
            '## 콘텐츠 분석',       # noun_phrase
            '## SEO 최적화',        # noun_phrase
            '## 왜 중요한가요?',    # question
        ])
        result = check_heading_parallelism(content)
        self.assertFalse(result['groups'][2]['is_parallel'])
        self.assertEqual(len(result['issues']), 1)
        self.assertEqual(result['issues'][0]['mismatched_heading'], '왜 중요한가요?')
        self.assertEqual(result['issues'][0]['expected_form'], 'noun_phrase')
        self.assertEqual(result['issues'][0]['actual_form'], 'question')

    # --- 형태 분류 ---

    def test_question_detection(self):
        """질문형 헤딩 인식."""
        content = '\n'.join([
            '## 이것은 무엇인가요?',
            '## 왜 필요할까요?',
            '## How to use it?',
        ])
        result = check_heading_parallelism(content)
        for h in result['headings']:
            self.assertEqual(h['form'], 'question', f'"{h["text"]}" 가 question이어야 합니다')

    def test_imperative_detection(self):
        """명령형 헤딩 인식 (한국어 + 영어)."""
        content = '\n'.join([
            '## 설정을 확인하세요',
            '## Use the API',
            '## Create a project',
        ])
        result = check_heading_parallelism(content)
        for h in result['headings']:
            self.assertEqual(h['form'], 'imperative', f'"{h["text"]}" 가 imperative이어야 합니다')

    def test_noun_phrase_detection(self):
        """명사구 헤딩 인식."""
        content = '\n'.join([
            '## 프로젝트 개요',
            '## 시스템 아키텍처',
            '## 배포 전략',
        ])
        result = check_heading_parallelism(content)
        for h in result['headings']:
            self.assertEqual(h['form'], 'noun_phrase', f'"{h["text"]}" 가 noun_phrase이어야 합니다')

    def test_numbered_detection(self):
        """숫자형 헤딩 인식."""
        content = '\n'.join([
            '## 1. 첫 번째 단계',
            '## 2. 두 번째 단계',
            '## Step 3 마무리',
        ])
        result = check_heading_parallelism(content)
        for h in result['headings']:
            self.assertEqual(h['form'], 'numbered', f'"{h["text"]}" 가 numbered이어야 합니다')

    def test_gerund_detection(self):
        """동명사형 헤딩 인식 (한국어 + 영어)."""
        content = '\n'.join([
            '## 데이터 수집하기',
            '## Building APIs',
        ])
        result = check_heading_parallelism(content)
        for h in result['headings']:
            self.assertEqual(h['form'], 'gerund', f'"{h["text"]}" 가 gerund이어야 합니다')

    # --- 점수 범위 ---

    def test_parallelism_score_range(self):
        """점수가 항상 0~100 범위입니다."""
        # 완전 불일치 사례
        content = '\n'.join([
            '## 콘텐츠 분석',        # noun_phrase
            '## 왜 필요한가요?',     # question
            '## 설정을 확인하세요',   # imperative
            '## 1. 시작',            # numbered
        ])
        result = check_heading_parallelism(content)
        self.assertGreaterEqual(result['parallelism_score'], 0)
        self.assertLessEqual(result['parallelism_score'], 100)
        # 4개 중 1개만 dominant → 25점
        self.assertLess(result['parallelism_score'], 50)

    # --- 다중 레벨 ---

    def test_multiple_levels(self):
        """여러 레벨이 각각 독립적으로 검사됩니다."""
        content = '\n'.join([
            '# 프로젝트 개요',        # h1 noun_phrase
            '# 시스템 설계',          # h1 noun_phrase
            '## 왜 중요한가요?',      # h2 question
            '## 어떻게 동작하나요?',  # h2 question (무엇 → question)
            '### Use Docker',         # h3 imperative
            '### Create CI pipeline', # h3 imperative
        ])
        result = check_heading_parallelism(content)
        # 3개 레벨 모두 존재
        self.assertIn(1, result['groups'])
        self.assertIn(2, result['groups'])
        self.assertIn(3, result['groups'])
        # 각 레벨 내부에서 일관
        self.assertTrue(result['groups'][1]['is_parallel'])
        self.assertTrue(result['groups'][2]['is_parallel'])
        self.assertTrue(result['groups'][3]['is_parallel'])
        self.assertEqual(result['parallelism_score'], 100.0)

    # --- 반환 구조 ---

    def test_issues_structure(self):
        """issues 항목의 필수 키가 모두 존재합니다."""
        content = '\n'.join([
            '## 기본 개요',
            '## SEO 전략',
            '## 왜 필요한가요?',
        ])
        result = check_heading_parallelism(content)
        self.assertGreater(len(result['issues']), 0)
        for issue in result['issues']:
            self.assertIn('level', issue)
            self.assertIn('mismatched_heading', issue)
            self.assertIn('expected_form', issue)
            self.assertIn('actual_form', issue)

    def test_suggestions(self):
        """비일관성 있을 때 개선 제안이 포함됩니다."""
        content = '\n'.join([
            '## 콘텐츠 분석',
            '## SEO 최적화',
            '## 왜 중요한가요?',
        ])
        result = check_heading_parallelism(content)
        self.assertGreater(len(result['suggestions']), 0)

        # 일관적일 때도 긍정 메시지 제공
        parallel_content = '\n'.join([
            '## 개요',
            '## 설계',
        ])
        result2 = check_heading_parallelism(parallel_content)
        self.assertGreater(len(result2['suggestions']), 0)
        self.assertIn('일관된', result2['suggestions'][0])

    # --- 추가: None 입력 ---

    def test_none_content(self):
        """None 입력 시에도 안전하게 기본 반환값."""
        result = check_heading_parallelism(None)
        self.assertEqual(result['headings'], [])
        self.assertEqual(result['parallelism_score'], 100.0)

    # --- 추가: h4 이상은 무시 ---

    def test_h4_ignored(self):
        """h4(####) 이상은 추출 대상에서 제외됩니다."""
        content = '\n'.join([
            '#### 이것은 h4',
            '##### 이것은 h5',
        ])
        result = check_heading_parallelism(content)
        self.assertEqual(result['headings'], [])


if __name__ == '__main__':
    unittest.main()
