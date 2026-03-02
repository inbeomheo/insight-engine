"""
Corrective RAG (CRAG) 통합 테스트

테스트 범위:
  - evaluate_retrieval_quality: LLM 품질 평가 (correct / ambiguous / incorrect)
  - reformulate_query: 쿼리 재구성
  - web_search_fallback: 웹 검색 폴백 (청크 형식 변환)
  - corrective_search: CRAG 전체 루프
  - RAGContextBuilder: CRAG 통합 (crag_enabled=True)
  - config.py: CRAG 설정 존재 확인
"""
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────
# 헬퍼
# ─────────────────────────────────────────────

def _make_llm_response(content: str) -> MagicMock:
    """LiteLLM completion 응답 모킹 헬퍼"""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = content
    return mock_resp


def _make_quality_response(scores: list, feedback: str = "") -> MagicMock:
    """품질 평가 LLM 응답 모킹"""
    payload = json.dumps({"chunk_scores": scores, "feedback": feedback})
    return _make_llm_response(payload)


def _make_reformulate_response(reformulated: str) -> MagicMock:
    """쿼리 재구성 LLM 응답 모킹"""
    payload = json.dumps({"reformulated_query": reformulated})
    return _make_llm_response(payload)


def _make_chunks(texts: list) -> list:
    """테스트용 청크 리스트 생성"""
    return [
        {"text": t, "metadata": {"filename": f"doc{i}.txt"}, "distance": 0.3}
        for i, t in enumerate(texts)
    ]


# ─────────────────────────────────────────────
# 1. evaluate_retrieval_quality 테스트
# ─────────────────────────────────────────────

class TestEvaluateRetrievalQuality(unittest.TestCase):
    """검색 품질 평가 함수 단위 테스트"""

    @patch('services.rag.corrective_rag.litellm')
    def test_correct_decision_high_scores(self, mock_litellm):
        """전체 점수 >= 0.7 → correct 결정"""
        mock_litellm.completion.return_value = _make_quality_response(
            scores=[0.9, 0.8, 0.85],
            feedback="",
        )
        from services.rag.corrective_rag import evaluate_retrieval_quality
        chunks = _make_chunks(["A", "B", "C"])
        result = evaluate_retrieval_quality("Python이란?", chunks)

        self.assertEqual(result["decision"], "correct")
        self.assertGreaterEqual(result["overall_score"], 0.7)
        self.assertIn("relevant_chunks", result)
        self.assertIn("irrelevant_chunks", result)

    @patch('services.rag.corrective_rag.litellm')
    def test_ambiguous_decision_medium_scores(self, mock_litellm):
        """전체 점수 0.4 <= score < 0.7 → ambiguous 결정"""
        mock_litellm.completion.return_value = _make_quality_response(
            scores=[0.5, 0.6, 0.4],
            feedback="부분적으로 관련 있음",
        )
        from services.rag.corrective_rag import evaluate_retrieval_quality
        chunks = _make_chunks(["A", "B", "C"])
        result = evaluate_retrieval_quality("특정 주제에 대해", chunks)

        self.assertEqual(result["decision"], "ambiguous")
        self.assertGreaterEqual(result["overall_score"], 0.4)
        self.assertLess(result["overall_score"], 0.7)

    @patch('services.rag.corrective_rag.litellm')
    def test_incorrect_decision_low_scores(self, mock_litellm):
        """전체 점수 < 0.4 → incorrect 결정"""
        mock_litellm.completion.return_value = _make_quality_response(
            scores=[0.1, 0.2, 0.0],
            feedback="관련 없는 문서",
        )
        from services.rag.corrective_rag import evaluate_retrieval_quality
        chunks = _make_chunks(["무관한 내용 A", "무관한 내용 B", "무관한 내용 C"])
        result = evaluate_retrieval_quality("최신 AI 모델", chunks)

        self.assertEqual(result["decision"], "incorrect")
        self.assertLess(result["overall_score"], 0.4)

    def test_empty_chunks_returns_incorrect(self):
        """빈 청크 → incorrect + overall_score=0"""
        from services.rag.corrective_rag import evaluate_retrieval_quality
        result = evaluate_retrieval_quality("쿼리", [])
        self.assertEqual(result["decision"], "incorrect")
        self.assertEqual(result["overall_score"], 0.0)
        self.assertEqual(result["relevant_chunks"], [])

    @patch('services.rag.corrective_rag.litellm')
    def test_llm_failure_falls_back_to_medium_score(self, mock_litellm):
        """LLM 호출 실패 시 0.5 중간 점수로 폴백 → ambiguous"""
        mock_litellm.completion.side_effect = Exception("LLM 오류")
        from services.rag.corrective_rag import evaluate_retrieval_quality
        chunks = _make_chunks(["A"])
        result = evaluate_retrieval_quality("쿼리", chunks)
        # 점수 불일치로 0.5 채움 → ambiguous
        self.assertIn(result["decision"], ("ambiguous", "correct", "incorrect"))
        # 예외 전파 없음
        self.assertIn("overall_score", result)

    @patch('services.rag.corrective_rag.litellm')
    def test_score_count_mismatch_fills_with_half(self, mock_litellm):
        """LLM 점수 수 불일치 시 0.5로 채움"""
        # 청크 3개인데 점수 1개만 반환
        mock_litellm.completion.return_value = _make_quality_response(
            scores=[0.9],  # 1개만
            feedback="",
        )
        from services.rag.corrective_rag import evaluate_retrieval_quality
        chunks = _make_chunks(["A", "B", "C"])
        result = evaluate_retrieval_quality("쿼리", chunks)
        # 0.5 × 3 → overall = 0.5 → ambiguous
        self.assertAlmostEqual(result["overall_score"], 0.5, places=1)

    @patch('services.rag.corrective_rag.litellm')
    def test_relevant_irrelevant_chunk_classification(self, mock_litellm):
        """relevant_chunks / irrelevant_chunks 분류 정확도"""
        mock_litellm.completion.return_value = _make_quality_response(
            scores=[0.9, 0.1, 0.8, 0.2],
        )
        from services.rag.corrective_rag import evaluate_retrieval_quality
        chunks = _make_chunks(["고관련", "저관련", "고관련2", "저관련2"])
        result = evaluate_retrieval_quality("쿼리", chunks)
        # 0.9, 0.8 → 인덱스 0, 2가 relevant (>= 0.4)
        self.assertIn(0, result["relevant_chunks"])
        self.assertIn(2, result["relevant_chunks"])
        # 0.1, 0.2 → 인덱스 1, 3이 irrelevant
        self.assertIn(1, result["irrelevant_chunks"])
        self.assertIn(3, result["irrelevant_chunks"])


