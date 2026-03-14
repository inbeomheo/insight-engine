"""Emoji Usage Analyzer 서비스 테스트."""
import unittest
from services.analysis.emoji_usage_analyzer_service import analyze_emoji_usage


class TestEmojiUsageAnalyzer(unittest.TestCase):

    def test_empty_content(self):
        result = analyze_emoji_usage('')
        self.assertEqual(result['summary']['total_emojis'], 0)
        self.assertEqual(result['score'], 100.0)

    def test_none_content(self):
        result = analyze_emoji_usage(None)
        self.assertEqual(result['summary']['total_emojis'], 0)

    def test_no_emoji(self):
        content = '이 글에는 이모지가 전혀 없습니다. 순수한 텍스트만 있습니다.'
        result = analyze_emoji_usage(content)
        self.assertEqual(result['summary']['total_emojis'], 0)
        self.assertEqual(result['summary']['level'], 'none')

    def test_single_emoji(self):
        content = '오늘 날씨가 좋습니다 \U0001F600 정말 기분이 좋네요.'
        result = analyze_emoji_usage(content)
        self.assertGreaterEqual(result['summary']['total_emojis'], 1)

    def test_multiple_emojis(self):
        content = '\U0001F600 안녕하세요! \U0001F44D 좋은 하루 되세요! \U0001F389 축하합니다!'
        result = analyze_emoji_usage(content)
        self.assertGreaterEqual(result['summary']['total_emojis'], 3)
        self.assertGreaterEqual(result['summary']['unique_emojis'], 3)

    def test_repeated_emoji(self):
        content = '\U0001F600 좋아요 \U0001F600 정말 \U0001F600 너무 좋아요'
        result = analyze_emoji_usage(content)
        self.assertGreaterEqual(result['summary']['total_emojis'], 3)
        self.assertEqual(result['summary']['unique_emojis'], 1)

    def test_emoji_in_heading(self):
        content = '# \U0001F4DD 제목입니다\n이것은 본문입니다.'
        result = analyze_emoji_usage(content)
        self.assertGreaterEqual(result['summary']['in_headings'], 1)

    def test_emoji_density(self):
        content = '\U0001F600 단어1 단어2 단어3 단어4 단어5 단어6 단어7 단어8 단어9 단어10'
        result = analyze_emoji_usage(content)
        self.assertGreater(result['summary']['emoji_density'], 0.0)

    def test_excessive_emoji(self):
        # 이모지 과다 사용
        emojis = ' '.join(['\U0001F600'] * 20)
        content = f'{emojis} 단어1 단어2 단어3 단어4 단어5'
        result = analyze_emoji_usage(content)
        self.assertEqual(result['summary']['level'], 'excessive')
        self.assertLess(result['score'], 80.0)

    def test_score_range(self):
        content = '일반적인 콘텐츠입니다 \U0001F44D.'
        result = analyze_emoji_usage(content)
        self.assertGreaterEqual(result['score'], 0.0)
        self.assertLessEqual(result['score'], 100.0)

    def test_return_structure(self):
        content = '\U0001F600 구조 확인입니다.'
        result = analyze_emoji_usage(content)
        self.assertIn('emoji_list', result)
        self.assertIn('summary', result)
        self.assertIn('score', result)
        self.assertIn('suggestions', result)
        self.assertIn('total_emojis', result['summary'])
        self.assertIn('unique_emojis', result['summary'])
        self.assertIn('emoji_density', result['summary'])
        self.assertIn('level', result['summary'])
        self.assertIn('in_headings', result['summary'])
        self.assertIn('in_body', result['summary'])

    def test_emoji_list_structure(self):
        content = '\U0001F600 좋아요 \U0001F44D 최고 \U0001F389 축하'
        result = analyze_emoji_usage(content)
        for item in result['emoji_list']:
            self.assertIn('emoji', item)
            self.assertIn('count', item)

    def test_emoji_list_max_20(self):
        # 고유 이모지 20개 초과 시 상위 20개만
        emojis_chars = [chr(0x1F600 + i) for i in range(25)]
        content = ' '.join([f'{e} 단어' for e in emojis_chars])
        result = analyze_emoji_usage(content)
        self.assertLessEqual(len(result['emoji_list']), 20)

    def test_suggestions_for_excessive(self):
        emojis = ' '.join(['\U0001F600'] * 15)
        content = f'{emojis} 단어1 단어2 단어3'
        result = analyze_emoji_usage(content)
        self.assertGreater(len(result['suggestions']), 0)

    def test_suggestion_no_heading_emoji(self):
        # 본문에만 이모지, 제목에는 없음
        content = '# 제목입니다\n본문에 \U0001F600 이모지가 있습니다.'
        result = analyze_emoji_usage(content)
        has_heading_suggestion = any('제목' in s for s in result['suggestions'])
        self.assertTrue(has_heading_suggestion)


if __name__ == '__main__':
    unittest.main()
