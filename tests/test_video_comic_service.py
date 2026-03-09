"""비디오-코믹 서비스 테스트"""
import unittest
from services.video_comic_service import (
    create_strip, add_dialogue, reorder_panels, generate_layout,
    ComicStrip, ComicPanel
)


class TestVideoComicService(unittest.TestCase):

    def setUp(self):
        self.scenes = [
            {'description': '주인공 등장', 'dialogue': '안녕!', 'visual_style': 'manga'},
            {'description': '갈등 발생', 'dialogue': '이게 뭐야?', 'size': 'large'},
            {'description': '해결', 'dialogue': '다 해결됐어!'},
        ]
        self.strip = create_strip('에피소드 1', self.scenes)

    def test_create_strip(self):
        self.assertIsInstance(self.strip, ComicStrip)
        self.assertEqual(self.strip.title, '에피소드 1')
        self.assertEqual(len(self.strip.panels), 3)

    def test_create_strip_layout(self):
        self.assertEqual(self.strip.page_layout, 'strip')  # 3패널

    def test_panel_positions(self):
        for i, panel in enumerate(self.strip.panels):
            self.assertEqual(panel.position, i)

    def test_add_dialogue(self):
        pid = self.strip.panels[0].panel_id
        updated = add_dialogue(self.strip, pid, '새 대사!')
        self.assertEqual(updated.panels[0].dialogue, '새 대사!')

    def test_add_dialogue_invalid_panel(self):
        with self.assertRaises(ValueError):
            add_dialogue(self.strip, 'nonexistent', '대사')

    def test_reorder_panels(self):
        ids = [p.panel_id for p in self.strip.panels]
        reversed_ids = list(reversed(ids))
        reordered = reorder_panels(self.strip, reversed_ids)
        self.assertEqual(reordered.panels[0].panel_id, ids[2])
        self.assertEqual(reordered.panels[0].position, 0)

    def test_reorder_panels_invalid_id(self):
        with self.assertRaises(ValueError):
            reorder_panels(self.strip, ['bad_id'])

    def test_generate_layout_strip(self):
        self.assertEqual(generate_layout(1), 'strip')
        self.assertEqual(generate_layout(3), 'strip')

    def test_generate_layout_half_page(self):
        self.assertEqual(generate_layout(4), 'half-page')
        self.assertEqual(generate_layout(6), 'half-page')

    def test_generate_layout_full_page(self):
        self.assertEqual(generate_layout(7), 'full-page')
        self.assertEqual(generate_layout(12), 'full-page')

    def test_create_strip_defaults(self):
        strip = create_strip('빈', [{'description': 'test'}])
        self.assertEqual(strip.panels[0].dialogue, '')
        self.assertEqual(strip.panels[0].visual_style, 'manga')
        self.assertEqual(strip.panels[0].size, 'medium')


if __name__ == '__main__':
    unittest.main()
