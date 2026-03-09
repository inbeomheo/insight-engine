"""실시간 공동 캔버스 서비스 테스트"""

import unittest
from services.collaborative_canvas_service import (
    CanvasElement, Canvas,
    create_canvas, add_element, move_element, detect_overlap,
    get_contributor_stats,
)


class TestCreateCanvas(unittest.TestCase):
    """create_canvas 테스트"""

    def test_create_basic(self):
        """기본 캔버스 생성"""
        canvas = create_canvas("기획 보드", "user1")
        self.assertTrue(canvas.canvas_id.startswith("canvas_"))
        self.assertEqual(canvas.title, "기획 보드")
        self.assertIn("user1", canvas.collaborators)
        self.assertEqual(len(canvas.elements), 0)

    def test_empty_title_raises(self):
        """빈 제목은 ValueError"""
        with self.assertRaises(ValueError):
            create_canvas("   ", "user1")

    def test_owner_in_collaborators(self):
        """소유자가 협업자 목록에 포함"""
        canvas = create_canvas("보드", "owner1")
        self.assertEqual(canvas.collaborators, ["owner1"])


class TestAddElement(unittest.TestCase):
    """add_element 테스트"""

    def setUp(self):
        self.canvas = create_canvas("테스트 캔버스", "user1")

    def test_add_text_element(self):
        """텍스트 요소 추가"""
        updated = add_element(self.canvas, {
            "element_type": "text",
            "content": "메모",
            "position": {"x": 10, "y": 20},
            "author": "user1",
        })
        self.assertEqual(len(updated.elements), 1)
        self.assertEqual(updated.elements[0].element_type, "text")

    def test_add_sticky_note(self):
        """스티키 노트 추가"""
        updated = add_element(self.canvas, {
            "element_type": "sticky_note",
            "content": "중요!",
            "author": "user2",
        })
        self.assertEqual(updated.elements[0].element_type, "sticky_note")

    def test_invalid_type_raises(self):
        """유효하지 않은 타입은 ValueError"""
        with self.assertRaises(ValueError):
            add_element(self.canvas, {"element_type": "invalid", "content": "x"})

    def test_new_author_added_to_collaborators(self):
        """새 작성자 자동 추가"""
        updated = add_element(self.canvas, {
            "element_type": "text",
            "content": "내용",
            "author": "new_user",
        })
        self.assertIn("new_user", updated.collaborators)

    def test_existing_author_not_duplicated(self):
        """기존 작성자 중복 추가 안됨"""
        updated = add_element(self.canvas, {
            "element_type": "text",
            "content": "내용",
            "author": "user1",
        })
        self.assertEqual(updated.collaborators.count("user1"), 1)


class TestMoveElement(unittest.TestCase):
    """move_element 테스트"""

    def setUp(self):
        self.canvas = create_canvas("보드", "user1")
        self.canvas = add_element(self.canvas, {
            "element_type": "shape",
            "content": "원",
            "position": {"x": 0, "y": 0},
            "author": "user1",
        })
        self.elem_id = self.canvas.elements[0].element_id

    def test_move_updates_position(self):
        """이동 시 위치 업데이트"""
        updated = move_element(self.canvas, self.elem_id, {"x": 100, "y": 200})
        self.assertEqual(updated.elements[0].position, {"x": 100, "y": 200})

    def test_move_nonexistent_raises(self):
        """존재하지 않는 요소 이동은 ValueError"""
        with self.assertRaises(ValueError):
            move_element(self.canvas, "nonexistent", {"x": 0, "y": 0})

    def test_move_updates_timestamp(self):
        """이동 시 수정 시간 업데이트"""
        old_time = self.canvas.elements[0].last_modified
        updated = move_element(self.canvas, self.elem_id, {"x": 50, "y": 50})
        self.assertNotEqual(updated.elements[0].last_modified, "")


class TestDetectOverlap(unittest.TestCase):
    """detect_overlap 테스트"""

    def test_overlapping_elements(self):
        """겹치는 요소 탐지"""
        canvas = create_canvas("보드", "u1")
        canvas = add_element(canvas, {
            "element_type": "shape",
            "content": "A",
            "position": {"x": 0, "y": 0},
            "size": {"w": 100, "h": 100},
            "author": "u1",
        })
        canvas = add_element(canvas, {
            "element_type": "shape",
            "content": "B",
            "position": {"x": 50, "y": 50},
            "size": {"w": 100, "h": 100},
            "author": "u1",
        })

        overlaps = detect_overlap(canvas)
        self.assertEqual(len(overlaps), 1)

    def test_no_overlap(self):
        """겹치지 않는 요소"""
        canvas = create_canvas("보드", "u1")
        canvas = add_element(canvas, {
            "element_type": "text",
            "content": "A",
            "position": {"x": 0, "y": 0},
            "size": {"w": 50, "h": 50},
            "author": "u1",
        })
        canvas = add_element(canvas, {
            "element_type": "text",
            "content": "B",
            "position": {"x": 200, "y": 200},
            "size": {"w": 50, "h": 50},
            "author": "u1",
        })

        overlaps = detect_overlap(canvas)
        self.assertEqual(len(overlaps), 0)

    def test_empty_canvas_no_overlap(self):
        """빈 캔버스"""
        canvas = create_canvas("빈", "u1")
        overlaps = detect_overlap(canvas)
        self.assertEqual(len(overlaps), 0)


class TestGetContributorStats(unittest.TestCase):
    """get_contributor_stats 테스트"""

    def test_contributor_counts(self):
        """기여자별 요소 수"""
        canvas = create_canvas("보드", "u1")
        canvas = add_element(canvas, {"element_type": "text", "content": "A", "author": "u1"})
        canvas = add_element(canvas, {"element_type": "shape", "content": "B", "author": "u1"})
        canvas = add_element(canvas, {"element_type": "text", "content": "C", "author": "u2"})

        stats = get_contributor_stats(canvas)
        self.assertEqual(stats["u1"]["count"], 2)
        self.assertEqual(stats["u2"]["count"], 1)

    def test_element_types_tracked(self):
        """기여자별 요소 타입 추적"""
        canvas = create_canvas("보드", "u1")
        canvas = add_element(canvas, {"element_type": "text", "content": "A", "author": "u1"})
        canvas = add_element(canvas, {"element_type": "shape", "content": "B", "author": "u1"})

        stats = get_contributor_stats(canvas)
        self.assertIn("text", stats["u1"]["element_types"])
        self.assertIn("shape", stats["u1"]["element_types"])

    def test_empty_canvas_stats(self):
        """빈 캔버스 통계"""
        canvas = create_canvas("빈", "u1")
        stats = get_contributor_stats(canvas)
        self.assertEqual(len(stats), 0)


if __name__ == "__main__":
    unittest.main()
