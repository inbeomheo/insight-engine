"""paragraph_balance_service 단위 테스트"""
import unittest

from services.paragraph_balance_service import (
    analyze_balance,
)


class TestAnalyzeBalance(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_balance('')
        self.assertEqual(result['paragraphs'], [])
        self.assertEqual(result['balance_score'], 0)

    def test_none_content(self):
        result = analyze_balance(None)
        self.assertEqual(result['stats']['count'], 0)

    def test_single_paragraph(self):
        result = analyze_balance('단일 문단 콘텐츠입니다. 여러 문장을 포함합니다.')
        self.assertEqual(result['stats']['count'], 1)

    def test_balanced_paragraphs(self):
        p1 = '파이썬은 간결한 프로그래밍 언어입니다. 초보자도 쉽게 배울 수 있으며 다양한 분야에 활용됩니다. 데이터 과학에서 웹 개발까지 폭넓게 사용됩니다.'
        p2 = '자바스크립트는 웹 개발의 핵심 언어입니다. 프론트엔드와 백엔드 모두 지원하며 React와 Node 생태계가 강력합니다. 현대 웹의 필수 기술입니다.'
        content = f'{p1}\n\n{p2}'
        result = analyze_balance(content)
        self.assertEqual(result['stats']['count'], 2)
        self.assertGreater(result['balance_score'], 50)

    def test_too_short_paragraph(self):
        content = '짧음.\n\n' + '적절한 길이의 문단으로 다양한 내용을 담고 있습니다. 충분한 설명과 예시를 포함하고 있어 독자가 이해하기 쉽습니다.'
        result = analyze_balance(content)
        short_issues = [i for i in result['issues'] if i['type'] == 'too_short']
        self.assertGreater(len(short_issues), 0)

    def test_too_long_paragraph(self):
        long_para = '매우 긴 문단입니다. ' * 50  # 500자+
        short_para = '짧은 문단입니다. 여기에 적절한 내용을 포함합니다.'
        content = f'{long_para}\n\n{short_para}'
        result = analyze_balance(content)
        long_issues = [i for i in result['issues'] if i['type'] == 'too_long']
        self.assertGreater(len(long_issues), 0)

    def test_stats_calculation(self):
        p1 = '첫 번째 문단의 내용입니다. 다양한 정보를 포함하고 있습니다.'
        p2 = '두 번째 문단은 조금 더 깁니다. 추가적인 설명과 예시를 포함하며 더 자세한 내용을 다룹니다.'
        content = f'{p1}\n\n{p2}'
        result = analyze_balance(content)
        stats = result['stats']
        self.assertGreater(stats['avg_length'], 0)
        self.assertGreaterEqual(stats['max_length'], stats['min_length'])
        self.assertGreaterEqual(stats['std_dev'], 0)

    def test_score_bounded(self):
        content = '문단 하나.\n\n문단 둘.'
        result = analyze_balance(content)
        self.assertGreaterEqual(result['balance_score'], 0)
        self.assertLessEqual(result['balance_score'], 100)

    def test_suggestions_exist(self):
        result = analyze_balance('짧은 글.')
        self.assertIsInstance(result['suggestions'], list)
        self.assertGreater(len(result['suggestions']), 0)

    def test_paragraph_preview(self):
        content = '이것은 첫 번째 문단입니다. 미리보기가 표시됩니다.\n\n두 번째 문단의 내용입니다.'
        result = analyze_balance(content)
        for p in result['paragraphs']:
            self.assertIn('preview', p)
            self.assertIn('status', p)

    def test_markdown_heading_stripped(self):
        content = '## 제목\n\n본문 내용이 여기에 있습니다. 충분한 길이의 문단입니다.\n\n### 소제목\n\n두 번째 본문 문단입니다. 역시 적절한 길이입니다.'
        result = analyze_balance(content)
        # 헤딩이 문단 길이에 포함되지 않아야 함
        for p in result['paragraphs']:
            self.assertNotIn('##', p['preview'])


if __name__ == '__main__':
    unittest.main()
