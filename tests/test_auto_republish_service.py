"""자동 재발행 서비스 테스트"""
import unittest
from services.auto_republish_service import (
    auto_republish,
    RepublishResult,
    _compute_hash,
    _apply_text_updates,
)


class TestComputeHash(unittest.TestCase):
    """해시 계산 테스트"""

    def test_deterministic(self):
        h1 = _compute_hash("hello")
        h2 = _compute_hash("hello")
        self.assertEqual(h1, h2)

    def test_different_content(self):
        h1 = _compute_hash("hello")
        h2 = _compute_hash("world")
        self.assertNotEqual(h1, h2)


class TestApplyTextUpdates(unittest.TestCase):
    """텍스트 업데이트 적용 테스트"""

    def test_replacements(self):
        content = "Python 2 is great."
        updates = {"replacements": [{"old": "Python 2", "new": "Python 3"}]}
        result, changes = _apply_text_updates(content, updates)
        self.assertIn("Python 3", result)
        self.assertEqual(len(changes), 1)

    def test_append(self):
        content = "Hello"
        updates = {"append": "World"}
        result, changes = _apply_text_updates(content, updates)
        self.assertTrue(result.endswith("World"))

    def test_prepend(self):
        content = "World"
        updates = {"prepend": "Hello"}
        result, changes = _apply_text_updates(content, updates)
        self.assertTrue(result.startswith("Hello"))

    def test_title_change(self):
        content = "# Old Title\n\nBody text here."
        updates = {"title": "New Title"}
        result, changes = _apply_text_updates(content, updates)
        self.assertIn("# New Title", result)
        self.assertNotIn("# Old Title", result)


class TestAutoRepublish(unittest.TestCase):
    """재발행 테스트"""

    def test_no_updates(self):
        result = auto_republish("post-1", "Hello World")
        self.assertIsInstance(result, RepublishResult)
        self.assertEqual(result.content_id, "post-1")
        self.assertEqual(result.original_hash, result.updated_hash)
        self.assertIn("변경 없음", result.changes[0])

    def test_with_updates(self):
        content = "Python 2 is used."
        updates = {"replacements": [{"old": "Python 2", "new": "Python 3"}]}
        result = auto_republish("post-2", content, updates)
        self.assertNotEqual(result.original_hash, result.updated_hash)
        self.assertGreater(len(result.changes), 0)

    def test_republished_at_set(self):
        result = auto_republish("post-3", "content")
        self.assertTrue(result.republished_at)
        self.assertIn("T", result.republished_at)

    def test_hash_format(self):
        result = auto_republish("post-4", "test")
        self.assertEqual(len(result.original_hash), 64)  # SHA-256

    def test_multiple_replacements(self):
        content = "Foo is great. Bar is nice."
        updates = {
            "replacements": [
                {"old": "Foo", "new": "Alpha"},
                {"old": "Bar", "new": "Beta"},
            ]
        }
        result = auto_republish("post-5", content, updates)
        self.assertEqual(len(result.changes), 2)

    def test_replacement_not_found(self):
        content = "Hello World"
        updates = {"replacements": [{"old": "NotFound", "new": "Replaced"}]}
        result = auto_republish("post-6", content, updates)
        self.assertEqual(result.original_hash, result.updated_hash)

    def test_empty_updates_dict(self):
        result = auto_republish("post-7", "content", {})
        self.assertEqual(result.original_hash, result.updated_hash)

    def test_append_and_prepend_combined(self):
        content = "Body"
        updates = {"prepend": "Start", "append": "End"}
        result = auto_republish("post-8", content, updates)
        self.assertNotEqual(result.original_hash, result.updated_hash)
        self.assertEqual(len(result.changes), 2)


if __name__ == "__main__":
    unittest.main()
