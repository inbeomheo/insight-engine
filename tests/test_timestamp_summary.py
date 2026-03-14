"""
타임스탬프 포함 요약 기능 통합 테스트 (P2-1F)

테스트 범위:
- P2-1D: timestamp_utils 유틸 함수 (seconds_to_hhmmss, hhmmss_to_seconds, make_youtube_deeplink 등)
- P2-1A: content_service._extract_segments_from_transcript
- P2-1B: ai_service.format_transcript_with_timestamps
- P2-1C: prompts/base.py 타임코드 지침 포함 여부
"""
import sys
import os
import pytest

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ==================== P2-1D: timestamp_utils 테스트 ====================

class TestSecondsToHhmmss:
    """seconds_to_hhmmss 함수 테스트"""

    def test_zero(self):
        from utils.timestamp_utils import seconds_to_hhmmss
        assert seconds_to_hhmmss(0) == "00:00:00"

    def test_under_one_minute(self):
        from utils.timestamp_utils import seconds_to_hhmmss
        assert seconds_to_hhmmss(5) == "00:00:05"

    def test_exact_one_minute(self):
        from utils.timestamp_utils import seconds_to_hhmmss
        assert seconds_to_hhmmss(60) == "00:01:00"

    def test_minutes_and_seconds(self):
        from utils.timestamp_utils import seconds_to_hhmmss
        assert seconds_to_hhmmss(125.5) == "00:02:05"

    def test_one_hour(self):
        from utils.timestamp_utils import seconds_to_hhmmss
        assert seconds_to_hhmmss(3600) == "01:00:00"

    def test_over_one_hour(self):
        from utils.timestamp_utils import seconds_to_hhmmss
        assert seconds_to_hhmmss(3723) == "01:02:03"

    def test_negative_returns_zero(self):
        from utils.timestamp_utils import seconds_to_hhmmss
        assert seconds_to_hhmmss(-10) == "00:00:00"

    def test_float_truncated(self):
        from utils.timestamp_utils import seconds_to_hhmmss
        # 소수점 버림 (59.9 → 59초)
        assert seconds_to_hhmmss(59.9) == "00:00:59"


class TestHhmmssToSeconds:
    """hhmmss_to_seconds 함수 테스트"""

    def test_zero(self):
        from utils.timestamp_utils import hhmmss_to_seconds
        assert hhmmss_to_seconds("00:00:00") == 0

    def test_seconds_only(self):
        from utils.timestamp_utils import hhmmss_to_seconds
        assert hhmmss_to_seconds("00:00:05") == 5

    def test_minutes_and_seconds(self):
        from utils.timestamp_utils import hhmmss_to_seconds
        assert hhmmss_to_seconds("00:02:05") == 125

    def test_one_hour(self):
        from utils.timestamp_utils import hhmmss_to_seconds
        assert hhmmss_to_seconds("01:00:00") == 3600

    def test_full_time(self):
        from utils.timestamp_utils import hhmmss_to_seconds
        assert hhmmss_to_seconds("01:02:03") == 3723

    def test_mm_ss_format(self):
        """MM:SS 형식도 지원"""
        from utils.timestamp_utils import hhmmss_to_seconds
        assert hhmmss_to_seconds("2:05") == 125

    def test_invalid_returns_zero(self):
        from utils.timestamp_utils import hhmmss_to_seconds
        assert hhmmss_to_seconds("invalid") == 0

    def test_roundtrip(self):
        """seconds → hhmmss → seconds 왕복 변환"""
        from utils.timestamp_utils import seconds_to_hhmmss, hhmmss_to_seconds
        for secs in [0, 5, 60, 125, 3600, 7323]:
            assert hhmmss_to_seconds(seconds_to_hhmmss(secs)) == secs


class TestMakeYoutubeDeeplink:
    """make_youtube_deeplink 함수 테스트"""

    def test_basic_watch_url(self):
        from utils.timestamp_utils import make_youtube_deeplink
        result = make_youtube_deeplink("https://www.youtube.com/watch?v=abc123", 125)
        assert "t=125" in result
        assert "abc123" in result

    def test_short_url(self):
        from utils.timestamp_utils import make_youtube_deeplink
        result = make_youtube_deeplink("https://youtu.be/abc123", 60)
        assert "t=60" in result

    def test_zero_seconds(self):
        from utils.timestamp_utils import make_youtube_deeplink
        result = make_youtube_deeplink("https://www.youtube.com/watch?v=abc123", 0)
        assert "t=0" in result

    def test_existing_t_parameter_replaced(self):
        """기존 t= 파라미터가 있으면 새 값으로 교체"""
        from utils.timestamp_utils import make_youtube_deeplink
        result = make_youtube_deeplink("https://www.youtube.com/watch?v=abc123&t=999", 125)
        assert "t=125" in result
        # 기존 t=999가 남아있으면 안 됨
        assert "t=999" not in result

    def test_empty_url_returns_as_is(self):
        from utils.timestamp_utils import make_youtube_deeplink
        assert make_youtube_deeplink("", 125) == ""


