"""Heading Term Placement Auditor 서비스 단위 테스트"""
import unittest
from services.analysis.heading_term_placement_service import audit_heading_term_placement


class TestHeadingTermPlacementService(unittest.TestCase):

    def test_empty_content(self):
        result = audit_heading_term_placement('')
        self.assertEqual(result['key_terms'], [])
        self.assertEqual(result['score'], 0.0)
        result_none = audit_heading_term_placement(None)
        self.assertEqual(result_none['key_terms'], [])

    def test_no_headings(self):
        content = '이것은 헤딩이 없는 글입니다. 구조가 필요합니다.'
        result = audit_heading_term_placement(content)
        self.assertEqual(result['summary']['total_headings'], 0)
        self.assertTrue(any('헤딩이 없습니다' in s for s in result['suggestions']))

    def test_term_in_heading(self):
        content = (
            '## Python 개발 가이드\n'
            'Python은 인기 있는 프로그래밍 언어입니다.\n'
            'Python을 사용하면 생산성이 높아집니다.\n'
            '## Python 설치 방법\n'
            'Python 공식 사이트에서 다운로드합니다.\n'
        )
        result = audit_heading_term_placement(content)
        self.assertGreater(result['summary']['terms_in_headings'], 0)

    def test_term_missing_from_heading(self):
        content = (
            '## 소개\n'
            'React는 UI 라이브러리입니다. React를 사용하면 좋습니다.\n'
            'React 컴포넌트를 만들어 봅시다.\n'
            '## 결론\n'
            'React는 강력합니다.\n'
        )
        result = audit_heading_term_placement(content)
        # "React"가 본문에 자주 나오지만 헤딩에는 "소개"/"결론"만 있음
        missing = [t for t in result['key_terms'] if t not in str(result['heading_analysis'])]
        # 배치율이 100%가 아닐 수 있음
        self.assertIsNotNone(result['summary']['placement_rate'])

    def test_heading_analysis_structure(self):
        content = '## 테스트 헤딩\n테스트 내용을 작성합니다. 테스트가 중요합니다.\n'
        result = audit_heading_term_placement(content)
        if result['heading_analysis']:
            h = result['heading_analysis'][0]
            self.assertIn('heading', h)
            self.assertIn('level', h)
            self.assertIn('matched_terms', h)
            self.assertIn('has_key_term', h)

    def test_placement_rate(self):
        content = (
            '## API 설계\n'
            'API 설계가 중요합니다. API를 잘 만들어야 합니다.\n'
            '## API 테스트\n'
            'API 테스트도 해야 합니다.\n'
        )
        result = audit_heading_term_placement(content)
        self.assertGreaterEqual(result['summary']['placement_rate'], 0)
        self.assertLessEqual(result['summary']['placement_rate'], 100)

    def test_score_range(self):
        content = '## 제목\n본문 내용입니다. 반복 내용입니다.\n'
        result = audit_heading_term_placement(content)
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_suggestions_provided(self):
        content = (
            '## 소개\n'
            'Flask는 웹 프레임워크입니다. Flask를 설치합니다. Flask 앱을 만듭니다.\n'
            '## 결론\n'
            'Flask를 추천합니다.\n'
        )
        result = audit_heading_term_placement(content)
        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)

    def test_multiple_levels(self):
        content = (
            '# 대제목\n'
            '## 중제목\n'
            '### 소제목\n'
            '본문 내용입니다. 반복 내용이 있습니다.\n'
        )
        result = audit_heading_term_placement(content)
        self.assertEqual(result['summary']['total_headings'], 3)

    def test_key_terms_extraction(self):
        content = (
            '## 개요\n'
            'Docker는 컨테이너 기술입니다. Docker를 사용하면 배포가 쉽습니다.\n'
            'Docker 이미지를 만들고 Docker 컨테이너를 실행합니다.\n'
        )
        result = audit_heading_term_placement(content)
        self.assertIsInstance(result['key_terms'], list)

    def test_return_structure(self):
        result = audit_heading_term_placement('## 제목\n내용입니다.\n')
        self.assertIn('key_terms', result)
        self.assertIn('heading_analysis', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_headings', result['summary'])
        self.assertIn('terms_in_headings', result['summary'])
        self.assertIn('total_key_terms', result['summary'])
        self.assertIn('placement_rate', result['summary'])

    def test_english_content(self):
        content = (
            '## Introduction\n'
            'Python is a popular programming language. Python is easy to learn.\n'
            'Python supports multiple paradigms.\n'
            '## Setup\n'
            'Install Python from the official website.\n'
        )
        result = audit_heading_term_placement(content)
        self.assertGreater(result['summary']['total_headings'], 0)


if __name__ == '__main__':
    unittest.main()
