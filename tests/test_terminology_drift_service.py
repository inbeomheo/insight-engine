"""Terminology Drift Analyzer 서비스 테스트."""
import unittest
from services.terminology_drift_service import analyze_terminology_drift


class TestTerminologyDrift(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_terminology_drift('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = analyze_terminology_drift(None)
        self.assertEqual(result['score'], 100.0)

    def test_single_section(self):
        content = '섹션이 하나뿐인 문서입니다. 제목 없이 본문만 있습니다.'
        result = analyze_terminology_drift(content)
        self.assertEqual(result['summary']['drift_count'], 0)

    def test_consistent_terminology(self):
        content = ('## 사용자 관리\n'
                   '사용자를 추가합니다. 사용자 목록을 확인합니다.\n\n'
                   '## 사용자 권한\n'
                   '사용자에게 권한을 부여합니다. 사용자 역할을 설정합니다.\n')
        result = analyze_terminology_drift(content)
        self.assertEqual(result['summary']['level'], 'consistent')

    def test_drift_detected(self):
        content = ('## 소개\n'
                   '사용자가 로그인합니다. 사용자 계정을 만듭니다.\n\n'
                   '## 기능\n'
                   '유저가 설정을 변경합니다. 유저 프로필을 편집합니다.\n')
        result = analyze_terminology_drift(content)
        self.assertGreater(result['summary']['drift_count'], 0)

    def test_english_drift(self):
        content = ('## Setup\n'
                   'Install the package using npm. Install dependencies first.\n\n'
                   '## Configuration\n'
                   'Configure the settings. Setup the environment variables.\n')
        result = analyze_terminology_drift(content)
        self.assertGreater(result['summary']['drift_count'], 0)

    def test_multiple_drifts(self):
        content = ('## 시작\n'
                   '사용자가 서버에 접속합니다. 함수를 실행합니다.\n\n'
                   '## 사용\n'
                   '유저가 백엔드와 통신합니다. 메서드를 호출합니다.\n')
        result = analyze_terminology_drift(content)
        self.assertGreater(result['summary']['drift_count'], 1)

    def test_score_range(self):
        content = '## 테스트\n일반적인 콘텐츠입니다.\n\n## 결론\n마무리합니다.'
        result = analyze_terminology_drift(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '## 섹션\n구조 확인 테스트입니다.'
        result = analyze_terminology_drift(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('drift_items', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sections', result['summary'])
        self.assertIn('drift_count', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_drift(self):
        content = ('## 시작\n'
                   '사용자가 접속합니다. 사용자를 확인합니다.\n\n'
                   '## 사용\n'
                   '유저가 활동합니다. 유저를 관리합니다.\n')
        result = analyze_terminology_drift(content)
        if result['summary']['drift_count'] > 0:
            self.assertGreater(len(result['suggestions']), 1)

    def test_drift_items_content(self):
        content = ('## 설치\n'
                   '설치를 진행합니다. 설치가 완료되었습니다.\n\n'
                   '## 구성\n'
                   '셋업을 시작합니다. 인스톨 후 확인합니다.\n')
        result = analyze_terminology_drift(content)
        if result['drift_items']:
            item = result['drift_items'][0]
            self.assertIn('terms', item)
            self.assertIn('sections_count', item)

    def test_no_heading_single_block(self):
        content = '제목이 없는 긴 문서입니다. 여러 단락으로 구성되어 있습니다.'
        result = analyze_terminology_drift(content)
        self.assertEqual(result['summary']['level'], 'none')


if __name__ == '__main__':
    unittest.main()
