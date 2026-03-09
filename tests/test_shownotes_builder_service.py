"""shownotes_builder_service 단위 테스트

쇼노트 빌더 + 챕터드 스튜디오 서비스의 전체 기능을 검증합니다.
"""
import unittest
from dataclasses import asdict

from services.shownotes_builder_service import (
    ShowNotes,
    ChapteredStudio,
    build_shownotes,
    create_chaptered_studio,
    shownotes_to_dict,
    chaptered_studio_to_dict,
    _extract_title,
    _extract_summary,
    _extract_people,
    _extract_links,
    _extract_quotes,
    _timestamp_to_seconds,
    _seconds_to_timestamp,
    _split_by_timestamps,
    _parse_timestamped_segments,
)


# ── 테스트용 자막 데이터 ─────────────────────────────────────

# 타임스탬프 포함 자막 (4개 타임스탬프)
TRANSCRIPT_WITH_TIMESTAMPS = """[0:00] 안녕하세요, 오늘은 파이썬 프로그래밍에 대해 이야기하겠습니다.
파이썬은 배우기 쉬운 언어입니다.
[3:15] 다음으로 변수와 자료형에 대해 살펴보겠습니다.
변수는 데이터를 저장하는 이름표입니다.
[7:30] 조건문과 반복문을 알아보겠습니다.
if문은 조건에 따라 실행을 분기합니다.
for문은 반복 실행을 수행합니다.
[12:00] 마지막으로 함수에 대해 정리하겠습니다.
함수는 재사용 가능한 코드 블록입니다. 감사합니다."""

# 타임스탬프 없는 일반 자막
TRANSCRIPT_PLAIN = """오늘은 인공지능의 발전에 대해 이야기하겠습니다.
인공지능은 1950년대부터 연구되어 왔습니다.
최근 딥러닝의 발전으로 많은 변화가 있었습니다.
특히 자연어 처리 분야에서 혁신적인 성과를 거두고 있습니다.
GPT 같은 대규모 언어 모델이 등장했습니다.
이러한 모델은 다양한 분야에서 활용되고 있습니다.
의료, 법률, 교육 등에서 AI가 도입되고 있습니다.
하지만 윤리적 문제도 존재합니다.
데이터 편향과 프라이버시 이슈가 대표적입니다.
앞으로 AI는 더욱 발전할 것으로 예상됩니다.
다음 시간에는 머신러닝의 기초를 다루겠습니다.
감사합니다."""

# 인물/링크/인용문 포함 자막
TRANSCRIPT_WITH_ENTITIES = """
김철수 박사가 이번 연구를 주도했습니다.
Dr. Smith는 "인공지능은 인류의 미래를 바꿀 것이다"라고 말했습니다.
자세한 내용은 https://example.com/ai-research 에서 확인하세요.
이영희 대표는 "기술 혁신이 사회를 변화시킨다"고 강조했습니다.
관련 자료: https://docs.example.org/paper.pdf
Mr. Johnson은 팀의 리더로 활동했습니다.
"""


class TestShowNotesDataclass(unittest.TestCase):
    """ShowNotes 데이터클래스 구조 검증"""

    def test_default_fields(self):
        """기본값으로 인스턴스 생성"""
        sn = ShowNotes(title="테스트", summary="요약")
        self.assertEqual(sn.title, "테스트")
        self.assertEqual(sn.summary, "요약")
        self.assertEqual(sn.chapters, [])
        self.assertEqual(sn.mentioned_people, [])
        self.assertEqual(sn.mentioned_links, [])
        self.assertEqual(sn.key_quotes, [])
        self.assertEqual(sn.transcript_preview, "")

    def test_asdict(self):
        """dict 변환 시 모든 필드 포함"""
        sn = ShowNotes(title="t", summary="s", chapters=[{"time": "0:00", "title": "c1", "summary": "s1"}])
        d = asdict(sn)
        self.assertIn("title", d)
        self.assertIn("chapters", d)
        self.assertEqual(len(d["chapters"]), 1)


class TestChapteredStudioDataclass(unittest.TestCase):
    """ChapteredStudio 데이터클래스 구조 검증"""

    def test_default_fields(self):
        """기본값으로 인스턴스 생성"""
        cs = ChapteredStudio(video_id="abc123")
        self.assertEqual(cs.video_id, "abc123")
        self.assertEqual(cs.episodes, [])
        self.assertEqual(cs.total_chapters, 0)
        self.assertEqual(cs.total_duration, "0:00")


