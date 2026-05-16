"""stats_aggregator_service 단위 테스트"""
import unittest

from services.content.stats_aggregator_service import (
    aggregate_stats,
    _content_stats,
)


class TestAggregateStats(unittest.TestCase):

    def test_empty_list(self):
        result = aggregate_stats([])
        self.assertEqual(result['summary']['total_contents'], 0)

    def test_single_content(self):
        contents = [{'content': '테스트 콘텐츠입니다. ' * 10, 'title': 'T1', 'style': 'blog'}]
        result = aggregate_stats(contents)
        self.assertEqual(result['summary']['total_contents'], 1)
        self.assertGreater(result['summary']['total_words'], 0)

    def test_multiple_contents(self):
        contents = [
            {'content': '짧은 글', 'title': 'A', 'style': 'blog'},
            {'content': '긴 글입니다. ' * 50, 'title': 'B', 'style': 'tutorial'},
            {'content': '중간 글. ' * 20, 'title': 'C', 'style': 'blog'},
        ]
        result = aggregate_stats(contents)
        self.assertEqual(result['summary']['total_contents'], 3)
        self.assertEqual(len(result['per_content']), 3)

    def test_avg_words(self):
        contents = [
            {'content': '단어 ' * 100, 'title': 'A'},
            {'content': '단어 ' * 200, 'title': 'B'},
        ]
        result = aggregate_stats(contents)
        self.assertGreater(result['summary']['avg_words'], 0)

    def test_style_distribution(self):
        contents = [
            {'content': '내용', 'style': 'blog'},
            {'content': '내용', 'style': 'blog'},
            {'content': '내용', 'style': 'tutorial'},
        ]
        result = aggregate_stats(contents)
        self.assertEqual(result['style_distribution']['blog'], 2)
        self.assertEqual(result['style_distribution']['tutorial'], 1)

    def test_length_distribution(self):
        contents = [
            {'content': '짧음', 'title': 'S'},
            {'content': '중간길이 단어 ' * 100, 'title': 'M'},
            {'content': '긴글작성 ' * 500, 'title': 'L'},
        ]
        result = aggregate_stats(contents)
        dist = result['length_distribution']
        # short < 200 words
        self.assertGreaterEqual(dist['short'], 1)

    def test_per_content_details(self):
        contents = [{'content': '# 제목\n테스트 내용입니다.', 'title': 'T1', 'style': 'blog'}]
        result = aggregate_stats(contents)
        item = result['per_content'][0]
        self.assertEqual(item['title'], 'T1')
        self.assertEqual(item['style'], 'blog')
        self.assertIn('word_count', item)
        self.assertIn('reading_minutes', item)

    def test_total_reading_minutes(self):
        contents = [
            {'content': '한국어 ' * 250, 'title': 'A'},
            {'content': '한국어 ' * 250, 'title': 'B'},
        ]
        result = aggregate_stats(contents)
        self.assertGreater(result['summary']['total_reading_minutes'], 0)

    def test_empty_content_handled(self):
        contents = [
            {'content': '', 'title': 'Empty'},
            {'content': '유효한 콘텐츠입니다.', 'title': 'Valid'},
        ]
        result = aggregate_stats(contents)
        self.assertEqual(result['summary']['total_contents'], 2)

    def test_missing_style_defaults(self):
        contents = [{'content': '내용', 'title': 'T1'}]
        result = aggregate_stats(contents)
        self.assertEqual(result['style_distribution']['unknown'], 1)


class TestContentStats(unittest.TestCase):

    def test_empty(self):
        stats = _content_stats('')
        self.assertEqual(stats['word_count'], 0)

    def test_none(self):
        stats = _content_stats(None)
        self.assertEqual(stats['word_count'], 0)

    def test_basic_stats(self):
        stats = _content_stats('# 제목\n한국어 콘텐츠입니다.')
        self.assertGreater(stats['word_count'], 0)
        self.assertGreater(stats['char_count'], 0)
        self.assertEqual(stats['heading_count'], 1)

    def test_reading_minutes(self):
        stats = _content_stats('한국어 ' * 500)
        self.assertGreater(stats['reading_minutes'], 0)


if __name__ == '__main__':
    unittest.main()
