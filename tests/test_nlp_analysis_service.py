"""nlp_analysis_service 단위 테스트 (내부 함수 위주)"""
import json
import unittest

from services.nlp_analysis_service import (
    _parse_analysis_json, _validate_analysis,
    _parse_sentiment_flow, _EMPTY_ANALYSIS,
)


class TestParseAnalysisJson(unittest.TestCase):

    def test_plain_json(self):
        """일반 JSON 파싱"""
        data = {
            "keywords": [{"word": "AI", "relevance": 0.9}],
            "sentiment": {"overall": "positive", "score": 0.7, "aspects": []},
            "topics": [{"topic": "기술", "confidence": 0.8}]
        }
        result = _parse_analysis_json(json.dumps(data))
        self.assertEqual(len(result['keywords']), 1)
        self.assertEqual(result['keywords'][0]['word'], 'AI')

    def test_code_block_json(self):
        """```json 코드블록 내 JSON 파싱"""
        inner = '{"keywords": [], "sentiment": {"overall": "neutral", "score": 0.0, "aspects": []}, "topics": []}'
        raw = f'```json\n{inner}\n```'
        result = _parse_analysis_json(raw)
        self.assertIsNotNone(result)
        self.assertEqual(result['sentiment']['overall'], 'neutral')

    def test_surrounding_text(self):
        """JSON 앞뒤에 텍스트가 있는 경우"""
        raw = '분석 결과입니다:\n{"keywords": [], "sentiment": {"overall": "positive", "score": 0.5, "aspects": []}, "topics": []}\n끝.'
        result = _parse_analysis_json(raw)
        self.assertEqual(result['sentiment']['overall'], 'positive')

    def test_invalid_json(self):
        """잘못된 JSON → 빈 분석 결과"""
        result = _parse_analysis_json('이것은 JSON이 아닙니다')
        self.assertEqual(result['keywords'], [])
        self.assertEqual(result['sentiment']['overall'], 'neutral')

    def test_empty_string(self):
        """빈 문자열 → 빈 분석 결과"""
        result = _parse_analysis_json('')
        self.assertEqual(result, dict(_EMPTY_ANALYSIS))

    def test_none_input(self):
        """None 입력 → 빈 분석 결과"""
        result = _parse_analysis_json(None)
        self.assertEqual(result, dict(_EMPTY_ANALYSIS))


class TestValidateAnalysis(unittest.TestCase):

    def test_valid_full_data(self):
        """유효한 전체 데이터 검증"""
        data = {
            "keywords": [{"word": "파이썬", "relevance": 0.9}],
            "sentiment": {
                "overall": "positive",
                "score": 0.8,
                "aspects": [{"aspect": "성능", "sentiment": "positive", "score": 0.7}]
            },
            "topics": [{"topic": "프로그래밍", "confidence": 0.85}]
        }
        result = _validate_analysis(data)
        self.assertEqual(len(result['keywords']), 1)
        self.assertEqual(result['keywords'][0]['word'], '파이썬')
        self.assertEqual(result['sentiment']['overall'], 'positive')
        self.assertAlmostEqual(result['sentiment']['score'], 0.8)

    def test_invalid_sentiment_overall(self):
        """잘못된 sentiment overall → neutral 기본값"""
        data = {
            "keywords": [],
            "sentiment": {"overall": "unknown_value", "score": 0.5, "aspects": []},
            "topics": []
        }
        result = _validate_analysis(data)
        self.assertEqual(result['sentiment']['overall'], 'neutral')

    def test_score_clamping(self):
        """score 범위 제한 (-1.0 ~ 1.0)"""
        data = {
            "keywords": [],
            "sentiment": {"overall": "positive", "score": 5.0, "aspects": []},
            "topics": []
        }
        result = _validate_analysis(data)
        self.assertEqual(result['sentiment']['score'], 1.0)

    def test_negative_score_clamping(self):
        """음수 score 범위 제한"""
        data = {
            "keywords": [],
            "sentiment": {"overall": "negative", "score": -10.0, "aspects": []},
            "topics": []
        }
        result = _validate_analysis(data)
        self.assertEqual(result['sentiment']['score'], -1.0)

    def test_keywords_max_10(self):
        """keywords 최대 10개 제한"""
        keywords = [{"word": f"kw{i}", "relevance": 0.5} for i in range(15)]
        data = {"keywords": keywords, "sentiment": {}, "topics": []}
        result = _validate_analysis(data)
        self.assertEqual(len(result['keywords']), 10)

    def test_keyword_word_truncation(self):
        """keyword word 50자 제한"""
        data = {
            "keywords": [{"word": "A" * 100, "relevance": 0.5}],
            "sentiment": {},
            "topics": []
        }
        result = _validate_analysis(data)
        self.assertEqual(len(result['keywords'][0]['word']), 50)

    def test_topics_max_5(self):
        """topics 최대 5개 제한"""
        topics = [{"topic": f"t{i}", "confidence": 0.5} for i in range(10)]
        data = {"keywords": [], "sentiment": {}, "topics": topics}
        result = _validate_analysis(data)
        self.assertEqual(len(result['topics']), 5)

    def test_invalid_score_type(self):
        """score가 숫자가 아닌 경우 → 0.0"""
        data = {
            "keywords": [],
            "sentiment": {"overall": "neutral", "score": "not_a_number", "aspects": []},
            "topics": []
        }
        result = _validate_analysis(data)
        self.assertEqual(result['sentiment']['score'], 0.0)

    def test_aspect_invalid_sentiment(self):
        """aspect의 잘못된 sentiment → neutral"""
        data = {
            "keywords": [],
            "sentiment": {
                "overall": "positive",
                "score": 0.5,
                "aspects": [{"aspect": "UI", "sentiment": "amazing", "score": 0.9}]
            },
            "topics": []
        }
        result = _validate_analysis(data)
        self.assertEqual(result['sentiment']['aspects'][0]['sentiment'], 'neutral')

    def test_empty_data(self):
        """빈 dict → 기본 구조 반환"""
        result = _validate_analysis({})
        self.assertEqual(result['keywords'], [])
        self.assertEqual(result['sentiment']['overall'], 'neutral')
        self.assertEqual(result['topics'], [])