class TestFormatSegmentsForPrompt:
    """format_segments_for_prompt 함수 테스트"""

    def test_empty_segments(self):
        from utils.timestamp_utils import format_segments_for_prompt
        assert format_segments_for_prompt([]) == ""

    def test_basic_segments(self):
        from utils.timestamp_utils import format_segments_for_prompt
        segments = [
            {'start': 0.0, 'text': '안녕하세요', 'duration': 3.0},
            {'start': 125.5, 'text': '두 번째 내용', 'duration': 5.0},
        ]
        result = format_segments_for_prompt(segments)
        assert "[00:00:00]" in result
        assert "안녕하세요" in result
        assert "[00:02:05]" in result
        assert "두 번째 내용" in result

    def test_max_segments_sampling(self):
        """세그먼트 수가 max_segments를 초과하면 샘플링"""
        from utils.timestamp_utils import format_segments_for_prompt
        segments = [{'start': float(i), 'text': f'내용 {i}', 'duration': 1.0} for i in range(200)]
        result = format_segments_for_prompt(segments, max_segments=50)
        lines = [l for l in result.split('\n') if l.strip()]
        assert len(lines) <= 50

    def test_empty_text_skipped(self):
        """빈 텍스트 세그먼트는 무시"""
        from utils.timestamp_utils import format_segments_for_prompt
        segments = [
            {'start': 0.0, 'text': '', 'duration': 1.0},
            {'start': 5.0, 'text': '내용', 'duration': 1.0},
        ]
        result = format_segments_for_prompt(segments)
        lines = [l for l in result.split('\n') if l.strip()]
        assert len(lines) == 1


class TestExtractTimestampsFromContent:
    """extract_timestamps_from_content 함수 테스트"""

    def test_no_timestamps(self):
        from utils.timestamp_utils import extract_timestamps_from_content
        assert extract_timestamps_from_content("타임스탬프 없는 텍스트") == []

    def test_single_timestamp(self):
        from utils.timestamp_utils import extract_timestamps_from_content
        result = extract_timestamps_from_content("[00:02:05] 섹션 시작")
        assert len(result) == 1
        assert result[0]['hhmmss'] == '00:02:05'
        assert result[0]['seconds'] == 125

    def test_multiple_timestamps(self):
        from utils.timestamp_utils import extract_timestamps_from_content
        content = "[00:00:00] 시작\n[00:01:30] 중간\n[01:00:00] 후반"
        result = extract_timestamps_from_content(content)
        assert len(result) == 3
        assert result[1]['seconds'] == 90
        assert result[2]['seconds'] == 3600


# ==================== P2-1A: content_service 세그먼트 추출 테스트 ====================

class TestExtractSegmentsFromTranscript:
    """_extract_segments_from_transcript 함수 테스트"""

    def test_dict_format(self):
        """딕셔너리 형식의 자막 세그먼트 처리"""
        from services.core.content_service import _extract_segments_from_transcript

        class MockFetched:
            def __iter__(self):
                return iter([
                    {'start': 0.0, 'text': '첫 번째', 'duration': 3.0},
                    {'start': 5.0, 'text': '두 번째', 'duration': 4.0},
                ])

        result = _extract_segments_from_transcript(MockFetched())
        assert len(result) == 2
        assert result[0]['start'] == 0.0
        assert result[0]['text'] == '첫 번째'
        assert result[1]['start'] == 5.0

    def test_object_format(self):
        """객체 속성 형식의 자막 세그먼트 처리"""
        from services.core.content_service import _extract_segments_from_transcript

        class Snippet:
            def __init__(self, start, text, duration):
                self.start = start
                self.text = text
                self.duration = duration

        class MockFetched:
            def __iter__(self):
                return iter([
                    Snippet(10.0, '객체 형식 텍스트', 2.5),
                ])

        result = _extract_segments_from_transcript(MockFetched())
        assert len(result) == 1
        assert result[0]['start'] == 10.0
        assert result[0]['text'] == '객체 형식 텍스트'
        assert result[0]['duration'] == 2.5

    def test_empty_text_skipped(self):
        """빈 텍스트 세그먼트는 무시"""
        from services.core.content_service import _extract_segments_from_transcript

        class MockFetched:
            def __iter__(self):
                return iter([
                    {'start': 0.0, 'text': '', 'duration': 1.0},
                    {'start': 5.0, 'text': '유효한 텍스트', 'duration': 2.0},
                ])

        result = _extract_segments_from_transcript(MockFetched())
        assert len(result) == 1
        assert result[0]['text'] == '유효한 텍스트'

    def test_empty_fetched(self):
        """빈 자막 객체"""
        from services.core.content_service import _extract_segments_from_transcript

        class MockFetched:
            def __iter__(self):
                return iter([])

        result = _extract_segments_from_transcript(MockFetched())
        assert result == []


