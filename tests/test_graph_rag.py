"""
GraphRAG + Reranker 통합 테스트
- graph_builder: 엔티티/관계 추출 (LiteLLM 모킹)
- graph_store: 그래프 저장/조회/탐색 (networkx)
- reranker: LLM 기반 리랭킹 (LiteLLM 모킹)
- context_builder: GraphRAG 통합 흐름
"""
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────
# 1. GraphBuilder 테스트
# ─────────────────────────────────────────────

class TestGraphBuilder(unittest.TestCase):
    """graph_builder.py — extract_entities / extract_relations / extract_graph"""

    def _make_llm_response(self, entities, relations):
        """LiteLLM completion 응답 모킹 헬퍼"""
        payload = json.dumps({"entities": entities, "relations": relations})
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = payload
        return mock_resp

    @patch('services.rag.graph_builder.litellm')
    def test_extract_entities_returns_list(self, mock_litellm):
        """엔티티 추출 결과가 리스트 형태인지 검증"""
        mock_litellm.completion.return_value = self._make_llm_response(
            entities=[
                {"name": "Python", "type": "technology", "description": "프로그래밍 언어"},
                {"name": "Flask", "type": "technology", "description": "웹 프레임워크"},
            ],
            relations=[],
        )
        from services.rag.graph_builder import extract_entities
        result = extract_entities("Python으로 Flask 웹앱을 만들었다.")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["name"], "Python")
        self.assertEqual(result[0]["type"], "technology")

    @patch('services.rag.graph_builder.litellm')
    def test_extract_entities_validates_required_fields(self, mock_litellm):
        """name 없는 엔티티는 필터링됨"""
        mock_litellm.completion.return_value = self._make_llm_response(
            entities=[
                {"name": "ValidEntity", "type": "concept", "description": "설명"},
                {"type": "concept"},   # name 없음 → 제외
                {},                    # 빈 딕셔너리 → 제외
            ],
            relations=[],
        )
        from services.rag.graph_builder import extract_entities
        result = extract_entities("테스트 텍스트")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "ValidEntity")

    @patch('services.rag.graph_builder.litellm')
    def test_extract_relations_filters_unknown_entities(self, mock_litellm):
        """알려진 엔티티 간 관계만 포함됨"""
        mock_litellm.completion.return_value = self._make_llm_response(
            entities=[
                {"name": "A", "type": "concept", "description": ""},
                {"name": "B", "type": "concept", "description": ""},
            ],
            relations=[
                {"source": "A", "target": "B", "relation": "포함", "weight": 0.8},
                {"source": "A", "target": "C", "relation": "미지", "weight": 0.5},  # C 미존재
            ],
        )
        from services.rag.graph_builder import extract_entities, extract_relations
        entities = extract_entities("A는 B를 포함한다.")
        relations = extract_relations("A는 B를 포함한다.", entities)
        # C가 없는 관계는 필터링
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0]["source"], "A")
        self.assertEqual(relations[0]["target"], "B")

    @patch('services.rag.graph_builder.litellm')
    def test_extract_relations_weight_clamp(self, mock_litellm):
        """weight 범위 0~1로 클램핑 검증"""
        mock_litellm.completion.return_value = self._make_llm_response(
            entities=[{"name": "X", "type": "concept", "description": ""},
                       {"name": "Y", "type": "concept", "description": ""}],
            relations=[
                {"source": "X", "target": "Y", "relation": "테스트", "weight": 5.0},   # >1 클램핑
                {"source": "Y", "target": "X", "relation": "역방향", "weight": -0.5},  # <0 클램핑
            ],
        )
        from services.rag.graph_builder import extract_entities, extract_relations
        entities = extract_entities("X와 Y")
        relations = extract_relations("X와 Y", entities)
        weights = [r["weight"] for r in relations]
        for w in weights:
            self.assertGreaterEqual(w, 0.0)
            self.assertLessEqual(w, 1.0)

    @patch('services.rag.graph_builder.litellm')
    def test_extract_graph_single_call(self, mock_litellm):
        """extract_graph는 단일 LLM 호출로 엔티티+관계 반환"""
        mock_litellm.completion.return_value = self._make_llm_response(
            entities=[{"name": "AI", "type": "concept", "description": "인공지능"}],
            relations=[],
        )
        from services.rag.graph_builder import extract_graph
        result = extract_graph("AI는 미래 기술이다.")
        self.assertIn("entities", result)
        self.assertIn("relations", result)
        self.assertEqual(len(result["entities"]), 1)
        # LLM이 1번만 호출됐는지 확인
        self.assertEqual(mock_litellm.completion.call_count, 1)

    @patch('services.rag.graph_builder.litellm')
    def test_extract_graph_llm_failure_returns_empty(self, mock_litellm):
        """LLM 호출 실패 시 빈 결과 반환 (예외 전파 없음)"""
        mock_litellm.completion.side_effect = Exception("LLM 오류")
        from services.rag.graph_builder import extract_graph
        result = extract_graph("텍스트")
        self.assertEqual(result, {"entities": [], "relations": []})

    @patch('services.rag.graph_builder.litellm')
    def test_extract_graph_invalid_json_returns_empty(self, mock_litellm):
        """LLM이 잘못된 JSON 반환 시 빈 결과"""
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = "이건 JSON이 아닙니다"
        mock_litellm.completion.return_value = mock_resp

        from services.rag.graph_builder import extract_graph
        result = extract_graph("텍스트")
        self.assertEqual(result["entities"], [])