class TestParseSentimentFlow(unittest.TestCase):

    def test_valid_flow(self):
        """유효한 감정 흐름 파싱"""
        data = {
            "flow": [
                {"paragraph_index": 0, "text_preview": "서론입니다", "sentiment": "positive", "score": 0.6, "emotion": "기대"},
                {"paragraph_index": 1, "text_preview": "결론입니다", "sentiment": "neutral", "score": 0.1, "emotion": "설명"}
            ],
            "overall_arc": "descending",
            "dominant_emotion": "기대"
        }
        result = _parse_sentiment_flow(json.dumps(data))
        self.assertEqual(len(result['flow']), 2)
        self.assertEqual(result['overall_arc'], 'descending')
        self.assertEqual(result['dominant_emotion'], '기대')

    def test_code_block(self):
        """코드블록 내 JSON 파싱"""
        inner = '{"flow": [], "overall_arc": "stable", "dominant_emotion": "설명"}'
        raw = f'```json\n{inner}\n```'
        result = _parse_sentiment_flow(raw)
        self.assertEqual(result['overall_arc'], 'stable')

    def test_empty_string(self):
        """빈 문자열 → 기본값"""
        result = _parse_sentiment_flow('')
        self.assertEqual(result['flow'], [])
        self.assertEqual(result['overall_arc'], 'stable')

    def test_invalid_json(self):
        """잘못된 JSON → 기본값"""
        result = _parse_sentiment_flow('not json at all')
        self.assertEqual(result['flow'], [])

    def test_invalid_arc(self):
        """잘못된 overall_arc → stable"""
        data = {"flow": [], "overall_arc": "chaotic", "dominant_emotion": "분노"}
        result = _parse_sentiment_flow(json.dumps(data))
        self.assertEqual(result['overall_arc'], 'stable')

    def test_sentiment_validation(self):
        """flow 항목의 잘못된 sentiment → neutral"""
        data = {
            "flow": [{"paragraph_index": 0, "text_preview": "test", "sentiment": "wrong", "score": 0.5, "emotion": "기쁨"}],
            "overall_arc": "stable",
            "dominant_emotion": "기쁨"
        }
        result = _parse_sentiment_flow(json.dumps(data))
        self.assertEqual(result['flow'][0]['sentiment'], 'neutral')

    def test_score_clamping(self):
        """flow score 범위 제한"""
        data = {
            "flow": [{"paragraph_index": 0, "text_preview": "test", "sentiment": "positive", "score": 5.0, "emotion": "기쁨"}],
            "overall_arc": "ascending",
            "dominant_emotion": "기쁨"
        }
        result = _parse_sentiment_flow(json.dumps(data))
        self.assertEqual(result['flow'][0]['score'], 1.0)

    def test_max_30_paragraphs(self):
        """최대 30개 문단 제한"""
        flow = [{"paragraph_index": i, "text_preview": f"p{i}", "sentiment": "neutral", "score": 0.0, "emotion": "설명"} for i in range(40)]
        data = {"flow": flow, "overall_arc": "stable", "dominant_emotion": "설명"}
        result = _parse_sentiment_flow(json.dumps(data))
        self.assertEqual(len(result['flow']), 30)


if __name__ == '__main__':
    unittest.main()
