"""
네이티브 스레드 변환 서비스

긴 콘텐츠를 Threads / Bluesky / Mastodon 네이티브 스레드 형식으로
분할합니다. 플랫폼별 글자 제한과 해시태그를 자동 처리.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

# 플랫폼별 글자 제한 (대략적)
_CHAR_LIMITS: dict[str, int] = {
    "threads": 500,
    "bluesky": 300,
    "mastodon": 500,
    "twitter": 280,   # X (구 트위터)
}

# 기본 해시태그 최대 개수
_MAX_HASHTAGS = 5

# 마크다운 제거 패턴
_MD_PATTERNS = [
    (re.compile(r'^#{1,6}\s+', re.MULTILINE), ''),   # 제목
    (re.compile(r'\*\*(.+?)\*\*'), r'\1'),            # 볼드
    (re.compile(r'\*(.+?)\*'), r'\1'),                # 이탤릭
    (re.compile(r'`(.+?)`'), r'\1'),                  # 인라인 코드
    (re.compile(r'\[(.+?)\]\((.+?)\)'), r'\1(\2)'),   # 링크
    (re.compile(r'^[-*]\s+', re.MULTILINE), '• '),    # 리스트
    (re.compile(r'^\d+\.\s+', re.MULTILINE), ''),     # 번호 리스트
]


@dataclass
class ThreadParts:
    """스레드 변환 결과"""
    platform: str
    parts: List[str]
    total_parts: int
    hashtags: List[str] = field(default_factory=list)


def _strip_markdown(text: str) -> str:
    """마크다운 문법 제거."""
    result = text
    for pattern, replacement in _MD_PATTERNS:
        result = pattern.sub(replacement, result)
    return result.strip()


def _extract_hashtags(text: str, max_count: int = _MAX_HASHTAGS) -> list[str]:
    """텍스트에서 핵심 키워드 기반 해시태그 추출.

    기존 해시태그를 먼저 수집하고, 부족하면 긴 단어를 후보로 추가.
    """
    # 기존 해시태그 수집
    existing = re.findall(r'#(\w+)', text)
    tags = list(dict.fromkeys(existing))  # 중복 제거, 순서 유지

    if len(tags) >= max_count:
        return tags[:max_count]

    # 부족하면 긴 단어에서 추가 (한글 2자+ / 영문 4자+)
    words = re.findall(r'[가-힣]{2,}|[a-zA-Z]{4,}', text)
    word_freq: dict[str, int] = {}
    stopwords = {"그리고", "하지만", "그래서", "때문에", "위해서", "이것은", "that", "this", "with", "from", "have", "been"}
    for w in words:
        lower = w.lower()
        if lower not in stopwords and lower not in {t.lower() for t in tags}:
            word_freq[lower] = word_freq.get(lower, 0) + 1

    # 빈도순 상위 단어 추가
    sorted_words = sorted(word_freq, key=word_freq.get, reverse=True)  # type: ignore[arg-type]
    for w in sorted_words:
        if len(tags) >= max_count:
            break
        tags.append(w)

    return tags[:max_count]


def _split_by_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리."""
    # 한국어/영어 문장 종결 기준
    sentences = re.split(r'(?<=[.!?。])\s+', text)
    return [s.strip() for s in sentences if s.strip()]


def _split_into_parts(text: str, char_limit: int) -> list[str]:
    """텍스트를 글자 제한에 맞게 파트로 분할.

    문장 단위로 분할하되, 단일 문장이 제한을 초과하면 강제 분할.
    """
    sentences = _split_by_sentences(text)
    parts: list[str] = []
    current_part: list[str] = []
    current_length = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        # 단일 문장이 제한 초과 — 강제 분할
        if sentence_len > char_limit:
            # 현재 버퍼 먼저 플러시
            if current_part:
                parts.append(' '.join(current_part))
                current_part = []
                current_length = 0
            # 긴 문장을 char_limit 단위로 자르기
            for i in range(0, sentence_len, char_limit):
                chunk = sentence[i:i + char_limit]
                parts.append(chunk)
            continue

        # 추가하면 제한 초과 → 현재 파트 마무리
        separator_len = 1 if current_part else 0
        if current_length + separator_len + sentence_len > char_limit:
            if current_part:
                parts.append(' '.join(current_part))
            current_part = [sentence]
            current_length = sentence_len
        else:
            current_part.append(sentence)
            current_length += separator_len + sentence_len

    # 잔여 문장 플러시
    if current_part:
        parts.append(' '.join(current_part))

    return parts


def _add_thread_numbering(parts: list[str]) -> list[str]:
    """각 파트에 (1/N) 형태의 번호를 추가."""
    total = len(parts)
    if total <= 1:
        return parts
    return [f"({i+1}/{total}) {part}" for i, part in enumerate(parts)]


def convert_to_thread(
    content: str,
    platform: str = "threads",
) -> ThreadParts:
    """콘텐츠를 네이티브 스레드로 변환.

    Args:
        content: 변환할 원본 콘텐츠 (마크다운 가능)
        platform: 대상 플랫폼 ("threads", "bluesky", "mastodon", "twitter")

    Returns:
        ThreadParts: 분할된 파트, 해시태그 포함

    Raises:
        ValueError: 콘텐츠가 비어 있는 경우
    """
    if not content or not content.strip():
        raise ValueError("변환할 콘텐츠가 비어 있습니다.")

    platform = platform.lower().strip()
    char_limit = _CHAR_LIMITS.get(platform, 500)

    # 마크다운 제거
    clean = _strip_markdown(content)

    # 해시태그 추출 (마크다운 제거 전 원문에서)
    hashtags = _extract_hashtags(content)

    # 파트 분할
    parts = _split_into_parts(clean, char_limit)

    # 번호 매기기
    parts = _add_thread_numbering(parts)

    logger.info(
        "스레드 변환 완료: platform=%s, parts=%d, hashtags=%d",
        platform, len(parts), len(hashtags),
    )

    return ThreadParts(
        platform=platform,
        parts=parts,
        total_parts=len(parts),
        hashtags=hashtags,
    )