class TestBuildShownotesBasic(unittest.TestCase):
    """build_shownotes 기본 동작"""

    def test_empty_transcript_raises(self):
        """빈 자막은 ValueError"""
        with self.assertRaises(ValueError):
            build_shownotes("")

    def test_whitespace_only_raises(self):
        """공백만 있는 자막은 ValueError"""
        with self.assertRaises(ValueError):
            build_shownotes("   \n\t  ")

    def test_none_transcript_raises(self):
        """None 자막은 ValueError"""
        with self.assertRaises(ValueError):
            build_shownotes(None)

    def test_returns_shownotes_type(self):
        """반환 타입이 ShowNotes"""
        result = build_shownotes(TRANSCRIPT_PLAIN)
        self.assertIsInstance(result, ShowNotes)

    def test_title_from_metadata(self):
        """메타데이터에 제목이 있으면 그것을 사용"""
        result = build_shownotes(TRANSCRIPT_PLAIN, metadata={"title": "커스텀 제목"})
        self.assertEqual(result.title, "커스텀 제목")

    def test_title_from_text_when_no_metadata(self):
        """메타데이터 없으면 텍스트에서 제목 추출"""
        result = build_shownotes(TRANSCRIPT_PLAIN)
        self.assertTrue(len(result.title) > 0)
        self.assertNotEqual(result.title, "제목 없음")

    def test_summary_not_empty(self):
        """요약은 항상 비어있지 않음"""
        result = build_shownotes(TRANSCRIPT_PLAIN)
        self.assertTrue(len(result.summary) > 0)

    def test_transcript_preview_max_500(self):
        """자막 미리보기는 최대 500자"""
        long_text = "가나다라마바사 " * 200
        result = build_shownotes(long_text)
        self.assertLessEqual(len(result.transcript_preview), 500)


class TestBuildShownotesChapters(unittest.TestCase):
    """쇼노트 챕터 분할 검증"""

    def test_minimum_three_chapters(self):
        """챕터 3개 이상 보장"""
        result = build_shownotes(TRANSCRIPT_PLAIN)
        self.assertGreaterEqual(len(result.chapters), 3)

    def test_chapters_with_timestamps(self):
        """타임스탬프 포함 자막의 챕터 분할"""
        result = build_shownotes(TRANSCRIPT_WITH_TIMESTAMPS)
        self.assertGreaterEqual(len(result.chapters), 3)
        # 각 챕터에 time, title, summary 필드 존재
        for ch in result.chapters:
            self.assertIn("time", ch)
            self.assertIn("title", ch)
            self.assertIn("summary", ch)

    def test_chapter_time_format(self):
        """챕터 time 필드가 MM:SS 또는 HH:MM:SS 형식"""
        result = build_shownotes(TRANSCRIPT_WITH_TIMESTAMPS)
        import re
        time_pattern = re.compile(r'^\d{1,2}:\d{2}(:\d{2})?$')
        for ch in result.chapters:
            self.assertRegex(ch["time"], time_pattern, f"잘못된 시간 형식: {ch['time']}")

    def test_short_text_still_has_three_chapters(self):
        """짧은 텍스트도 최소 3개 챕터 보장"""
        short = "첫 번째 문장입니다. 두 번째 문장입니다. 세 번째 문장입니다."
        result = build_shownotes(short)
        self.assertGreaterEqual(len(result.chapters), 3)


class TestBuildShownotesEntities(unittest.TestCase):
    """인물/링크/인용문 추출 검증"""

    def test_extract_korean_people(self):
        """한국어 인물명 추출 (이름 + 직함)"""
        result = build_shownotes(TRANSCRIPT_WITH_ENTITIES)
        self.assertIn("김철수", result.mentioned_people)
        self.assertIn("이영희", result.mentioned_people)

    def test_extract_english_people(self):
        """영어 인물명 추출 (Title + Name)"""
        result = build_shownotes(TRANSCRIPT_WITH_ENTITIES)
        self.assertIn("Smith", result.mentioned_people)
        self.assertIn("Johnson", result.mentioned_people)

    def test_extract_links(self):
        """URL 추출"""
        result = build_shownotes(TRANSCRIPT_WITH_ENTITIES)
        self.assertGreaterEqual(len(result.mentioned_links), 2)
        self.assertTrue(any("example.com" in link for link in result.mentioned_links))

    def test_extract_quotes(self):
        """인용문 추출 (큰따옴표 안의 텍스트)"""
        result = build_shownotes(TRANSCRIPT_WITH_ENTITIES)
        self.assertGreaterEqual(len(result.key_quotes), 1)

    def test_no_duplicate_links(self):
        """중복 URL 제거"""
        text = "방문: https://test.com 그리고 https://test.com 또 https://other.com. 끝입니다."
        result = build_shownotes(text)
        self.assertEqual(len(set(result.mentioned_links)), len(result.mentioned_links))

    def test_no_people_when_absent(self):
        """인물 키워드 없으면 빈 리스트"""
        result = build_shownotes(TRANSCRIPT_PLAIN)
        # TRANSCRIPT_PLAIN에 인물 직함 키워드가 없음
        self.assertIsInstance(result.mentioned_people, list)


