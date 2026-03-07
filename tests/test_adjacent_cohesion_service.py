"""Adjacent Paragraph Cohesion Analyzer 서비스 테스트."""
import unittest
from services.adjacent_cohesion_service import analyze_adjacent_cohesion


class TestAdjacentCohesion(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_adjacent_cohesion('')
        self.assertEqual(result['score'], 100.0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_none_content(self):
        result = analyze_adjacent_cohesion(None)
        self.assertEqual(result['score'], 100.0)

    def test_single_paragraph(self):
        content = '하나의 문단만 있는 경우 인접 쌍이 없습니다.'
        result = analyze_adjacent_cohesion(content)
        self.assertEqual(result['summary']['total_pairs'], 0)

    def test_cohesive_paragraphs(self):
        content = ('데이터베이스 인덱스를 생성합니다. '
                   '데이터베이스 성능이 향상됩니다.\n\n'
                   '데이터베이스 쿼리를 최적화합니다. '
                   '데이터베이스 응답 시간이 줄어듭니다.')
        result = analyze_adjacent_cohesion(content)
        self.assertEqual(result['summary']['weak_pairs'], 0)

    def test_weak_cohesion(self):
        content = ('서버 인프라를 구축합니다. '
                   '서버 모니터링을 설정합니다.\n\n'
                   '오늘 점심 메뉴를 정합니다. '
                   '맛있는 음식을 먹었습니다.')
        result = analyze_adjacent_cohesion(content)
        self.assertGreater(result['summary']['weak_pairs'], 0)

    def test_transition_word_bonus(self):
        content = ('첫 번째 주제를 설명합니다. '
                   '상세한 내용을 다룹니다.\n\n'
                   '따라서 두 번째 결론에 도달합니다. '
                   '종합적인 분석을 마칩니다.')
        result = analyze_adjacent_cohesion(content)
        details = result['pair_details']
        if details:
            self.assertTrue(details[0]['has_transition'])

    def test_multiple_pairs(self):
        content = ('문단 하나입니다. 충분한 길이의 문장입니다.\n\n'
                   '문단 둘입니다. 역시 충분한 길이입니다.\n\n'
                   '문단 셋입니다. 마지막 충분한 문장입니다.')
        result = analyze_adjacent_cohesion(content)
        self.assertEqual(result['summary']['total_pairs'], 2)

    def test_avg_cohesion(self):
        content = ('파이썬 프로그래밍을 배웁니다. '
                   '파이썬 변수를 선언합니다.\n\n'
                   '파이썬 함수를 정의합니다. '
                   '파이썬 클래스를 만듭니다.')
        result = analyze_adjacent_cohesion(content)
        self.assertGreater(result['summary']['avg_cohesion'], 0)

    def test_score_range(self):
        content = '충분히 긴 문장으로 구성된 일반 콘텐츠입니다.'
        result = analyze_adjacent_cohesion(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '구조 확인을 위한 충분히 긴 콘텐츠입니다.'
        result = analyze_adjacent_cohesion(content)
        self.assertIn('score', result)
        self.assertIn('summary', result)
        self.assertIn('pair_details', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_pairs', result['summary'])
        self.assertIn('weak_pairs', result['summary'])
        self.assertIn('avg_cohesion', result['summary'])
        self.assertIn('level', result['summary'])

    def test_suggestions_for_weak(self):
        content = ('서버 설정을 완료합니다. '
                   '서버를 구축하고 관리합니다.\n\n'
                   '맛있는 요리 레시피를 소개합니다. '
                   '재료를 준비하고 조리합니다.')
        result = analyze_adjacent_cohesion(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_english_paragraphs(self):
        content = ('Database optimization is important. '
                   'Database indexes improve performance.\n\n'
                   'Furthermore, database caching reduces latency. '
                   'Database monitoring helps identify issues.')
        result = analyze_adjacent_cohesion(content)
        self.assertGreater(result['summary']['total_pairs'], 0)

    def test_heading_excluded(self):
        content = '# 제목은 제외됩니다\n\n본문이 여기에 있습니다.'
        result = analyze_adjacent_cohesion(content)
        # 제목은 문단으로 카운트되지 않음
        self.assertEqual(result['summary']['total_pairs'], 0)


if __name__ == '__main__':
    unittest.main()
