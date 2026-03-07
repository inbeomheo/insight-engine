"""Update Delta Summary Checker 서비스 테스트."""
import unittest
from services.update_delta_summary_service import check_update_delta_summary


class TestUpdateDeltaSummary(unittest.TestCase):

    def test_empty_content(self):
        result = check_update_delta_summary('')
        self.assertEqual(result['score'], 50.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = check_update_delta_summary(None)
        self.assertEqual(result['score'], 50.0)

    def test_no_update_signals(self):
        content = '일반적인 기술 문서입니다. 특별한 업데이트 표시가 없습니다.'
        result = check_update_delta_summary(content)
        self.assertFalse(result['summary']['has_update_date'])
        self.assertFalse(result['summary']['has_delta_summary'])

    def test_with_update_date(self):
        content = '최종 수정: 2024.06.15. 이 문서는 정기적으로 업데이트됩니다.'
        result = check_update_delta_summary(content)
        self.assertTrue(result['summary']['has_update_date'])

    def test_with_delta_summary(self):
        content = ('이번 업데이트 변경 사항입니다. '
                   '새로운 기능이 추가됨. 기존 버그가 수정됨.')
        result = check_update_delta_summary(content)
        self.assertTrue(result['summary']['has_delta_summary'])

    def test_with_delta_heading(self):
        content = ('# 가이드\n내용입니다.\n'
                   '## 변경 사항\n'
                   '최근 업데이트 내용입니다.')
        result = check_update_delta_summary(content)
        self.assertTrue(result['summary']['has_delta_heading'])

    def test_with_version(self):
        content = 'v2.1 릴리스 노트입니다. 버전 2.1에서 변경된 사항을 정리합니다.'
        result = check_update_delta_summary(content)
        self.assertTrue(result['summary']['has_version'])

    def test_comprehensive(self):
        content = ('# 프로젝트 가이드 v3.0\n'
                   '최종 수정: 2024.08.01 업데이트.\n'
                   '## Changelog\n'
                   '변경 사항: 새 기능 추가됨. 성능 개선됨. 버그 수정됨.\n'
                   '이전 버전 대비 속도가 2배 향상되었습니다.')
        result = check_update_delta_summary(content)
        self.assertEqual(result['summary']['level'], 'comprehensive')

    def test_english_changelog(self):
        content = ('Last updated: 2024-06-15. '
                   '## What\'s New\n'
                   'Added: new dashboard feature. '
                   'Changed: improved performance. '
                   'Fixed: login bug.')
        result = check_update_delta_summary(content)
        self.assertTrue(result['summary']['has_update_date'])
        self.assertTrue(result['summary']['has_delta_summary'])

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다.'
        result = check_update_delta_summary(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 테스트입니다.'
        result = check_update_delta_summary(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('update_signals', result)
        self.assertIn('suggestions', result)
        self.assertIn('has_update_date', result['summary'])
        self.assertIn('has_delta_summary', result['summary'])
        self.assertIn('has_delta_heading', result['summary'])
        self.assertIn('has_version', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_exist(self):
        content = '업데이트 표시 없는 긴 문서입니다. ' * 30
        result = check_update_delta_summary(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_partial_level(self):
        content = '최종 수정: 2024.03.20 업데이트된 문서입니다.'
        result = check_update_delta_summary(content)
        self.assertIn(result['summary']['level'], ('partial', 'good'))

    def test_release_notes_pattern(self):
        content = 'Release notes for version 2.0. Added new API. Changed: response format updated.'
        result = check_update_delta_summary(content)
        self.assertTrue(result['summary']['has_delta_summary'])


if __name__ == '__main__':
    unittest.main()
