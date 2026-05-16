"""publish_time_service 단위 테스트"""
import unittest
from services.content.publish_time_service import (
    suggest_publish_time,
    get_platform_options,
    PLATFORM_SCHEDULES,
)


class TestSuggestPublishTime(unittest.TestCase):

    def test_default_blog(self):
        result = suggest_publish_time()
        self.assertGreater(len(result['recommendations']), 0)
        self.assertEqual(result['timezone'], 'KST')

    def test_newsletter(self):
        result = suggest_publish_time(content_type='newsletter')
        self.assertGreater(len(result['recommendations']), 0)
        self.assertTrue(any('뉴스레터' in r['platform'] for r in result['recommendations']))

    def test_multiple_platforms(self):
        result = suggest_publish_time(platforms=['blog', 'sns', 'youtube'])
        self.assertEqual(len(result['recommendations']), 3)

    def test_combined_best(self):
        result = suggest_publish_time(platforms=['blog', 'sns'])
        self.assertGreater(len(result['combined_best']['days']), 0)
        self.assertGreater(len(result['combined_best']['hours']), 0)

    def test_avoid_times(self):
        result = suggest_publish_time(content_type='blog')
        self.assertIn('avoid', result)

    def test_reason_included(self):
        result = suggest_publish_time(content_type='youtube')
        for rec in result['recommendations']:
            self.assertIn('reason', rec)
            self.assertGreater(len(rec['reason']), 0)

    def test_best_slot_format(self):
        result = suggest_publish_time(content_type='blog')
        for rec in result['recommendations']:
            self.assertIn('best_slot', rec)
            self.assertIn('요일', rec['best_slot'])

    def test_all_platforms_valid(self):
        for platform in PLATFORM_SCHEDULES:
            result = suggest_publish_time(content_type=platform)
            self.assertGreater(len(result['recommendations']), 0)

    def test_invalid_platform_fallback(self):
        result = suggest_publish_time(content_type='nonexistent')
        self.assertGreater(len(result['recommendations']), 0)

    def test_custom_timezone(self):
        result = suggest_publish_time(timezone_label='JST')
        self.assertEqual(result['timezone'], 'JST')


class TestGetPlatformOptions(unittest.TestCase):

    def test_returns_all(self):
        options = get_platform_options()
        self.assertEqual(len(options), len(PLATFORM_SCHEDULES))

    def test_structure(self):
        options = get_platform_options()
        for o in options:
            self.assertIn('id', o)
            self.assertIn('label', o)


if __name__ == '__main__':
    unittest.main()
