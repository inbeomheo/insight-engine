"""브랜치 버전 서비스 테스트"""

import unittest
from services.branch_version_service import (
    ContentBranch,
    create_branch, list_branches, merge_branches,
    detect_conflicts, get_branch_history,
)


class TestCreateBranch(unittest.TestCase):
    """create_branch 테스트"""

    def test_create_branch_basic(self):
        """기본 브랜치 생성"""
        branch = create_branch("parent_1", "feature-a", "콘텐츠 내용")
        self.assertTrue(branch.branch_id.startswith("branch_"))
        self.assertEqual(branch.name, "feature-a")
        self.assertEqual(branch.content, "콘텐츠 내용")
        self.assertFalse(branch.is_merged)

    def test_create_root_branch(self):
        """루트 브랜치 (parent_id 없음)"""
        branch = create_branch("", "main", "루트 내용")
        self.assertEqual(branch.parent_id, "")

    def test_create_branch_none_parent(self):
        """parent_id가 None이면 빈 문자열로 변환"""
        branch = create_branch(None, "main", "내용")
        self.assertEqual(branch.parent_id, "")

    def test_empty_name_raises(self):
        """빈 이름은 ValueError"""
        with self.assertRaises(ValueError):
            create_branch("parent", "   ", "내용")

    def test_name_trimmed(self):
        """이름 양쪽 공백 제거"""
        branch = create_branch("p", "  trimmed  ", "내용")
        self.assertEqual(branch.name, "trimmed")

    def test_created_at_set(self):
        """생성 시간 설정됨"""
        branch = create_branch("p", "test", "내용")
        self.assertTrue(len(branch.created_at) > 0)


class TestListBranches(unittest.TestCase):
    """list_branches 테스트"""

    def test_list_child_branches(self):
        """자식 브랜치만 반환"""
        b1 = create_branch("root", "child1", "내용1")
        b2 = create_branch("root", "child2", "내용2")
        b3 = create_branch("other", "child3", "내용3")

        children = list_branches("root", [b1, b2, b3])
        self.assertEqual(len(children), 2)

    def test_list_empty_children(self):
        """자식이 없으면 빈 목록"""
        b1 = create_branch("root", "child", "내용")
        children = list_branches("nonexistent", [b1])
        self.assertEqual(len(children), 0)


class TestMergeBranches(unittest.TestCase):
    """merge_branches 테스트"""

    def test_merge_basic(self):
        """기본 병합"""
        a = create_branch("root", "a", "공통 줄\na 전용")
        b = create_branch("root", "b", "공통 줄\nb 전용")
        merged = merge_branches(a, b)

        self.assertTrue(merged.is_merged)
        self.assertIn("공통 줄", merged.content)
        self.assertIn("a 전용", merged.content)
        self.assertIn("b 전용", merged.content)

    def test_merge_name_format(self):
        """병합 브랜치 이름 형식"""
        a = create_branch("root", "feature-a", "내용a")
        b = create_branch("root", "feature-b", "내용b")
        merged = merge_branches(a, b)
        self.assertIn("feature-a", merged.name)
        self.assertIn("feature-b", merged.name)

    def test_merge_identical_content(self):
        """동일 콘텐츠 병합"""
        a = create_branch("root", "a", "동일한 내용")
        b = create_branch("root", "b", "동일한 내용")
        merged = merge_branches(a, b)
        self.assertEqual(merged.content, "동일한 내용")

    def test_merge_completely_different(self):
        """완전히 다른 콘텐츠 병합"""
        a = create_branch("root", "a", "aaa")
        b = create_branch("root", "b", "bbb")
        merged = merge_branches(a, b)
        self.assertIn("aaa", merged.content)
        self.assertIn("bbb", merged.content)


class TestDetectConflicts(unittest.TestCase):
    """detect_conflicts 테스트"""

    def test_no_conflicts(self):
        """충돌 없음"""
        a = create_branch("root", "a", "동일 줄1\n동일 줄2")
        b = create_branch("root", "b", "동일 줄1\n동일 줄2")
        conflicts = detect_conflicts(a, b)
        self.assertEqual(len(conflicts), 0)

    def test_line_conflict(self):
        """라인 내용 충돌"""
        a = create_branch("root", "a", "줄1\n충돌-A")
        b = create_branch("root", "b", "줄1\n충돌-B")
        conflicts = detect_conflicts(a, b)
        self.assertTrue(any("충돌" in c for c in conflicts))

    def test_length_conflict(self):
        """줄 수 불일치 충돌"""
        a = create_branch("root", "a", "줄1\n줄2\n줄3")
        b = create_branch("root", "b", "줄1")
        conflicts = detect_conflicts(a, b)
        self.assertTrue(any("불일치" in c for c in conflicts))


class TestGetBranchHistory(unittest.TestCase):
    """get_branch_history 테스트"""

    def test_linear_history(self):
        """선형 이력 추적"""
        root = ContentBranch("b1", "", "root", "루트", "2024-01-01", False)
        child = ContentBranch("b2", "b1", "child", "자식", "2024-01-02", False)
        grandchild = ContentBranch("b3", "b2", "grandchild", "손자", "2024-01-03", False)

        history = get_branch_history([root, child, grandchild], "b3")
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0].branch_id, "b3")
        self.assertEqual(history[-1].branch_id, "b1")

    def test_root_history(self):
        """루트 브랜치 이력"""
        root = ContentBranch("b1", "", "root", "루트", "2024-01-01", False)
        history = get_branch_history([root], "b1")
        self.assertEqual(len(history), 1)

    def test_nonexistent_branch(self):
        """존재하지 않는 브랜치"""
        root = ContentBranch("b1", "", "root", "루트", "2024-01-01", False)
        history = get_branch_history([root], "nonexistent")
        self.assertEqual(len(history), 0)

    def test_cycle_protection(self):
        """순환 참조 방어"""
        a = ContentBranch("b1", "b2", "a", "A", "2024-01-01", False)
        b = ContentBranch("b2", "b1", "b", "B", "2024-01-02", False)
        history = get_branch_history([a, b], "b1")
        # 순환이 있어도 무한루프 없이 반환
        self.assertLessEqual(len(history), 2)


if __name__ == "__main__":
    unittest.main()