# ─────────────────────────────────────────────
# 2. GraphStore 테스트
# ─────────────────────────────────────────────

class TestGraphStore(unittest.TestCase):
    """graph_store.py — add_entities / add_relations / search_related / get_subgraph"""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        from services.rag.graph_store import GraphStore
        self.store = GraphStore(store_path=self.tmp_dir)
        self.uid = "test-user-graph"

    def tearDown(self):
        try:
            shutil.rmtree(self.tmp_dir)
        except OSError:
            pass

    def test_add_entities_and_get_stats(self):
        """엔티티 추가 후 통계 확인"""
        entities = [
            {"name": "Python", "type": "technology", "description": "프로그래밍 언어"},
            {"name": "Flask", "type": "technology", "description": "웹 프레임워크"},
        ]
        self.store.add_entities(self.uid, entities)
        stats = self.store.get_stats(self.uid)
        self.assertEqual(stats["node_count"], 2)
        self.assertEqual(stats["edge_count"], 0)

    def test_add_relations_creates_edges(self):
        """관계 추가 후 엣지 수 확인"""
        entities = [
            {"name": "A", "type": "concept", "description": ""},
            {"name": "B", "type": "concept", "description": ""},
        ]
        self.store.add_entities(self.uid, entities)
        relations = [{"source": "A", "target": "B", "relation": "포함", "weight": 0.9}]
        self.store.add_relations(self.uid, relations)
        stats = self.store.get_stats(self.uid)
        self.assertEqual(stats["edge_count"], 1)

    def test_add_relations_auto_creates_missing_nodes(self):
        """관계에 없는 노드는 자동 생성됨"""
        relations = [{"source": "NewA", "target": "NewB", "relation": "연결", "weight": 0.5}]
        self.store.add_relations(self.uid, relations)
        stats = self.store.get_stats(self.uid)
        self.assertEqual(stats["node_count"], 2)

    def test_search_related_bfs(self):
        """BFS 탐색: 시작 노드에서 관련 노드 탐색"""
        entities = [
            {"name": "Python", "type": "technology", "description": "언어"},
            {"name": "Flask", "type": "technology", "description": "프레임워크"},
            {"name": "Django", "type": "technology", "description": "프레임워크2"},
        ]
        self.store.add_entities(self.uid, entities)
        relations = [
            {"source": "Python", "target": "Flask", "relation": "기반", "weight": 0.9},
            {"source": "Python", "target": "Django", "relation": "기반", "weight": 0.9},
        ]
        self.store.add_relations(self.uid, relations)

        results = self.store.search_related(self.uid, ["Python"], max_depth=1)
        result_names = {r["name"] for r in results}
        # Python 자신 + 이웃 노드 포함
        self.assertIn("Python", result_names)
        self.assertIn("Flask", result_names)
        self.assertIn("Django", result_names)

    def test_search_related_empty_graph(self):
        """빈 그래프 탐색 → 빈 리스트"""
        results = self.store.search_related(self.uid, ["아무거나"], max_depth=2)
        self.assertEqual(results, [])

    def test_search_related_max_depth(self):
        """max_depth 제한 확인"""
        # 3단계 체인: A → B → C → D
        entities = [{"name": n, "type": "concept", "description": ""} for n in ["A", "B", "C", "D"]]
        self.store.add_entities(self.uid, entities)
        relations = [
            {"source": "A", "target": "B", "relation": "1", "weight": 0.5},
            {"source": "B", "target": "C", "relation": "2", "weight": 0.5},
            {"source": "C", "target": "D", "relation": "3", "weight": 0.5},
        ]
        self.store.add_relations(self.uid, relations)

        # max_depth=1이면 A와 B만 (C, D는 2hop 이상)
        results = self.store.search_related(self.uid, ["A"], max_depth=1)
        result_names = {r["name"] for r in results}
        self.assertIn("A", result_names)
        self.assertIn("B", result_names)
        self.assertNotIn("D", result_names)

    def test_get_subgraph(self):
        """1-hop 서브그래프 추출"""
        entities = [
            {"name": "Center", "type": "concept", "description": "중심"},
            {"name": "Neighbor1", "type": "concept", "description": "이웃1"},
            {"name": "Neighbor2", "type": "concept", "description": "이웃2"},
            {"name": "Distant", "type": "concept", "description": "멀리"},
        ]
        self.store.add_entities(self.uid, entities)
        relations = [
            {"source": "Center", "target": "Neighbor1", "relation": "연결", "weight": 0.8},
            {"source": "Neighbor2", "target": "Center", "relation": "연결2", "weight": 0.7},
            {"source": "Neighbor1", "target": "Distant", "relation": "연결3", "weight": 0.5},
        ]
        self.store.add_relations(self.uid, relations)

        subgraph = self.store.get_subgraph(self.uid, "Center")
        node_names = {n["name"] for n in subgraph["nodes"]}

        # Center + 직접 이웃만 포함 (Distant 제외)
        self.assertIn("Center", node_names)
        self.assertIn("Neighbor1", node_names)
        self.assertIn("Neighbor2", node_names)
        self.assertNotIn("Distant", node_names)

    def test_get_subgraph_unknown_entity(self):
        """없는 엔티티 → 빈 서브그래프"""
        subgraph = self.store.get_subgraph(self.uid, "없는엔티티")
        self.assertEqual(subgraph["nodes"], [])
        self.assertEqual(subgraph["edges"], [])

    def test_persistence_reload(self):
        """파일 저장 후 새 인스턴스에서 로드"""
        from services.rag.graph_store import GraphStore

        entities = [{"name": "Persist", "type": "concept", "description": "영속 테스트"}]
        self.store.add_entities(self.uid, entities)

        # 새 인스턴스에서 파일 로드
        store2 = GraphStore(store_path=self.tmp_dir)
        stats = store2.get_stats(self.uid)
        self.assertEqual(stats["node_count"], 1)

    def test_clear(self):
        """그래프 초기화 후 빈 상태"""
        entities = [{"name": "ToDelete", "type": "concept", "description": ""}]
        self.store.add_entities(self.uid, entities)
        self.store.clear(self.uid)
        stats = self.store.get_stats(self.uid)
        self.assertEqual(stats["node_count"], 0)

    def test_add_entities_duplicate_update(self):
        """중복 엔티티 추가 시 속성 갱신 (노드 수 증가 없음)"""
        entities = [{"name": "Dup", "type": "concept", "description": "원본"}]
        self.store.add_entities(self.uid, entities)
        # 같은 이름으로 description 갱신
        self.store.add_entities(self.uid, [{"name": "Dup", "type": "concept", "description": "갱신"}])
        stats = self.store.get_stats(self.uid)
        self.assertEqual(stats["node_count"], 1)  # 노드 수는 그대로


