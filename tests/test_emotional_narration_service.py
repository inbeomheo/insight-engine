"""
감정 내레이션 서비스 테스트
"""
import pytest
from services.emotional_narration_service import (
    EmotionalNarration,
    EmotionSegment,
    narrate_with_emotion,
    _detect_emotion,
    _split_sentences,
    _get_dominant_emotion,
)


class TestNarrateWithEmotion:
    """narrate_with_emotion 함수 테스트"""

    def test_기본_내레이션_성공(self):
        """기본 텍스트로 내레이션이 정상 반환되는지 확인"""
        result = narrate_with_emotion("안녕하세요. 오늘은 좋은 날입니다.")
        assert isinstance(result, EmotionalNarration)
        assert result.total_segments > 0
        assert result.dominant_emotion
        assert result.text

    def test_빈_텍스트_에러(self):
        """빈 텍스트는 ValueError 발생"""
        with pytest.raises(ValueError, match="내레이션할 텍스트가 필요합니다"):
            narrate_with_emotion("")

    def test_None_텍스트_에러(self):
        """None은 ValueError 발생"""
        with pytest.raises(ValueError):
            narrate_with_emotion(None)

    def test_공백_텍스트_에러(self):
        """공백만 있는 텍스트는 ValueError 발생"""
        with pytest.raises(ValueError):
            narrate_with_emotion("   ")

    def test_기쁨_감지(self):
        """기쁨 감정 키워드가 있는 텍스트"""
        result = narrate_with_emotion("정말 기쁘고 행복한 하루였어요!")
        emotions = [s.emotion for s in result.segments]
        assert "joy" in emotions or result.dominant_emotion == "joy"

    def test_슬픔_감지(self):
        """슬픔 감정 키워드가 있는 텍스트"""
        result = narrate_with_emotion("너무 슬프고 눈물이 나요.")
        emotions = [s.emotion for s in result.segments]
        assert "sadness" in emotions

    def test_분노_감지(self):
        """분노 감정 키워드가 있는 텍스트"""
        result = narrate_with_emotion("정말 화나고 짜증나는 상황이다.")
        emotions = [s.emotion for s in result.segments]
        assert "anger" in emotions

    def test_emotion_tags_우선_적용(self):
        """emotion_tags가 감지에 우선 적용됨"""
        result = narrate_with_emotion(
            "기쁘고 행복해요.", emotion_tags=["joy"]
        )
        assert any(s.emotion == "joy" for s in result.segments)

    def test_세그먼트에_ssml_hint_포함(self):
        """각 세그먼트에 SSML 힌트가 있는지 확인"""
        result = narrate_with_emotion("기쁜 소식입니다! 슬픈 이야기도 있어요.")
        for segment in result.segments:
            assert isinstance(segment, EmotionSegment)
            assert segment.ssml_hint.startswith("<prosody")

    def test_강도_범위(self):
        """강도가 0~1 범위인지 확인"""
        result = narrate_with_emotion("정말 기쁘고 행복하고 즐거운 하루!")
        for segment in result.segments:
            assert 0.0 <= segment.intensity <= 1.0

    def test_단일_문장_처리(self):
        """문장 구분자 없는 단일 텍스트도 처리"""
        result = narrate_with_emotion("구분자없는텍스트")
        assert result.total_segments >= 1

    def test_total_segments_정확성(self):
        """total_segments가 segments 리스트 길이와 일치"""
        result = narrate_with_emotion("첫 문장. 두번째 문장. 세번째 문장.")
        assert result.total_segments == len(result.segments)

    def test_neutral_감정_기본값(self):
        """감정 키워드 없는 문장은 neutral"""
        result = narrate_with_emotion("이것은 일반적인 설명 문장입니다")
        assert any(s.emotion == "neutral" for s in result.segments)


class TestDetectEmotion:
    """_detect_emotion 함수 테스트"""

    def test_기쁨_감지(self):
        """'행복' 키워드로 joy 감지"""
        emotion, intensity = _detect_emotion("행복한 순간")
        assert emotion == "joy"
        assert intensity > 0

    def test_공포_감지(self):
        """'무서운' 키워드로 fear 감지"""
        emotion, intensity = _detect_emotion("무서운 이야기")
        assert emotion == "fear"

    def test_놀람_감지(self):
        """'놀라운' 키워드로 surprise 감지"""
        emotion, intensity = _detect_emotion("놀라운 일이 벌어졌다")
        assert emotion == "surprise"

    def test_키워드_없으면_neutral(self):
        """키워드 없는 텍스트는 neutral"""
        emotion, intensity = _detect_emotion("xyz abc")
        assert emotion == "neutral"

    def test_emotion_tags_우선(self):
        """emotion_tags에 해당하는 감정이 우선 매칭"""
        emotion, _ = _detect_emotion("기쁘고 행복한 날", emotion_tags=["joy"])
        assert emotion == "joy"

    def test_매칭_많을수록_높은_강도(self):
        """키워드가 많을수록 강도가 높음"""
        _, intensity1 = _detect_emotion("기쁘다")
        _, intensity2 = _detect_emotion("기쁘고 행복하고 즐거운 축하")
        assert intensity2 >= intensity1

    def test_영어_키워드_감지(self):
        """영어 감정 키워드도 감지"""
        emotion, _ = _detect_emotion("I am so happy and glad")
        assert emotion == "joy"


class TestSplitSentences:
    """_split_sentences 함수 테스트"""

    def test_마침표_분리(self):
        """마침표로 문장 분리"""
        result = _split_sentences("첫 문장. 두번째 문장.")
        assert len(result) == 2

    def test_느낌표_분리(self):
        """느낌표로 문장 분리"""
        result = _split_sentences("놀라워! 정말이야!")
        assert len(result) == 2

    def test_물음표_분리(self):
        """물음표로 문장 분리"""
        result = _split_sentences("정말? 진짜?")
        assert len(result) == 2

    def test_빈_텍스트(self):
        """빈 텍스트는 빈 리스트"""
        result = _split_sentences("")
        assert result == []

    def test_공백만_제거(self):
        """빈 요소는 제거됨"""
        result = _split_sentences("문장.   ")
        assert all(s.strip() for s in result)


class TestGetDominantEmotion:
    """_get_dominant_emotion 함수 테스트"""

    def test_빈_세그먼트_neutral(self):
        """빈 세그먼트 목록은 neutral 반환"""
        assert _get_dominant_emotion([]) == "neutral"

    def test_모두_neutral이면_neutral(self):
        """모든 세그먼트가 neutral이면 neutral"""
        segs = [EmotionSegment("t", "neutral", 0.3, "")]
        assert _get_dominant_emotion(segs) == "neutral"

    def test_가장_빈번한_감정_반환(self):
        """가장 빈번한 비-neutral 감정 반환"""
        segs = [
            EmotionSegment("a", "joy", 0.7, ""),
            EmotionSegment("b", "joy", 0.8, ""),
            EmotionSegment("c", "sadness", 0.6, ""),
        ]
        assert _get_dominant_emotion(segs) == "joy"
