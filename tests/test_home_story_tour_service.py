"""홈스토리 투어 서비스 테스트"""
import unittest
from services.home_story_tour_service import (
    create_tour, add_room, generate_narrative, calculate_stats,
    HomeTour, Room
)


class TestHomeStoryTourService(unittest.TestCase):

    def setUp(self):
        self.rooms_config = [
            {'name': '거실', 'description': '넓은 거실', 'features': ['채광', '수납'], 'area_sqm': 25.0, 'photos': ['a.jpg']},
            {'name': '침실', 'description': '아늑한 침실', 'features': ['채광'], 'area_sqm': 15.0, 'photos': []},
            {'name': '주방', 'description': '모던 주방', 'features': ['수납', '인덕션'], 'area_sqm': 10.0, 'photos': ['b.jpg']},
        ]
        self.tour = create_tour('모던 아파트', self.rooms_config)

    def test_create_tour(self):
        self.assertIsInstance(self.tour, HomeTour)
        self.assertEqual(self.tour.title, '모던 아파트')
        self.assertEqual(len(self.tour.rooms), 3)

    def test_create_tour_total_area(self):
        self.assertEqual(self.tour.total_area, 50.0)

    def test_create_tour_highlights(self):
        # 채광 2회, 수납 2회
        self.assertIn('채광', self.tour.highlights)

    def test_add_room(self):
        updated = add_room(self.tour, {'name': '서재', 'area_sqm': 8.0})
        self.assertEqual(len(updated.rooms), 4)
        self.assertEqual(updated.total_area, 58.0)

    def test_add_room_immutable(self):
        add_room(self.tour, {'name': '새 방', 'area_sqm': 5.0})
        self.assertEqual(len(self.tour.rooms), 3)

    def test_generate_narrative_contains_title(self):
        text = generate_narrative(self.tour)
        self.assertIn('모던 아파트', text)
        self.assertIn('거실', text)

    def test_generate_narrative_contains_area(self):
        text = generate_narrative(self.tour)
        self.assertIn('50.0', text)

    def test_calculate_stats(self):
        stats = calculate_stats(self.tour)
        self.assertEqual(stats['total_area'], 50.0)
        self.assertEqual(stats['room_count'], 3)
        self.assertEqual(stats['feature_frequency']['채광'], 2)

    def test_calculate_stats_avg_area(self):
        stats = calculate_stats(self.tour)
        self.assertAlmostEqual(stats['avg_room_area'], 50.0 / 3, places=2)

    def test_create_tour_empty(self):
        tour = create_tour('빈 집', [])
        self.assertEqual(len(tour.rooms), 0)
        self.assertEqual(tour.total_area, 0.0)

    def test_room_photos(self):
        self.assertEqual(len(self.tour.rooms[0].photos), 1)
        self.assertEqual(len(self.tour.rooms[1].photos), 0)


if __name__ == '__main__':
    unittest.main()