# ==================== P2-1B: ai_service 타임스탬프 포맷터 테스트 ====================

class TestFormatTranscriptWithTimestamps:
    """format_transcript_with_timestamps 함수 테스트"""

    def test_empty_segments(self):
        from services.core.ai_service import format_transcript_with_timestamps
        assert format_transcript_with_timestamps([]) == ""

    def test_basic_segments(self):
        from services.core.ai_service import format_transcript_with_timestamps
        segments = [
            {'start': 0.0, 'text': '안녕하세요', 'duration': 3.0},
            {'start': 125.0, 'text': '주요 내용', 'duration': 5.0},
        ]
        result = format_transcript_with_timestamps(segments)
        assert "[00:00:00]" in result
        assert "안녕하세요" in result
        assert "[00:02:05]" in result
        assert "주요 내용" in result

    def test_none_segments(self):
        from services.core.ai_service import format_transcript_with_timestamps
        assert format_transcript_with_timestamps(None) == ""


# ==================== P2-1C: base.py 타임코드 지침 테스트 ====================

class TestBasePromptTimestampInstruction:
    """BASE_PROMPT에 타임코드 지침이 포함되어 있는지 확인"""

    def test_timestamp_instruction_exists(self):
        from prompts.base import BASE_PROMPT
        assert "[타임스탬프 자막]" in BASE_PROMPT
        assert "[HH:MM:SS]" in BASE_PROMPT

    def test_timestamp_instruction_content(self):
        """타임코드 활용 규칙이 올바른 내용을 포함하는지 확인"""
        from prompts.base import BASE_PROMPT
        assert "타임코드" in BASE_PROMPT
        # 지어내지 말라는 경고가 있어야 함
        assert "지어내지" in BASE_PROMPT


# ==================== 통합 플로우 테스트 ====================

class TestTimestampIntegrationFlow:
    """타임스탬프 기능 통합 플로우 테스트"""

    def test_segment_to_prompt_flow(self):
        """세그먼트 → 프롬프트 포맷 전체 플로우"""
        from utils.timestamp_utils import format_segments_for_prompt, seconds_to_hhmmss

        segments = [
            {'start': 0.0, 'text': '인트로', 'duration': 5.0},
            {'start': 60.0, 'text': '본론 시작', 'duration': 10.0},
            {'start': 300.0, 'text': '결론', 'duration': 8.0},
        ]

        formatted = format_segments_for_prompt(segments)
        assert "[00:00:00] 인트로" in formatted
        assert "[00:01:00] 본론 시작" in formatted
        assert "[00:05:00] 결론" in formatted

    def test_deeplink_with_extracted_timestamp(self):
        """콘텐츠에서 타임스탬프 추출 후 딥링크 생성 플로우"""
        from utils.timestamp_utils import extract_timestamps_from_content, make_youtube_deeplink

        content = "## 소개\n[00:00:30] 이 영상에서는...\n\n## 본론\n[00:02:15] 핵심 내용은..."
        video_url = "https://www.youtube.com/watch?v=test123"

        timestamps = extract_timestamps_from_content(content)
        assert len(timestamps) == 2

        deeplink = make_youtube_deeplink(video_url, timestamps[0]['seconds'])
        assert "t=30" in deeplink
        assert "test123" in deeplink

        deeplink2 = make_youtube_deeplink(video_url, timestamps[1]['seconds'])
        assert "t=135" in deeplink2
