import os
import unittest


class TestUrlDragSortContract(unittest.TestCase):
    def setUp(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.js_path = os.path.join(base_dir, 'static', 'js', 'main.js')
        self.url_manager_path = os.path.join(base_dir, 'static', 'js', 'modules', 'UrlManager.js')
        self.css_path = os.path.join(base_dir, 'static', 'css', 'style.css')

    def _read(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def test_js_has_drag_events_logic(self):
        # 리팩터링 후 드래그 로직은 UrlManager.js에 있음
        js = self._read(self.url_manager_path)
        self.assertIn('setupDragEvents', js)  # 함수명 변경: setupUrlDragEvents -> setupDragEvents
        self.assertIn('url-drag-handle', js)
        self.assertIn('dragstart', js)
        self.assertIn('dragend', js)

    def test_css_has_drag_handle_styles(self):
        css = self._read(self.css_path)
        self.assertIn('.url-drag-handle', css)
        self.assertTrue(
            ('.url-input-group.dragging' in css) or ('.dragging' in css)
        )


if __name__ == '__main__':
    unittest.main()
