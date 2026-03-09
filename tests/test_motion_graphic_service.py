"""
motion_graphic_service 단위 테스트
"""
import unittest
from services.motion_graphic_service import (
    overlay_infocards,
    InfocardOverlay,
    _validate_timestamp,
    _normalize_timestamp,
    _resolve_position,
    _resolve_style,
    _build_title,
    VALID_POSITIONS,
    DEFAULT_POSITION,
    DEFAULT_DURATION,
    DEFAULT_STYLE,
)


class TestValidateTimestamp(unittest.TestCase):
    """타임스탬프 검증 테스트"""

    def test_valid_mm_ss(self):
        self.assertTrue(_validate_timestamp("01:30"))
        self.assertTrue(_validate_timestamp("0:00"))
        self.assertTrue(_validate_timestamp("59:59"))

    def test_valid_hh_mm_ss(self):
        self.assertTrue(_validate_timestamp("1:30:00"))
        self.assertTrue(_validate_timestamp("01:30:45"))

    def test_invalid_format(self):
        self.assertFalse(_validate_timestamp(""))
        self.assertFalse(_validate_timestamp("abc"))
        self.assertFalse(_validate_timestamp("1234"))
        self.assertFalse(_validate_timestamp("1:2:3:4"))


class TestNormalizeTimestamp(unittest.TestCase):
    """타임스탬프 정규화 테스트"""

    def test_mm_ss_padding(self):
        self.assertEqual(_normalize_timestamp("1:30"), "01:30")
        self.assertEqual(_normalize_timestamp("00:05"), "00:05")

    def test_hh_mm_ss_conversion(self):
        # 1:30:00 → 90:00
        self.assertEqual(_normalize_timestamp("1:30:00"), "90:00")
        # 0:05:30 → 05:30
        self.assertEqual(_normalize_timestamp("0:05:30"), "05:30")


class TestResolvePosition(unittest.TestCase):
    """위치 결정 테스트"""

    def test_valid_positions(self):
        for pos in VALID_POSITIONS:
            hl = {"position": pos}
            self.assertEqual(_resolve_position(hl), pos)

    def test_invalid_position_fallback(self):
        hl = {"position": "invalid_pos"}
        self.assertEqual(_resolve_position(hl), DEFAULT_POSITION)

    def test_missing_position_fallback(self):
        hl = {}
        self.assertEqual(_resolve_position(hl), DEFAULT_POSITION)


class TestResolveStyle(unittest.TestCase):
    """스타일 결정 테스트"""

    def test_stat_type(self):
        self.assertEqual(_resolve_style({"type": "stat"}), "highlight")

    def test_quote_type(self):
        self.assertEqual(_resolve_style({"type": "quote"}), "quote")

    def test_unknown_type(self):
        self.assertEqual(_resolve_style({"type": "unknown"}), DEFAULT_STYLE)

    def test_missing_type(self):
        self.assertEqual(_resolve_style({}), DEFAULT_STYLE)


class TestBuildTitle(unittest.TestCase):
    """제목 생성 테스트"""

    def test_normal_text(self):
        self.assertEqual(_build_title({"text": "핵심 포인트"}), "핵심 포인트")

    def test_long_text_truncated(self):
        long_text = "가" * 60
        result = _build_title({"text": long_text})
        self.assertEqual(len(result), 50)
        self.assertTrue(result.endswith("..."))

    def test_empty_text(self):
        self.assertEqual(_build_title({"text": ""}), "정보")
        self.assertEqual(_build_title({}), "정보")


class TestOverlayInfocards(unittest.TestCase):
    """overlay_infocards 메인 함수 테스트"""

    def test_basic_generation(self):
        """기본 인포카드 생성"""
        highlights = [
            {"timestamp": "01:30", "text": "핵심 포인트", "type": "stat"},
            {"timestamp": "03:00", "text": "인용구", "type": "quote"},
        ]
        result = overlay_infocards("video123", highlights)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], InfocardOverlay)
        self.assertEqual(result[0].video_id, "video123")
        self.assertEqual(result[0].timestamp, "01:30")
        self.assertEqual(result[0].style, "highlight")
        self.assertEqual(result[1].style, "quote")

    def test_empty_video_id(self):
        """빈 video_id → 빈 리스트"""
        result = overlay_infocards("", [{"timestamp": "01:00", "text": "test"}])
        self.assertEqual(result, [])

    def test_empty_highlights(self):
        """빈 하이라이트 → 빈 리스트"""
        result = overlay_infocards("video123", [])
        self.assertEqual(result, [])

    def test_none_highlights(self):
        """None 하이라이트 → 빈 리스트"""
        result = overlay_infocards("video123", None)
        self.assertEqual(result, [])

    def test_invalid_timestamp_skipped(self):
        """유효하지 않은 타임스탬프 건너뛰기"""
        highlights = [
            {"timestamp": "invalid", "text": "skip"},
            {"timestamp": "02:00", "text": "keep"},
        ]
        result = overlay_infocards("video123", highlights)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].timestamp, "02:00")

    def test_non_dict_highlight_skipped(self):
        """dict가 아닌 하이라이트 건너뛰기"""
        highlights = [
            "not_a_dict",
            {"timestamp": "01:00", "text": "valid"},
        ]
        result = overlay_infocards("video123", highlights)
        self.assertEqual(len(result), 1)

    def test_custom_duration(self):
        """커스텀 duration 적용"""
        highlights = [{"timestamp": "01:00", "text": "test", "duration": 10}]
        result = overlay_infocards("video123", highlights)
        self.assertEqual(result[0].duration_seconds, 10)

    def test_duration_clamped(self):
        """duration 범위 제한 (1~30)"""
        highlights = [
            {"timestamp": "01:00", "text": "too short", "duration": 0},
            {"timestamp": "02:00", "text": "too long", "duration": 100},
        ]
        result = overlay_infocards("video123", highlights)
        self.assertEqual(result[0].duration_seconds, 1)
        self.assertEqual(result[1].duration_seconds, 30)

    def test_invalid_duration_uses_default(self):
        """유효하지 않은 duration → 기본값"""
        highlights = [{"timestamp": "01:00", "text": "test", "duration": "abc"}]
        result = overlay_infocards("video123", highlights)
        self.assertEqual(result[0].duration_seconds, DEFAULT_DURATION)

    def test_unique_card_ids(self):
        """각 카드 ID가 고유"""
        highlights = [
            {"timestamp": "01:00", "text": "a"},
            {"timestamp": "02:00", "text": "b"},
            {"timestamp": "03:00", "text": "c"},
        ]
        result = overlay_infocards("video123", highlights)
        ids = [c.card_id for c in result]
        self.assertEqual(len(ids), len(set(ids)))

    def test_video_id_stripped(self):
        """video_id 공백 제거"""
        highlights = [{"timestamp": "01:00", "text": "test"}]
        result = overlay_infocards("  video123  ", highlights)
        self.assertEqual(result[0].video_id, "video123")

    def test_custom_position(self):
        """커스텀 위치 적용"""
        highlights = [{"timestamp": "01:00", "text": "test", "position": "top_left"}]
        result = overlay_infocards("video123", highlights)
        self.assertEqual(result[0].position, "top_left")


if __name__ == '__main__':
    unittest.main()
