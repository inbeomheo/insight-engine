"""qa_gate_service 단위 테스트"""
import unittest
from unittest.mock import patch

from services.quality.qa_gate_service import check_quality


class TestCheckQuality(unittest.TestCase):
    """check_quality 함수 테스트"""

    def _make_content(self, chars=500, sections=3):
        """테스트용 콘텐츠 생성"""
        body = '본문 내용입니다. ' * (chars // 10)
        headings = '\n'.join(f'## 섹션 {i+1}\n' for i in range(sections))
        return headings + body

    # ── 정상 통과 케이스 ──

    def test_good_content_passes(self):
        """충분한 길이/섹션의 콘텐츠는 통과"""
        content = self._make_content(chars=600, sections=4)
        result = check_quality(content)
        self.assertTrue(result['passed'])
        self.assertEqual(len(result['issues']), 0)

    def test_return_structure(self):
        """반환 dict에 passed, issues, score 키 존재"""
        result = check_quality(self._make_content())
        self.assertIn('passed', result)
        self.assertIn('issues', result)
        self.assertIn('score', result)

    def test_perfect_score(self):
        """이슈 없으면 100점"""
        content = self._make_content(chars=600, sections=4)
        result = check_quality(content)
        self.assertEqual(result['score'], 100)

    # ── 길이 체크 ──

    def test_short_content_fails(self):
        """최소 길이 미달 시 error 이슈"""
        result = check_quality('짧은 글')
        self.assertFalse(result['passed'])
        types = [i['type'] for i in result['issues']]
        self.assertIn('length', types)

    # ── 섹션 체크 ──

    def test_few_sections_warning(self):
        """섹션 부족 시 warning 이슈"""
        content = '가' * 500  # 긴 글이지만 헤딩 없음
        result = check_quality(content)
        types = [i['type'] for i in result['issues']]
        self.assertIn('structure', types)
        # 섹션 부족은 warning이므로 passed는 True일 수 있음
        severity = [i['severity'] for i in result['issues'] if i['type'] == 'structure']
        self.assertEqual(severity[0], 'warning')

    # ── 금칙어 체크 ──

    @patch('services.quality.qa_gate_service.QA_FORBIDDEN_WORDS', ['금지단어', '나쁜말'])
    def test_forbidden_words_detected(self):
        """금칙어 포함 시 warning 이슈"""
        content = self._make_content() + ' 금지단어가 포함됨'
        result = check_quality(content)
        types = [i['type'] for i in result['issues']]
        self.assertIn('forbidden_words', types)

    # ── 중복 문장 체크 ──

    def test_duplicate_sentences(self):
        """중복 문장 감지"""
        # qa_gate는 [.!?。] + 공백으로 문장 분리, 20자 이상만 체크
        repeated = '이것은 충분히 긴 반복 문장이며 스무자가 넘습니다. '
        content = self._make_content() + (repeated * 5)
        result = check_quality(content)
        types = [i['type'] for i in result['issues']]
        self.assertIn('duplicate', types)

    def test_duplicate_sentences_no_space_after_period(self):
        """마침표 뒤에 공백 없이 연결된 중복 문장도 감지"""
        repeated = '이것은 충분히 긴 반복 문장이며 스무자가 넘습니다'
        content = self._make_content() + f'{repeated}.{repeated}.끝'
        result = check_quality(content)
        types = [i['type'] for i in result['issues']]
        self.assertIn('duplicate', types)

    def test_duplicate_sentences_exclamation_mark(self):
        """느낌표 뒤 공백 없이 연결된 중복 문장도 감지"""
        repeated = '이것은 충분히 긴 반복 문장이며 스무자가 넘습니다'
        content = self._make_content() + f'{repeated}!{repeated}!끝'
        result = check_quality(content)
        types = [i['type'] for i in result['issues']]
        self.assertIn('duplicate', types)

    def test_duplicate_sentences_korean_period(self):
        """한국어 마침표(。) 뒤 공백 없이 연결된 중복도 감지"""
        repeated = '이것은 충분히 긴 반복 문장이며 스무자가 넘습니다'
        content = self._make_content() + f'{repeated}。{repeated}。끝'
        result = check_quality(content)
        types = [i['type'] for i in result['issues']]
        self.assertIn('duplicate', types)

    def test_no_duplicate_unique_sentences(self):
        """고유 문장들은 중복 이슈 없음"""
        content = self._make_content() + '첫 번째 긴 문장이며 스무자 이상입니다. 두 번째로 다른 긴 문장이며 역시 스무자 넘습니다.'
        result = check_quality(content)
        types = [i['type'] for i in result['issues']]
        self.assertNotIn('duplicate', types)

    # ── 빈 링크 체크 ──

    def test_broken_links_detected(self):
        """빈 링크 감지 시 error"""
        content = self._make_content() + '\n[클릭하세요]()'
        result = check_quality(content)
        self.assertFalse(result['passed'])
        types = [i['type'] for i in result['issues']]
        self.assertIn('broken_links', types)

    # ── 점수 계산 ──

    def test_score_decreases_with_issues(self):
        """이슈 많을수록 점수 감소"""
        content = '짧은 글'  # length error + structure warning
        result = check_quality(content)
        self.assertLess(result['score'], 100)

    def test_score_minimum_zero(self):
        """점수는 0 이하로 내려가지 않음"""
        content = '짧은 글 [빈링크1]() [빈링크2]() [빈링크3]() [빈링크4]() [빈링크5]() [빈링크6]() [빈링크7]()'
        result = check_quality(content)
        self.assertGreaterEqual(result['score'], 0)


    # ── error_count / warning_count ──

    def test_error_warning_counts_in_result(self):
        """결과에 error_count, warning_count 포함"""
        content = self._make_content(chars=600, sections=4)
        result = check_quality(content)
        self.assertIn('error_count', result)
        self.assertIn('warning_count', result)
        self.assertEqual(result['error_count'], 0)
        self.assertEqual(result['warning_count'], 0)

    def test_error_count_on_short_content(self):
        """짧은 글은 error_count >= 1"""
        result = check_quality('짧은 글')
        self.assertGreaterEqual(result['error_count'], 1)

    def test_warning_count_on_no_sections(self):
        """섹션 없는 긴 글은 warning_count >= 1"""
        content = '가' * 500
        result = check_quality(content)
        self.assertGreaterEqual(result['warning_count'], 1)

    def test_score_penalty_weighted(self):
        """error는 25점, warning은 10점 감점"""
        # 빈 링크(error) + 섹션 부족(warning) = -35점 = 65점
        content = '가' * 500 + '\n[빈링크]()'
        result = check_quality(content)
        # error 1개(-25) + warning 1개(-10) = 65
        self.assertEqual(result['score'], 65)

    # ── suggestions ──

    def test_suggestions_in_result(self):
        """결과에 suggestions 키 존재"""
        result = check_quality(self._make_content(chars=600, sections=4))
        self.assertIn('suggestions', result)
        self.assertIsInstance(result['suggestions'], list)

    def test_suggestions_empty_for_perfect(self):
        """이슈 없으면 suggestions 비어있음"""
        result = check_quality(self._make_content(chars=600, sections=4))
        self.assertEqual(result['suggestions'], [])

    def test_suggestions_generated_for_issues(self):
        """이슈 있으면 개선 제안 문구 생성"""
        content = '짧은 글'  # length error + structure warning
        result = check_quality(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_suggestions_max_three(self):
        """suggestions는 최대 3개"""
        content = '짧은 글 [빈1]() [빈2]() 이것은 충분히 긴 반복 문장이며 스무자가 넘습니다. 이것은 충분히 긴 반복 문장이며 스무자가 넘습니다. '
        result = check_quality(content)
        self.assertLessEqual(len(result['suggestions']), 3)


class TestQaCheckAPITiming(unittest.TestCase):
    """POST /api/qa-check 응답에 check_duration_ms 포함 테스트."""

    def setUp(self):
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        self.client = app.test_client()

    @patch('services.data.supabase_service.is_supabase_enabled', return_value=False)
    def test_qa_check_includes_duration_ms(self, _mock_supa):
        """QA 검증 응답에 check_duration_ms 필드가 포함되어야 한다."""
        import json
        resp = self.client.post(
            '/api/qa-check',
            headers={'Origin': 'http://localhost:3000', 'Content-Type': 'application/json'},
            data=json.dumps({'content': '## 섹션 1\n' + '가나다라마바사. ' * 80})
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('check_duration_ms', data)
        self.assertIsInstance(data['check_duration_ms'], float)
        self.assertGreaterEqual(data['check_duration_ms'], 0)


if __name__ == '__main__':
    unittest.main()
