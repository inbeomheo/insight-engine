"""style_label 헬퍼 함수 테스트."""
import unittest

from app import create_app


class TestGetStyleLabel(unittest.TestCase):

    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True

    def test_known_style_returns_label(self):
        """등록된 스타일 ID는 한글 라벨을 반환."""
        with self.app.app_context():
            from routes.generation_helpers import _get_style_label
            label = _get_style_label('blog_seo')
            self.assertIn('블로그', label)
            self.assertIn('SEO', label)

    def test_unknown_style_returns_id(self):
        """미등록 스타일 ID는 ID를 그대로 반환."""
        with self.app.app_context():
            from routes.generation_helpers import _get_style_label
            label = _get_style_label('unknown_style_xyz')
            self.assertEqual(label, 'unknown_style_xyz')

    def test_all_styles_have_labels(self):
        """STYLE_OPTIONS의 모든 스타일이 라벨을 반환."""
        with self.app.app_context():
            from routes.generation_helpers import _get_style_label
            from config import STYLE_OPTIONS
            for style_id, expected_label in STYLE_OPTIONS:
                label = _get_style_label(style_id)
                self.assertEqual(label, expected_label)


if __name__ == '__main__':
    unittest.main()
