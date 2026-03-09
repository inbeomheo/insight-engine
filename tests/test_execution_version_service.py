"""실행 버전/재생 서비스 테스트."""

import unittest
from services.execution_version_service import (
    ExecutionVersion,
    save_version,
    list_versions,
    get_version,
    compare_versions,
    replay_version,
    _reset_store,
)


class TestSaveVersion(unittest.TestCase):
    """버전 저장 테스트."""

    def setUp(self):
        _reset_store()

    def test_save_basic(self):
        """기본 버전 저장."""
        v = save_version("p1", {"key": "value"})
        self.assertTrue(v.version_id)
        self.assertEqual(v.pipeline_id, "p1")
        self.assertEqual(v.version_number, 1)
        self.assertEqual(v.snapshot, {"key": "value"})
        self.assertTrue(v.created_at)

    def test_save_auto_increment(self):
        """같은 pipeline_id에 버전 번호 자동 증가."""
        v1 = save_version("p1", {"a": 1})
        v2 = save_version("p1", {"b": 2})
        self.assertEqual(v1.version_number, 1)
        self.assertEqual(v2.version_number, 2)

    def test_save_different_pipelines(self):
        """다른 pipeline_id는 독립 번호."""
        v1 = save_version("p1", {"a": 1})
        v2 = save_version("p2", {"b": 2})
        self.assertEqual(v1.version_number, 1)
        self.assertEqual(v2.version_number, 1)

    def test_save_with_tags(self):
        """태그 포함 저장."""
        v = save_version("p1", {"key": "val"}, tags=["release", "stable"])
        self.assertEqual(v.tags, ["release", "stable"])

    def test_save_defensive_copy(self):
        """스냅샷 방어적 복사."""
        snapshot = {"key": "original"}
        v = save_version("p1", snapshot)
        snapshot["key"] = "modified"
        self.assertEqual(v.snapshot["key"], "original")


class TestListVersions(unittest.TestCase):
    """버전 목록 조회 테스트."""

    def setUp(self):
        _reset_store()

    def test_list_empty(self):
        """해당 파이프라인 버전 없음."""
        result = list_versions("nonexistent")
        self.assertEqual(result, [])

    def test_list_sorted(self):
        """버전 번호 오름차순."""
        save_version("p1", {"step": 1})
        save_version("p1", {"step": 2})
        save_version("p1", {"step": 3})
        versions = list_versions("p1")
        self.assertEqual(len(versions), 3)
        self.assertEqual(versions[0].version_number, 1)
        self.assertEqual(versions[2].version_number, 3)

    def test_list_filters_by_pipeline(self):
        """pipeline_id별 필터링."""
        save_version("p1", {"a": 1})
        save_version("p2", {"b": 2})
        save_version("p1", {"c": 3})
        self.assertEqual(len(list_versions("p1")), 2)
        self.assertEqual(len(list_versions("p2")), 1)


class TestGetVersion(unittest.TestCase):
    """버전 조회 테스트."""

    def setUp(self):
        _reset_store()

    def test_get_existing(self):
        """존재하는 버전 조회."""
        v = save_version("p1", {"key": "value"})
        found = get_version(v.version_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.version_id, v.version_id)

    def test_get_nonexistent(self):
        """존재하지 않는 ID → None."""
        result = get_version("nonexistent_id")
        self.assertIsNone(result)


class TestCompareVersions(unittest.TestCase):
    """버전 비교 테스트."""

    def setUp(self):
        _reset_store()

    def test_compare_added_keys(self):
        """v2에만 있는 키 감지."""
        v1 = save_version("p1", {"a": 1})
        v2 = save_version("p1", {"a": 1, "b": 2})
        diff = compare_versions(v1, v2)
        self.assertIn("b", diff["added"])
        self.assertEqual(diff["removed"], [])
        self.assertEqual(diff["changed"], [])

    def test_compare_removed_keys(self):
        """v1에만 있는 키 감지."""
        v1 = save_version("p1", {"a": 1, "b": 2})
        v2 = save_version("p1", {"a": 1})
        diff = compare_versions(v1, v2)
        self.assertIn("b", diff["removed"])

    def test_compare_changed_keys(self):
        """값 변경 감지."""
        v1 = save_version("p1", {"a": 1, "b": "old"})
        v2 = save_version("p1", {"a": 1, "b": "new"})
        diff = compare_versions(v1, v2)
        self.assertIn("b", diff["changed"])
        self.assertEqual(diff["added"], [])
        self.assertEqual(diff["removed"], [])

    def test_compare_identical(self):
        """동일 스냅샷."""
        v1 = save_version("p1", {"x": 10})
        v2 = save_version("p1", {"x": 10})
        diff = compare_versions(v1, v2)
        self.assertEqual(diff["added"], [])
        self.assertEqual(diff["removed"], [])
        self.assertEqual(diff["changed"], [])

    def test_compare_all_different(self):
        """완전히 다른 스냅샷."""
        v1 = save_version("p1", {"a": 1})
        v2 = save_version("p1", {"b": 2})
        diff = compare_versions(v1, v2)
        self.assertIn("b", diff["added"])
        self.assertIn("a", diff["removed"])


class TestReplayVersion(unittest.TestCase):
    """버전 재생 테스트."""

    def setUp(self):
        _reset_store()

    def test_replay_basic(self):
        """기본 재생."""
        v = save_version("p1", {"key": "val"})
        result = replay_version(v)
        self.assertEqual(result["version_id"], v.version_id)
        self.assertEqual(result["pipeline_id"], "p1")
        self.assertEqual(result["snapshot"], {"key": "val"})
        self.assertIn("replayed_at", result)

    def test_replay_preserves_version_number(self):
        """재생 시 버전 번호 보존."""
        save_version("p1", {"a": 1})
        v2 = save_version("p1", {"b": 2})
        result = replay_version(v2)
        self.assertEqual(result["version_number"], 2)


if __name__ == "__main__":
    unittest.main()
