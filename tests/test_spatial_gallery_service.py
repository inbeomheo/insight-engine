"""공간 갤러리 서비스 테스트"""
import unittest
from services.spatial_gallery_service import (
    create_gallery, place_item, auto_arrange, check_collisions,
    Gallery, GalleryItem
)


class TestSpatialGalleryService(unittest.TestCase):

    def setUp(self):
        self.gallery = create_gallery('전시회', {'width': 10, 'height': 5, 'depth': 10})

    def test_create_gallery(self):
        self.assertIsInstance(self.gallery, Gallery)
        self.assertEqual(self.gallery.title, '전시회')
        self.assertEqual(len(self.gallery.items), 0)

    def test_place_item(self):
        g = place_item(self.gallery, {
            'title': '작품 1', 'content_type': 'image',
            'position_3d': {'x': 1, 'y': 2, 'z': 3}
        })
        self.assertEqual(len(g.items), 1)
        self.assertEqual(g.items[0].title, '작품 1')

    def test_place_item_defaults(self):
        g = place_item(self.gallery, {'title': 'test'})
        self.assertEqual(g.items[0].content_type, 'image')
        self.assertEqual(g.items[0].scale, 1.0)

    def test_auto_arrange_wall(self):
        g = self.gallery
        for i in range(3):
            g = place_item(g, {'title': f'작품 {i}'})
        arranged = auto_arrange(g, 'wall')
        # 벽면 배치: z=0, y=중앙
        for item in arranged.items:
            self.assertEqual(item.position_3d['z'], 0)

    def test_auto_arrange_circular(self):
        g = self.gallery
        for i in range(4):
            g = place_item(g, {'title': f'작품 {i}'})
        arranged = auto_arrange(g, 'circular')
        self.assertEqual(len(arranged.items), 4)

    def test_auto_arrange_floating(self):
        g = self.gallery
        for i in range(3):
            g = place_item(g, {'title': f'작품 {i}'})
        arranged = auto_arrange(g, 'floating')
        # 각 아이템이 다른 rotation을 가짐
        rotations = [item.rotation for item in arranged.items]
        self.assertEqual(len(set(rotations)), 3)

    def test_auto_arrange_empty_gallery(self):
        arranged = auto_arrange(self.gallery, 'wall')
        self.assertEqual(len(arranged.items), 0)

    def test_check_collisions_close(self):
        g = place_item(self.gallery, {'title': 'A', 'position_3d': {'x': 0, 'y': 0, 'z': 0}})
        g = place_item(g, {'title': 'B', 'position_3d': {'x': 0.5, 'y': 0, 'z': 0}})
        collisions = check_collisions(g, 1.0)
        self.assertEqual(len(collisions), 1)

    def test_check_collisions_no_collision(self):
        g = place_item(self.gallery, {'title': 'A', 'position_3d': {'x': 0, 'y': 0, 'z': 0}})
        g = place_item(g, {'title': 'B', 'position_3d': {'x': 5, 'y': 5, 'z': 5}})
        collisions = check_collisions(g, 1.0)
        self.assertEqual(len(collisions), 0)

    def test_place_item_immutable(self):
        place_item(self.gallery, {'title': 'new'})
        self.assertEqual(len(self.gallery.items), 0)

    def test_auto_arrange_unknown_layout(self):
        g = place_item(self.gallery, {'title': 'A'})
        arranged = auto_arrange(g, 'unknown_layout')
        self.assertEqual(len(arranged.items), 1)


if __name__ == '__main__':
    unittest.main()
