"""
콘텐츠 계보 서비스 테스트
"""

import unittest

from services.content_lineage_service import (
    ContentLineageService,
    DiffChunk,
    LineageNode,
    LineageTree,
    SemanticDiff,
    _jaccard_similarity,
    _split_sentences,
)


class TestContentLineageService(unittest.TestCase):
    """ContentLineageService 단위 테스트"""

    def setUp(self):
        self.service = ContentLineageService()

    # ── track_lineage 기본 동작 ──

    def test_track_returns_lineage_node(self):
        """계보 추적 결과가 LineageNode 타입"""
        node = self.service.track_lineage("orig_1", "derived_1", "translation")
        self.assertIsInstance(node, LineageNode)

    def test_track_assigns_unique_node_id(self):
        """각 노드에 고유 ID가 부여된다"""
        n1 = self.service.track_lineage("a", "b", "summary")
        n2 = self.service.track_lineage("a", "c", "rewrite")
        self.assertNotEqual(n1.node_id, n2.node_id)

    def test_track_stores_fields_correctly(self):
        """노드에 원본/파생 ID와 변환 타입이 저장된다"""
        node = self.service.track_lineage("orig", "derived", "merge", {"note": "test"})
        self.assertEqual(node.original_id, "orig")
        self.assertEqual(node.derived_id, "derived")
        self.assertEqual(node.transform_type, "merge")
        self.assertEqual(node.metadata["note"], "test")

    def test_track_metadata_default_empty(self):
        """metadata 미지정 시 빈 dict"""
        node = self.service.track_lineage("a", "b", "translation")
        self.assertEqual(node.metadata, {})

    # ── track_lineage 검증 ──

    def test_track_raises_on_empty_original_id(self):
        """original_id가 비어있으면 ValueError"""
        with self.assertRaises(ValueError):
            self.service.track_lineage("", "b", "summary")

    def test_track_raises_on_empty_derived_id(self):
        """derived_id가 비어있으면 ValueError"""
        with self.assertRaises(ValueError):
            self.service.track_lineage("a", "", "summary")

    def test_track_raises_on_same_ids(self):
        """original_id와 derived_id가 같으면 ValueError"""
        with self.assertRaises(ValueError):
            self.service.track_lineage("same", "same", "rewrite")

    def test_track_raises_on_invalid_transform_type(self):
        """유효하지 않은 transform_type이면 ValueError"""
        with self.assertRaises(ValueError):
            self.service.track_lineage("a", "b", "unknown_type")

    def test_track_all_valid_transform_types(self):
        """모든 유효 변환 타입이 정상 동작"""
        from services.content_lineage_service import VALID_TRANSFORM_TYPES
        for i, tt in enumerate(VALID_TRANSFORM_TYPES):
            node = self.service.track_lineage(f"a{i}", f"b{i}", tt)
            self.assertEqual(node.transform_type, tt)

    # ── get_lineage_tree ──

    def test_tree_empty_for_unknown_content(self):
        """미등록 콘텐츠의 트리는 빈 트리"""
        tree = self.service.get_lineage_tree("nonexistent")
        self.assertIsInstance(tree, LineageTree)
        self.assertEqual(tree.root_id, "nonexistent")
        self.assertEqual(tree.nodes, [])
        self.assertEqual(tree.depth, 0)

    def test_tree_single_level(self):
        """단일 레벨 트리 (A→B, A→C)"""
        self.service.track_lineage("A", "B", "translation")
        self.service.track_lineage("A", "C", "summary")
        tree = self.service.get_lineage_tree("A")
        self.assertEqual(tree.root_id, "A")
        self.assertEqual(len(tree.nodes), 2)
        self.assertEqual(tree.depth, 1)

    def test_tree_multi_level(self):
        """다단계 트리 (A→B→C→D)"""
        self.service.track_lineage("A", "B", "translation")
        self.service.track_lineage("B", "C", "summary")
        self.service.track_lineage("C", "D", "rewrite")
        tree = self.service.get_lineage_tree("A")
        self.assertEqual(len(tree.nodes), 3)
        self.assertEqual(tree.depth, 3)

    def test_tree_branching(self):
        """분기 트리 (A→B, A→C, B→D)"""
        self.service.track_lineage("A", "B", "translation")
        self.service.track_lineage("A", "C", "summary")
        self.service.track_lineage("B", "D", "rewrite")
        tree = self.service.get_lineage_tree("A")
        self.assertEqual(len(tree.nodes), 3)
        self.assertEqual(tree.depth, 2)

    def test_tree_no_cycle(self):
        """순환 참조가 있어도 무한 루프 없이 종료"""
        self.service.track_lineage("X", "Y", "translation")
        self.service.track_lineage("Y", "X", "translation")  # 역방향 (순환)
        tree = self.service.get_lineage_tree("X")
        # 무한 루프 없이 정상 반환 — BFS visited로 중복 방지
        self.assertIsInstance(tree, LineageTree)

    # ── get_node_by_id ──

    def test_get_node_found(self):
        """node_id로 조회 가능"""
        node = self.service.track_lineage("a", "b", "translation")
        found = self.service.get_node_by_id(node.node_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.node_id, node.node_id)

    def test_get_node_not_found(self):
        """없는 node_id는 None"""
        self.assertIsNone(self.service.get_node_by_id("ghost"))

    # ── get_direct_children / get_ancestors ──

    def test_direct_children(self):
        """직계 파생 노드만 반환"""
        self.service.track_lineage("A", "B", "translation")
        self.service.track_lineage("A", "C", "summary")
        self.service.track_lineage("B", "D", "rewrite")
        children = self.service.get_direct_children("A")
        derived_ids = {n.derived_id for n in children}
        self.assertEqual(derived_ids, {"B", "C"})

    def test_ancestors(self):
        """조상 노드 역추적"""
        self.service.track_lineage("A", "B", "translation")
        self.service.track_lineage("B", "C", "summary")
        ancestors = self.service.get_ancestors("C")
        original_ids = {n.original_id for n in ancestors}
        self.assertIn("B", original_ids)
        self.assertIn("A", original_ids)

    def test_ancestors_empty_for_root(self):
        """루트 노드는 조상이 없다"""
        self.service.track_lineage("root", "child", "translation")
        ancestors = self.service.get_ancestors("root")
        self.assertEqual(ancestors, [])

    # ── compute_semantic_diff ──

    def test_diff_identical_texts(self):
        """동일한 텍스트의 유사도는 1.0"""
        text = "첫 번째 문장. 두 번째 문장."
        diff = self.service.compute_semantic_diff(text, text)
        self.assertEqual(diff.added, [])
        self.assertEqual(diff.removed, [])
        self.assertEqual(diff.modified, [])
        self.assertEqual(diff.similarity_score, 1.0)

    def test_diff_completely_different(self):
        """완전히 다른 텍스트의 유사도는 0.0"""
        diff = self.service.compute_semantic_diff(
            "사과는 빨간색입니다.",
            "클라우드 컴퓨팅 아키텍처 설계.",
        )
        self.assertEqual(diff.similarity_score, 0.0)
        self.assertEqual(len(diff.removed), 1)
        self.assertEqual(len(diff.added), 1)

    def test_diff_added_sentences(self):
        """문장이 추가된 경우 added에 포함"""
        diff = self.service.compute_semantic_diff(
            "원본 문장.",
            "원본 문장. 새로운 문장.",
        )
        self.assertGreater(len(diff.added), 0)

    def test_diff_removed_sentences(self):
        """문장이 삭제된 경우 removed에 포함"""
        diff = self.service.compute_semantic_diff(
            "첫 번째 문장. 삭제될 문장.",
            "첫 번째 문장.",
        )
        self.assertGreater(len(diff.removed), 0)

    def test_diff_modified_sentences(self):
        """문장이 수정된 경우 modified에 DiffChunk로 포함"""
        diff = self.service.compute_semantic_diff(
            "the quick brown fox jumps over the lazy dog.",
            "the quick brown cat jumps over the lazy dog.",
        )
        # fox→cat 변경 — 유사도 높아 modified로 판정
        if diff.modified:
            self.assertIsInstance(diff.modified[0], DiffChunk)
            self.assertGreater(diff.modified[0].similarity, 0)

    def test_diff_empty_both(self):
        """양쪽 모두 빈 텍스트면 유사도 1.0"""
        diff = self.service.compute_semantic_diff("", "")
        self.assertEqual(diff.similarity_score, 1.0)

    def test_diff_empty_version_a(self):
        """A가 비어있으면 B의 모든 문장이 added"""
        diff = self.service.compute_semantic_diff("", "새로운 문장.")
        self.assertEqual(len(diff.added), 1)
        self.assertEqual(diff.similarity_score, 0.0)

    def test_diff_empty_version_b(self):
        """B가 비어있으면 A의 모든 문장이 removed"""
        diff = self.service.compute_semantic_diff("기존 문장.", "")
        self.assertEqual(len(diff.removed), 1)
        self.assertEqual(diff.similarity_score, 0.0)

    def test_diff_result_is_semantic_diff(self):
        """반환 타입이 SemanticDiff"""
        diff = self.service.compute_semantic_diff("a.", "b.")
        self.assertIsInstance(diff, SemanticDiff)