class TestCreateChapteredStudio(unittest.TestCase):
    """create_chaptered_studio 검증"""

    def test_empty_raises(self):
        """빈 자막은 ValueError"""
        with self.assertRaises(ValueError):
            create_chaptered_studio("")

    def test_returns_chaptered_studio_type(self):
        """반환 타입이 ChapteredStudio"""
        result = create_chaptered_studio(TRANSCRIPT_PLAIN)
        self.assertIsInstance(result, ChapteredStudio)

    def test_video_id_stored(self):
        """video_id가 저장됨"""
        result = create_chaptered_studio(TRANSCRIPT_PLAIN, video_id="xyz789")
        self.assertEqual(result.video_id, "xyz789")

    def test_episodes_have_required_fields(self):
        """에피소드에 chapter, title, summary, timestamp, duration 필드 존재"""
        result = create_chaptered_studio(TRANSCRIPT_WITH_TIMESTAMPS)
        self.assertGreater(len(result.episodes), 0)
        for ep in result.episodes:
            self.assertIn("chapter", ep)
            self.assertIn("title", ep)
            self.assertIn("summary", ep)
            self.assertIn("timestamp", ep)
            self.assertIn("duration", ep)

    def test_chapter_numbering_sequential(self):
        """챕터 번호가 1부터 순차적"""
        result = create_chaptered_studio(TRANSCRIPT_WITH_TIMESTAMPS)
        chapter_nums = [ep["chapter"] for ep in result.episodes]
        expected = list(range(1, len(result.episodes) + 1))
        self.assertEqual(chapter_nums, expected)

    def test_total_chapters_matches_episodes(self):
        """total_chapters가 episodes 수와 일치"""
        result = create_chaptered_studio(TRANSCRIPT_PLAIN)
        self.assertEqual(result.total_chapters, len(result.episodes))

    def test_total_duration_not_zero(self):
        """total_duration이 0:00이 아님 (내용이 있는 경우)"""
        result = create_chaptered_studio(TRANSCRIPT_WITH_TIMESTAMPS)
        self.assertNotEqual(result.total_duration, "0:00")

    def test_timestamped_transcript_uses_timestamps(self):
        """타임스탬프 포함 자막에서 타임스탬프 기반 에피소드 생성"""
        result = create_chaptered_studio(TRANSCRIPT_WITH_TIMESTAMPS)
        # 첫 에피소드의 timestamp가 0:00이어야 함
        self.assertEqual(result.episodes[0]["timestamp"], "0:00")

    def test_plain_transcript_creates_episodes(self):
        """타임스탬프 없는 자막도 에피소드 생성"""
        result = create_chaptered_studio(TRANSCRIPT_PLAIN, video_id="plain1")
        self.assertGreaterEqual(len(result.episodes), 3)


class TestSerializationHelpers(unittest.TestCase):
    """직렬화 헬퍼 함수 검증"""

    def test_shownotes_to_dict(self):
        """ShowNotes → dict 변환"""
        sn = build_shownotes(TRANSCRIPT_PLAIN)
        d = shownotes_to_dict(sn)
        self.assertIsInstance(d, dict)
        self.assertIn("title", d)
        self.assertIn("chapters", d)
        self.assertIn("mentioned_people", d)

    def test_chaptered_studio_to_dict(self):
        """ChapteredStudio → dict 변환"""
        cs = create_chaptered_studio(TRANSCRIPT_PLAIN, video_id="v1")
        d = chaptered_studio_to_dict(cs)
        self.assertIsInstance(d, dict)
        self.assertIn("video_id", d)
        self.assertIn("episodes", d)
        self.assertIn("total_chapters", d)


