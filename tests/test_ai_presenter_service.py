"""
AI 발표자 생성 서비스 테스트
"""
import pytest
from services.ai_presenter_service import (
    generate_presenter,
    PresenterResult,
    _detect_style,
    _split_script,
)


class TestDetectStyle:
    """스타일 감지 테스트."""

    def test_professional(self):
        assert _detect_style("정장을 입은 30대 남성") == "professional"

    def test_casual(self):
        assert _detect_style("캐주얼한 복장의 여성") == "casual"

    def test_educational(self):
        assert _detect_style("칠판 앞의 교수") == "educational"

    def test_default_professional(self):
        assert _detect_style("사람 설명") == "professional"


class TestSplitScript:
    """스크립트 분절 테스트."""

    def test_basic_split(self):
        script = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
        segments = _split_script(script)
        assert len(segments) >= 1
        assert all("text" in s for s in segments)

    def test_empty_script(self):
        assert _split_script("") == []
        assert _split_script("   ") == []

    def test_segment_has_timing(self):
        script = "안녕하세요, 오늘 발표를 시작하겠습니다. 주제는 AI 기술입니다."
        segments = _split_script(script)
        for seg in segments:
            assert "start_time" in seg
            assert "duration" in seg
            assert seg["duration"] > 0

    def test_long_sentence_split(self):
        """200자 초과 문장은 분할됨."""
        long_text = "이것은 매우 긴 문장입니다, " * 20 + "끝."
        segments = _split_script(long_text)
        # 분할이 발생했으므로 최소 2개 이상
        assert len(segments) >= 1


class TestGeneratePresenter:
    """generate_presenter 통합 테스트."""

    def test_empty_description_raises(self):
        with pytest.raises(ValueError, match="외형 설명"):
            generate_presenter("", "스크립트 텍스트")

    def test_empty_script_raises(self):
        with pytest.raises(ValueError, match="스크립트"):
            generate_presenter("정장을 입은 남성", "")

    def test_basic_generation(self):
        """기본 생성 테스트."""
        result = generate_presenter(
            "정장을 입은 30대 남성 발표자",
            "안녕하세요. 오늘은 AI 기술에 대해 알아보겠습니다. 먼저 기본 개념부터 시작하겠습니다."
        )

        assert isinstance(result, PresenterResult)
        assert result.presenter_id
        assert result.appearance["style"] == "professional"
        assert len(result.script_segments) >= 1
        assert result.estimated_duration > 0

    def test_lip_sync_ready(self):
        """스크립트가 있으면 립싱크 준비됨."""
        result = generate_presenter(
            "캐주얼한 여성",
            "오늘의 주제를 소개합니다. 재미있는 내용이 많습니다."
        )
        assert result.lip_sync_ready is True

    def test_appearance_fields(self):
        """외형 정보에 필수 필드 포함."""
        result = generate_presenter(
            "교수 스타일 강사",
            "학생 여러분, 오늘의 수업을 시작하겠습니다."
        )
        appearance = result.appearance
        assert "style" in appearance
        assert "description" in appearance
        assert "posture" in appearance
        assert "expression" in appearance

    def test_educational_style_detected(self):
        """교육 스타일 감지."""
        result = generate_presenter(
            "칠판 앞에 선 교수님",
            "이 개념은 매우 중요합니다. 잘 기억해 두세요."
        )
        assert result.appearance["style"] == "educational"

    def test_segments_sequential_timing(self):
        """세그먼트 시간이 순차적."""
        result = generate_presenter(
            "발표자",
            "첫 번째 포인트입니다. 두 번째 포인트를 설명합니다. 마지막으로 정리하겠습니다."
        )
        for i in range(1, len(result.script_segments)):
            prev = result.script_segments[i - 1]
            curr = result.script_segments[i]
            assert curr["start_time"] >= prev["start_time"]

    def test_whitespace_only_raises(self):
        """공백만 있는 입력은 ValueError."""
        with pytest.raises(ValueError):
            generate_presenter("   ", "스크립트")

        with pytest.raises(ValueError):
            generate_presenter("설명", "   ")
