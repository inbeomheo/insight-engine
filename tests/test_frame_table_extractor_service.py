"""
frame_table_extractor_service 단위 테스트
"""
import unittest
from services.frame_table_extractor_service import (
    extract_tables_from_frames,
    ExtractedTable,
    _validate_timestamp,
    _parse_pipe_table,
    _parse_tab_table,
    _parse_csv_like,
    _try_parse_table,
)


class TestValidateTimestamp(unittest.TestCase):
    """타임스탬프 검증 테스트"""

    def test_valid(self):
        self.assertTrue(_validate_timestamp("02:00"))
        self.assertTrue(_validate_timestamp("1:30:00"))

    def test_invalid(self):
        self.assertFalse(_validate_timestamp(""))
        self.assertFalse(_validate_timestamp("abc"))


class TestParsePipeTable(unittest.TestCase):
    """파이프 테이블 파싱 테스트"""

    def test_basic_pipe_table(self):
        text = "| Name | Age |\n|------|-----|\n| Alice | 30 |\n| Bob | 25 |"
        result = _parse_pipe_table(text)
        self.assertIsNotNone(result)
        self.assertEqual(result["headers"], ["Name", "Age"])
        self.assertEqual(len(result["rows"]), 2)
        self.assertAlmostEqual(result["confidence"], 0.9)

    def test_pipe_table_no_separator(self):
        """구분선 없는 파이프 테이블"""
        text = "| Name | Age |\n| Alice | 30 |\n| Bob | 25 |"
        result = _parse_pipe_table(text)
        self.assertIsNotNone(result)
        self.assertEqual(len(result["rows"]), 2)

    def test_insufficient_rows(self):
        text = "| Only header |"
        result = _parse_pipe_table(text)
        self.assertIsNone(result)

    def test_column_normalization(self):
        """컬럼 수가 맞지 않으면 정규화"""
        text = "| A | B | C |\n|---|---|---|\n| 1 | 2 |"
        result = _parse_pipe_table(text)
        self.assertIsNotNone(result)
        # 부족한 컬럼은 빈 문자열로 채움
        self.assertEqual(len(result["rows"][0]), 3)


class TestParseTabTable(unittest.TestCase):
    """탭 구분 테이블 파싱 테스트"""

    def test_basic_tab_table(self):
        text = "Name\tAge\nAlice\t30\nBob\t25"
        result = _parse_tab_table(text)
        self.assertIsNotNone(result)
        self.assertEqual(result["headers"], ["Name", "Age"])
        self.assertEqual(len(result["rows"]), 2)
        self.assertAlmostEqual(result["confidence"], 0.7)

    def test_no_tabs(self):
        text = "No tabs here\nJust plain text"
        result = _parse_tab_table(text)
        self.assertIsNone(result)


class TestParseCsvLike(unittest.TestCase):
    """CSV 형식 파싱 테스트"""

    def test_basic_csv(self):
        text = "Name,Age\nAlice,30\nBob,25"
        result = _parse_csv_like(text)
        self.assertIsNotNone(result)
        self.assertEqual(result["headers"], ["Name", "Age"])
        self.assertAlmostEqual(result["confidence"], 0.5)

    def test_single_column_rejected(self):
        """단일 컬럼 CSV는 거부"""
        text = "Name\nAlice\nBob"
        result = _parse_csv_like(text)
        self.assertIsNone(result)

    def test_insufficient_lines(self):
        text = "Name,Age"
        result = _parse_csv_like(text)
        self.assertIsNone(result)


class TestTryParseTable(unittest.TestCase):
    """복합 파서 우선순위 테스트"""

    def test_pipe_takes_priority(self):
        text = "| A | B |\n|---|---|\n| 1 | 2 |"
        result = _try_parse_table(text)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["confidence"], 0.9)

    def test_fallback_to_tab(self):
        text = "A\tB\n1\t2"
        result = _try_parse_table(text)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["confidence"], 0.7)

    def test_fallback_to_csv(self):
        text = "A,B\n1,2"
        result = _try_parse_table(text)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result["confidence"], 0.5)

    def test_no_table_detected(self):
        text = "Just plain text without any table structure"
        result = _try_parse_table(text)
        self.assertIsNone(result)


class TestExtractTablesFromFrames(unittest.TestCase):
    """extract_tables_from_frames 메인 함수 테스트"""

    def test_basic_extraction(self):
        frames = [
            {
                "timestamp": "02:00",
                "content": "| 항목 | 수량 |\n|------|------|\n| 사과 | 10 |\n| 배 | 5 |",
            }
        ]
        result = extract_tables_from_frames("vid1", frames)
        self.assertEqual(len(result), 1)
        self.assertIsInstance(result[0], ExtractedTable)
        self.assertEqual(result[0].video_id, "vid1")
        self.assertEqual(result[0].timestamp, "02:00")
        self.assertEqual(len(result[0].rows), 2)

    def test_empty_video_id(self):
        result = extract_tables_from_frames("", [{"timestamp": "01:00", "content": "a,b\n1,2"}])
        self.assertEqual(result, [])

    def test_empty_frames(self):
        result = extract_tables_from_frames("vid1", [])
        self.assertEqual(result, [])

    def test_none_frames(self):
        result = extract_tables_from_frames("vid1", None)
        self.assertEqual(result, [])

    def test_invalid_timestamp_skipped(self):
        frames = [
            {"timestamp": "bad", "content": "A,B\n1,2"},
            {"timestamp": "03:00", "content": "A,B\n1,2"},
        ]
        result = extract_tables_from_frames("vid1", frames)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].timestamp, "03:00")

    def test_no_table_content_skipped(self):
        """표 구조가 아닌 내용은 건너뛰기"""
        frames = [{"timestamp": "01:00", "content": "그냥 텍스트입니다"}]
        result = extract_tables_from_frames("vid1", frames)
        self.assertEqual(len(result), 0)

    def test_empty_content_skipped(self):
        frames = [{"timestamp": "01:00", "content": ""}]
        result = extract_tables_from_frames("vid1", frames)
        self.assertEqual(len(result), 0)

    def test_non_dict_frame_skipped(self):
        frames = ["not_a_dict", {"timestamp": "01:00", "content": "A,B\n1,2"}]
        result = extract_tables_from_frames("vid1", frames)
        self.assertEqual(len(result), 1)

    def test_unique_table_ids(self):
        frames = [
            {"timestamp": "01:00", "content": "A,B\n1,2"},
            {"timestamp": "02:00", "content": "X,Y\n3,4"},
        ]
        result = extract_tables_from_frames("vid1", frames)
        ids = [t.table_id for t in result]
        self.assertEqual(len(ids), len(set(ids)))

    def test_confidence_field(self):
        """파이프 테이블은 높은 confidence"""
        frames = [
            {"timestamp": "01:00", "content": "| H1 | H2 |\n|---|---|\n| A | B |"},
        ]
        result = extract_tables_from_frames("vid1", frames)
        self.assertEqual(len(result), 1)
        self.assertGreaterEqual(result[0].confidence, 0.8)

    def test_multiple_tables(self):
        """여러 프레임에서 여러 테이블 추출"""
        frames = [
            {"timestamp": "01:00", "content": "| A | B |\n|---|---|\n| 1 | 2 |"},
            {"timestamp": "05:00", "content": "X\tY\n3\t4"},
        ]
        result = extract_tables_from_frames("vid1", frames)
        self.assertEqual(len(result), 2)


if __name__ == '__main__':
    unittest.main()
