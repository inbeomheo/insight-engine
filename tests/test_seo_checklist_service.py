"""seo_checklist_service 단위 테스트"""
import unittest

from services.seo_checklist_service import run_checklist, PASS, WARN, FAIL


class TestSeoChecklist(unittest.TestCase):
    """SEO 체크리스트 통합 테스트"""

    def _find_check(self, checks, check_id):
        return next((c for c in checks if c['id'] == check_id), None)

    def test_perfect_score(self):
        """모든 항목 통과 시 높은 점수"""
        title = '파이썬 프로그래밍 입문 가이드 완벽 정리'  # 30~60자
        content = (
            '# 파이썬 프로그래밍 입문\n'
            '## 기초 문법\n'
            '파이썬 ' * 200 + '\n'
            '[링크1](https://example.com)\n'
            '[링크2](https://example2.com)\n'
        )
        meta = {'description': 'A' * 140}  # 120~160자
        result = run_checklist(title, content, meta)
        self.assertEqual(result['grade'], 'A')
        self.assertGreaterEqual(result['score'], 80)

    def test_title_too_short(self):
        """짧은 제목"""
        result = run_checklist('짧은', 'x' * 1000)
        check = self._find_check(result['checks'], 'title_length')
        self.assertEqual(check['status'], WARN)

    def test_title_too_long(self):
        """긴 제목"""
        result = run_checklist('가' * 70, 'x' * 1000)
        check = self._find_check(result['checks'], 'title_length')
        self.assertEqual(check['status'], WARN)

    def test_content_too_short(self):
        """300자 미만 본문"""
        result = run_checklist('적절한 길이의 제목이 들어갑니다 여기에', '짧은 본문')
        check = self._find_check(result['checks'], 'content_length')
        self.assertEqual(check['status'], FAIL)

    def test_no_headings(self):
        """헤딩 없으면 FAIL"""
        result = run_checklist('적절한 길이의 제목이 들어갑니다 여기에', '본문 ' * 500)
        check = self._find_check(result['checks'], 'headings')
        self.assertEqual(check['status'], FAIL)

    def test_both_headings(self):
        """H1+H2 둘 다 있으면 PASS"""
        content = '# H1 제목\n## H2 부제목\n' + '내용 ' * 500
        result = run_checklist('적절한 길이의 제목이 들어갑니다 여기에', content)
        check = self._find_check(result['checks'], 'headings')
        self.assertEqual(check['status'], PASS)

    def test_links_pass(self):
        """링크 2개 이상이면 PASS"""
        content = '[a](https://a.com) [b](https://b.com) ' + '내용 ' * 500
        result = run_checklist('적절한 길이의 제목이 들어갑니다 여기에', content)
        check = self._find_check(result['checks'], 'links')
        self.assertEqual(check['status'], PASS)

    def test_keyword_in_content(self):
        """제목 키워드가 본문에 3회+ 등장"""
        title = '파이썬 프로그래밍 완벽 가이드 작성합니다'
        content = '파이썬 파이썬 파이썬 파이썬 ' * 100
        result = run_checklist(title, content)
        check = self._find_check(result['checks'], 'keyword_density')
        self.assertEqual(check['status'], PASS)

    def test_keyword_missing(self):
        """키워드 본문 미포함"""
        title = '자바스크립트로 배우는 웹 프로그래밍 입문'
        content = '파이썬 ' * 500
        result = run_checklist(title, content)
        check = self._find_check(result['checks'], 'keyword_density')
        self.assertEqual(check['status'], FAIL)

    def test_meta_description_good(self):
        """메타 설명 120~160자"""
        result = run_checklist('적절한 길이의 제목이 들어갑니다 여기에', 'x' * 1000, {'description': 'A' * 140})
        check = self._find_check(result['checks'], 'meta_description')
        self.assertEqual(check['status'], PASS)

    def test_no_meta(self):
        """메타 없으면 WARN"""
        result = run_checklist('적절한 길이의 제목이 들어갑니다 여기에', 'x' * 1000)
        check = self._find_check(result['checks'], 'meta_description')
        self.assertEqual(check['status'], WARN)

    def test_grade_d(self):
        """모든 항목 실패 시 D"""
        result = run_checklist('', '')
        self.assertEqual(result['grade'], 'D')

    def test_score_range(self):
        """점수 0~100 범위"""
        result = run_checklist('제목', '내용')
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)


if __name__ == '__main__':
    unittest.main()
