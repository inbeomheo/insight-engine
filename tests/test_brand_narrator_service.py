"""
브랜드 내레이터 서비스 테스트
"""
import pytest
from services.brand_narrator_service import (
    NarratorProfile,
    design_narrator,
    _detect_value,
    _build_voice_traits,
    _generate_sample_script,
    _TONE_MAP,
    _PACE_MAP,
    _VOCAB_MAP,
)


class TestDesignNarrator:
    """design_narrator 함수 테스트"""

    def test_기본_프로필_생성(self):
        """설명만으로 내레이터 프로필이 정상 생성되는지 확인"""
        result = design_narrator("일반적인 브랜드 설명입니다")
        assert isinstance(result, NarratorProfile)
        assert result.narrator_id
        assert result.name.startswith("Narrator-")
        assert result.description
        assert result.tone
        assert result.pace
        assert result.vocabulary_level
        assert result.sample_script

    def test_빈_설명_에러(self):
        """빈 설명은 ValueError 발생"""
        with pytest.raises(ValueError, match="브랜드 설명이 필요합니다"):
            design_narrator("")

    def test_None_설명_에러(self):
        """None 설명은 ValueError 발생"""
        with pytest.raises(ValueError):
            design_narrator(None)

    def test_공백_설명_에러(self):
        """공백만 있는 설명은 ValueError 발생"""
        with pytest.raises(ValueError):
            design_narrator("   ")

    def test_전문적_톤_감지(self):
        """'전문적' 키워드로 professional 톤 감지"""
        result = design_narrator("전문적인 비즈니스 브랜드")
        assert result.tone == "professional"

    def test_친근한_톤_감지(self):
        """'친근한' 키워드로 friendly 톤 감지"""
        result = design_narrator("친근하고 따뜻한 브랜드")
        assert result.tone == "friendly"

    def test_재미있는_톤_감지(self):
        """'재미있는' 키워드로 playful 톤 감지"""
        result = design_narrator("재미있고 유쾌한 콘텐츠 브랜드")
        assert result.tone == "playful"

    def test_빠른_속도_감지(self):
        """'빠른' 키워드로 fast pace 감지"""
        result = design_narrator("빠르고 역동적인 스타트업")
        assert result.pace == "fast"

    def test_느린_속도_감지(self):
        """'느린' 키워드로 slow pace 감지"""
        result = design_narrator("느리고 여유로운 라이프스타일")
        assert result.pace == "slow"

    def test_고급_어휘_감지(self):
        """'전문' 키워드로 advanced 어휘 수준 감지"""
        result = design_narrator("전문 기술 블로그 브랜드")
        assert result.vocabulary_level == "advanced"

    def test_쉬운_어휘_감지(self):
        """'쉬운' 키워드로 simple 어휘 수준 감지"""
        result = design_narrator("쉬운 설명의 대중적 브랜드")
        assert result.vocabulary_level == "simple"

    def test_brand_values_반영(self):
        """brand_values가 voice_traits에 반영되는지 확인"""
        result = design_narrator("테스트 브랜드", brand_values=["innovation", "trust"])
        assert any("혁신" in t for t in result.voice_traits)
        assert any("신뢰" in t for t in result.voice_traits)

    def test_brand_values_없으면_기본_특성(self):
        """brand_values 없이도 voice_traits가 생성됨"""
        result = design_narrator("평범한 브랜드 설명")
        assert len(result.voice_traits) > 0

    def test_한국어_brand_values(self):
        """한국어 브랜드 가치도 매핑됨"""
        result = design_narrator("테스트", brand_values=["혁신", "따뜻"])
        traits_text = " ".join(result.voice_traits)
        assert "혁신" in traits_text
        assert "따뜻" in traits_text

    def test_알수없는_brand_value는_직접_추가(self):
        """매핑에 없는 브랜드 가치는 직접 특성으로 추가"""
        result = design_narrator("테스트", brand_values=["독특한가치"])
        assert any("독특한가치" in t for t in result.voice_traits)


class TestDetectValue:
    """_detect_value 함수 테스트"""

    def test_매칭_성공(self):
        """키워드 매칭 시 해당 값 반환"""
        result = _detect_value("전문적인 어조", _TONE_MAP, "default")
        assert result == "professional"

    def test_매칭_실패시_기본값(self):
        """매칭 실패 시 기본값 반환"""
        result = _detect_value("abcdef", _TONE_MAP, "default")
        assert result == "default"

    def test_대소문자_무시(self):
        """대소문자 구분 없이 매칭"""
        result = _detect_value("PROFESSIONAL business", _TONE_MAP, "default")
        assert result == "professional"


class TestBuildVoiceTraits:
    """_build_voice_traits 함수 테스트"""

    def test_빈_입력_기본_특성(self):
        """빈 입력이면 기본 특성 반환"""
        traits = _build_voice_traits("일반 텍스트", [])
        assert len(traits) >= 1

    def test_유머_키워드_감지(self):
        """'유머' 키워드로 특성 추가"""
        traits = _build_voice_traits("유머가 있는 스타일", [])
        assert any("유머" in t for t in traits)

    def test_데이터_키워드_감지(self):
        """'데이터' 키워드로 특성 추가"""
        traits = _build_voice_traits("데이터 기반 분석", [])
        assert any("데이터" in t for t in traits)

    def test_스토리_키워드_감지(self):
        """'스토리' 키워드로 특성 추가"""
        traits = _build_voice_traits("스토리텔링 중심", [])
        assert any("스토리" in t for t in traits)


class TestGenerateSampleScript:
    """_generate_sample_script 함수 테스트"""

    def test_스크립트에_이름_포함(self):
        """샘플 스크립트에 내레이터 이름이 포함됨"""
        script = _generate_sample_script("TestNarr", "professional", "moderate")
        assert "TestNarr" in script

    def test_톤별_다른_인트로(self):
        """톤에 따라 다른 인트로 생성"""
        s1 = _generate_sample_script("N", "friendly", "moderate")
        s2 = _generate_sample_script("N", "authoritative", "moderate")
        assert s1 != s2

    def test_알수없는_톤_기본_인트로(self):
        """알 수 없는 톤이면 기본 인트로 사용"""
        script = _generate_sample_script("N", "unknown_tone", "moderate")
        assert "안녕하세요" in script
