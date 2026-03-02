import os
import unittest


class TestUrlDragSortContract(unittest.TestCase):
    def setUp(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.page_path = os.path.join(base_dir, 'frontend', 'app', 'page.tsx')

    def _read(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def test_page_has_drag_drop_logic(self):
        """page.tsx에 드래그 앤 드롭 로직이 있는지 확인"""
        tsx = self._read(self.page_path)
        self.assertIn('dragCounter', tsx)
        self.assertIn('onDragEnter', tsx)
        self.assertIn('onDrop', tsx)


if __name__ == '__main__':
    unittest.main()
