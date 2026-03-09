"""
분류체계 서비스 테스트
"""

import unittest

from services.taxonomy_service import (
    TaxonomyNode,
    Taxonomy,
    create_taxonomy,
    add_category,
    classify_content,
    get_path,
    get_depth,
    find_node,
)


class TestCreateTaxonomy(unittest.TestCase):
    """분류체계 생성 테스트"""

    def test_create_basic(self):
        """기본 분류체계 생성"""
        tax = create_taxonomy("기술")
        self.assertEqual(len(tax.nodes), 1)
        self.assertEqual(tax.nodes[0].name, "기술")
        self.assertEqual(tax.nodes[0].level, 0)
        self.assertIsNone(tax.nodes[0].parent_id)
        self.assertEqual(tax.root_id, tax.nodes[0].node_id)

    def test_create_has_unique_ids(self):
        """고유 ID 생성"""
        t1 = create_taxonomy("A")
        t2 = create_taxonomy("B")
        self.assertNotEqual(t1.taxonomy_id, t2.taxonomy_id)


class TestAddCategory(unittest.TestCase):
    """카테고리 추가 테스트"""

    def setUp(self):
        self.tax = create_taxonomy("기술")
        self.root_id = self.tax.root_id

    def test_add_child_category(self):
        """자식 카테고리 추가"""
        self.tax = add_category(self.tax, self.root_id, "프로그래밍", ["코딩", "개발"])
        self.assertEqual(len(self.tax.nodes), 2)
        child = self.tax.nodes[1]
        self.assertEqual(child.name, "프로그래밍")
        self.assertEqual(child.level, 1)
        self.assertEqual(child.parent_id, self.root_id)

    def test_add_nested_category(self):
        """중첩 카테고리 추가"""
        self.tax = add_category(self.tax, self.root_id, "프로그래밍")
        prog_id = self.tax.nodes[1].node_id
        self.tax = add_category(self.tax, prog_id, "Python", ["파이썬"])
        python_node = self.tax.nodes[2]
        self.assertEqual(python_node.level, 2)
        self.assertEqual(python_node.parent_id, prog_id)

    def test_add_category_invalid_parent(self):
        """잘못된 부모 ID"""
        with self.assertRaises(ValueError):
            add_category(self.tax, "nonexistent", "테스트")

    def test_parent_children_updated(self):
        """부모의 children 목록 업데이트 확인"""
        self.tax = add_category(self.tax, self.root_id, "웹개발")
        root = self.tax.nodes[0]
        self.assertEqual(len(root.children), 1)
        self.assertEqual(root.children[0], self.tax.nodes[1].node_id)


class TestClassifyContent(unittest.TestCase):
    """콘텐츠 분류 테스트"""

    def setUp(self):
        self.tax = create_taxonomy("콘텐츠")
        root_id = self.tax.root_id
        self.tax = add_category(self.tax, root_id, "프로그래밍", ["코딩", "개발", "프로그래밍"])
        prog_id = self.tax.nodes[1].node_id
        self.tax = add_category(self.tax, prog_id, "Python", ["파이썬", "python", "pip"])
        self.tax = add_category(self.tax, prog_id, "JavaScript", ["자바스크립트", "javascript", "npm"])
        self.tax = add_category(self.tax, root_id, "디자인", ["디자인", "UI", "UX"])

    def test_classify_specific_match(self):
        """구체적 매칭 (깊은 레벨 우선)"""
        results = classify_content(self.tax, "Python 파이썬으로 프로그래밍 개발하기")
        self.assertGreater(len(results), 0)
        # Python 노드(레벨 2)가 프로그래밍(레벨 1)보다 먼저
        self.assertEqual(results[0].name, "Python")

    def test_classify_multiple_categories(self):
        """여러 카테고리 매칭"""
        results = classify_content(self.tax, "프로그래밍과 디자인을 함께 배우는 개발 강좌")
        names = [n.name for n in results]
        self.assertIn("프로그래밍", names)
        self.assertIn("디자인", names)

    def test_classify_empty_content(self):
        """빈 콘텐츠"""
        results = classify_content(self.tax, "")
        self.assertEqual(results, [])

    def test_classify_no_match(self):
        """매칭 없는 콘텐츠"""
        results = classify_content(self.tax, "요리 레시피 소개")
        self.assertEqual(results, [])

    def test_classify_case_insensitive(self):
        """대소문자 무시"""
        results = classify_content(self.tax, "PYTHON programming")
        self.assertGreater(len(results), 0)


class TestGetPath(unittest.TestCase):
    """경로 조회 테스트"""

    def setUp(self):
        self.tax = create_taxonomy("루트")
        root_id = self.tax.root_id
        self.tax = add_category(self.tax, root_id, "레벨1")
        l1_id = self.tax.nodes[1].node_id
        self.tax = add_category(self.tax, l1_id, "레벨2")
        self.l2_id = self.tax.nodes[2].node_id

    def test_get_path_leaf(self):
        """리프 노드까지 경로"""
        path = get_path(self.tax, self.l2_id)
        self.assertEqual(path, ["루트", "레벨1", "레벨2"])

    def test_get_path_root(self):
        """루트 노드 경로"""
        path = get_path(self.tax, self.tax.root_id)
        self.assertEqual(path, ["루트"])

    def test_get_path_invalid(self):
        """잘못된 노드 ID"""
        with self.assertRaises(ValueError):
            get_path(self.tax, "nonexistent")


class TestGetDepth(unittest.TestCase):
    """깊이 조회 테스트"""

    def test_depth_root_only(self):
        """루트만 있는 분류체계"""
        tax = create_taxonomy("루트")
        self.assertEqual(get_depth(tax), 0)

    def test_depth_nested(self):
        """중첩된 분류체계"""
        tax = create_taxonomy("루트")
        tax = add_category(tax, tax.root_id, "L1")
        l1_id = tax.nodes[1].node_id
        tax = add_category(tax, l1_id, "L2")
        self.assertEqual(get_depth(tax), 2)


class TestFindNode(unittest.TestCase):
    """노드 검색 테스트"""

    def test_find_existing(self):
        """기존 노드 검색"""
        tax = create_taxonomy("기술")
        tax = add_category(tax, tax.root_id, "Python")
        result = find_node(tax, "Python")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "Python")

    def test_find_case_insensitive(self):
        """대소문자 무시 검색"""
        tax = create_taxonomy("기술")
        tax = add_category(tax, tax.root_id, "Python")
        result = find_node(tax, "python")
        self.assertIsNotNone(result)

    def test_find_nonexistent(self):
        """존재하지 않는 노드"""
        tax = create_taxonomy("기술")
        result = find_node(tax, "Ruby")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
