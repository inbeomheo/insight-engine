import os
import unittest


class TestUrlDragSortContract(unittest.TestCase):
    def setUp(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.url_manager_path = os.path.join(base_dir, 'static', 'js', 'modules', 'UrlManager.js')

    def _read(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def test_js_has_drag_events_logic(self):
        """UrlManager에 드래그 정렬 로직이 있는지 확인"""
        js = self._read(self.url_manager_path)
        self.assertIn('setupDragEvents', js)
        self.assertIn('dragstart', js)
        self.assertIn('dragend', js)


if __name__ == '__main__':
    unittest.main()
