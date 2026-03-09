"""smart_reframe_service 단위 테스트"""
import pytest
from services.smart_reframe_service import (
    reframe_for_shorts,
    get_supported_aspects,
    ReframeResult,
    _determine_strategy,
    _parse_time,
    _split_transcript_segments,
)


class TestReframeForShorts:
    """reframe_for_shorts 함수 테스트"""

    def test_basic_9_16(self):
        """기본 9:16 리프레임"""
        result = reframe_for_shorts("vid1")
        assert isinstance(result, ReframeResult)
        assert result.video_id == "vid1"
        assert result.original_aspect == "16:9"
        assert result.target_aspect == "9:16"
        assert len(result.crop_regions) >= 1

    def test_1_1_aspect(self):
        """1:1 정사각형 리프레임"""
        result = reframe_for_shorts("vid2", aspect="1:1")
        assert result.target_aspect == "1:1"
        for region in result.crop_regions:
            assert region["w"] == 1080
            assert region["h"] == 1080

    def test_4_5_aspect(self):
        """4:5 인스타 피드 리프레임"""
        result = reframe_for_shorts("vid3", aspect="4:5")
        assert result.target_aspect == "4:5"
        for region in result.crop_regions:
            assert region["w"] == 864

    def test_unsupported_aspect_raises(self):
        """지원하지 않는 비율 → ValueError"""
        with pytest.raises(ValueError, match="지원하지 않는 화면 비율"):
            reframe_for_shorts("vid4", aspect="21:9")

    def test_empty_video_id_raises(self):
        """빈 video_id → ValueError"""
        with pytest.raises(ValueError, match="video_id"):
            reframe_for_shorts("")

    def test_with_timed_transcript(self):
        """타임스탬프 포함 자막으로 리프레임"""
        transcript = (
            "[0:00] 안녕하세요 여러분\n"
            "[0:30] 오늘은 리프레임에 대해 설명하겠습니다\n"
            "[1:00] 저는 이 기능을 자주 사용합니다\n"
            "[1:30] 여러분도 해보세요\n"
            "[2:00] 감사합니다\n"
        )
        result = reframe_for_shorts("vid5", transcript=transcript)
        assert len(result.crop_regions) >= 1
        # 첫 구간은 0:00 시작
        assert result.crop_regions[0]["start"] == "0:00"

    def test_crop_region_within_bounds(self):
        """크롭 영역이 원본 해상도 내에 있는지"""
        result = reframe_for_shorts("vid6", aspect="9:16")
        for region in result.crop_regions:
            assert region["x"] >= 0
            assert region["y"] >= 0
            assert region["x"] + region["w"] <= 1920
            assert region["y"] + region["h"] <= 1080

    def test_strategy_center_without_transcript(self):
        """자막 없으면 center 전략"""
        result = reframe_for_shorts("vid7")
        assert result.strategy == "center"

    def test_strategy_speaker_track(self):
        """발표 패턴 자막 → speaker_track 전략"""
        transcript = "저는 여러분 안녕하세요 오늘은 제가 설명 드리겠습니다. " * 5
        result = reframe_for_shorts("vid8", transcript=transcript)
        assert result.strategy == "speaker_track"


class TestDetermineStrategy:
    """_determine_strategy 함수 테스트"""

    def test_empty_returns_center(self):
        assert _determine_strategy("") == "center"

    def test_short_returns_center(self):
        assert _determine_strategy("짧은 텍스트") == "center"

    def test_speaker_keywords(self):
        """발표 키워드 3개 이상 → speaker_track"""
        text = "저는 여러분 안녕하세요 오늘은 제가 설명하겠습니다. " * 3
        assert _determine_strategy(text) == "speaker_track"

    def test_content_aware(self):
        """일반 긴 텍스트 → content_aware"""
        text = "기술 발전이 빠르게 진행되고 있다. 다양한 분야에서 활용된다. " * 10
        assert _determine_strategy(text) == "content_aware"


class TestGetSupportedAspects:
    """get_supported_aspects 함수 테스트"""

    def test_returns_dict(self):
        result = get_supported_aspects()
        assert isinstance(result, dict)
        assert "9:16" in result
        assert "1:1" in result

    def test_labels(self):
        result = get_supported_aspects()
        assert "Shorts" in result["9:16"]


class TestParseTime:
    """_parse_time 함수 테스트"""

    def test_mm_ss(self):
        assert _parse_time("1:30") == 90

    def test_hh_mm_ss(self):
        assert _parse_time("1:00:00") == 3600


class TestSplitTranscriptSegments:
    """_split_transcript_segments 함수 테스트"""

    def test_empty_transcript(self):
        result = _split_transcript_segments("")
        assert len(result) == 1
        assert result[0]["start_sec"] == 0

    def test_timed_transcript(self):
        transcript = "[0:00] 첫번째\n[0:30] 두번째"
        result = _split_transcript_segments(transcript)
        assert len(result) == 2
        assert result[0]["start_sec"] == 0
        assert result[1]["start_sec"] == 30
