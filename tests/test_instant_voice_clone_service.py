"""
인스턴트 음성 복제 서비스 테스트
"""
import pytest
from services.instant_voice_clone_service import (
    VoiceClone,
    clone_voice,
    _calculate_quality_score,
    _extract_characteristics,
)


class TestCloneVoice:
    """clone_voice 함수 테스트"""

    def test_기본_복제_성공(self):
        """기본 텍스트로 음성 복제가 정상 반환되는지 확인"""
        result = clone_voice("안녕하세요, 이것은 테스트 샘플입니다.")
        assert isinstance(result, VoiceClone)
        assert result.clone_id
        assert result.sample_length > 0
        assert result.quality_score > 0
        assert result.created_at

    def test_음성_이름_지정(self):
        """voice_name을 지정하면 해당 이름이 사용되는지 확인"""
        result = clone_voice("테스트 샘플", voice_name="내 음성")
        assert result.voice_name == "내 음성"

    def test_음성_이름_자동생성(self):
        """voice_name이 비어있으면 자동 생성되는지 확인"""
        result = clone_voice("테스트 샘플")
        assert result.voice_name.startswith("voice_")
        assert len(result.voice_name) > 6

    def test_빈_음성_이름은_자동생성(self):
        """빈 문자열 voice_name도 자동 생성 처리"""
        result = clone_voice("테스트", voice_name="")
        assert result.voice_name.startswith("voice_")

    def test_공백_음성_이름은_자동생성(self):
        """공백만 있는 voice_name도 자동 생성 처리"""
        result = clone_voice("테스트", voice_name="   ")
        assert result.voice_name.startswith("voice_")

    def test_빈_텍스트_에러(self):
        """빈 텍스트는 ValueError 발생"""
        with pytest.raises(ValueError, match="샘플 텍스트가 필요합니다"):
            clone_voice("")

    def test_공백만_있는_텍스트_에러(self):
        """공백만 있는 텍스트는 ValueError 발생"""
        with pytest.raises(ValueError, match="샘플 텍스트가 필요합니다"):
            clone_voice("   ")

    def test_None_텍스트_에러(self):
        """None 텍스트는 ValueError 발생"""
        with pytest.raises(ValueError):
            clone_voice(None)

    def test_샘플_길이_정확성(self):
        """sample_length가 strip된 텍스트 길이와 일치하는지 확인"""
        text = "  테스트 문장  "
        result = clone_voice(text)
        assert result.sample_length == len(text.strip())

    def test_clone_id_유니크(self):
        """두 번 호출 시 clone_id가 다른지 확인"""
        r1 = clone_voice("샘플1")
        r2 = clone_voice("샘플2")
        assert r1.clone_id != r2.clone_id

    def test_characteristics_기본키_존재(self):
        """characteristics에 pitch, speed, tone 키가 항상 존재"""
        result = clone_voice("일반적인 텍스트입니다.")
        assert "pitch" in result.characteristics
        assert "speed" in result.characteristics
        assert "tone" in result.characteristics


class TestCalculateQualityScore:
    """품질 점수 계산 테스트"""

    def test_빈_텍스트_점수_0(self):
        """길이 0이면 점수 0"""
        assert _calculate_quality_score(0) == 0.0

    def test_음수_길이_점수_0(self):
        """음수 길이면 점수 0"""
        assert _calculate_quality_score(-5) == 0.0

    def test_짧은_텍스트_낮은_점수(self):
        """짧은 텍스트(5자)는 낮은 점수"""
        score = _calculate_quality_score(5)
        assert 40.0 <= score <= 60.0

    def test_중간_텍스트_중간_점수(self):
        """중간 텍스트(60자)는 중간 점수"""
        score = _calculate_quality_score(60)
        assert 70.0 <= score <= 90.0

    def test_긴_텍스트_높은_점수(self):
        """긴 텍스트(250자)는 높은 점수"""
        score = _calculate_quality_score(250)
        assert score >= 90.0

    def test_최대_100_제한(self):
        """아무리 길어도 100을 넘지 않음"""
        score = _calculate_quality_score(10000)
        assert score <= 100.0

    def test_길이_증가에_따른_점수_증가(self):
        """길이가 길수록 점수가 높거나 같음"""
        scores = [_calculate_quality_score(i) for i in [10, 50, 100, 200]]
        for i in range(len(scores) - 1):
            assert scores[i] <= scores[i + 1]


class TestExtractCharacteristics:
    """음성 특성 추출 테스트"""

    def test_기본_특성(self):
        """키워드 없는 텍스트는 기본 특성 반환"""
        result = _extract_characteristics("일반적인 문장")
        assert result["pitch"] == "medium"
        assert result["speed"] == "normal"
        assert result["tone"] == "warm"

    def test_높은_피치_감지(self):
        """'높은' 키워드로 high pitch 감지"""
        result = _extract_characteristics("높은 목소리로 말합니다")
        assert result["pitch"] == "high"

    def test_낮은_피치_감지(self):
        """'낮은' 키워드로 low pitch 감지"""
        result = _extract_characteristics("낮은 톤의 깊은 목소리")
        assert result["pitch"] == "low"

    def test_빠른_속도_감지(self):
        """'빠른' 키워드로 fast speed 감지"""
        result = _extract_characteristics("빠른 속도로 전달합니다")
        assert result["speed"] == "fast"

    def test_느린_속도_감지(self):
        """'천천히' 키워드로 slow speed 감지"""
        result = _extract_characteristics("천천히 말하는 스타일")
        assert result["speed"] == "slow"

    def test_밝은_톤_감지(self):
        """'밝은' 키워드로 bright tone 감지"""
        result = _extract_characteristics("밝고 명랑한 분위기")
        assert result["tone"] == "bright"

    def test_차분한_톤_감지(self):
        """'차분한' 키워드로 calm tone 감지"""
        result = _extract_characteristics("차분하고 안정적인 어조")
        assert result["tone"] == "calm"

    def test_영어_키워드_감지(self):
        """영어 키워드도 감지"""
        result = _extract_characteristics("a deep voice with slow pace")
        assert result["pitch"] == "low"
        assert result["speed"] == "slow"
