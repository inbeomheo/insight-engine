"""Clause Overload Detector 서비스 단위 테스트"""
import unittest
from services.clause_overload_service import detect_clause_overload


class TestClauseOverloadService(unittest.TestCase):

    def test_empty_content(self):
        """빈 콘텐츠 입력"""
        result = detect_clause_overload('')
        self.assertEqual(result['overloaded_sentences'], [])
        self.assertEqual(result['summary']['total_sentences'], 0)
        self.assertEqual(result['score'], 100.0)
        result_none = detect_clause_overload(None)
        self.assertEqual(result_none['overloaded_sentences'], [])

    def test_simple_sentences(self):
        """간단한 문장 — 과부하 없음"""
        content = '오늘 날씨가 좋다. 하늘이 파랗다. 바람이 분다.'
        result = detect_clause_overload(content)
        self.assertEqual(result['summary']['overloaded'], 0)
        self.assertEqual(result['score'], 100.0)

    def test_korean_clause_detection(self):
        """한국어 절 표지 감지"""
        content = '날씨가 좋고 바람이 불며 하늘은 맑지만 비가 올 수도 있다.'
        result = detect_clause_overload(content)
        self.assertGreater(result['summary']['overloaded'], 0)
        overloaded = result['overloaded_sentences'][0]
        self.assertGreaterEqual(overloaded['clause_count'], 3)

    def test_english_clause_detection(self):
        """영어 접속사 기반 절 감지"""
        content = 'The system processes data and it handles requests but sometimes it fails because of high load.'
        result = detect_clause_overload(content)
        self.assertGreater(result['summary']['overloaded'], 0)

    def test_comma_based_clauses(self):
        """쉼표 기반 절 분리"""
        content = '첫째, 설계를 하고, 둘째, 구현을 하고, 셋째, 테스트를 한다.'
        result = detect_clause_overload(content)
        self.assertGreater(result['summary']['overloaded'], 0)

    def test_severity_medium(self):
        """3절 문장 — medium 심각도"""
        content = '코드를 작성하고 테스트를 실행하며 결과를 확인한다.'
        result = detect_clause_overload(content)
        if result['overloaded_sentences']:
            self.assertEqual(result['overloaded_sentences'][0]['severity'], 'medium')

    def test_severity_high(self):
        """4절+ 문장 — high 심각도"""
        content = '코드를 작성하고 테스트를 실행하며 결과를 확인하지만 버그가 있으면 다시 수정해야 하므로 시간이 걸린다.'
        result = detect_clause_overload(content)
        high = [s for s in result['overloaded_sentences'] if s['severity'] == 'high']
        self.assertGreater(len(high), 0)

    def test_clause_count_accuracy(self):
        """절 수 정확도"""
        content = '날씨가 좋고 기분이 좋다.'
        result = detect_clause_overload(content)
        # 2절(~고 + 주절) — 과부하 아님
        self.assertEqual(result['summary']['overloaded'], 0)

    def test_score_range(self):
        """점수가 0-100 범위"""
        content = '간단한 문장이다.'
        result = detect_clause_overload(content)
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)

    def test_avg_clauses(self):
        """평균 절 수 계산"""
        content = '간단한 문장이다. 또 하나의 문장이다.'
        result = detect_clause_overload(content)
        self.assertGreater(result['summary']['avg_clauses'], 0)
        self.assertIsInstance(result['summary']['avg_clauses'], float)

    def test_suggestions(self):
        """제안 생성"""
        content = '코드를 작성하고 테스트를 실행하며 결과를 확인하지만 버그가 있다.'
        result = detect_clause_overload(content)
        self.assertIsInstance(result['suggestions'], list)

    def test_return_structure(self):
        """반환값 구조 검증"""
        result = detect_clause_overload('테스트 문장이다.')
        self.assertIn('overloaded_sentences', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_sentences', result['summary'])
        self.assertIn('overloaded', result['summary'])
        self.assertIn('avg_clauses', result['summary'])

    def test_markers_list(self):
        """과부하 문장의 markers 목록 반환"""
        content = '코드를 작성하고 테스트를 실행하며 결과를 확인한다.'
        result = detect_clause_overload(content)
        if result['overloaded_sentences']:
            markers = result['overloaded_sentences'][0]['markers']
            self.assertIsInstance(markers, list)
            self.assertGreater(len(markers), 0)


if __name__ == '__main__':
    unittest.main()
