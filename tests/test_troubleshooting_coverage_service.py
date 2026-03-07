"""Troubleshooting Coverage Analyzer 서비스 테스트."""
import unittest
from services.troubleshooting_coverage_service import analyze_troubleshooting_coverage


class TestTroubleshootingCoverage(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_troubleshooting_coverage('')
        self.assertEqual(result['score'], 100.0)
        self.assertFalse(result['summary']['is_guide_content'])

    def test_none_content(self):
        result = analyze_troubleshooting_coverage(None)
        self.assertEqual(result['score'], 100.0)

    def test_non_guide(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다.'
        result = analyze_troubleshooting_coverage(content)
        self.assertEqual(result['summary']['level'], 'none')

    def test_guide_without_troubleshooting(self):
        content = ('튜토리얼 시작합니다. 단계별 가이드를 따라하세요. '
                   '설치가 완료되었습니다.')
        result = analyze_troubleshooting_coverage(content)
        self.assertTrue(result['summary']['is_guide_content'])
        self.assertEqual(result['summary']['level'], 'missing')

    def test_with_error_handling(self):
        content = ('설치 가이드 튜토리얼입니다. '
                   '에러가 발생하면 다음을 확인하세요. '
                   '문제 해결 방법을 안내합니다.')
        result = analyze_troubleshooting_coverage(content)
        self.assertIn('error_handling', result['summary']['categories_found'])

    def test_with_validation(self):
        content = ('배포 가이드를 따라하세요. 설정 튜토리얼입니다. '
                   '설치 후 확인 방법: 정상 작동하는지 테스트하세요.')
        result = analyze_troubleshooting_coverage(content)
        self.assertIn('validation', result['summary']['categories_found'])

    def test_with_rollback(self):
        content = ('서버 설정 가이드 튜토리얼입니다. '
                   '문제가 생기면 롤백하세요. '
                   '이전 상태로 복구하는 방법입니다.')
        result = analyze_troubleshooting_coverage(content)
        self.assertIn('rollback', result['summary']['categories_found'])

    def test_with_faq(self):
        content = ('개발 환경 가이드 튜토리얼입니다. '
                   '## FAQ\n'
                   'Q: 설치가 안 됩니다.\n'
                   'A: 버전을 확인하세요.')
        result = analyze_troubleshooting_coverage(content)
        self.assertIn('faq', result['summary']['categories_found'])

    def test_with_workaround(self):
        content = ('데이터베이스 설정 가이드 튜토리얼입니다. '
                   '안 되면 대안으로 다른 방법을 사용하세요. '
                   '우회 방법도 있습니다.')
        result = analyze_troubleshooting_coverage(content)
        self.assertIn('workaround', result['summary']['categories_found'])

    def test_comprehensive_coverage(self):
        content = ('# 서버 구축 가이드\n'
                   '단계별 튜토리얼입니다.\n'
                   '에러 발생 시 문제 해결 방법.\n'
                   '확인 방법: 정상 작동 테스트.\n'
                   '롤백: 이전 상태로 복구.\n'
                   '## FAQ\n자주 묻는 질문입니다.\n'
                   '대안이 필요하면 우회 방법을 사용하세요.')
        result = analyze_troubleshooting_coverage(content)
        self.assertIn(result['summary']['level'], ('comprehensive', 'good'))

    def test_troubleshooting_section_heading(self):
        content = ('설치 가이드 튜토리얼입니다.\n'
                   '## 문제 해결\n'
                   '에러가 나면 로그를 확인하세요.')
        result = analyze_troubleshooting_coverage(content)
        self.assertTrue(result['summary']['has_troubleshooting_section'])

    def test_score_range(self):
        content = '일반적인 가이드 콘텐츠입니다.'
        result = analyze_troubleshooting_coverage(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 가이드 튜토리얼 테스트입니다.'
        result = analyze_troubleshooting_coverage(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('missing_categories', result)
        self.assertIn('suggestions', result)
        self.assertIn('is_guide_content', result['summary'])
        self.assertIn('has_troubleshooting_section', result['summary'])
        self.assertIn('categories_found', result['summary'])
        self.assertIn('categories_missing', result['summary'])
        self.assertIn('coverage_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_exist(self):
        content = ('설치 가이드를 시작합니다. 단계별 튜토리얼입니다. '
                   '설치 완료.')
        result = analyze_troubleshooting_coverage(content)
        self.assertGreater(len(result['suggestions']), 0)


if __name__ == '__main__':
    unittest.main()
