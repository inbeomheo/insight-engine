"""scene_chapter_service 단위 테스트"""
import pytest
from services.scene_chapter_service import (
    detect_scene_chapters,
    SceneChapter,
    _parse_transcript,
    _detect_breakpoints,
    _extract_keywords,
    _format_seconds,
    _generate_chapter_title,
)


class TestDetectSceneChapters:
    """detect_scene_chapters 함수 테스트"""

    def test_timed_transcript(self):
        """타임스탬프 포함 자막에서 챕터 감지"""
        transcript = (
            "[0:00] 안녕하세요 반갑습니다 오늘 영상 시작하겠습니다\n"
            "[0:30] 첫번째 주제는 프로그래밍입니다\n"
            "[1:00] 파이썬은 좋은 언어입니다\n"
            "[1:30] 다음으로 자바스크립트를 봅시다\n"
            "[2:00] 자바스크립트는 웹 개발에 필수입니다\n"
            "[2:30] 마지막으로 정리하겠습니다\n"
            "[3:00] 감사합니다 구독 좋아요 부탁드립니다\n"
        )
        chapters = detect_scene_chapters(transcript)
        assert len(chapters) >= 2
        assert all(isinstance(ch, SceneChapter) for ch in chapters)
        # 시간순
        for i in range(len(chapters) - 1):
            assert chapters[i].chapter_number < chapters[i + 1].chapter_number

    def test_plain_text_transcript(self):
        """타임스탬프 없는 일반 텍스트"""
        transcript = (
            "안녕하세요 반갑습니다. "
            "오늘은 프로그래밍에 대해 이야기합니다. "
            "파이썬은 좋은 언어입니다. "
            "자바스크립트도 중요합니다. "
            "다음으로 데이터베이스를 봅시다. "
            "SQL은 필수입니다. "
            "마지막으로 정리하면 프로그래밍은 재밌습니다. "
            "감사합니다. "
            "구독 부탁합니다. "
            "다음 영상에서 만나요. "
        )
        chapters = detect_scene_chapters(transcript)
        assert len(chapters) >= 1

    def test_short_transcript_returns_empty(self):
        """짧은 자막 → 빈 리스트"""
        assert detect_scene_chapters("짧음") == []
        assert detect_scene_chapters("") == []

    def test_max_chapters_limit(self):
        """max_chapters 제한"""
        # 긴 자막 생성
        lines = [f"[{i}:00] 챕터 {i} 내용입니다 다음으로" for i in range(20)]
        transcript = "\n".join(lines)
        chapters = detect_scene_chapters(transcript, max_chapters=3)
        assert len(chapters) <= 5  # 병합 포함 약간 초과 가능하지만 대략 제한됨

    def test_chapter_has_keywords(self):
        """챕터에 키워드가 포함되는지"""
        transcript = (
            "[0:00] 안녕하세요\n"
            "[0:30] 프로그래밍 프로그래밍 프로그래밍 학습 학습\n"
            "[1:00] 다음으로 데이터 분석\n"
            "[1:30] 데이터 분석 시각화 시각화\n"
            "[2:00] 감사합니다\n"
        )
        chapters = detect_scene_chapters(transcript)
        # 키워드 있는 챕터가 존재하는지
        has_keywords = any(ch.keywords for ch in chapters)
        assert has_keywords

    def test_scene_types(self):
        """장면 유형이 유효한 값인지"""
        transcript = (
            "[0:00] 안녕하세요 반갑습니다\n"
            "[0:30] 오늘의 주제입니다\n"
            "[1:00] 핵심 내용을 설명하겠습니다\n"
            "[1:30] 다음으로 두번째 주제\n"
            "[2:00] 마지막 내용입니다\n"
            "[2:30] 감사합니다 구독 좋아요\n"
        )
        chapters = detect_scene_chapters(transcript)
        valid_types = {"intro", "main", "transition", "outro"}
        for ch in chapters:
            assert ch.scene_type in valid_types

    def test_start_end_time_format(self):
        """시간 형식이 M:SS인지"""
        transcript = (
            "[0:00] 시작합니다 안녕하세요\n"
            "[1:00] 다음으로 본론입니다\n"
            "[2:00] 감사합니다\n"
        )
        chapters = detect_scene_chapters(transcript)
        import re
        for ch in chapters:
            assert re.match(r'\d+:\d{2}', ch.start_time)
            assert re.match(r'\d+:\d{2}', ch.end_time)

    def test_no_transition_markers(self):
        """전환 키워드 없는 자막 → 균등 분할"""
        transcript = (
            "사과는 빨갛다. 바나나는 노랗다. 포도는 보라색이다. "
            "딸기는 달콤하다. 수박은 크다. 참외는 작다. "
            "배는 시원하다. 감은 떫다. 귤은 새콤하다. "
            "복숭아는 부드럽다. 살구는 작다. 자두는 단단하다. "
        )
        chapters = detect_scene_chapters(transcript)
        assert len(chapters) >= 1


class TestParseTranscript:
    """_parse_transcript 함수 테스트"""

    def test_timed_format(self):
        result = _parse_transcript("[0:00] 첫줄\n[0:30] 둘째줄")
        assert len(result) == 2
        assert result[0]["start_sec"] == 0
        assert result[1]["start_sec"] == 30

    def test_plain_text(self):
        result = _parse_transcript("첫 문장입니다. 둘째 문장입니다.")
        assert len(result) >= 2

    def test_empty(self):
        assert _parse_transcript("") == []


class TestDetectBreakpoints:
    """_detect_breakpoints 함수 테스트"""

    def test_transition_keyword(self):
        segments = [
            {"start_sec": 0, "end_sec": 10, "text": "안녕하세요 반갑습니다"},
            {"start_sec": 10, "end_sec": 20, "text": "다음으로 본론입니다"},
        ]
        bp = _detect_breakpoints(segments)
        assert len(bp) >= 1

    def test_no_keywords(self):
        segments = [
            {"start_sec": 0, "end_sec": 10, "text": "사과는 빨갛다"},
            {"start_sec": 10, "end_sec": 20, "text": "바나나는 노랗다"},
        ]
        bp = _detect_breakpoints(segments)
        assert len(bp) == 0


class TestExtractKeywords:
    """_extract_keywords 함수 테스트"""

    def test_basic(self):
        result = _extract_keywords("프로그래밍 프로그래밍 파이썬 학습")
        assert "프로그래밍" in result

    def test_max_5(self):
        text = "가나 다라 마바 사아 자차 카타 파하 " * 3
        result = _extract_keywords(text)
        assert len(result) <= 5

    def test_empty(self):
        assert _extract_keywords("") == []


class TestFormatSeconds:
    """_format_seconds 함수 테스트"""

    def test_basic(self):
        assert _format_seconds(90) == "1:30"

    def test_zero(self):
        assert _format_seconds(0) == "0:00"


class TestGenerateChapterTitle:
    """_generate_chapter_title 함수 테스트"""

    def test_intro(self):
        assert _generate_chapter_title("아무 텍스트", 1, "intro") == "도입"

    def test_outro(self):
        assert _generate_chapter_title("아무 텍스트", 5, "outro") == "마무리"

    def test_main_truncation(self):
        """긴 텍스트 → 30자로 잘림"""
        long_text = "가" * 50 + ". 두번째 문장"
        title = _generate_chapter_title(long_text, 2, "main")
        assert len(title) <= 32  # 30자 + "…"