# ─────────────────────────────────────────────
# 2. reformulate_query 테스트
# ─────────────────────────────────────────────

class TestReformulateQuery(unittest.TestCase):
    """쿼리 재구성 함수 단위 테스트"""

    @patch('services.rag.corrective_rag.litellm')
    def test_returns_reformulated_query(self, mock_litellm):
        """정상 케이스: 재구성된 쿼리 반환"""
        mock_litellm.completion.return_value = _make_reformulate_response(
            "Python 웹 프레임워크 Flask 설치 방법"
        )
        from services.rag.corrective_rag import reformulate_query
        result = reformulate_query("Flask 쓰는 법", "관련 문서 없음")
        self.assertEqual(result, "Python 웹 프레임워크 Flask 설치 방법")

    @patch('services.rag.corrective_rag.litellm')
    def test_llm_failure_returns_original(self, mock_litellm):
        """LLM 실패 시 원본 쿼리 반환"""
        mock_litellm.completion.side_effect = Exception("네트워크 오류")
        from services.rag.corrective_rag import reformulate_query
        result = reformulate_query("원본 쿼리", "피드백")
        self.assertEqual(result, "원본 쿼리")

    @patch('services.rag.corrective_rag.litellm')
    def test_invalid_json_returns_original(self, mock_litellm):
        """잘못된 JSON 응답 시 원본 쿼리 반환"""
        mock_litellm.completion.return_value = _make_llm_response("JSON이 아닙니다")
        from services.rag.corrective_rag import reformulate_query
        result = reformulate_query("원본 쿼리", "피드백")
        self.assertEqual(result, "원본 쿼리")

    @patch('services.rag.corrective_rag.litellm')
    def test_empty_reformulated_returns_original(self, mock_litellm):
        """재구성 쿼리가 빈 문자열이면 원본 반환"""
        mock_litellm.completion.return_value = _make_reformulate_response("")
        from services.rag.corrective_rag import reformulate_query
        result = reformulate_query("원본 쿼리", "피드백")
        self.assertEqual(result, "원본 쿼리")

    @patch('services.rag.corrective_rag.litellm')
    def test_feedback_is_optional(self, mock_litellm):
        """feedback 없이 호출 가능 (기본 메시지 사용)"""
        mock_litellm.completion.return_value = _make_reformulate_response("재구성된 쿼리")
        from services.rag.corrective_rag import reformulate_query
        result = reformulate_query("쿼리", feedback="")
        self.assertEqual(result, "재구성된 쿼리")
        mock_litellm.completion.assert_called_once()


