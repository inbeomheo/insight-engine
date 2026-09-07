"""
graph_builder 단위 테스트
"""
import unittest
from unittest.mock import patch, MagicMock

from services.rag.graph_builder import (
    extract_entities,
    extract_relations,
    extract_graph,
    extract_graph_from_chunks,
    _call_llm,
)


def _mock_llm_response(content: str):
    """litellm.completion 응답 mock 객체 생성"""
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = content
    return mock_resp


class TestCallLLM(unittest.TestCase):

    @patch('services.usage.usage_decorator.mark_usage_charge_committed')
    @patch('services.rag.graph_builder.litellm')
    def test_explicit_callback_runs_at_provider_boundary(
        self,
        mock_litellm,
        mock_mark,
    ):
        events = []
        mock_litellm.completion.side_effect = lambda **_kwargs: (
            events.append('provider')
            or _mock_llm_response('{"entities": [], "relations": []}')
        )

        _call_llm(
            'text',
            'model',
            on_cost_start=lambda: events.append('cost'),
        )

        self.assertEqual(events, ['cost', 'provider'])
        mock_mark.assert_not_called()

    @patch('services.rag.graph_builder.litellm')
    def test_successful_extraction(self, mock_litellm):
        resp_json = '{"entities": [{"name": "Python", "type": "technology"}], "relations": []}'
        mock_litellm.completion.return_value = _mock_llm_response(resp_json)
        result = _call_llm("Python is great", "test-model")
        self.assertEqual(len(result["entities"]), 1)
        self.assertEqual(result["entities"][0]["name"], "Python")

    @patch('services.rag.graph_builder.litellm')
    def test_json_in_code_block(self, mock_litellm):
        resp = '```json\n{"entities": [{"name": "A"}], "relations": []}\n```'
        mock_litellm.completion.return_value = _mock_llm_response(resp)
        result = _call_llm("text", "model")
        self.assertEqual(len(result["entities"]), 1)

    @patch('services.rag.graph_builder.litellm')
    def test_invalid_json(self, mock_litellm):
        mock_litellm.completion.return_value = _mock_llm_response("not json at all")
        result = _call_llm("text", "model")
        self.assertEqual(result["entities"], [])
        self.assertEqual(result["relations"], [])

    @patch('services.usage.usage_decorator.mark_usage_charge_committed')
    @patch('services.rag.graph_builder.litellm')
    def test_llm_exception_keeps_charge_committed(self, mock_litellm, mock_mark):
        def fail_after_provider_start(**_kwargs):
            self.assertTrue(mock_mark.called)
            raise Exception("API 에러")

        mock_litellm.completion.side_effect = fail_after_provider_start
        result = _call_llm("text", "model")
        self.assertEqual(result["entities"], [])
        mock_mark.assert_called_once_with()

    @patch('services.usage.usage_decorator.mark_usage_charge_committed')
    @patch('services.rag.graph_builder.litellm')
    def test_usage_lock_loss_is_not_swallowed(self, mock_litellm, mock_mark):
        from services.usage.usage_lock import UsageLockUnavailable

        mock_mark.side_effect = UsageLockUnavailable('lease lost')
        with self.assertRaises(UsageLockUnavailable):
            _call_llm("text", "model")

        mock_litellm.completion.assert_not_called()


class TestExtractEntities(unittest.TestCase):

    @patch('services.rag.graph_builder._call_llm')
    def test_extracts_and_validates(self, mock_call):
        mock_call.return_value = {
            "entities": [
                {"name": "Python", "type": "technology", "description": "언어"},
                {"name": "", "type": "tech"},  # 빈 이름 → 필터링됨
                "invalid_entity",               # dict가 아님 → 필터링됨
            ],
            "relations": [],
        }
        result = extract_entities("text")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "Python")

    @patch('services.rag.graph_builder._call_llm')
    def test_defaults(self, mock_call):
        mock_call.return_value = {
            "entities": [{"name": "X"}],
            "relations": [],
        }
        result = extract_entities("text")
        self.assertEqual(result[0]["type"], "concept")
        self.assertEqual(result[0]["description"], "")


