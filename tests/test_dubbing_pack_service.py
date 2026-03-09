"""
DubbingPackService 단위 테스트 (T12.3)
"""
import unittest
from services.dubbing_pack_service import (
    create_dub_pack,
    DubPack,
    DubTrack,
    DubSegment,
    _split_transcript,
    _translate_text,
    _estimate_duration,
    _format_timestamp,
    SUPPORTED_LANGUAGES,
)


class TestSplitTranscript(unittest.TestCase):
    """자막 분할 테스트"""

    def test_split_by_period(self):
        text = "첫 번째 문장입니다. 두 번째 문장입니다."
        result = _split_transcript(text)
        self.assertEqual(len(result), 2)

    def test_split_by_question_mark(self):
        text = "이건 뭐죠? 그건 아닙니다."
        result = _split_transcript(text)
        self.assertEqual(len(result), 2)

    def test_empty_transcript(self):
        self.assertEqual(_split_transcript(''), [])
        self.assertEqual(_split_transcript('   '), [])

    def test_single_sentence(self):
        result = _split_transcript("하나의 문장만 있습니다.")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "하나의 문장만 있습니다.")


class TestTranslateText(unittest.TestCase):
    """시뮬레이션 번역 테스트"""

    def test_english_prefix(self):
        result = _translate_text("안녕하세요", "en")
        self.assertEqual(result, "[EN] 안녕하세요")

    def test_japanese_prefix(self):
        result = _translate_text("안녕하세요", "ja")
        self.assertEqual(result, "[JA] 안녕하세요")

    def test_unknown_language_prefix(self):
        result = _translate_text("텍스트", "xx")
        self.assertEqual(result, "[XX] 텍스트")


class TestEstimateDuration(unittest.TestCase):
    """소요 시간 추정 테스트"""

    def test_korean_text(self):
        # 한글 16자 → 약 2초
        duration = _estimate_duration("가나다라마바사아자차카타파하가나")
        self.assertGreater(duration, 1.0)

    def test_english_text(self):
        # 영어 8단어 → 약 2초
        duration = _estimate_duration("one two three four five six seven eight")
        self.assertEqual(duration, 2.0)

    def test_minimum_duration(self):
        # 매우 짧은 텍스트 → 최소 1.0초
        duration = _estimate_duration("Hi")
        self.assertEqual(duration, 1.0)


class TestFormatTimestamp(unittest.TestCase):
    """타임스탬프 포맷 테스트"""

    def test_zero(self):
        self.assertEqual(_format_timestamp(0), "00:00")

    def test_one_minute(self):
        self.assertEqual(_format_timestamp(60), "01:00")

    def test_mixed(self):
        self.assertEqual(_format_timestamp(125), "02:05")


class TestCreateDubPack(unittest.TestCase):
    """더빙 팩 생성 통합 테스트"""

    def test_basic_creation(self):
        """기본 더빙 팩 생성"""
        pack = create_dub_pack(
            video_id="abc123",
            languages=["en", "ja"],
            transcript="첫 번째 문장입니다. 두 번째 문장입니다.",
            original_language="ko",
        )
        self.assertIsInstance(pack, DubPack)
        self.assertEqual(pack.video_id, "abc123")
        self.assertEqual(pack.original_language, "ko")
        self.assertEqual(len(pack.dub_tracks), 2)
        self.assertGreater(pack.total_segments, 0)

    def test_empty_video_id_raises(self):
        """빈 video_id → ValueError"""
        with self.assertRaises(ValueError):
            create_dub_pack(video_id="", languages=["en"])

    def test_empty_languages_raises(self):
        """빈 languages → ValueError"""
        with self.assertRaises(ValueError):
            create_dub_pack(video_id="abc", languages=[])

    def test_unsupported_language_raises(self):
        """지원하지 않는 언어만 → ValueError"""
        with self.assertRaises(ValueError):
            create_dub_pack(video_id="abc", languages=["xx", "yy"])

    def test_same_language_excluded(self):
        """원본 언어와 동일한 대상 언어는 제외"""
        pack = create_dub_pack(
            video_id="abc",
            languages=["ko", "en"],
            transcript="테스트 문장입니다.",
            original_language="ko",
        )
        # ko는 제외되고 en만 남아야 함
        track_languages = [t.language for t in pack.dub_tracks]
        self.assertNotIn("ko", track_languages)
        self.assertIn("en", track_languages)

    def test_empty_transcript(self):
        """빈 자막 → 세그먼트 0개"""
        pack = create_dub_pack(
            video_id="abc",
            languages=["en"],
            transcript="",
        )
        self.assertEqual(pack.total_segments, 0)
        self.assertEqual(len(pack.dub_tracks[0].segments), 0)

    def test_track_has_translated_segments(self):
        """트랙 세그먼트에 번역된 텍스트가 포함"""
        pack = create_dub_pack(
            video_id="abc",
            languages=["en"],
            transcript="안녕하세요.",
        )
        track = pack.dub_tracks[0]
        self.assertEqual(track.language, "en")
        self.assertEqual(len(track.segments), 1)
        self.assertTrue(track.segments[0].translated_text.startswith("[EN]"))

    def test_segment_dataclass_fields(self):
        """DubSegment의 모든 필드 확인"""
        pack = create_dub_pack(
            video_id="vid",
            languages=["ja"],
            transcript="테스트.",
        )
        seg = pack.dub_tracks[0].segments[0]
        self.assertIsInstance(seg, DubSegment)
        self.assertIsInstance(seg.timestamp, str)
        self.assertIsInstance(seg.original_text, str)
        self.assertIsInstance(seg.translated_text, str)
        self.assertIsInstance(seg.duration_seconds, float)

    def test_estimated_duration_accumulates(self):
        """트랙의 estimated_duration이 세그먼트 합산과 일치"""
        pack = create_dub_pack(
            video_id="vid",
            languages=["en"],
            transcript="첫째. 둘째. 셋째.",
        )
        track = pack.dub_tracks[0]
        seg_sum = sum(s.duration_seconds for s in track.segments)
        self.assertAlmostEqual(track.estimated_duration, round(seg_sum, 1), places=1)

    def test_whitespace_video_id_stripped(self):
        """video_id 앞뒤 공백 제거"""
        pack = create_dub_pack(
            video_id="  abc123  ",
            languages=["en"],
            transcript="테스트.",
        )
        self.assertEqual(pack.video_id, "abc123")

    def test_multiple_languages(self):
        """3개 이상 언어로 더빙 팩 생성"""
        pack = create_dub_pack(
            video_id="vid",
            languages=["en", "ja", "zh", "es"],
            transcript="문장입니다.",
            original_language="ko",
        )
        self.assertEqual(len(pack.dub_tracks), 4)
        langs = {t.language for t in pack.dub_tracks}
        self.assertEqual(langs, {"en", "ja", "zh", "es"})


if __name__ == '__main__':
    unittest.main()
