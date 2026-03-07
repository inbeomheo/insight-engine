"""Prerequisite Disclosure Checker 서비스 테스트."""
import unittest
from services.prerequisite_disclosure_service import check_prerequisite_disclosure


class TestPrerequisiteDisclosure(unittest.TestCase):

    def test_empty_content(self):
        result = check_prerequisite_disclosure('')
        self.assertEqual(result['score'], 100.0)
        self.assertFalse(result['summary']['is_tutorial_content'])

    def test_none_content(self):
        result = check_prerequisite_disclosure(None)
        self.assertEqual(result['score'], 100.0)

    def test_non_tutorial(self):
        content = '오늘 날씨가 좋습니다. 산책을 나갔습니다.'
        result = check_prerequisite_disclosure(content)
        self.assertEqual(result['summary']['level'], 'none')

    def test_tutorial_with_prereqs(self):
        content = ('# Python 웹앱 구축 가이드\n'
                   '## 사전 준비\n'
                   'Python 3.10 이상 버전이 필요합니다. '
                   '계정을 먼저 가입하세요. '
                   '관리자 권한이 필요합니다. '
                   '## 설치 방법\n'
                   '단계별로 따라하기 쉽게 설명합니다.')
        result = check_prerequisite_disclosure(content)
        self.assertTrue(result['summary']['is_tutorial_content'])
        self.assertTrue(result['summary']['has_prereq_section'])
        self.assertGreater(len(result['summary']['prereqs_found']), 0)

    def test_tutorial_without_prereqs(self):
        content = ('튜토리얼입니다. 단계별 가이드를 시작합니다. '
                   '설치 방법을 따라하세요.')
        result = check_prerequisite_disclosure(content)
        self.assertTrue(result['summary']['is_tutorial_content'])

    def test_account_prereq(self):
        content = ('Docker 설치 튜토리얼 가이드입니다. '
                   'Docker Hub 계정이 필요합니다. API 키를 발급받으세요.')
        result = check_prerequisite_disclosure(content)
        self.assertIn('account', result['summary']['prereqs_found'])

    def test_version_prereq(self):
        content = ('Node.js 가이드 튜토리얼입니다. '
                   'Node.js 18 이상 version 필요합니다. '
                   'npm install express로 설치하세요.')
        result = check_prerequisite_disclosure(content)
        self.assertIn('version', result['summary']['prereqs_found'])

    def test_cost_prereq(self):
        content = ('AWS 배포 가이드 튜토리얼입니다. '
                   '월 $10 비용이 발생합니다. 유료 구독이 필요합니다.')
        result = check_prerequisite_disclosure(content)
        self.assertIn('cost', result['summary']['prereqs_found'])

    def test_environment_prereq(self):
        content = ('개발 환경 구축 가이드입니다. 따라하기 쉽습니다. '
                   'Windows 또는 macOS 운영 체제가 필요합니다. '
                   '시스템 요구 사항을 확인하세요.')
        result = check_prerequisite_disclosure(content)
        self.assertIn('environment', result['summary']['prereqs_found'])

    def test_english_tutorial(self):
        content = ('Getting started with React tutorial step by step. '
                   'Prerequisites: Node.js 16+, basic understanding of JavaScript. '
                   'You\'ll need a GitHub account.')
        result = check_prerequisite_disclosure(content)
        self.assertTrue(result['summary']['is_tutorial_content'])
        self.assertGreater(len(result['summary']['prereqs_found']), 0)

    def test_score_range(self):
        content = '일반적인 가이드 콘텐츠입니다.'
        result = check_prerequisite_disclosure(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인 튜토리얼 테스트입니다.'
        result = check_prerequisite_disclosure(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('missing_prereqs', result)
        self.assertIn('suggestions', result)
        self.assertIn('is_tutorial_content', result['summary'])
        self.assertIn('has_prereq_section', result['summary'])
        self.assertIn('prereqs_found', result['summary'])
        self.assertIn('completeness_ratio', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_exist(self):
        content = ('튜토리얼 시작합니다. 가이드를 따라하세요. '
                   '설치 진행합니다.')
        result = check_prerequisite_disclosure(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_knowledge_prereq(self):
        content = ('프로그래밍 가이드 튜토리얼입니다. '
                   '기본 지식이 필요합니다. Python을 이해하고 있어야 합니다.')
        result = check_prerequisite_disclosure(content)
        self.assertIn('knowledge', result['summary']['prereqs_found'])


if __name__ == '__main__':
    unittest.main()