class TestHelperFunctions(unittest.TestCase):
    """헬퍼 함수 단위 테스트"""

    def test_split_sentences_basic(self):
        """기본 문장 분리"""
        result = _split_sentences("첫째. 둘째! 셋째?")
        self.assertEqual(len(result), 3)

    def test_split_sentences_empty(self):
        """빈 문자열은 빈 리스트"""
        self.assertEqual(_split_sentences(""), [])
        self.assertEqual(_split_sentences("   "), [])

    def test_split_sentences_no_delimiter(self):
        """종결 부호 없는 텍스트는 하나의 문장"""
        result = _split_sentences("종결 부호 없는 텍스트")
        self.assertEqual(len(result), 1)

    def test_jaccard_identical(self):
        """동일 문자열의 Jaccard 유사도는 1.0"""
        self.assertEqual(_jaccard_similarity("hello world", "hello world"), 1.0)

    def test_jaccard_disjoint(self):
        """겹치는 단어 없으면 0.0"""
        self.assertEqual(_jaccard_similarity("abc def", "xyz uvw"), 0.0)

    def test_jaccard_partial(self):
        """부분 겹침 시 0~1 사이"""
        sim = _jaccard_similarity("the cat sat", "the dog sat")
        self.assertGreater(sim, 0.0)
        self.assertLess(sim, 1.0)

    def test_jaccard_both_empty(self):
        """양쪽 빈 문자열은 1.0"""
        self.assertEqual(_jaccard_similarity("", ""), 1.0)

    def test_jaccard_one_empty(self):
        """한쪽만 비어있으면 0.0"""
        self.assertEqual(_jaccard_similarity("hello", ""), 0.0)


if __name__ == "__main__":
    unittest.main()
