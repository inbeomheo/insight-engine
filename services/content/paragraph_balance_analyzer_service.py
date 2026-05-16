"""
문단(Paragraph) 길이 균형 분석 서비스

콘텐츠 전체의 문단 길이 분포를 계산하여 가독성 측면의 불균형을 탐지합니다.
블로그·기사 가독성 연구에서 제안된 40~220자 권장 범위를 기준으로 판단합니다.

탐지 항목:
- 너무 긴 문단(집중력 저하)
- 너무 짧은 문단(흐름 단절)
- 길이 표준편차 과다(리듬 불균형)
"""
import logging
import re
import statistics
from typing import List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MIN_CHARS = 40
DEFAULT_MAX_CHARS = 220

_CODE_BLOCK_PATTERN = re.compile(r'```[\s\S]*?```|~~~[\s\S]*?~~~')
_HEADING_LINE_PATTERN = re.compile(r'^#{1,6}\s+.*$', re.MULTILINE)
_LIST_PREFIX = re.compile(r'^\s*([-*•]|\d+[.)])\s+')


def analyze_paragraph_balance(
    content: str,
    min_chars: int = DEFAULT_MIN_CHARS,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> dict:
    """문단 길이 분포를 분석하고 불균형 문단을 탐지합니다.

    Args:
        content: 마크다운 또는 일반 텍스트.
        min_chars: 문단 최소 권장 글자 수.
        max_chars: 문단 최대 권장 글자 수.

    Returns:
        {
            'paragraph_count': int,
            'total_chars': int,
            'avg_length': float,
            'median_length': float,
            'stdev_length': float,
            'min_length': int,
            'max_length': int,
            'too_short': [{'index': int, 'length': int, 'preview': str}],
            'too_long':  [{'index': int, 'length': int, 'preview': str}],
            'balance_grade': 'A' | 'B' | 'C' | 'D',
            'balance_score': int,              # 0~100
            'recommendations': [str],
        }
    """
    paragraphs = _extract_paragraphs(content)

    if not paragraphs:
        return _empty_result()

    lengths = [len(p) for p in paragraphs]
    total_chars = sum(lengths)
    avg = total_chars / len(lengths)
    median = statistics.median(lengths)
    stdev = statistics.stdev(lengths) if len(lengths) > 1 else 0.0

    too_short: List[dict] = []
    too_long: List[dict] = []
    for idx, (para, length) in enumerate(zip(paragraphs, lengths)):
        preview = _make_preview(para)
        if length < min_chars:
            too_short.append({'index': idx, 'length': length, 'preview': preview})
        elif length > max_chars:
            too_long.append({'index': idx, 'length': length, 'preview': preview})

    score, grade = _grade_balance(
        lengths, too_short=len(too_short), too_long=len(too_long),
        stdev=stdev, avg=avg,
    )
    recommendations = _build_recommendations(
        too_short_count=len(too_short),
        too_long_count=len(too_long),
        avg=avg,
        stdev=stdev,
        min_chars=min_chars,
        max_chars=max_chars,
    )

    return {
        'paragraph_count': len(paragraphs),
        'total_chars': total_chars,
        'avg_length': round(avg, 1),
        'median_length': float(median),
        'stdev_length': round(stdev, 1),
        'min_length': min(lengths),
        'max_length': max(lengths),
        'too_short': too_short,
        'too_long': too_long,
        'balance_grade': grade,
        'balance_score': score,
        'recommendations': recommendations,
    }


def _extract_paragraphs(content: str) -> List[str]:
    """문단 단위로 분리합니다.

    - 코드 블록은 통째로 제거
    - 제목 라인 제거
    - 순수 리스트 블록과 표 블록은 문단 리듬과 구조가 달라 분석에서 제외
    - 빈 줄로 구분된 블록을 문단으로 간주
    """
    if not content or not content.strip():
        return []

    # 코드 블록 제거
    cleaned = _CODE_BLOCK_PATTERN.sub('', content)
    # 제목 라인 통째로 제거
    cleaned = _HEADING_LINE_PATTERN.sub('', cleaned)

    # 빈 줄 기준 분리
    raw_blocks = re.split(r'\n\s*\n', cleaned)

    paragraphs = []
    for block in raw_blocks:
        text = block.strip()
        if not text:
            continue
        # 순수 리스트 블록/테이블 줄은 문단 분석에서 제외 (리스트는 문단 리듬과 다른 구조)
        if _is_pure_list_block(text) or _is_table_block(text):
            continue
        paragraphs.append(text)

    return paragraphs


def _is_pure_list_block(text: str) -> bool:
    """블록 전체가 리스트 항목인지 검사."""
    lines = [ln for ln in text.split('\n') if ln.strip()]
    if not lines:
        return False
    return all(_LIST_PREFIX.match(ln) for ln in lines)


def _is_table_block(text: str) -> bool:
    """블록이 마크다운 표인지 검사."""
    lines = [ln for ln in text.split('\n') if ln.strip()]
    return bool(lines) and all(ln.strip().startswith('|') for ln in lines)


def _make_preview(text: str, max_len: int = 40) -> str:
    preview = ' '.join(text.split())
    if len(preview) > max_len:
        return preview[:max_len] + '...'
    return preview


def _grade_balance(
    lengths: List[int], too_short: int, too_long: int, stdev: float, avg: float,
) -> tuple:
    """불균형 지표로 점수와 등급을 산출합니다."""
    if not lengths:
        return 100, 'A'

    total = len(lengths)
    short_ratio = too_short / total
    long_ratio = too_long / total
    # 변동계수(CV): 표준편차 / 평균. 일반적으로 0.5 이하가 안정적
    cv = stdev / avg if avg > 0 else 0

    penalty = 0
    penalty += int(short_ratio * 100) * 0.5  # 짧은 문단 비율
    penalty += int(long_ratio * 100) * 0.7   # 긴 문단은 가독성 저하 더 큼
    if cv > 0.8:
        penalty += 15
    elif cv > 0.6:
        penalty += 8

    score = max(0, min(100, int(100 - penalty)))

    # 문단이 2개 미만이면 표본이 너무 작아 '균형'을 단정할 수 없음 → 상한 클램프
    if total < 2:
        score = min(score, 85)

    if score >= 90:
        grade = 'A'
    elif score >= 75:
        grade = 'B'
    elif score >= 60:
        grade = 'C'
    else:
        grade = 'D'

    return score, grade


def _build_recommendations(
    too_short_count: int, too_long_count: int, avg: float, stdev: float,
    min_chars: int, max_chars: int,
) -> List[str]:
    recs = []
    if too_long_count > 0:
        recs.append(
            f'{too_long_count}개 문단이 {max_chars}자를 초과합니다. '
            '2~3개 문단으로 분리하면 스캔성이 향상됩니다.'
        )
    if too_short_count > 2:
        recs.append(
            f'{too_short_count}개 문단이 {min_chars}자 미만입니다. '
            '관련된 짧은 문단은 합쳐 리듬을 안정화하세요.'
        )
    if avg > 0 and stdev / avg > 0.8:
        recs.append(
            '문단 길이 편차가 큽니다. 평균 길이 근처로 조정하면 일관된 리듬을 얻을 수 있습니다.'
        )
    if not recs:
        recs.append('문단 길이 분포가 양호합니다.')
    return recs


def _empty_result() -> dict:
    return {
        'paragraph_count': 0,
        'total_chars': 0,
        'avg_length': 0.0,
        'median_length': 0.0,
        'stdev_length': 0.0,
        'min_length': 0,
        'max_length': 0,
        'too_short': [],
        'too_long': [],
        'balance_grade': 'A',
        'balance_score': 100,
        'recommendations': ['분석할 문단이 없습니다.'],
    }
