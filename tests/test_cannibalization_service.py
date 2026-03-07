"""cannibalization_service 단위 테스트"""
import unittest

from services.cannibalization_service import (
    detect_cannibalization,
    check_pair,
    _extract_keywords,
)


class TestDetectCannibalization(unittest.TestCase):

    def test_empty_input(self):
        result = detect_cannibalization([])
        self.assertEqual(result['total_conflicts'], 0)

    def test_single_content(self):
        result = detect_cannibalization([{'id': '1', 'title': 'test', 'content': 'test'}])
        self.assertEqual(result['total_conflicts'], 0)
        self.assertIn('최소 2개', result['summary'])

    def test_no_conflict(self):
        contents = [
            {'id': '1', 'title': '파이썬 가이드', 'content': '파이썬은 프로그래밍 언어입니다. 파이썬 문법은 간결합니다. 파이썬 생태계가 풍부합니다.'},
            {'id': '2', 'title': '요리 레시피', 'content': '오늘의 요리는 김치찌개입니다. 요리 재료를 준비합니다. 요리 시간은 30분입니다.'},
        ]
        result = detect_cannibalization(contents)
        # 전혀 다른 주제이므로 높은 충돌은 없어야 함
        high_conflicts = [c for c in result['conflicts'] if c['severity'] == 'high']
        self.assertEqual(len(high_conflicts), 0)

    def test_detects_conflict(self):
        shared_text = '인공지능 머신러닝 딥러닝 자연어처리 신경망 학습 모델 데이터 '
        contents = [
            {'id': '1', 'title': '인공지능 입문', 'content': (shared_text * 5) + '인공지능 기초를 배웁니다.'},
            {'id': '2', 'title': '인공지능 심화', 'content': (shared_text * 5) + '인공지능 고급 과정입니다.'},
        ]
        result = detect_cannibalization(contents)
        self.assertGreater(result['total_conflicts'], 0)

    def test_conflict_has_suggestion(self):
        shared = '파이썬 개발 프로그래밍 코딩 소프트웨어 ' * 4
        contents = [
            {'id': 'a', 'title': '파이썬 기초', 'content': shared},
            {'id': 'b', 'title': '파이썬 입문', 'content': shared},
        ]
        result = detect_cannibalization(contents)
        for conflict in result['conflicts']:
            self.assertIn('suggestion', conflict)
            self.assertIn('severity', conflict)


class TestCheckPair(unittest.TestCase):

    def test_empty_content(self):
        result = check_pair('', 'content')
        self.assertFalse(result['is_cannibalized'])
        self.assertEqual(result['similarity_score'], 0.0)

    def test_similar_content(self):
        text = '파이썬 프로그래밍 개발 가이드 튜토리얼 학습 코딩 입문 기초'
        result = check_pair(text, text)
        self.assertGreater(result['similarity_score'], 0.5)
        self.assertTrue(result['is_cannibalized'])

    def test_different_content(self):
        a = '파이썬 프로그래밍 개발 가이드 튜토리얼'
        b = '맛있는 김치찌개 요리 레시피 재료 준비'
        result = check_pair(a, b)
        self.assertLess(result['similarity_score'], 0.3)

    def test_shared_keywords_returned(self):
        text = '인공지능 머신러닝 딥러닝 데이터 분석'
        result = check_pair(text, text)
        self.assertIsInstance(result['shared_keywords'], list)


class TestExtractKeywords(unittest.TestCase):

    def test_extracts_keywords(self):
        keywords = _extract_keywords('파이썬 프로그래밍 개발 가이드')
        self.assertIn('파이썬', keywords)
        self.assertIn('프로그래밍', keywords)

    def test_filters_stopwords(self):
        keywords = _extract_keywords('이것은 매우 좋은 것이다')
        self.assertNotIn('이것', keywords)
        self.assertNotIn('매우', keywords)

    def test_empty_text(self):
        keywords = _extract_keywords('')
        self.assertEqual(len(keywords), 0)


if __name__ == '__main__':
    unittest.main()