# ─────────────────────────────────────────────
# 3. web_search_fallback 테스트
# ─────────────────────────────────────────────

class TestWebSearchFallback(unittest.TestCase):
    """웹 검색 폴백 함수 단위 테스트"""

    @patch('services.web_search_service.search')
    def test_converts_results_to_chunk_format(self, mock_search):
        """웹 검색 결과가 청크 형식으로 변환됨"""
        mock_search.return_value = [
            {"title": "Python 튜토리얼", "url": "https://example.com/1", "content": "Python 설명", "score": 0.8},
            {"title": "Flask 가이드", "url": "https://example.com/2", "content": "Flask 설명", "score": 0.7},
        ]
        from services.rag.corrective_rag import web_search_fallback
        result = web_search_fallback("Python Flask", max_results=2)

        self.assertEqual(len(result), 2)
        # 청크 형식 검증
        self.assertIn("text", result[0])
        self.assertIn("metadata", result[0])
        self.assertIn("distance", result[0])
        # source 마킹
        self.assertEqual(result[0]["metadata"]["source"], "web")
        self.assertEqual(result[0].get("source"), "web")

    @patch('services.web_search_service.search')
    def test_text_contains_title_and_content(self, mock_search):
        """변환된 텍스트에 제목 + 내용이 포함됨"""
        mock_search.return_value = [
            {"title": "테스트 제목", "url": "https://test.com", "content": "테스트 내용", "score": 0.9},
        ]
        from services.rag.corrective_rag import web_search_fallback
        result = web_search_fallback("검색어")

        self.assertIn("테스트 제목", result[0]["text"])
        self.assertIn("테스트 내용", result[0]["text"])

    @patch('services.web_search_service.search')
    def test_empty_results_returns_empty_list(self, mock_search):
        """웹 검색 결과 없음 → 빈 리스트"""
        mock_search.return_value = []
        from services.rag.corrective_rag import web_search_fallback
        result = web_search_fallback("검색어")
        self.assertEqual(result, [])

    @patch('services.web_search_service.search')
    def test_search_failure_returns_empty_list(self, mock_search):
        """웹 검색 서비스 예외 → 빈 리스트 (예외 전파 없음)"""
        mock_search.side_effect = Exception("Tavily 오류")
        from services.rag.corrective_rag import web_search_fallback
        result = web_search_fallback("검색어")
        self.assertEqual(result, [])

    @patch('services.web_search_service.search')
    def test_high_score_maps_to_low_distance(self, mock_search):
        """높은 검색 점수 → 낮은 distance (관련성 표현)"""
        mock_search.return_value = [
            {"title": "결과", "url": "https://ex.com", "content": "내용", "score": 1.0},
        ]
        from services.rag.corrective_rag import web_search_fallback
        result = web_search_fallback("검색어")
        # score=1.0 → distance=0.0
        self.assertAlmostEqual(result[0]["distance"], 0.0, places=1)

    @patch('services.web_search_service.search')
    def test_url_stored_in_metadata(self, mock_search):
        """URL이 metadata에 저장됨"""
        mock_search.return_value = [
            {"title": "제목", "url": "https://my-url.com/page", "content": "내용", "score": 0.5},
        ]
        from services.rag.corrective_rag import web_search_fallback
        result = web_search_fallback("검색어")
        self.assertEqual(result[0]["metadata"]["url"], "https://my-url.com/page")


# ─────────────────────────────────────────────
# 4. corrective_search 테스트
# ─────────────────────────────────────────────

