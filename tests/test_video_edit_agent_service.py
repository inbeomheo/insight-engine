"""video_edit_agent_service 단위 테스트"""
import pytest
from services.video_edit_agent_service import (
    process_edit_command,
    EditResult,
    _extract_times,
    _format_seconds,
)


class TestProcessEditCommand:
    """process_edit_command 함수 테스트"""

    def test_cut_command_with_time_range(self):
        """시간 범위 지정 cut 명령"""
        result = process_edit_command("vid1", "1:30부터 2:00까지 잘라줘")
        assert isinstance(result, EditResult)
        assert result.video_id == "vid1"
        assert len(result.actions) == 1
        assert result.actions[0]["type"] == "cut"
        assert result.actions[0]["params"]["start"] == "1:30"
        assert result.actions[0]["params"]["end"] == "2:00"

    def test_cut_command_english(self):
        """영어 cut 명령"""
        result = process_edit_command("vid2", "cut from 0:10 to 0:30")
        assert len(result.actions) >= 1
        assert result.actions[0]["type"] == "cut"

    def test_trim_front(self):
        """앞부분 트림"""
        result = process_edit_command("vid3", "앞부분 0:05까지 트림해줘")
        assert len(result.actions) >= 1
        assert result.actions[0]["type"] == "trim"
        assert result.actions[0]["params"]["position"] == "start"

    def test_trim_back(self):
        """뒷부분 트림"""
        result = process_edit_command("vid3", "뒷부분 끝 3:00부터 트림")
        assert len(result.actions) >= 1
        has_end_trim = any(
            a["type"] == "trim" and a["params"]["position"] == "end"
            for a in result.actions
        )
        assert has_end_trim

    def test_speed_command(self):
        """속도 변경 명령"""
        result = process_edit_command("vid4", "2배속으로 빠르게 해줘")
        assert len(result.actions) == 1
        assert result.actions[0]["type"] == "speed"
        assert result.actions[0]["params"]["factor"] == 2.0

    def test_speed_slow(self):
        """느리게 속도 변경"""
        result = process_edit_command("vid5", "느리게 0.5배속")
        assert len(result.actions) == 1
        assert result.actions[0]["type"] == "speed"
        assert result.actions[0]["params"]["factor"] == 0.5

    def test_merge_command(self):
        """병합 명령"""
        result = process_edit_command("vid6", "0:00~1:00과 2:00~3:00 합치기")
        assert len(result.actions) >= 1
        assert result.actions[0]["type"] == "merge"

    def test_empty_video_id_raises(self):
        """빈 video_id → ValueError"""
        with pytest.raises(ValueError, match="video_id"):
            process_edit_command("", "잘라줘")

    def test_empty_command_raises(self):
        """빈 명령 → ValueError"""
        with pytest.raises(ValueError, match="편집 명령"):
            process_edit_command("vid", "")

    def test_unrecognized_command(self):
        """인식 불가 명령 → 빈 actions"""
        result = process_edit_command("vid7", "화질을 높여줘")
        # 시간도 없고 키워드도 없으면 빈 결과
        assert result.actions == []
        assert "인식 가능한 편집 작업이 없습니다" in result.preview_description

    def test_preview_description_generated(self):
        """미리보기 설명이 생성되는지"""
        result = process_edit_command("vid8", "1:00~2:00 삭제해줘")
        assert result.preview_description
        assert "구간 제거" in result.preview_description

    def test_estimated_duration(self):
        """예상 소요 시간 반환"""
        result = process_edit_command("vid9", "0:30~1:00 잘라줘")
        assert result.estimated_duration
        assert "초" in result.estimated_duration or "분" in result.estimated_duration


class TestExtractTimes:
    """_extract_times 헬퍼 테스트"""

    def test_mm_ss_format(self):
        """MM:SS 형식 파싱"""
        assert _extract_times("1:30부터 2:00까지") == [90, 120]

    def test_hh_mm_ss_format(self):
        """HH:MM:SS 형식 파싱"""
        assert _extract_times("1:30:00에서") == [5400]

    def test_no_time(self):
        """시간 없는 텍스트"""
        assert _extract_times("빠르게 해줘") == []

    def test_multiple_times(self):
        """여러 시간 추출"""
        result = _extract_times("0:10, 0:20, 0:30")
        assert len(result) == 3
        assert result == [10, 20, 30]


class TestFormatSeconds:
    """_format_seconds 헬퍼 테스트"""

    def test_basic(self):
        assert _format_seconds(90) == "1:30"

    def test_zero(self):
        assert _format_seconds(0) == "0:00"

    def test_exact_minute(self):
        assert _format_seconds(120) == "2:00"
