"""content_grader_service 단위 테스트"""
import unittest
from unittest.mock import patch

from services.content_grader_service import grade_content, _predict_engagement, _score_to_grade


class TestGradeContent(unittest.TestCase):

    def test_empty_content(self):
        result = grade_content('')
        self.assertEqual(result['grade'], 'F')
        self.assertEqual(result['total_score'], 0)
        self.assertIn('콘텐츠가 비어 있습니다.', result['suggestions'])

    def test_none_content(self):
        result = grade_content(None)
        self.assertEqual(result['grade'], 'F')

    def test_short_content(self):
        result = grade_content('짧은 텍스트입니다.')
        self.assertIn(result['grade'], ('C', 'D', 'F'))
        self.assertIsInstance(result['total_score'], int)
        self.assertIn('readability', result['scores'])
        self.assertIn('seo', result['scores'])
        self.assertIn('engagement', result['scores'])

    def test_good_content(self):
        content = """# 파이썬 가이드

## 소개
파이썬은 다양한 분야에서 활용되는 프로그래밍 언어입니다.
초보자도 쉽게 배울 수 있으며, 강력한 생태계를 가지고 있습니다.

## 주요 특징
- 간결한 문법으로 배우기 쉽습니다
- 풍부한 라이브러리를 제공합니다
- 데이터 분석, 웹 개발, AI 등 다양한 분야에 활용됩니다

## 시작하기
파이썬을 시작하려면 공식 사이트에서 설치 파일을 다운로드하세요.
어떤 경험이 있으신가요? 댓글로 알려주세요!

전 세계 개발자의 30%가 파이썬을 주력으로 사용합니다.
"""
        result = grade_content(content)
        self.assertGreaterEqual(result['total_score'], 40)
        self.assertIn(result['grade'], ('A', 'B', 'C', 'D'))
        self.assertTrue(len(result['suggestions']) > 0)
        self.assertIsInstance(result['summary'], str)

    def test_scores_are_bounded(self):
        result = grade_content('테스트 콘텐츠')
        for key, score in result['scores'].items():
            self.assertGreaterEqual(score, 0, f'{key} should be >= 0')
            self.assertLessEqual(score, 100, f'{key} should be <= 100')

    def test_total_score_bounded(self):
        result = grade_content('x' * 5000)
        self.assertGreaterEqual(result['total_score'], 0)
        self.assertLessEqual(result['total_score'], 100)


class TestPredictEngagement(unittest.TestCase):

    def test_questions_boost(self):
        score_with = _predict_engagement('이것은 좋은 방법인가요? 어떻게 생각하세요?')
        score_without = _predict_engagement('이것은 좋은 방법이다.')
        self.assertGreater(score_with, score_without)

    def test_cta_boost(self):
        score = _predict_engagement('여러분의 의견을 댓글로 알려주세요. 구독도 부탁드립니다.')
        self.assertGreater(score, 50)

    def test_numbers_boost(self):
        score = _predict_engagement('매출이 30% 증가했고 사용자 100만명을 돌파했습니다.')
        self.assertGreater(score, 50)


class TestScoreToGrade(unittest.TestCase):

    def test_grade_boundaries(self):
        self.assertEqual(_score_to_grade(95), 'A')
        self.assertEqual(_score_to_grade(90), 'A')
        self.assertEqual(_score_to_grade(80), 'B')
        self.assertEqual(_score_to_grade(75), 'B')
        self.assertEqual(_score_to_grade(60), 'C')
        self.assertEqual(_score_to_grade(40), 'D')
        self.assertEqual(_score_to_grade(39), 'F')
        self.assertEqual(_score_to_grade(0), 'F')


if __name__ == '__main__':
    unittest.main()