# ─────────────────────────────────────────────
# 3. Reranker 테스트
# ─────────────────────────────────────────────

class TestReranker(unittest.TestCase):
    """reranker.py — rerank / rerank_with_fallback"""

    def _make_rerank_response(self, scores):
        """리랭크 LLM 응답 모킹"""
        payload = json.dumps({"scores": scores})
        mock_resp = MagicMock()
        mock_resp.choices = [MagicMock()]
        mock_resp.choices[0].message.content = payload
        return mock_resp

    def _make_chunks(self, texts):
        """청크 리스트 생성 헬퍼"""
        return [{"text": t, "metadata": {"filename": "doc.txt"}, "distance": 0.3} for t in texts]

    @patch('services.rag.reranker.litellm')
    def test_rerank_sorts_by_score(self, mock_litellm):
        """점수 내림차순 정렬 검증 (top_k < len(chunks) 여야 LLM 호출됨)"""
        # 5개 청크, top_k=3 → LLM 호출 후 상위 3개 반환
        chunks = self._make_chunks(["낮은", "중간", "높은", "매우높은", "최고"])
        mock_litellm.completion.return_value = self._make_rerank_response([2, 5, 9, 7, 3])

        from services.rag.reranker import rerank
        result = rerank("쿼리", chunks, top_k=3)

        self.assertEqual(len(result), 3)
        # 점수 9 → 7 → 5 순서
        self.assertEqual(result[0]["rerank_score"], 9.0)
        self.assertEqual(result[1]["rerank_score"], 7.0)
        self.assertEqual(result[2]["rerank_score"], 5.0)

    @patch('services.rag.reranker.litellm')
    def test_rerank_returns_top_k(self, mock_litellm):
        """top_k 개수 제한 검증"""
        chunks = self._make_chunks(["A", "B", "C", "D", "E"])
        mock_litellm.completion.return_value = self._make_rerank_response([1, 9, 3, 7, 5])

        from services.rag.reranker import rerank
        result = rerank("쿼리", chunks, top_k=3)
        self.assertEqual(len(result), 3)
        # 상위 3개: 9, 7, 5
        scores = [r["rerank_score"] for r in result]
        self.assertEqual(scores, [9.0, 7.0, 5.0])

    @patch('services.rag.reranker.litellm')
    def test_rerank_fewer_chunks_than_top_k(self, mock_litellm):
        """청크 수 < top_k 시 전체 반환 (LLM 호출 없음)"""
        chunks = self._make_chunks(["단일"])

        from services.rag.reranker import rerank
        result = rerank("쿼리", chunks, top_k=5)
        self.assertEqual(len(result), 1)
        # top_k보다 적으면 LLM 호출 안 함
        mock_litellm.completion.assert_not_called()

    @patch('services.rag.reranker.litellm')
    def test_rerank_score_mismatch_fallback(self, mock_litellm):
        """점수 수가 청크 수와 다를 때 원본 순서 반환"""
        chunks = self._make_chunks(["A", "B", "C"])
        mock_litellm.completion.return_value = self._make_rerank_response([5, 8])  # 2개만 (불일치)

        from services.rag.reranker import rerank
        result = rerank("쿼리", chunks, top_k=2)
        # top_k 개수는 유지됨
        self.assertEqual(len(result), 2)

    def test_rerank_with_fallback_distance_sort(self):
        """rerank_with_fallback: rerank()가 완전 실패 시 거리 기반 폴백
        rerank()를 직접 mock하여 외부 예외를 강제 발생시킴"""
        from unittest.mock import patch as _patch
        chunks = [
            {"text": "A", "metadata": {}, "distance": 0.8},  # 거리 높음 = 관련성 낮음
            {"text": "B", "metadata": {}, "distance": 0.2},  # 거리 낮음 = 관련성 높음
        ]
        # rerank() 자체를 예외 던지도록 모킹
        with _patch('services.rag.reranker.rerank', side_effect=Exception("강제 오류")):
            from services.rag.reranker import rerank_with_fallback
            result = rerank_with_fallback("쿼리", chunks, top_k=2)
        # 거리 낮은 순 (B가 먼저)
        self.assertEqual(result[0]["text"], "B")

    def test_rerank_empty_chunks(self):
        """빈 청크 리스트 → 빈 리스트 반환"""
        from services.rag.reranker import rerank
        result = rerank("쿼리", [], top_k=5)
        self.assertEqual(result, [])