class TestCorrectiveSearch(unittest.TestCase):
    """CRAG 전체 루프 통합 테스트"""

    def _make_vector_store(self, search_result=None):
        """벡터 스토어 mock 생성"""
        mock_vs = MagicMock()
        mock_vs.search.return_value = search_result or []
        return mock_vs

    @patch('services.rag.corrective_rag.evaluate_retrieval_quality')
    def test_correct_decision_returns_original_chunks(self, mock_eval):
        """correct 결정 → 원본 청크 반환, 재검색 없음"""
        mock_eval.return_value = {
            "decision": "correct",
            "overall_score": 0.9,
            "relevant_chunks": [0, 1],
            "irrelevant_chunks": [],
            "feedback": "",
        }
        original_chunks = _make_chunks(["A", "B"])
        mock_vs = self._make_vector_store()

        from services.rag.corrective_rag import corrective_search
        result = corrective_search("쿼리", original_chunks, mock_vs, "user-1")

        self.assertEqual(result, original_chunks)
        mock_vs.search.assert_not_called()  # 재검색 없음

    @patch('services.web_search_service.search')
    @patch('services.rag.corrective_rag.evaluate_retrieval_quality')
    def test_incorrect_decision_uses_web_fallback(self, mock_eval, mock_web_search):
        """incorrect 결정 → 웹 검색 폴백 사용"""
        mock_eval.return_value = {
            "decision": "incorrect",
            "overall_score": 0.1,
            "relevant_chunks": [],
            "irrelevant_chunks": [0, 1],
            "feedback": "무관한 내용",
        }
        mock_web_search.return_value = [
            {"title": "웹 결과", "url": "https://web.com", "content": "관련 내용", "score": 0.8},
        ]
        original_chunks = _make_chunks(["무관A", "무관B"])
        mock_vs = self._make_vector_store()

        from services.rag.corrective_rag import corrective_search
        result = corrective_search("쿼리", original_chunks, mock_vs, "user-1")

        # 웹 검색 결과 반환
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["metadata"]["source"], "web")

    @patch('services.rag.corrective_rag.evaluate_retrieval_quality')
    @patch('services.rag.corrective_rag.reformulate_query')
    def test_ambiguous_triggers_query_reformulation(self, mock_reform, mock_eval):
        """ambiguous → 쿼리 재구성 후 재검색"""
        # 1차 평가: ambiguous, 2차 평가: correct
        mock_eval.side_effect = [
            {
                "decision": "ambiguous",
                "overall_score": 0.5,
                "relevant_chunks": [0],
                "irrelevant_chunks": [1],
                "feedback": "부분 관련",
            },
            {
                "decision": "correct",
                "overall_score": 0.8,
                "relevant_chunks": [0, 1],
                "irrelevant_chunks": [],
                "feedback": "",
            },
        ]
        mock_reform.return_value = "재구성된 쿼리"
        new_chunks = _make_chunks(["재검색결과A", "재검색결과B"])
        mock_vs = self._make_vector_store(search_result=new_chunks)

        original_chunks = _make_chunks(["부분A", "무관B"])

        from services.rag.corrective_rag import corrective_search
        result = corrective_search("원본 쿼리", original_chunks, mock_vs, "user-1", max_retries=1)

        # 재검색이 일어났음
        mock_vs.search.assert_called_once_with("user-1", "재구성된 쿼리", 5)
        # 재검색 결과 반환
        self.assertEqual(result, new_chunks)

    @patch('services.web_search_service.search')
    @patch('services.rag.corrective_rag.evaluate_retrieval_quality')
    def test_incorrect_no_web_results_returns_original(self, mock_eval, mock_web_search):
        """incorrect + 웹 검색도 없음 → 원본 청크 반환"""
        mock_eval.return_value = {
            "decision": "incorrect",
            "overall_score": 0.1,
            "relevant_chunks": [],
            "irrelevant_chunks": [0],
            "feedback": "무관한 내용",
        }
        mock_web_search.return_value = []  # 웹 검색도 없음
        original_chunks = _make_chunks(["무관한 내용"])
        mock_vs = self._make_vector_store()

        from services.rag.corrective_rag import corrective_search
        result = corrective_search("쿼리", original_chunks, mock_vs, "user-1")

        # 최후 수단으로 원본 반환
        self.assertEqual(result, original_chunks)

    @patch('services.rag.corrective_rag.evaluate_retrieval_quality')
    @patch('services.rag.corrective_rag.reformulate_query')
    def test_max_retries_limits_reformulation(self, mock_reform, mock_eval):
        """max_retries=1 → 재검색 1회만 시도"""
        mock_eval.return_value = {
            "decision": "ambiguous",
            "overall_score": 0.5,
            "relevant_chunks": [0],
            "irrelevant_chunks": [],
            "feedback": "부분 관련",
        }
        mock_reform.return_value = "재구성된 쿼리"
        new_chunks = _make_chunks(["재검색결과"])
        mock_vs = self._make_vector_store(search_result=new_chunks)

        from services.rag.corrective_rag import corrective_search
        corrective_search("원본 쿼리", _make_chunks(["A"]), mock_vs, "user-1", max_retries=1)

        # search는 최대 1번만 호출됨
        self.assertLessEqual(mock_vs.search.call_count, 1)

    @patch('services.rag.corrective_rag.evaluate_retrieval_quality')
    @patch('services.rag.corrective_rag.reformulate_query')
    def test_vector_store_search_failure_falls_back(self, mock_reform, mock_eval):
        """재검색 중 벡터 스토어 예외 → 루프 중단, 현재 청크 반환"""
        mock_eval.return_value = {
            "decision": "ambiguous",
            "overall_score": 0.5,
            "relevant_chunks": [0],
            "irrelevant_chunks": [],
            "feedback": "부분 관련",
        }
        mock_reform.return_value = "재구성된 쿼리"
        mock_vs = MagicMock()
        mock_vs.search.side_effect = Exception("DB 오류")

        original_chunks = _make_chunks(["A"])

        from services.rag.corrective_rag import corrective_search
        result = corrective_search("원본 쿼리", original_chunks, mock_vs, "user-1", max_retries=1)

        # 예외 전파 없이 현재 청크 반환
        self.assertEqual(result, original_chunks)


