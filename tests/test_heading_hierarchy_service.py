"""Heading Hierarchy Integrity Checker 서비스 테스트."""
import unittest
from services.analysis.heading_hierarchy_service import check_heading_hierarchy, suggest_fixes


class TestHeadingHierarchy(unittest.TestCase):

    def test_empty_content(self):
        result = check_heading_hierarchy('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = check_heading_hierarchy(None)
        self.assertEqual(result['score'], 100.0)

    def test_no_headings(self):
        content = '일반 텍스트입니다.\n문단이 이어집니다.'
        result = check_heading_hierarchy(content)
        self.assertEqual(result['summary']['total_headings'], 0)

    def test_clean_hierarchy(self):
        content = ('# 제목\n\n본문입니다.\n\n'
                   '## 섹션 1\n\n내용입니다.\n\n'
                   '### 하위 섹션\n\n세부 내용입니다.\n\n'
                   '## 섹션 2\n\n다른 내용입니다.\n')
        result = check_heading_hierarchy(content)
        self.assertEqual(result['summary']['level'], 'clean')
        self.assertEqual(result['score'], 100.0)

    def test_skip_detection(self):
        content = ('# 제목\n\n본문입니다.\n\n'
                   '### 건너뛴 섹션\n\n내용입니다.\n')
        result = check_heading_hierarchy(content)
        skip_issues = [i for i in result['hierarchy_issues']
                       if i['type'] == 'skip']
        self.assertGreater(len(skip_issues), 0)

    def test_duplicate_h1(self):
        content = ('# 첫 번째 제목\n\n본문입니다.\n\n'
                   '# 두 번째 제목\n\n다른 내용입니다.\n')
        result = check_heading_hierarchy(content)
        h1_issues = [i for i in result['hierarchy_issues']
                     if i['type'] == 'duplicate_h1']
        self.assertGreater(len(h1_issues), 0)

    def test_empty_section(self):
        content = ('# 제목\n\n본문입니다.\n\n'
                   '## 빈 섹션\n'
                   '## 다음 섹션\n\n내용이 있습니다.\n')
        result = check_heading_hierarchy(content)
        empty_issues = [i for i in result['hierarchy_issues']
                        if i['type'] == 'empty_section']
        self.assertGreater(len(empty_issues), 0)

    def test_deep_nesting(self):
        content = ('# 제목\n\n본문.\n\n'
                   '## H2\n\n본문.\n\n'
                   '### H3\n\n본문.\n\n'
                   '#### H4\n\n본문.\n\n'
                   '##### H5\n\n깊은 본문.\n')
        result = check_heading_hierarchy(content)
        deep_issues = [i for i in result['hierarchy_issues']
                       if i['type'] == 'deep_nesting']
        self.assertGreater(len(deep_issues), 0)

    def test_max_depth(self):
        content = ('# 제목\n\n본문.\n\n'
                   '## 섹션\n\n본문.\n\n'
                   '### 하위\n\n본문.\n')
        result = check_heading_hierarchy(content)
        self.assertEqual(result['summary']['max_depth'], 3)

    def test_score_range(self):
        content = '## 테스트 제목\n\n내용입니다.'
        result = check_heading_hierarchy(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '## 구조 확인\n\n테스트입니다.'
        result = check_heading_hierarchy(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('hierarchy_issues', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_headings', result['summary'])
        self.assertIn('max_depth', result['summary'])
        self.assertIn('issue_count', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_issues(self):
        content = ('# 제목\n\n본문.\n\n'
                   '### 건너뛴 H3\n\n내용.\n\n'
                   '# 중복 H1\n\n내용.\n')
        result = check_heading_hierarchy(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_problematic_level(self):
        content = ('# 제목1\n# 제목2\n# 제목3\n'
                   '### 건너뜀1\n##### 건너뜀2\n'
                   '## 빈섹션1\n## 빈섹션2\n## 빈섹션3\n'
                   '## 내용있음\n\n본문입니다.\n')
        result = check_heading_hierarchy(content)
        self.assertIn(result['summary']['level'], ('moderate', 'problematic'))

    def test_heading_count(self):
        content = ('## 섹션 A\n\n본문.\n\n'
                   '## 섹션 B\n\n본문.\n\n'
                   '## 섹션 C\n\n본문.\n')
        result = check_heading_hierarchy(content)
        self.assertEqual(result['summary']['total_headings'], 3)


class TestSuggestFixes(unittest.TestCase):
    """suggest_fixes 테스트"""

    def test_empty_content(self):
        result = suggest_fixes('')
        self.assertEqual(result['fix_count'], 0)

    def test_clean_no_fixes(self):
        """이슈 없는 콘텐츠는 수정 제안 없음"""
        content = '# 제목\n\n본문.\n\n## 섹션\n\n내용.\n'
        result = suggest_fixes(content)
        self.assertEqual(result['fix_count'], 0)

    def test_skip_fix(self):
        """건너뛰기 이슈에 레벨 변경 제안"""
        content = '# 제목\n\n본문.\n\n### 건너뛴 헤딩\n\n내용.\n'
        result = suggest_fixes(content)
        self.assertGreater(result['fix_count'], 0)
        fix = result['fixes'][0]
        self.assertEqual(fix['type'], 'level_change')
        self.assertIn('##', fix['suggested'])  # H2로 변경
        self.assertTrue(fix['auto_fixable'])

    def test_duplicate_h1_fix(self):
        """중복 H1에 H2 변경 제안"""
        content = '# 제목 1\n\n본문.\n\n# 제목 2\n\n내용.\n'
        result = suggest_fixes(content)
        h1_fixes = [f for f in result['fixes'] if f['reason'].startswith('H1 중복')]
        self.assertGreater(len(h1_fixes), 0)
        self.assertIn('##', h1_fixes[0]['suggested'])

    def test_empty_section_not_auto_fixable(self):
        """빈 섹션은 자동 수정 불가"""
        content = '# 제목\n\n본문.\n\n## 빈 섹션\n## 다음\n\n내용.\n'
        result = suggest_fixes(content)
        empty_fixes = [f for f in result['fixes'] if f['type'] == 'content_needed']
        self.assertGreater(len(empty_fixes), 0)
        self.assertFalse(empty_fixes[0]['auto_fixable'])

    def test_deep_nesting_fix(self):
        """깊은 헤딩에 H4 축소 제안"""
        content = '# 제목\n\n본문.\n\n## H2\n\n본문.\n\n### H3\n\n본문.\n\n#### H4\n\n본문.\n\n##### 깊은 헤딩\n\n내용.\n'
        result = suggest_fixes(content)
        deep_fixes = [f for f in result['fixes'] if 'H4' in f['reason']]
        self.assertGreater(len(deep_fixes), 0)
        self.assertTrue(deep_fixes[0]['auto_fixable'])

    def test_auto_fixable_count(self):
        """auto_fixable_count 정확성"""
        content = '# 제목\n\n본문.\n\n### 건너뛰기\n\n내용.\n\n## 빈 섹션\n## 다음\n\n내용.\n'
        result = suggest_fixes(content)
        auto = sum(1 for f in result['fixes'] if f['auto_fixable'])
        self.assertEqual(result['auto_fixable_count'], auto)


if __name__ == '__main__':
    unittest.main()
