"""timecode_review_service 단위 테스트"""
import unittest

from services.timecode_review_service import (
    validate_timecode,
    add_timecode_annotation,
    list_annotations,
    clear_annotations,
    _parse_timecode_to_seconds,
    Annotation,
    _annotation_store,
)


class TestValidateTimecode(unittest.TestCase):
    """타임코드 검증 테스트"""

    def test_valid_mmss(self):
        """MM:SS 형식 유효"""
        self.assertTrue(validate_timecode("01:30"))

    def test_valid_hhmmss(self):
        """HH:MM:SS 형식 유효"""
        self.assertTrue(validate_timecode("1:30:45"))

    def test_valid_short_minutes(self):
        """M:SS 형식 유효"""
        self.assertTrue(validate_timecode("5:30"))

    def test_invalid_format(self):
        """잘못된 형식"""
        self.assertFalse(validate_timecode("abc"))

    def test_invalid_single_number(self):
        self.assertFalse(validate_timecode("30"))

    def test_empty_string(self):
        self.assertFalse(validate_timecode(""))

    def test_none_input(self):
        self.assertFalse(validate_timecode(None))

    def test_with_spaces(self):
        """양끝 공백 허용"""
        self.assertTrue(validate_timecode("  01:30  "))

    def test_zero_timecode(self):
        self.assertTrue(validate_timecode("0:00"))

    def test_large_minutes(self):
        """60분 이상도 MM:SS로 유효 (HH 없을 때)"""
        self.assertTrue(validate_timecode("99:59"))


class TestParseTimecodeToSeconds(unittest.TestCase):
    """타임코드 → 초 변환 테스트"""

    def test_mmss_basic(self):
        result = _parse_timecode_to_seconds("01:30")
        self.assertEqual(result, 90)

    def test_hhmmss_basic(self):
        result = _parse_timecode_to_seconds("1:30:45")
        self.assertEqual(result, 5445)

    def test_zero(self):
        result = _parse_timecode_to_seconds("0:00")
        self.assertEqual(result, 0)

    def test_invalid_raises(self):
        """잘못된 형식 → ValueError"""
        with self.assertRaises(ValueError):
            _parse_timecode_to_seconds("abc")

    def test_seconds_over_60_raises(self):
        """초가 60 이상 → ValueError"""
        with self.assertRaises(ValueError):
            _parse_timecode_to_seconds("1:65")

    def test_minutes_over_60_in_hhmmss_raises(self):
        """HH:MM:SS에서 분이 60 이상 → ValueError"""
        with self.assertRaises(ValueError):
            _parse_timecode_to_seconds("1:65:30")


class TestAddTimecodeAnnotation(unittest.TestCase):
    """주석 추가 테스트"""

    def setUp(self):
        clear_annotations()

    def test_add_basic(self):
        """기본 주석 추가"""
        ann = add_timecode_annotation("t1", "01:30", "여기 중요한 부분")
        self.assertEqual(ann.transcript_id, "t1")
        self.assertEqual(ann.timecode, "01:30")
        self.assertEqual(ann.timecode_seconds, 90)
        self.assertEqual(ann.note, "여기 중요한 부분")
        self.assertTrue(ann.annotation_id)

    def test_add_hhmmss(self):
        """HH:MM:SS 형식 주석"""
        ann = add_timecode_annotation("t1", "1:05:30", "장시간 구간")
        self.assertEqual(ann.timecode_seconds, 3930)

    def test_invalid_timecode_raises(self):
        """잘못된 타임코드 → ValueError"""
        with self.assertRaises(ValueError):
            add_timecode_annotation("t1", "invalid", "노트")

    def test_empty_transcript_id_raises(self):
        """빈 transcript_id → ValueError"""
        with self.assertRaises(ValueError):
            add_timecode_annotation("", "01:30", "노트")

    def test_empty_note_raises(self):
        """빈 note → ValueError"""
        with self.assertRaises(ValueError):
            add_timecode_annotation("t1", "01:30", "")

    def test_created_at_set(self):
        """created_at 타임스탬프 존재"""
        ann = add_timecode_annotation("t1", "01:30", "테스트")
        self.assertTrue(ann.created_at)

    def test_unique_ids(self):
        """각 주석은 고유 ID"""
        ann1 = add_timecode_annotation("t1", "01:00", "첫째")
        ann2 = add_timecode_annotation("t1", "02:00", "둘째")
        self.assertNotEqual(ann1.annotation_id, ann2.annotation_id)


class TestListAnnotations(unittest.TestCase):
    """주석 목록 테스트"""

    def setUp(self):
        clear_annotations()

    def test_empty_list(self):
        """주석 없으면 빈 리스트"""
        result = list_annotations("nonexistent")
        self.assertEqual(result, [])

    def test_returns_sorted_by_timecode(self):
        """타임코드 순 정렬"""
        add_timecode_annotation("t1", "03:00", "세 번째")
        add_timecode_annotation("t1", "01:00", "첫 번째")
        add_timecode_annotation("t1", "02:00", "두 번째")

        result = list_annotations("t1")
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].timecode, "01:00")
        self.assertEqual(result[1].timecode, "02:00")
        self.assertEqual(result[2].timecode, "03:00")

    def test_filters_by_transcript_id(self):
        """transcript_id별 필터링"""
        add_timecode_annotation("t1", "01:00", "t1 주석")
        add_timecode_annotation("t2", "02:00", "t2 주석")

        result = list_annotations("t1")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].transcript_id, "t1")


class TestClearAnnotations(unittest.TestCase):
    """주석 삭제 테스트"""

    def setUp(self):
        clear_annotations()

    def test_clear_specific(self):
        """특정 transcript_id 삭제"""
        add_timecode_annotation("t1", "01:00", "노트1")
        add_timecode_annotation("t2", "02:00", "노트2")

        removed = clear_annotations("t1")
        self.assertEqual(removed, 1)
        self.assertEqual(list_annotations("t1"), [])
        self.assertEqual(len(list_annotations("t2")), 1)

    def test_clear_all(self):
        """전체 삭제"""
        add_timecode_annotation("t1", "01:00", "노트1")
        add_timecode_annotation("t2", "02:00", "노트2")

        removed = clear_annotations()
        self.assertEqual(removed, 2)
        self.assertEqual(list_annotations("t1"), [])
        self.assertEqual(list_annotations("t2"), [])

    def test_clear_nonexistent(self):
        """없는 ID 삭제 → 0"""
        removed = clear_annotations("nonexistent")
        self.assertEqual(removed, 0)


if __name__ == '__main__':
    unittest.main()
