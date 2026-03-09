"""자막 구조 재구성 서비스 — 비정형 자막을 섹션별로 재구성"""
import re
from dataclasses import dataclass


@dataclass
class Section:
    """재구성된 섹션"""
    heading: str
    content: str
    word_count: int


@dataclass
class RebuiltTranscript:
    """재구성된 자막 구조"""
    sections: list  # list[Section]
    total_words: int
    reading_time_minutes: float


# 한국어 평균 읽기 속도 (단어/분)
_READING_WPM = 200

# 섹션 구분 힌트 키워드
_SECTION_MARKERS = [
    # 도입 관련
    (r'(?:오늘|이번|지금).*(?:살펴|알아|소개|시작)', '도입'),
    (r'(?:intro|introduction|welcome|hello)', '도입'),
    # 전환 관련
    (r'(?:다음|그다음|이어서|두\s*번째|세\s*번째)', '전환'),
    (r'(?:next|second|third|moving\s+on|let\'s\s+look)', '전환'),
    # 요약/마무리 관련
    (r'(?:정리|마무리|요약|결론|마지막)', '마무리'),
    (r'(?:summary|conclusion|finally|wrap\s*up|in\s+conclusion)', '마무리'),
]


def _count_words(text: str) -> int:
    """텍스트의 단어 수를 센다 (한글 + 영문 혼합 지원)."""
    if not text:
        return 0
    # 한글: 공백 기준 어절, 영문: 공백 기준 단어
    tokens = text.split()
    return len(tokens)


def _detect_section_type(text: str) -> str:
    """텍스트에서 섹션 유형을 감지한다."""
    text_lower = text.lower()
    for pattern, label in _SECTION_MARKERS:
        if re.search(pattern, text_lower):
            return label
    return "본문"


def _split_into_paragraphs(transcript: str) -> list[str]:
    """자막을 문단으로 분리한다."""
    # 빈 줄 2개 이상 또는 단일 빈 줄로 분리
    paragraphs = re.split(r'\n\s*\n', transcript)
    # 단일 줄바꿈 연속 텍스트는 문장 기준으로 분리
    result = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # 충분히 긴 단락은 그대로 유지
        if len(para) > 50:
            result.append(para)
        else:
            # 짧은 단락은 이전 단락에 합치거나 새 단락으로
            if result:
                result[-1] = result[-1] + " " + para
            else:
                result.append(para)
    return result


def _group_paragraphs(paragraphs: list[str], target_sections: int = 5) -> list[list[str]]:
    """문단을 섹션 그룹으로 묶는다."""
    if not paragraphs:
        return []
    if len(paragraphs) <= target_sections:
        return [[p] for p in paragraphs]

    # 균등 분배
    group_size = max(1, len(paragraphs) // target_sections)
    groups = []
    for i in range(0, len(paragraphs), group_size):
        groups.append(paragraphs[i:i + group_size])

    # 그룹 수가 target보다 많으면 마지막 그룹을 이전 그룹에 병합
    while len(groups) > target_sections and len(groups) > 1:
        last = groups.pop()
        groups[-1].extend(last)

    return groups


def _generate_heading(group: list[str], index: int) -> str:
    """섹션 그룹에서 적절한 제목을 생성한다."""
    combined = " ".join(group)
    section_type = _detect_section_type(combined)

    if section_type == "도입":
        return "도입"
    elif section_type == "마무리":
        return "마무리"
    elif section_type == "전환":
        return f"섹션 {index + 1}"

    # 첫 문장에서 핵심 키워드 추출
    first_sentence = re.split(r'[.!?。]', combined)[0].strip()
    if first_sentence and len(first_sentence) <= 30:
        return first_sentence
    elif first_sentence:
        return first_sentence[:27] + "..."
    return f"섹션 {index + 1}"


def rebuild_structure(transcript: str) -> RebuiltTranscript:
    """자막 텍스트를 구조화된 섹션으로 재구성한다.

    Args:
        transcript: 원본 자막 텍스트

    Returns:
        RebuiltTranscript 구조
    """
    if not transcript or not transcript.strip():
        return RebuiltTranscript(
            sections=[],
            total_words=0,
            reading_time_minutes=0.0,
        )

    paragraphs = _split_into_paragraphs(transcript)
    if not paragraphs:
        return RebuiltTranscript(
            sections=[],
            total_words=0,
            reading_time_minutes=0.0,
        )

    groups = _group_paragraphs(paragraphs)
    sections = []
    total_words = 0

    for i, group in enumerate(groups):
        content = "\n\n".join(group)
        word_count = _count_words(content)
        heading = _generate_heading(group, i)

        sections.append(Section(
            heading=heading,
            content=content,
            word_count=word_count,
        ))
        total_words += word_count

    reading_time = round(total_words / _READING_WPM, 1) if total_words > 0 else 0.0

    return RebuiltTranscript(
        sections=sections,
        total_words=total_words,
        reading_time_minutes=reading_time,
    )
