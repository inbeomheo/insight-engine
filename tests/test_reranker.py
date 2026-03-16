"""
reranker 단위 테스트
"""
import unittest
from unittest.mock import patch, MagicMock

from services.rag.reranker import rerank, rerank_with_fallback


def _mock_llm_response(content: str):
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = content
    return mock_resp


class TestRerank(unittest.TestCase):

    def test_empty_chunks(self):
        result = rerank("쿼리", [], top_k=5)
        self.assertEqual(result, [])

    def test_fewer_chunks_than_top_k(self):
        chunks = [
            {"text": "A", "metadata": {}},
            {"text": "B", "metadata": {}},
        ]
        result = rerank("쿼리", chunks, top_k=5)
        self.assertEqual(len(result), 2)
        for c in result:
            self.assertEqual(c["rerank_score"], 5.0)

    @patch('services.rag.reranker.litellm')
    def test_successful_reranking(self, mock_litellm):
        mock_litellm.completion.return_value = _mock_llm_response(
            '{"scores": [3, 9, 7, 1, 5, 8]}'
        )
        chunks = [{"text": f"chunk{i}", "metadata": {}} for i in range(6)]
        result = rerank("쿼리", chunks, top_k=3)
        self.assertEqual(len(result), 3)
        # 점수 내림차순: 9, 8, 7
        scores = [c["rerank_score"] for c in result]
        self.assertEqual(scores, sorted(scores, reverse=True))

    @patch('services.rag.reranker.litellm')
    def test_score_count_mismatch_fallback(self, mock_litellm):
        """점수 수가 청크 수와 불일치 → 원본 순서 유지"""
        mock_litellm.completion.return_value = _mock_llm_response(
            '{"scores": [5, 8]}'  # 6개 청크인데 2개만 반환
        )
        chunks = [{"text": f"chunk{i}", "metadata": {}} for i in range(6)]
        result = rerank("쿼리", chunks, top_k=3)
        self.assertEqual(len(result), 3)
        for c in result:
            self.assertIn("rerank_score", c)

    @patch('services.rag.reranker.litellm')
    def test_llm_exception_fallback(self, mock_litellm):
        mock_litellm.completion.side_effect = Exception("API 에러")
        chunks = [{"text": f"chunk{i}", "metadata": {}} for i in range(6)]
        result = rerank("쿼리", chunks, top_k=3)
        # 예외 시 scores=[] → score count mismatch → 원본 순서 폴백
        self.assertEqual(len(result), 3)

    @patch('services.rag.reranker.litellm')
    def test_invalid_json_response(self, mock_litellm):
        mock_litellm.completion.return_value = _mock_llm_response("not json")
        chunks = [{"text": f"c{i}", "metadata": {}} for i in range(6)]
        result = rerank("q", chunks, top_k=3)
        self.assertEqual(len(result), 3)

    @patch('services.rag.reranker.litellm')
    def test_invalid_score_value_defaults(self, mock_litellm):
        mock_litellm.completion.return_value = _mock_llm_response(
            '{"scores": [5, "bad", 8, 3, 7, 2]}'
        )
        chunks = [{"text": f"c{i}", "metadata": {}} for i in range(6)]
        result = rerank("q", chunks, top_k=6)
        # "bad" → 5.0 기본값
        scores = [c["rerank_score"] for c in result]
        self.assertIn(5.0, scores)


class TestRerankWithFallback(unittest.TestCase):

    @patch('services.rag.reranker.rerank')
    def test_success_passthrough(self, mock_rerank):
        expected = [{"text": "a", "rerank_score": 9}]
        mock_rerank.return_value = expected
        result = rerank_with_fallback("q", [{"text": "a"}], top_k=1)
        self.assertEqual(result, expected)

    @patch('services.rag.reranker.rerank')
    def test_fallback_sorts_by_distance(self, mock_rerank):
        mock_rerank.side_effect = Exception("전체 실패")
        chunks = [
            {"text": "far", "distance": 0.9},
            {"text": "close", "distance": 0.1},
            {"text": "mid", "distance": 0.5},
        ]
        result = rerank_with_fallback("q", chunks, top_k=2)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["text"], "close")
        self.assertEqual(result[1]["text"], "mid")

    @patch('services.rag.reranker.rerank')
    def test_fallback_default_distance(self, mock_rerank):
        mock_rerank.side_effect = Exception("fail")
        chunks = [{"text": "a"}, {"text": "b"}]
        result = rerank_with_fallback("q", chunks, top_k=5)
        self.assertEqual(len(result), 2)
        for c in result:
            self.assertEqual(c["rerank_score"], 5.0)


if __name__ == "__main__":
    unittest.main()
