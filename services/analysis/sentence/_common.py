"""문장 분석 공용 헬퍼 — 모든 분석기가 공유하는 기본 분할 로직."""
import re
from typing import List

_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n+')
_HEADING_RE = re.compile(r'^#{1,6}\s+', re.MULTILINE)


def split_sentences(content: str, min_len: int = 5) -> List[str]:
    """마크다운 제목을 제거하고 문장을 분리합니다."""
    cleaned = _HEADING_RE.sub('', content)
    raw = _SENTENCE_SPLIT.split(cleaned)
    return [s.strip() for s in raw if s.strip() and len(s.strip()) >= min_len]