class TestExtractRelations(unittest.TestCase):

    @patch('services.rag.graph_builder._call_llm')
    def test_filters_by_entity_names(self, mock_call):
        mock_call.return_value = {
            "entities": [],
            "relations": [
                {"source": "A", "target": "B", "relation": "관련", "weight": 0.8},
                {"source": "A", "target": "Z", "relation": "관련"},  # Z는 엔티티에 없음
            ],
        }
        entities = [{"name": "A"}, {"name": "B"}]
        result = extract_relations("text", entities)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["source"], "A")
        self.assertEqual(result[0]["target"], "B")

    @patch('services.rag.graph_builder._call_llm')
    def test_clamps_weight(self, mock_call):
        mock_call.return_value = {
            "entities": [],
            "relations": [
                {"source": "A", "target": "B", "relation": "r", "weight": 5.0},
            ],
        }
        entities = [{"name": "A"}, {"name": "B"}]
        result = extract_relations("text", entities)
        self.assertEqual(result[0]["weight"], 1.0)

    @patch('services.rag.graph_builder._call_llm')
    def test_invalid_weight_defaults(self, mock_call):
        mock_call.return_value = {
            "entities": [],
            "relations": [
                {"source": "A", "target": "B", "relation": "r", "weight": "invalid"},
            ],
        }
        entities = [{"name": "A"}, {"name": "B"}]
        result = extract_relations("text", entities)
        self.assertEqual(result[0]["weight"], 0.5)


class TestExtractGraph(unittest.TestCase):

    @patch('services.rag.graph_builder._call_llm')
    def test_combined_extraction(self, mock_call):
        mock_call.return_value = {
            "entities": [
                {"name": "A", "type": "concept", "description": "desc_a"},
                {"name": "B", "type": "person"},
            ],
            "relations": [
                {"source": "A", "target": "B", "relation": "knows", "weight": 0.9},
            ],
        }
        result = extract_graph("text")
        self.assertEqual(len(result["entities"]), 2)
        self.assertEqual(len(result["relations"]), 1)


class TestExtractGraphFromChunks(unittest.TestCase):

    @patch('services.rag.graph_builder.extract_graph')
    def test_merges_chunks(self, mock_extract):
        mock_extract.side_effect = [
            {"entities": [{"name": "A", "type": "t", "description": "short"}],
             "relations": [{"source": "A", "target": "B", "relation": "r1"}]},
            {"entities": [{"name": "A", "type": "t", "description": "longer description"},
                          {"name": "C", "type": "t"}],
             "relations": [{"source": "A", "target": "C", "relation": "r2"}]},
        ]
        result = extract_graph_from_chunks(["chunk1", "chunk2"])
        # A의 description은 더 긴 쪽으로 갱신
        entities_by_name = {e["name"]: e for e in result["entities"]}
        self.assertEqual(entities_by_name["A"]["description"], "longer description")
        self.assertEqual(len(result["relations"]), 2)

    @patch('services.rag.graph_builder.extract_graph')
    def test_deduplicates_relations(self, mock_extract):
        mock_extract.side_effect = [
            {"entities": [{"name": "A"}], "relations": [{"source": "A", "target": "B", "relation": "r"}]},
            {"entities": [{"name": "B"}], "relations": [{"source": "A", "target": "B", "relation": "r"}]},
        ]
        result = extract_graph_from_chunks(["c1", "c2"])
        self.assertEqual(len(result["relations"]), 1)

    @patch('services.rag.graph_builder.extract_graph')
    def test_skips_empty_chunks(self, mock_extract):
        mock_extract.return_value = {"entities": [{"name": "X"}], "relations": []}
        result = extract_graph_from_chunks(["", "  ", "valid"])
        mock_extract.assert_called_once_with(
            "valid",
            model=unittest.mock.ANY,
            on_cost_start=None,
        )


if __name__ == "__main__":
    unittest.main()
