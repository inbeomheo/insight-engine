"""
감정 흐름 분석 (F3-11) 단위 테스트
"""
import json
import unittest
from unittest.mock import patch, MagicMock


class TestSentimentFlow(unittest.TestCase):
    """analyze_sentiment_flow 테스트"""

    MOCK_FLOW_RESPONSE = json.dumps({
        "flow": [
            {"paragraph_index": 0, "text_preview": "인공지능은 미래...", "sentiment": "positive", "score": 0.7, "emotion": "기대"},
            {"paragraph_index": 1, "text_preview": "하지만 우려도...", "sentiment": "negative", "score": -0.4, "emotion": "우려"},
            {"paragraph_index": 2, "text_preview": "결론적으로...", "sentiment": "positive", "score": 0.5, "emotion": "희망"},
        ],
        "overall_arc": "fluctuating",
        "dominant_emotion": "기대",
    })

    def _mock_completion(self, content: str):
        mock = MagicMock()
        mock.choices[0].message.content = content
        return mock

    def test_empty_content(self):
        """빈 콘텐츠"""
        from services.nlp_analysis_service import analyze_sentiment_flow
        result = analyze_sentiment_flow("")
        self.assertEqual(result['flow'], [])
        self.assertEqual(result['overall_arc'], 'stable')

    @patch('services.nlp_analysis_service._get_analysis_model', return_value='zhipuai/GLM-4.5-Air')
    @patch('litellm.completion')
    def test_returns_flow(self, mock_llm, mock_model):
        """정상 응답 시 flow 목록 반환"""
        mock_llm.return_value = self._mock_completion(self.MOCK_FLOW_RESPONSE)

        from services.nlp_analysis_service import analyze_sentiment_flow
        result = analyze_sentiment_flow("인공지능은 미래 기술입니다.")

        self.assertEqual(len(result['flow']), 3)
        self.assertEqual(result['overall_arc'], 'fluctuating')
        self.assertEqual(result['dominant_emotion'], '기대')

    @patch('services.nlp_analysis_service._get_analysis_model', return_value='zhipuai/GLM-4.5-Air')
    @patch('litellm.completion')
    def test_flow_item_structure(self, mock_llm, mock_model):
        """flow 항목 구조 검증"""
        mock_llm.return_value = self._mock_completion(self.MOCK_FLOW_RESPONSE)

        from services.nlp_analysis_service import analyze_sentiment_flow
        result = analyze_sentiment_flow("테스트")

        item = result['flow'][0]
        self.assertIn('paragraph_index', item)
        self.assertIn('text_preview', item)
        self.assertIn('sentiment', item)
        self.assertIn('score', item)
        self.assertIn('emotion', item)
        self.assertIn(item['sentiment'], ('positive', 'neutral', 'negative'))

    @patch('services.nlp_analysis_service._get_analysis_model', return_value='zhipuai/GLM-4.5-Air')
    @patch('litellm.completion', side_effect=Exception("API 오류"))
    def test_llm_failure_graceful(self, mock_llm, mock_model):
        """LLM 실패 시 빈 결과"""
        from services.nlp_analysis_service import analyze_sentiment_flow
        result = analyze_sentiment_flow("테스트")
        self.assertEqual(result['flow'], [])
        self.assertEqual(result['overall_arc'], 'stable')


class TestParseSentimentFlow(unittest.TestCase):
    """_parse_sentiment_flow 파싱 테스트"""

    def setUp(self):
        from services.nlp_analysis_service import _parse_sentiment_flow
        self._parse = _parse_sentiment_flow

    def test_valid_json(self):
        """유효한 JSON"""
        data = {
            "flow": [{"paragraph_index": 0, "text_preview": "A", "sentiment": "positive", "score": 0.5, "emotion": "기쁨"}],
            "overall_arc": "stable",
            "dominant_emotion": "기쁨",
        }
        result = self._parse(json.dumps(data))
        self.assertEqual(len(result['flow']), 1)

    def test_code_block_wrapped(self):
        """```json 래핑"""
        data = {"flow": [], "overall_arc": "ascending", "dominant_emotion": "기대"}
        raw = f"```json\n{json.dumps(data)}\n```"
        result = self._parse(raw)
        self.assertEqual(result['overall_arc'], 'ascending')

    def test_invalid_json(self):
        """잘못된 JSON"""
        result = self._parse("not json")
        self.assertEqual(result['flow'], [])

    def test_empty_string(self):
        result = self._parse("")
        self.assertEqual(result['flow'], [])

    def test_score_clamped(self):
        """score -1~1 클램핑"""
        data = {
            "flow": [{"paragraph_index": 0, "text_preview": "", "sentiment": "positive", "score": 5.0, "emotion": ""}],
            "overall_arc": "stable",
            "dominant_emotion": "",
        }
        result = self._parse(json.dumps(data))
        self.assertLessEqual(result['flow'][0]['score'], 1.0)

    def test_invalid_arc_defaults(self):
        """유효하지 않은 arc는 stable"""
        data = {"flow": [], "overall_arc": "random", "dominant_emotion": ""}
        result = self._parse(json.dumps(data))
        self.assertEqual(result['overall_arc'], 'stable')


if __name__ == '__main__':
    unittest.main()