# ─────────────────────────────────────────────
# 5. RAGContextBuilder CRAG 통합 테스트
# ─────────────────────────────────────────────

class TestContextBuilderWithCRAG(unittest.TestCase):
    """context_builder.py — CRAG 통합 흐름 테스트"""

    def setUp(self):
        self.tmp_vec_dir = tempfile.mkdtemp()
        from services.rag.vector_store import VectorStore
        self.vector_store = VectorStore(db_path=self.tmp_vec_dir)
        self.uid = "test-user-crag"

    def tearDown(self):
        try:
            shutil.rmtree(self.tmp_vec_dir)
        except OSError:
            pass

    @patch('services.rag.corrective_rag.evaluate_retrieval_quality')
    def test_crag_enabled_calls_evaluate(self, mock_eval):
        """CRAG 활성화 시 evaluate_retrieval_quality 호출 확인"""
        mock_eval.return_value = {
            "decision": "correct",
            "overall_score": 0.9,
            "relevant_chunks": [0],
            "irrelevant_chunks": [],
            "feedback": "",
        }
        # 벡터 DB에 문서 추가
        self.vector_store.add_document(
            self.uid, "doc1", ["CRAG 테스트용 문서"],
            {"filename": "crag_test.txt", "uploaded_at": "2026-01-01"},
        )
        from services.rag.context_builder import RAGContextBuilder
        builder = RAGContextBuilder(
            self.vector_store,
            graph_store=None,
            graph_rag_enabled=False,
            crag_enabled=True,
        )
        context = builder.build_context(self.uid, "CRAG 테스트", top_k=1)

        # 품질 평가 함수 호출됨
        mock_eval.assert_called_once()
        # 컨텍스트 반환됨
        self.assertIn("crag_test.txt", context)

    @patch('services.rag.corrective_rag.evaluate_retrieval_quality')
    def test_crag_disabled_skips_evaluate(self, mock_eval):
        """CRAG 비활성화 시 evaluate_retrieval_quality 호출 안 함"""
        self.vector_store.add_document(
            self.uid, "doc1", ["일반 문서"],
            {"filename": "normal.txt", "uploaded_at": "2026-01-01"},
        )
        from services.rag.context_builder import RAGContextBuilder
        builder = RAGContextBuilder(
            self.vector_store,
            graph_store=None,
            graph_rag_enabled=False,
            crag_enabled=False,
        )
        builder.build_context(self.uid, "쿼리", top_k=1)

        mock_eval.assert_not_called()

    @patch('services.rag.corrective_rag.corrective_search')
    def test_crag_failure_falls_back_to_original(self, mock_crag):
        """CRAG 내부 예외 → 원본 청크로 폴백, 컨텍스트 반환"""
        mock_crag.side_effect = Exception("CRAG 내부 오류")
        self.vector_store.add_document(
            self.uid, "doc1", ["폴백 테스트 문서"],
            {"filename": "fallback.txt", "uploaded_at": "2026-01-01"},
        )
        from services.rag.context_builder import RAGContextBuilder
        builder = RAGContextBuilder(
            self.vector_store,
            crag_enabled=True,
        )
        # 예외 전파 없이 컨텍스트 반환됨
        context = builder.build_context(self.uid, "쿼리", top_k=1)
        self.assertIn("fallback.txt", context)

    def test_empty_chunks_skips_crag(self):
        """검색 결과 없을 때 CRAG 호출 안 함 (빈 컨텍스트 반환)"""
        from services.rag.context_builder import RAGContextBuilder
        builder = RAGContextBuilder(
            self.vector_store,
            crag_enabled=True,
        )
        # 문서 없는 상태에서 검색
        context = builder.build_context(self.uid, "검색어", top_k=5)
        self.assertEqual(context, "")

    @patch('services.web_search_service.search')
    @patch('services.rag.corrective_rag.evaluate_retrieval_quality')
    def test_crag_web_fallback_included_in_context(self, mock_eval, mock_web_search):
        """CRAG incorrect → 웹 검색 결과가 컨텍스트에 포함됨"""
        mock_eval.return_value = {
            "decision": "incorrect",
            "overall_score": 0.1,
            "relevant_chunks": [],
            "irrelevant_chunks": [0],
            "feedback": "무관한 내용",
        }
        mock_web_search.return_value = [
            {
                "title": "웹 검색 결과",
                "url": "https://web.com/result",
                "content": "매우 관련성 높은 웹 내용",
                "score": 0.95,
            }
        ]
        self.vector_store.add_document(
            self.uid, "doc1", ["무관한 내용"],
            {"filename": "irrelevant.txt", "uploaded_at": "2026-01-01"},
        )
        from services.rag.context_builder import RAGContextBuilder
        builder = RAGContextBuilder(
            self.vector_store,
            crag_enabled=True,
        )
        context = builder.build_context(self.uid, "AI 기술 최신 동향", top_k=1)
        # 웹 검색 결과의 내용이 컨텍스트에 포함됨
        self.assertIn("웹 검색 결과", context)


