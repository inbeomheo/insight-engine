"""공간 장면 서비스 테스트"""

import unittest
import math

from services.spatial_scene_service import (
    Object2D,
    Object3D,
    SpatialScene,
    convert_to_3d,
    arrange_gallery,
    calculate_bounds,
)


class TestConvertTo3d(unittest.TestCase):
    """convert_to_3d 함수 테스트"""

    def test_기본_변환(self):
        objects = [
            Object2D(object_id="1", name="obj1", x=0, y=0, layer=0),
            Object2D(object_id="2", name="obj2", x=5, y=5, layer=1),
        ]
        scene = convert_to_3d(objects)
        self.assertEqual(len(scene.objects), 2)
        self.assertEqual(scene.objects[0].z, 0.0)
        self.assertLess(scene.objects[1].z, 0.0)  # 더 먼 깊이

    def test_레이어_높을수록_작은_스케일(self):
        objects = [
            Object2D(object_id="1", name="front", layer=0),
            Object2D(object_id="2", name="back", layer=3),
        ]
        scene = convert_to_3d(objects)
        self.assertGreater(scene.objects[0].scale, scene.objects[1].scale)

    def test_depth_scale_적용(self):
        objects = [Object2D(object_id="1", name="obj", layer=2)]
        scene = convert_to_3d(objects, depth_scale=5.0)
        self.assertEqual(scene.objects[0].z, -10.0)

    def test_빈_오브젝트(self):
        scene = convert_to_3d([])
        self.assertEqual(len(scene.objects), 0)

    def test_카메라_위치_설정(self):
        objects = [Object2D(object_id="1", name="obj", layer=5)]
        scene = convert_to_3d(objects)
        self.assertGreater(scene.camera_position["z"], 0)


class TestArrangeGallery(unittest.TestCase):
    """arrange_gallery 함수 테스트"""

    def test_그리드_배치(self):
        items = ["A", "B", "C", "D"]
        scene = arrange_gallery(items, "grid")
        self.assertEqual(len(scene.objects), 4)

    def test_원형_배치(self):
        items = ["A", "B", "C"]
        scene = arrange_gallery(items, "circle")
        self.assertEqual(len(scene.objects), 3)
        # 모든 오브젝트의 z가 0
        for obj in scene.objects:
            self.assertEqual(obj.z, 0.0)

    def test_나선_배치(self):
        items = ["A", "B", "C", "D", "E"]
        scene = arrange_gallery(items, "spiral")
        self.assertEqual(len(scene.objects), 5)
        # z 값이 점점 감소
        for i in range(1, len(scene.objects)):
            self.assertLessEqual(scene.objects[i].z, scene.objects[i-1].z)

    def test_빈_아이템(self):
        scene = arrange_gallery([], "grid")
        self.assertEqual(len(scene.objects), 0)

    def test_잘못된_레이아웃_에러(self):
        with self.assertRaises(ValueError):
            arrange_gallery(["A"], "invalid")

    def test_단일_아이템_그리드(self):
        scene = arrange_gallery(["A"], "grid")
        self.assertEqual(len(scene.objects), 1)
        self.assertEqual(scene.objects[0].x, 0.0)
        self.assertEqual(scene.objects[0].y, 0.0)


class TestCalculateBounds(unittest.TestCase):
    """calculate_bounds 함수 테스트"""

    def test_정상_바운딩_박스(self):
        scene = SpatialScene(objects=[
            Object3D(object_id="1", x=0, y=0, z=0),
            Object3D(object_id="2", x=10, y=5, z=-3),
        ])
        bounds = calculate_bounds(scene)
        self.assertEqual(bounds["min"]["x"], 0)
        self.assertEqual(bounds["max"]["x"], 10)
        self.assertEqual(bounds["size"]["x"], 10)

    def test_빈_장면(self):
        scene = SpatialScene(objects=[])
        bounds = calculate_bounds(scene)
        self.assertEqual(bounds["size"]["x"], 0)

    def test_단일_오브젝트(self):
        scene = SpatialScene(objects=[
            Object3D(object_id="1", x=5, y=3, z=-2),
        ])
        bounds = calculate_bounds(scene)
        self.assertEqual(bounds["center"]["x"], 5)
        self.assertEqual(bounds["center"]["y"], 3)
        self.assertEqual(bounds["size"]["x"], 0)

    def test_음수_좌표(self):
        scene = SpatialScene(objects=[
            Object3D(object_id="1", x=-5, y=-3, z=-10),
            Object3D(object_id="2", x=5, y=3, z=0),
        ])
        bounds = calculate_bounds(scene)
        self.assertEqual(bounds["min"]["x"], -5)
        self.assertEqual(bounds["max"]["x"], 5)
        self.assertEqual(bounds["center"]["x"], 0)


if __name__ == "__main__":
    unittest.main()