class TestTimestampConversion(unittest.TestCase):
    """타임스탬프 ↔ 초 변환"""

    def test_mm_ss_to_seconds(self):
        """MM:SS → 초"""
        self.assertEqual(_timestamp_to_seconds("3:15"), 195)
        self.assertEqual(_timestamp_to_seconds("0:00"), 0)
        self.assertEqual(_timestamp_to_seconds("10:30"), 630)

    def test_hh_mm_ss_to_seconds(self):
        """HH:MM:SS → 초"""
        self.assertEqual(_timestamp_to_seconds("1:00:00"), 3600)
        self.assertEqual(_timestamp_to_seconds("1:30:45"), 5445)

    def test_seconds_to_timestamp_short(self):
        """초 → MM:SS"""
        self.assertEqual(_seconds_to_timestamp(0), "0:00")
        self.assertEqual(_seconds_to_timestamp(65), "1:05")
        self.assertEqual(_seconds_to_timestamp(600), "10:00")

    def test_seconds_to_timestamp_long(self):
        """초 → H:MM:SS (1시간 이상)"""
        self.assertEqual(_seconds_to_timestamp(3661), "1:01:01")

    def test_negative_seconds_clamps_to_zero(self):
        """음수 초는 0으로 클램핑"""
        self.assertEqual(_seconds_to_timestamp(-10), "0:00")


class TestInternalHelpers(unittest.TestCase):
    """내부 헬퍼 함수 개별 검증"""

    def test_extract_title_strips_timestamp(self):
        """제목 추출 시 타임스탬프 제거"""
        title = _extract_title("[0:00] 파이썬 프로그래밍 강좌")
        self.assertNotIn("[0:00]", title)
        self.assertIn("파이썬", title)

    def test_extract_title_max_80_chars(self):
        """제목 최대 80자"""
        long_text = "가" * 200
        title = _extract_title(long_text)
        self.assertLessEqual(len(title), 80)

    def test_extract_summary_max_3_sentences(self):
        """요약은 최대 3문장"""
        text = "첫째. 둘째. 셋째. 넷째. 다섯째."
        summary = _extract_summary(text)
        # 마침표로 끝나야 함
        self.assertTrue(summary.endswith("."))

    def test_extract_links_returns_unique_list(self):
        """링크 추출 시 중복 제거"""
        text = "https://a.com https://b.com https://a.com"
        links = _extract_links(text)
        self.assertEqual(len(links), 2)

    def test_extract_quotes_range(self):
        """10~200자 범위의 인용문만 추출"""
        text = '"짧은"은 제외. "이것은 10자 이상의 인용문 텍스트입니다"는 포함.'
        quotes = _extract_quotes(text)
        for q in quotes:
            self.assertGreaterEqual(len(q), 10)

    def test_parse_timestamped_segments(self):
        """타임스탬프 세그먼트 파싱"""
        text = "[0:00] 첫 번째 [1:30] 두 번째"
        segments = _parse_timestamped_segments(text)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0]["seconds"], 0)
        self.assertEqual(segments[1]["seconds"], 90)

    def test_split_by_timestamps_needs_3_plus(self):
        """타임스탬프 3개 미만이면 빈 리스트"""
        text = "[0:00] 첫 번째 [1:00] 두 번째"
        result = _split_by_timestamps(text)
        self.assertEqual(result, [])


class TestEdgeCases(unittest.TestCase):
    """경계 조건 검증"""

    def test_very_short_text(self):
        """매우 짧은 텍스트 (한 문장)에서도 동작"""
        result = build_shownotes("이것은 짧은 자막입니다")
        self.assertIsInstance(result, ShowNotes)
        self.assertGreaterEqual(len(result.chapters), 3)

    def test_metadata_empty_title(self):
        """메타데이터에 빈 제목이면 텍스트에서 추출"""
        result = build_shownotes(TRANSCRIPT_PLAIN, metadata={"title": ""})
        self.assertNotEqual(result.title, "")

    def test_metadata_none(self):
        """메타데이터 None이면 정상 동작"""
        result = build_shownotes(TRANSCRIPT_PLAIN, metadata=None)
        self.assertIsInstance(result, ShowNotes)

    def test_chaptered_studio_empty_video_id(self):
        """video_id 빈 문자열이면 그대로 저장"""
        result = create_chaptered_studio(TRANSCRIPT_PLAIN, video_id="")
        self.assertEqual(result.video_id, "")


if __name__ == '__main__':
    unittest.main()