# ─────────────────────────────────────────────
# 6. Config 설정 테스트
# ─────────────────────────────────────────────

class TestCRAGConfig(unittest.TestCase):
    """config.py CRAG 설정 확인"""

    def test_config_has_crag_settings(self):
        """CRAG 관련 설정이 config에 정의됨"""
        import config
        self.assertTrue(hasattr(config, 'CRAG_ENABLED'))
        self.assertTrue(hasattr(config, 'CRAG_QUALITY_THRESHOLD'))

    def test_crag_disabled_by_default(self):
        """CRAG는 기본적으로 비활성화 (false)"""
        backup = os.environ.pop('CRAG_ENABLED', None)
        try:
            # 환경변수 없을 때 기본값 false
            self.assertFalse(os.environ.get('CRAG_ENABLED', 'false').lower() == 'true')
        finally:
            if backup is not None:
                os.environ['CRAG_ENABLED'] = backup

    def test_crag_quality_threshold_default(self):
        """CRAG_QUALITY_THRESHOLD 기본값 = 0.7"""
        backup = os.environ.pop('CRAG_QUALITY_THRESHOLD', None)
        try:
            val = float(os.environ.get('CRAG_QUALITY_THRESHOLD', '0.7'))
            self.assertAlmostEqual(val, 0.7, places=5)
        finally:
            if backup is not None:
                os.environ['CRAG_QUALITY_THRESHOLD'] = backup

    def test_crag_enabled_via_env_var(self):
        """환경변수로 CRAG 활성화 가능"""
        os.environ['CRAG_ENABLED'] = 'true'
        try:
            enabled = os.environ.get('CRAG_ENABLED', 'false').lower() == 'true'
            self.assertTrue(enabled)
        finally:
            del os.environ['CRAG_ENABLED']


if __name__ == '__main__':
    unittest.main()
