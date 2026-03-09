"""장면 보드 서비스 테스트"""

import unittest
from services.scene_board_service import (
    Scene, SceneBoard,
    create_board, add_scene, reorder_scenes, calculate_pacing, split_scene,
)


class TestCreateBoard(unittest.TestCase):
    """create_board 테스트"""

    def test_create_basic(self):
        """기본 보드 생성"""
        board = create_board("프로모션 영상")
        self.assertTrue(board.board_id.startswith("board_"))
        self.assertEqual(board.title, "프로모션 영상")
        self.assertEqual(len(board.scenes), 0)
        self.assertEqual(board.total_duration, 0.0)

    def test_empty_title_raises(self):
        """빈 제목은 ValueError"""
        with self.assertRaises(ValueError):
            create_board("   ")


class TestAddScene(unittest.TestCase):
    """add_scene 테스트"""

    def setUp(self):
        self.board = create_board("테스트 보드")

    def test_add_scene_increments_order(self):
        """장면 추가 시 order 자동 부여"""
        b = add_scene(self.board, {"title": "장면1", "duration_sec": 10.0})
        b = add_scene(b, {"title": "장면2", "duration_sec": 20.0})
        self.assertEqual(b.scenes[0].order, 1)
        self.assertEqual(b.scenes[1].order, 2)

    def test_total_duration_calculated(self):
        """총 재생 시간 계산"""
        b = add_scene(self.board, {"title": "장면1", "duration_sec": 15.0})
        b = add_scene(b, {"title": "장면2", "duration_sec": 25.0})
        self.assertEqual(b.total_duration, 40.0)

    def test_negative_duration_raises(self):
        """음수 길이는 ValueError"""
        with self.assertRaises(ValueError):
            add_scene(self.board, {"title": "잘못", "duration_sec": -5.0})

    def test_default_fields(self):
        """기본 필드 설정"""
        b = add_scene(self.board, {"title": "장면", "duration_sec": 5.0})
        scene = b.scenes[0]
        self.assertEqual(scene.visual_notes, "")
        self.assertEqual(scene.audio_notes, "")


class TestReorderScenes(unittest.TestCase):
    """reorder_scenes 테스트"""

    def test_reorder_reverses(self):
        """역순 재정렬"""
        board = create_board("보드")
        board = add_scene(board, {"title": "A", "duration_sec": 10.0})
        board = add_scene(board, {"title": "B", "duration_sec": 20.0})

        ids = [s.scene_id for s in board.scenes]
        reordered = reorder_scenes(board, list(reversed(ids)))

        self.assertEqual(reordered.scenes[0].title, "B")
        self.assertEqual(reordered.scenes[0].order, 1)
        self.assertEqual(reordered.scenes[1].title, "A")
        self.assertEqual(reordered.scenes[1].order, 2)

    def test_reorder_invalid_id_raises(self):
        """존재하지 않는 ID는 ValueError"""
        board = create_board("보드")
        board = add_scene(board, {"title": "A", "duration_sec": 10.0})
        with self.assertRaises(ValueError):
            reorder_scenes(board, ["nonexistent"])

    def test_reorder_preserves_duration(self):
        """재정렬 시 총 시간 유지"""
        board = create_board("보드")
        board = add_scene(board, {"title": "A", "duration_sec": 10.0})
        board = add_scene(board, {"title": "B", "duration_sec": 20.0})
        ids = [s.scene_id for s in board.scenes]

        reordered = reorder_scenes(board, list(reversed(ids)))
        self.assertEqual(reordered.total_duration, 30.0)


class TestCalculatePacing(unittest.TestCase):
    """calculate_pacing 테스트"""

    def test_empty_board_pacing(self):
        """빈 보드 페이싱"""
        board = create_board("빈 보드")
        pacing = calculate_pacing(board)
        self.assertEqual(pacing["scene_count"], 0)
        self.assertEqual(pacing["avg_duration"], 0.0)

    def test_pacing_with_scenes(self):
        """장면이 있는 보드 페이싱"""
        board = create_board("보드")
        board = add_scene(board, {"title": "A", "duration_sec": 10.0})
        board = add_scene(board, {"title": "B", "duration_sec": 20.0})
        board = add_scene(board, {"title": "C", "duration_sec": 30.0})

        pacing = calculate_pacing(board)
        self.assertEqual(pacing["scene_count"], 3)
        self.assertEqual(pacing["avg_duration"], 20.0)
        self.assertEqual(pacing["max_duration"], 30.0)
        self.assertEqual(pacing["min_duration"], 10.0)
        self.assertEqual(pacing["total_duration"], 60.0)

    def test_pacing_variance(self):
        """변동성 계산"""
        board = create_board("보드")
        board = add_scene(board, {"title": "A", "duration_sec": 10.0})
        board = add_scene(board, {"title": "B", "duration_sec": 10.0})

        pacing = calculate_pacing(board)
        self.assertEqual(pacing["variance"], 0.0)
        self.assertEqual(pacing["std_dev"], 0.0)

    def test_single_scene_pacing(self):
        """장면 1개 페이싱"""
        board = create_board("보드")
        board = add_scene(board, {"title": "A", "duration_sec": 15.0})
        pacing = calculate_pacing(board)
        self.assertEqual(pacing["avg_duration"], 15.0)
        self.assertEqual(pacing["variance"], 0.0)


class TestSplitScene(unittest.TestCase):
    """split_scene 테스트"""

    def test_split_creates_two_scenes(self):
        """분할 시 2개 장면 생성"""
        board = create_board("보드")
        board = add_scene(board, {"title": "장면", "duration_sec": 20.0})
        scene_id = board.scenes[0].scene_id

        result = split_scene(board, scene_id, 8.0)
        self.assertEqual(len(result.scenes), 2)

    def test_split_preserves_total_duration(self):
        """분할 시 총 시간 보존"""
        board = create_board("보드")
        board = add_scene(board, {"title": "장면", "duration_sec": 30.0})
        scene_id = board.scenes[0].scene_id

        result = split_scene(board, scene_id, 10.0)
        self.assertAlmostEqual(result.total_duration, 30.0, places=2)

    def test_split_at_boundary_raises(self):
        """경계값 분할은 ValueError"""
        board = create_board("보드")
        board = add_scene(board, {"title": "장면", "duration_sec": 20.0})
        scene_id = board.scenes[0].scene_id

        with self.assertRaises(ValueError):
            split_scene(board, scene_id, 0)
        with self.assertRaises(ValueError):
            split_scene(board, scene_id, 20.0)

    def test_split_nonexistent_raises(self):
        """존재하지 않는 장면 분할은 ValueError"""
        board = create_board("보드")
        with self.assertRaises(ValueError):
            split_scene(board, "nonexistent", 5.0)

    def test_split_updates_order(self):
        """분할 후 order 재부여"""
        board = create_board("보드")
        board = add_scene(board, {"title": "A", "duration_sec": 10.0})
        board = add_scene(board, {"title": "B", "duration_sec": 20.0})
        scene_id = board.scenes[0].scene_id

        result = split_scene(board, scene_id, 5.0)
        orders = [s.order for s in result.scenes]
        self.assertEqual(orders, [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
