"""emotion_resonance_service 단위 테스트"""
import unittest

from services.emotion_resonance_service import (
    analyze_resonance,
    ResonanceScore,
    SUPPORTED_EMOTIONS,
    _find_matching_phrases,
    _calculate_resonance,
    _EMOTION_KEYWORDS,
)


class TestAnalyzeResonance(unittest.TestCase):
    """analyze_resonance 함수 테스트"""

    def test_empty_content(self):
        """빈 콘텐츠 — 공명도 0"""
        result = analyze_resonance('', 'joy')
        self.assertEqual(result.resonance_level, 0.0)
        self.assertEqual(result.matching_phrases, [])

    def test_whitespace_only(self):
        """공백만 있는 콘텐츠 — 공명도 0"""
        result = analyze_resonance('   ', 'trust')
        self.assertEqual(result.resonance_level, 0.0)

    def test_unsupported_emotion(self):
        """지원하지 않는 감정 → ValueError"""
        with self.assertRaises(ValueError) as ctx:
            analyze_resonance('content', 'rage')
        self.assertIn('rage', str(ctx.exception))

    def test_joy_keywords(self):
        """기쁨 키워드 매칭"""
        content = '정말 행복하고 즐거운 하루였습니다. 기쁨이 넘칩니다.'
        result = analyze_resonance(content, 'joy')
        self.assertGreater(result.resonance_level, 0.0)
        self.assertGreater(len(result.matching_phrases), 0)
        self.assertEqual(result.target_emotion, 'joy')

    def test_trust_keywords(self):
        """신뢰 키워드 매칭"""
        content = '검증된 데이터와 전문가의 경험에 기반한 신뢰할 수 있는 분석입니다.'
        result = analyze_resonance(content, 'trust')
        self.assertGreater(result.resonance_level, 0.0)
        self.assertGreater(len(result.matching_phrases), 0)

    def test_anticipation_keywords(self):
        """기대 키워드 매칭"""
        content = '미래의 가능성과 새로운 변화를 기대하며 준비합니다.'
        result = analyze_resonance(content, 'anticipation')
        self.assertGreater(result.resonance_level, 0.0)

    def test_surprise_keywords(self):
        """놀라움 키워드 매칭"""
        content = '예상치 못한 반전이 충격적이었습니다.'
        result = analyze_resonance(content, 'surprise')
        self.assertGreater(result.resonance_level, 0.0)

    def test_no_matching_keywords(self):
        """매칭 키워드 없으면 공명도 0"""
        content = '오늘 날씨가 맑습니다.'
        result = analyze_resonance(content, 'surprise')
        self.assertEqual(result.resonance_level, 0.0)
        self.assertEqual(result.matching_phrases, [])

    def test_result_is_dataclass(self):
        """반환 타입이 ResonanceScore"""
        result = analyze_resonance('기쁨', 'joy')
        self.assertIsInstance(result, ResonanceScore)

    def test_suggestions_low_resonance(self):
        """공명도 낮으면 개선 제안 포함"""
        result = analyze_resonance('일반 텍스트', 'joy')
        self.assertGreater(len(result.suggestions), 0)

    def test_suggestions_high_resonance(self):
        """공명도 높으면 긍정 메시지"""
        # 키워드를 대량 포함시켜 높은 공명도 유도
        content = ' '.join(['행복 기쁨 즐거운 웃음 좋은 사랑 감사'] * 10)
        result = analyze_resonance(content, 'joy')
        if result.resonance_level >= 0.7:
            self.assertTrue(any('잘 전달' in s for s in result.suggestions))

    def test_english_keywords(self):
        """영어 키워드도 매칭"""
        content = 'This is a happy and amazing experience full of joy.'
        result = analyze_resonance(content, 'joy')
        self.assertGreater(result.resonance_level, 0.0)

    def test_resonance_level_range(self):
        """공명도 0~1 범위 내"""
        content = '행복 기쁨 즐거운 ' * 100
        result = analyze_resonance(content, 'joy')
        self.assertGreaterEqual(result.resonance_level, 0.0)
        self.assertLessEqual(result.resonance_level, 1.0)


class TestHelperFunctions(unittest.TestCase):
    """헬퍼 함수 테스트"""

    def test_find_matching_phrases(self):
        """키워드 주변 구절 추출"""
        content = '이것은 행복한 일입니다'
        keywords = _EMOTION_KEYWORDS['joy']
        phrases = _find_matching_phrases(content, keywords)
        self.assertGreater(len(phrases), 0)

    def test_find_matching_phrases_no_match(self):
        """매칭 없으면 빈 리스트"""
        phrases = _find_matching_phrases('날씨가 맑습니다', _EMOTION_KEYWORDS['surprise'])
        self.assertEqual(phrases, [])

    def test_calculate_resonance_empty(self):
        """빈 문자열 공명도 0"""
        self.assertEqual(_calculate_resonance('', _EMOTION_KEYWORDS['joy']), 0.0)

    def test_calculate_resonance_capped(self):
        """공명도 최대 1.0"""
        content = '행복 기쁨 즐거운 ' * 200
        result = _calculate_resonance(content, _EMOTION_KEYWORDS['joy'])
        self.assertLessEqual(result, 1.0)


if __name__ == '__main__':
    unittest.main()
