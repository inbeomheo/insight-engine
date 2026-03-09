"""
video_timeline_service 단위 테스트
"""
import unittest
from services.video_timeline_service import (
    build_interactive_timeline,
    InteractiveTimeline,
    TimelineMarker,
    _validate_timestamp,
    _timestamp_to_seconds,
    _seconds_to_timestamp,
    _detect_marker_type,
    _markers_from_chapters,
    _markers_from_transcript,
    _estimate_duration,
)


class TestTimestampUtils(unittest.TestCase):
    """타임스탬프 유틸리티 테스트"""

    def test_validate_mm_ss(self):
        self.assertTrue(_validate_timestamp("01:30"))
        self.assertTrue(_validate_timestamp("0:00"))

    def test_validate_hh_mm_ss(self):
        self.assertTrue(_validate_timestamp("1:30:00"))

    def test_validate_invalid(self):
        self.assertFalse(_validate_timestamp(""))
        self.assertFalse(_validate_timestamp("abc"))

    def test_to_seconds_mm_ss(self):
        self.assertEqual(_timestamp_to_seconds("01:30"), 90)
        self.assertEqual(_timestamp_to_seconds("00:00"), 0)

    def test_to_seconds_hh_mm_ss(self):
        self.assertEqual(_timestamp_to_seconds("1:00:00"), 3600)
        self.assertEqual(_timestamp_to_seconds("1:30:30"), 5430)

    def test_seconds_to_timestamp(self):
        self.assertEqual(_seconds_to_timestamp(90), "01:30")
        self.assertEqual(_seconds_to_timestamp(0), "00:00")

    def test_seconds_to_timestamp_hours(self):
        self.assertEqual(_seconds_to_timestamp(3661), "01:01:01")


class TestDetectMarkerType(unittest.TestCase):
    """마커 타입 감지 테스트"""

    def test_question_korean(self):
        self.assertEqual(_detect_marker_type("어떻게 해야 하나요"), "question")

    def test_question_english(self):
        self.assertEqual(_detect_marker_type("How does it work?"), "question")

    def test_question_mark(self):
        self.assertEqual(_detect_marker_type("이거 맞나?"), "question")

    def test_reference_keyword(self):
        self.assertEqual(_detect_marker_type("참고 자료입니다"), "reference")

    def test_highlight_keyword(self):
        self.assertEqual(_detect_marker_type("핵심 내용 정리"), "highlight")

    def test_default_chapter(self):
        self.assertEqual(_detect_marker_type("일반적인 텍스트입니다"), "chapter")


class TestMarkersFromChapters(unittest.TestCase):
    """챕터에서 마커 생성 테스트"""

    def test_basic_chapters(self):
        chapters = [
            {"timestamp": "00:00", "title": "인트로"},
            {"timestamp": "05:00", "title": "본론"},
        ]
        markers = _markers_from_chapters(chapters)
        self.assertEqual(len(markers), 2)
        self.assertEqual(markers[0].label, "인트로")
        self.assertEqual(markers[0].marker_type, "chapter")

    def test_invalid_timestamp_skipped(self):
        chapters = [
            {"timestamp": "invalid", "title": "Skip"},
            {"timestamp": "05:00", "title": "Keep"},
        ]
        markers = _markers_from_chapters(chapters)
        self.assertEqual(len(markers), 1)

    def test_start_key_fallback(self):
        """'start' 키도 지원"""
        chapters = [{"start": "01:00", "label": "Label"}]
        markers = _markers_from_chapters(chapters)
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0].label, "Label")


class TestMarkersFromTranscript(unittest.TestCase):
    """자막에서 마커 추출 테스트"""

    def test_timestamped_transcript(self):
        transcript = "[00:00] 안녕하세요 [01:30] 핵심 내용입니다 [03:00] 왜 이런 일이?"
        markers = _markers_from_transcript(transcript)
        self.assertEqual(len(markers), 3)
        self.assertEqual(markers[0].timestamp, "00:00")
        self.assertEqual(markers[2].marker_type, "question")

    def test_empty_text_skipped(self):
        transcript = "[00:00]  [01:00] 내용"
        markers = _markers_from_transcript(transcript)
        self.assertEqual(len(markers), 1)

    def test_no_timestamps(self):
        transcript = "타임스탬프가 없는 일반 텍스트"
        markers = _markers_from_transcript(transcript)
        self.assertEqual(len(markers), 0)


class TestEstimateDuration(unittest.TestCase):
    """재생 시간 추정 테스트"""

    def test_empty_markers(self):
        self.assertEqual(_estimate_duration([]), "00:00")

    def test_single_marker(self):
        markers = [TimelineMarker("05:30", "label", "chapter", "desc")]
        self.assertEqual(_estimate_duration(markers), "05:30")

    def test_multiple_markers(self):
        markers = [
            TimelineMarker("01:00", "a", "chapter", ""),
            TimelineMarker("10:30", "b", "chapter", ""),
            TimelineMarker("05:00", "c", "chapter", ""),
        ]
        self.assertEqual(_estimate_duration(markers), "10:30")


class TestBuildInteractiveTimeline(unittest.TestCase):
    """build_interactive_timeline 메인 함수 테스트"""

    def test_basic_with_chapters(self):
        chapters = [
            {"timestamp": "00:00", "title": "시작"},
            {"timestamp": "05:00", "title": "중간"},
            {"timestamp": "10:00", "title": "끝"},
        ]
        result = build_interactive_timeline("vid1", chapters=chapters)
        self.assertIsInstance(result, InteractiveTimeline)
        self.assertEqual(result.video_id, "vid1")
        self.assertEqual(len(result.markers), 3)
        self.assertEqual(result.chapter_count, 3)
        self.assertEqual(result.total_duration, "10:00")

    def test_with_transcript(self):
        transcript = "[00:00] 인트로 [02:00] 핵심 요약"
        result = build_interactive_timeline("vid2", transcript=transcript)
        self.assertEqual(len(result.markers), 2)

    def test_chapters_and_transcript_dedup(self):
        """챕터와 자막이 동시에 있을 때 중복 타임스탬프 제거"""
        chapters = [{"timestamp": "00:00", "title": "인트로"}]
        transcript = "[00:00] 중복 [01:00] 추가 내용"
        result = build_interactive_timeline("vid3", transcript=transcript, chapters=chapters)
        # 00:00은 챕터에서 이미 있으므로 자막에서 중복 제거
        timestamps = [m.timestamp for m in result.markers]
        self.assertEqual(len(timestamps), len(set(timestamps)))

    def test_empty_video_id(self):
        result = build_interactive_timeline("")
        self.assertEqual(result.video_id, "")
        self.assertEqual(result.markers, [])

    def test_no_input(self):
        result = build_interactive_timeline("vid4")
        self.assertEqual(result.markers, [])
        self.assertEqual(result.chapter_count, 0)

    def test_sorted_by_timestamp(self):
        """마커가 타임스탬프순으로 정렬"""
        chapters = [
            {"timestamp": "10:00", "title": "끝"},
            {"timestamp": "00:00", "title": "시작"},
            {"timestamp": "05:00", "title": "중간"},
        ]
        result = build_interactive_timeline("vid5", chapters=chapters)
        timestamps = [m.timestamp for m in result.markers]
        self.assertEqual(timestamps, ["00:00", "05:00", "10:00"])

    def test_video_id_stripped(self):
        result = build_interactive_timeline("  vid6  ", chapters=[{"timestamp": "00:00", "title": "t"}])
        self.assertEqual(result.video_id, "vid6")


if __name__ == '__main__':
    unittest.main()