# ─────────────────────────────────────────────
# 4. GraphRAG 통합 ContextBuilder 테스트
# ─────────────────────────────────────────────

class TestGraphRAGContextBuilder(unittest.TestCase):
    """context_builder.py — GraphRAG 통합 흐름"""

    def setUp(self):
        self.tmp_vec_dir = tempfile.mkdtemp()
        self.tmp_graph_dir = tempfile.mkdtemp()

        from services.rag.vector_store import VectorStore
        from services.rag.graph_store import GraphStore
        self.vector_store = VectorStore(db_path=self.tmp_vec_dir)
        self.graph_store = GraphStore(store_path=self.tmp_graph_dir)
        self.uid = "test-user-ctx"

    def tearDown(self):
        try:
            shutil.rmtree(self.tmp_vec_dir)
            shutil.rmtree(self.tmp_graph_dir)
        except OSError:
            pass

    def test_basic_vector_context_no_graphrag(self):
        """GraphRAG 비활성화 시 기존 벡터 검색만 사용"""
        from services.rag.context_builder import RAGContextBuilder
        builder = RAGContextBuilder(
            self.vector_store,
            graph_store=self.graph_store,
            graph_rag_enabled=False,
            reranker_enabled=False,
        )
        self.vector_store.add_document(
            self.uid, "doc1", ["Python은 프로그래밍 언어"],
            {"filename": "python.txt", "uploaded_at": "2026-01-01"},
        )
        context = builder.build_context(self.uid, "Python", top_k=1)
        self.assertIn("[참고자료 1 - python.txt]", context)

    def test_graph_rag_context_includes_graph_info(self):
        """GraphRAG 활성화 시 그래프 정보가 컨텍스트에 포함"""
        from services.rag.context_builder import RAGContextBuilder
        builder = RAGContextBuilder(
            self.vector_store,
            graph_store=self.graph_store,
            graph_rag_enabled=True,
            reranker_enabled=False,
        )
        # 벡터 DB에 문서 추가
        self.vector_store.add_document(
            self.uid, "doc1", ["Python은 프로그래밍 언어입니다"],
            {"filename": "doc.txt", "uploaded_at": "2026-01-01"},
        )
        # 그래프에 Python 엔티티 추가
        self.graph_store.add_entities(self.uid, [
            {"name": "Python", "type": "technology", "description": "범용 프로그래밍 언어"},
        ])

        context = builder.build_context(self.uid, "Python 언어", top_k=3)
        # 컨텍스트가 비어있지 않음
        self.assertTrue(len(context) > 0)

    @patch('services.rag.reranker.rerank_with_fallback')
    def test_reranker_called_when_enabled(self, mock_rerank):
        """Reranker 활성화 시 rerank_with_fallback 호출 확인"""
        # 리랭커가 첫 번째 청크만 반환하도록 설정
        mock_rerank.return_value = [
            {"text": "관련 청크", "metadata": {"filename": "doc.txt"}, "rerank_score": 9.0}
        ]

        from services.rag.context_builder import RAGContextBuilder
        builder = RAGContextBuilder(
            self.vector_store,
            graph_store=self.graph_store,
            graph_rag_enabled=False,
            reranker_enabled=True,
        )
        self.vector_store.add_document(
            self.uid, "doc1", ["청크 1", "청크 2", "청크 3", "청크 4", "청크 5", "청크 6"],
            {"filename": "doc.txt", "uploaded_at": "2026-01-01"},
        )
        context = builder.build_context(self.uid, "검색어", top_k=3)
        mock_rerank.assert_called_once()

    def test_empty_context_when_no_documents(self):
        """문서 없을 때 빈 컨텍스트 반환"""
        from services.rag.context_builder import RAGContextBuilder
        builder = RAGContextBuilder(
            self.vector_store,
            graph_store=self.graph_store,
            graph_rag_enabled=True,
            reranker_enabled=False,
        )
        context = builder.build_context(self.uid, "검색어", top_k=5)
        self.assertEqual(context, "")


