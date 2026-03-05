"""timeline_service 단위 테스트"""
import unittest

from services.timeline_service import generate_timeline


class TestGenerateTimeline(unittest.TestCase):

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            generate_timeline([])

    def test_missing_title_raises(self):
        with self.assertRaises(ValueError):
            generate_timeline([{'date': '2024-01'}])

    def test_basic_generation(self):
        events = [
            {'date': '2024-01', 'title': 'Launch', 'description': 'Product launched'},
            {'date': '2024-06', 'title': 'Update', 'description': 'Major update'},
        ]
        html = generate_timeline(events)
        self.assertIn('<!DOCTYPE html>', html)
        self.assertIn('Launch', html)
        self.assertIn('Update', html)
        self.assertIn('2024-01', html)

    def test_alternating_sides(self):
        events = [
            {'title': 'A'},
            {'title': 'B'},
            {'title': 'C'},
        ]
        html = generate_timeline(events)
        self.assertIn('tl-left', html)
        self.assertIn('tl-right', html)

    def test_optional_description(self):
        events = [{'title': 'Only title'}]
        html = generate_timeline(events)
        self.assertIn('Only title', html)
        # description이 없으면 tl-desc <p> 태그가 생성되지 않음 (CSS 정의는 존재)
        self.assertNotIn('<p class="tl-desc">', html)


if __name__ == '__main__':
    unittest.main()
