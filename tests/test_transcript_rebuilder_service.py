"""자막 구조 재구성 서비스 테스트"""
import pytest
from services.transcript_rebuilder_service import (
    rebuild_structure,
    RebuiltTranscript,
    Section,
    _count_words,
    _detect_section_type,
    _split_into_paragraphs,
)


class TestRebuildStructure:
    """rebuild_structure 함수 테스트"""

    def test_basic_rebuild(self):
        """기본 자막을 섹션별로 재구성한다."""
        transcript = (
            "오늘은 파이썬 프로그래밍에 대해 알아보겠습니다.\n\n"
            "첫 번째로, 변수와 자료형에 대해 설명하겠습니다. "
            "변수는 데이터를 저장하는 공간입니다.\n\n"
            "다음으로, 조건문과 반복문을 살펴보겠습니다. "
            "if문과 for문은 프로그래밍의 기본입니다.\n\n"
            "마지막으로, 정리하겠습니다. 오늘 배운 내용을 복습해보세요."
        )
        result = rebuild_structure(transcript)

        assert isinstance(result, RebuiltTranscript)
        assert len(result.sections) > 0
        assert result.total_words > 0
        assert result.reading_time_minutes > 0

    def test_empty_input(self):
        """빈 입력은 빈 구조를 반환한다."""
        result = rebuild_structure("")
        assert result.sections == []
        assert result.total_words == 0
        assert result.reading_time_minutes == 0.0

    def test_none_input(self):
        """None 입력도 빈 구조를 반환한다."""
        result = rebuild_structure(None)
        assert result.sections == []
        assert result.total_words == 0

    def test_whitespace_only(self):
        """공백만 있는 입력도 빈 구조를 반환한다."""
        result = rebuild_structure("   \n\n  \t  ")
        assert result.sections == []

    def test_section_has_heading(self):
        """각 섹션에 제목이 존재한다."""
        transcript = (
            "오늘 살펴볼 주제는 매우 흥미롭습니다.\n\n"
            "다음으로 중요한 포인트를 설명하겠습니다.\n\n"
            "마무리로 핵심을 정리하겠습니다."
        )
        result = rebuild_structure(transcript)

        for section in result.sections:
            assert isinstance(section, Section)
            assert section.heading != ""

    def test_word_count_consistency(self):
        """total_words가 각 섹션 word_count의 합과 일치한다."""
        transcript = (
            "첫 번째 단락입니다. 여러 단어를 포함하고 있습니다.\n\n"
            "두 번째 단락입니다. 이 단락도 단어를 포함합니다."
        )
        result = rebuild_structure(transcript)

        section_total = sum(s.word_count for s in result.sections)
        assert result.total_words == section_total

    def test_reading_time_calculation(self):
        """읽기 시간이 올바르게 계산된다."""
        # 200 단어 = 1분
        words = " ".join(["단어"] * 200)
        transcript = words
        result = rebuild_structure(transcript)

        # 200단어/200WPM = 1.0분
        assert result.reading_time_minutes == 1.0

    def test_intro_section_detection(self):
        """도입 키워드가 있는 섹션을 감지한다."""
        transcript = (
            "오늘 알아볼 내용은 다음과 같습니다. 이번 시간에는 중요한 개념을 살펴보겠습니다.\n\n"
            "본론으로 들어가서 자세한 내용을 설명하겠습니다. "
            "여기서 핵심 포인트를 짚어보겠습니다."
        )
        result = rebuild_structure(transcript)
        assert len(result.sections) > 0

    def test_single_paragraph(self):
        """단일 문단도 정상 처리한다."""
        transcript = "이것은 하나의 긴 문단입니다. 여러 문장이 있지만 빈 줄로 구분되지 않습니다."
        result = rebuild_structure(transcript)

        assert len(result.sections) >= 1
        assert result.total_words > 0

    def test_long_transcript(self):
        """긴 자막도 적절한 수의 섹션으로 분할한다."""
        paragraphs = [
            f"이것은 {i}번째 문단입니다. 충분히 긴 내용을 포함하고 있어서 독립적인 단락으로 인식됩니다."
            for i in range(15)
        ]
        transcript = "\n\n".join(paragraphs)
        result = rebuild_structure(transcript)

        # 너무 많은 섹션으로 분할하지 않음
        assert 1 <= len(result.sections) <= 10


class TestCountWords:
    """_count_words 함수 테스트"""

    def test_korean_words(self):
        """한국어 어절 수를 센다."""
        assert _count_words("안녕하세요 반갑습니다") == 2

    def test_english_words(self):
        """영문 단어 수를 센다."""
        assert _count_words("hello world test") == 3

    def test_empty_text(self):
        """빈 텍스트는 0을 반환한다."""
        assert _count_words("") == 0
        assert _count_words(None) == 0


class TestDetectSectionType:
    """_detect_section_type 함수 테스트"""

    def test_intro_detection(self):
        """도입 키워드를 감지한다."""
        assert _detect_section_type("오늘 살펴볼 내용은") == "도입"

    def test_transition_detection(self):
        """전환 키워드를 감지한다."""
        assert _detect_section_type("다음으로 알아보겠습니다") == "전환"

    def test_conclusion_detection(self):
        """마무리 키워드를 감지한다."""
        assert _detect_section_type("마무리로 정리하겠습니다") == "마무리"

    def test_default_body(self):
        """특별한 키워드가 없으면 본문을 반환한다."""
        assert _detect_section_type("일반적인 내용입니다") == "본문"