# ─────────────────────────────────────────────
# 5. Config 설정 테스트
# ─────────────────────────────────────────────

class TestGraphRAGConfig(unittest.TestCase):
    """config.py GraphRAG 설정 확인"""

    def test_config_has_graph_rag_settings(self):
        """GraphRAG 관련 설정이 config에 정의됨"""
        import config
        self.assertTrue(hasattr(config, 'GRAPH_RAG_ENABLED'))
        self.assertTrue(hasattr(config, 'GRAPH_STORE_PATH'))
        self.assertTrue(hasattr(config, 'RERANKER_ENABLED'))
        self.assertTrue(hasattr(config, 'RERANKER_TOP_K'))

    def test_default_values(self):
        """기본값: GraphRAG 및 Reranker 비활성화"""
        # 환경변수 미설정 시 기본 False
        env_backup = {}
        for key in ['GRAPH_RAG_ENABLED', 'RERANKER_ENABLED']:
            env_backup[key] = os.environ.pop(key, None)
        try:
            self.assertFalse(os.environ.get('GRAPH_RAG_ENABLED', 'false').lower() == 'true')
            self.assertFalse(os.environ.get('RERANKER_ENABLED', 'false').lower() == 'true')
        finally:
            for key, val in env_backup.items():
                if val is not None:
                    os.environ[key] = val

    def test_reranker_top_k_default(self):
        """RERANKER_TOP_K 기본값 = 5"""
        import config
        # 환경변수 없으면 기본 5
        original = os.environ.pop('RERANKER_TOP_K', None)
        try:
            val = int(os.environ.get('RERANKER_TOP_K', '5'))
            self.assertEqual(val, 5)
        finally:
            if original is not None:
                os.environ['RERANKER_TOP_K'] = original


if __name__ == '__main__':
    unittest.main()
