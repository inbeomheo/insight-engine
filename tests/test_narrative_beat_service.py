"""narrative_beat_service 단위 테스트"""
import unittest

from services.narrative_beat_service import (
    NarrativeBeat,
    tag_narrative_beats,
    narrative_beats_to_dicts,
    _split_sentences,
    _detect_beat_type,
    _deduplicate_beats,
)


class TestTagNarrativeBeats(unittest.TestCase):
    """tag_narrative_beats 함수 테스트"""

    def test_empty_transcript_raises(self):
        """빈 자막은 ValueError 발생"""
        with self.assertRaises(ValueError):
            tag_narrative_beats("")

    def test_whitespace_raises(self):
        """공백만 있는 자막은 ValueError 발생"""
        with self.assertRaises(ValueError):
            tag_narrative_beats("   \n\t  ")

    def test_short_transcript_raises(self):
        """20자 미만 자막은 ValueError 발생"""
        with self.assertRaises(ValueError):
            tag_narrative_beats("짧은 텍스트입니다")

    def test_basic_narrative_structure(self):
        """기본 서사 구조 탐지 — 최소 1개 비트 반환"""
        transcript = (
            "안녕하세요, 오늘은 인공지능에 대해 소개합니다. "
            "먼저 기본 개념을 알아보겠습니다.\n"
            "그리고 다음으로 머신러닝의 원리를 자세히 살펴보겠습니다. "
            "구체적으로 신경망 구조를 예를 들어 설명합니다.\n"
            "하지만 반면에 이 기술에는 한계가 있습니다. "
            "실제로 데이터 편향 문제가 심각합니다.\n"
            "가장 중요한 핵심은 윤리적 AI 개발입니다. "
            "이것이 결정적인 차이를 만듭니다.\n"
            "결론적으로 정리하면, AI는 도구일 뿐입니다. "
            "감사합니다. 다음에 또 뵙겠습니다."
        )
        beats = tag_narrative_beats(transcript)

        self.assertIsInstance(beats, list)
        self.assertGreater(len(beats), 0)
        for beat in beats:
            self.assertIsInstance(beat, NarrativeBeat)

    def test_beats_sorted_by_position(self):
        """비트는 위치 순으로 정렬"""
        transcript = (
            "안녕하세요, 오늘의 시작입니다.\n"
            "그리고 또한 자세히 살펴봅니다.\n"
            "하지만 그러나 문제가 있습니다.\n"
            "결론적으로 마무리합니다. 감사합니다."
        )
        beats = tag_narrative_beats(transcript)

        for i in range(len(beats) - 1):
            self.assertLessEqual(
                beats[i].start_position,
                beats[i + 1].start_position,
                f"비트 {i}의 위치가 {i+1}보다 뒤에 있음"
            )

    def test_beat_types_are_valid(self):
        """모든 비트 유형이 유효한 값"""
        valid_types = {"introduction", "development", "turning_point", "climax", "resolution"}
        transcript = (
            "안녕하세요 오늘 소개합니다.\n"
            "자세히 살펴보겠습니다.\n"
            "하지만 문제가 있습니다.\n"
            "결론을 정리하겠습니다. 감사합니다."
        )
        beats = tag_narrative_beats(transcript)

        for beat in beats:
            self.assertIn(beat.beat_type, valid_types, f"유효하지 않은 비트: {beat.beat_type}")

    def test_intensity_in_valid_range(self):
        """강도(intensity)는 0.0~1.0 범위"""
        transcript = (
            "안녕하세요, 오늘은 소개합니다. 먼저 기본을 알아봅니다.\n"
            "다음으로 자세히 살펴보겠습니다.\n"
            "결론으로 마무리합니다. 감사합니다."
        )
        beats = tag_narrative_beats(transcript)

        for beat in beats:
            self.assertGreaterEqual(beat.intensity, 0.0)
            self.assertLessEqual(beat.intensity, 1.0)

    def test_default_beats_when_no_keywords(self):
        """키워드 매칭 없을 때 위치 기반 기본 비트 생성"""
        # 서사 키워드 없는 평이한 텍스트
        transcript = (
            "데이터베이스 인덱스 최적화 방법론.\n"
            "B-트리 구조의 특성과 활용.\n"
            "해시 인덱스와 비교 분석.\n"
            "복합 인덱스 설계 패턴."
        )
        beats = tag_narrative_beats(transcript)
        # 기본 비트(introduction, resolution 등)가 생성되어야 함
        self.assertGreater(len(beats), 0)

    def test_text_excerpt_max_100_chars(self):
        """발췌문(text_excerpt)은 최대 100자"""
        transcript = "안녕하세요, " + "아" * 200 + ".\n결론입니다. 감사합니다."
        beats = tag_narrative_beats(transcript)

        for beat in beats:
            self.assertLessEqual(len(beat.text_excerpt), 100)


class TestSplitSentences(unittest.TestCase):
    """_split_sentences 함수 테스트"""

    def test_period_split(self):
        """마침표로 문장 분리"""
        sentences = _split_sentences("첫 번째 문장입니다. 두 번째 문장입니다.")
        self.assertGreaterEqual(len(sentences), 2)

    def test_newline_split(self):
        """줄바꿈으로 문장 분리"""
        sentences = _split_sentences("첫 번째 줄입니다\n두 번째 줄입니다")
        self.assertGreaterEqual(len(sentences), 2)

    def test_short_fragments_excluded(self):
        """5자 미만 조각은 제외"""
        sentences = _split_sentences("안녕. A. B. 긴 문장이 있습니다.")
        # "A", "B"는 5자 미만이므로 제외
        for text, _ in sentences:
            self.assertGreaterEqual(len(text), 5)


class TestDetectBeatType(unittest.TestCase):
    """_detect_beat_type 함수 테스트"""

    def test_introduction_at_start(self):
        """도입 키워드 + 앞부분 위치 → introduction 탐지"""
        result = _detect_beat_type("안녕하세요, 오늘 소개합니다", 0.1)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "introduction")

    def test_resolution_at_end(self):
        """결론 키워드 + 끝부분 위치 → resolution 탐지"""
        result = _detect_beat_type("결론적으로 정리하겠습니다. 감사합니다", 0.9)
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "resolution")

    def test_no_match_returns_none(self):
        """키워드 없으면 None 반환"""
        result = _detect_beat_type("평범한 문장입니다", 0.5)
        self.assertIsNone(result)


class TestDeduplicateBeats(unittest.TestCase):
    """_deduplicate_beats 함수 테스트"""

    def test_consecutive_same_type(self):
        """연속 같은 유형 → 강도 높은 것만 유지"""
        beats = [
            NarrativeBeat("introduction", 0, "문장1", 0.5),
            NarrativeBeat("introduction", 10, "문장2", 0.8),
            NarrativeBeat("development", 50, "문장3", 0.6),
        ]
        result = _deduplicate_beats(beats)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].intensity, 0.8)  # 강도 높은 것
        self.assertEqual(result[1].beat_type, "development")


class TestNarrativeBeatsToDict(unittest.TestCase):
    """직렬화 테스트"""

    def test_to_dicts(self):
        """NarrativeBeat → dict 변환"""
        beats = [
            NarrativeBeat("introduction", 0, "도입", 0.5),
        ]
        result = narrative_beats_to_dicts(beats)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["beat_type"], "introduction")
        self.assertEqual(result[0]["start_position"], 0)
        self.assertIsInstance(result[0], dict)


if __name__ == '__main__':
    unittest.main()
