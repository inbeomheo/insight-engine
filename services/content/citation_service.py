"""
인용 마커 파싱 + 검증 서비스

[MM:SS] 또는 [HH:MM:SS] 형식의 타임스탬프 인용을 파싱하고,
실제 자막 범위와 대조 검증하며, YouTube 타임스탬프 링크로 변환합니다.
"""
import logging
import re
from typing import List, Dict


logger = logging.getLogger(__name__)

# [MM:SS] 또는 [HH:MM:SS] 패턴
_CITATION_PATTERN = re.compile(
    r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]'
)


def _timestamp_to_seconds(ts: str) -> int:
    """타임스탬프 문자열을 초 단위로 변환합니다.

    Args:
        ts: "MM:SS" 또는 "HH:MM:SS" 형식

    Returns:
        초 단위 정수
    """
    parts = ts.split(':')
    try:
        if len(parts) == 2:
            minutes, seconds = int(parts[0]), int(parts[1])
            if seconds < 0 or seconds >= 60 or minutes < 0:
                return 0
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = int(parts[0]), int(parts[1]), int(parts[2])
            if seconds < 0 or seconds >= 60 or minutes < 0 or minutes >= 60 or hours < 0:
                return 0
            return hours * 3600 + minutes * 60 + seconds
    except (ValueError, TypeError):
        return 0
    return 0


def parse_citations(content: str) -> List[Dict]:
    """콘텐츠에서 [MM:SS] 또는 [HH:MM:SS] 인용 마커를 파싱합니다.

    Args:
        content: 마크다운 콘텐츠 문자열

    Returns:
        [{ "marker": "[03:25]", "seconds": 205, "context": "주변 텍스트" }, ...]
    """
    try:
        results = []
        seen = set()

        for match in _CITATION_PATTERN.finditer(content):
            marker = match.group(0)       # "[03:25]"
            ts_str = match.group(1)       # "03:25"
            seconds = _timestamp_to_seconds(ts_str)

            # 주변 컨텍스트 추출 (마커 앞뒤 50자)
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 50)
            context = content[start:end].strip()

            # 동일 마커+초 중복 방지
            key = (marker, seconds)
            if key in seen:
                continue
            seen.add(key)

            results.append({
                'marker': marker,
                'seconds': seconds,
                'context': context,
            })

        return results
    except Exception as e:
        logger.error(f"인용 마커 파싱 처리 실패: {e}")
        return []
def validate_citations(
    citations: List[Dict],
    transcript_segments: List[Dict],
) -> List[Dict]:
    """인용 타임스탬프가 실제 자막 범위 내인지 검증합니다.

    Args:
        citations: parse_citations()의 반환값
        transcript_segments: [{"start": float, "text": str}, ...]

    Returns:
        각 인용에 "valid" 필드가 추가된 리스트
    """
    if not transcript_segments:
        # 세그먼트 정보가 없으면 검증 불가 → 모두 valid=None
        for c in citations:
            c['valid'] = None
        return citations

    # 자막 범위: 첫 세그먼트 시작 ~ 마지막 세그먼트 시작 + 여유 30초
    starts = [seg.get('start', 0) for seg in transcript_segments if isinstance(seg.get('start'), (int, float))]
    if not starts:
        for c in citations:
            c['valid'] = None
        return citations

    min_time = min(starts)
    max_time = max(starts) + 30  # 마지막 세그먼트 이후 30초 여유

    for c in citations:
        c['valid'] = min_time <= c['seconds'] <= max_time

    return citations


def get_citation_stats(content: str) -> dict:
    """콘텐츠의 인용 통계를 분석합니다.

    인용 개수, 밀도(인용/1000자), 시간 분포(전반/중반/후반),
    평균 간격 등을 반환합니다.

    Args:
        content: 마크다운 콘텐츠

    Returns:
        count, density_per_1000, distribution, avg_gap_seconds, max_gap_seconds를 포함하는 dict
    """
    empty = {
        'count': 0,
        'density_per_1000': 0.0,
        'distribution': {'early': 0, 'mid': 0, 'late': 0},
        'avg_gap_seconds': 0.0,
        'max_gap_seconds': 0,
    }

    if not content or not content.strip():
        return empty

    citations = parse_citations(content)
    count = len(citations)
    if count == 0:
        return empty

    # 밀도: 인용 수 / 1000자
    char_count = len(content)
    density = round(count / max(1, char_count) * 1000, 2)

    # 시간 분포: 초 단위 정렬 후 3등분
    seconds_list = sorted(c['seconds'] for c in citations)
    if seconds_list[-1] > 0:
        max_sec = seconds_list[-1]
        third = max_sec / 3
        early = sum(1 for s in seconds_list if s <= third)
        mid = sum(1 for s in seconds_list if third < s <= third * 2)
        late = sum(1 for s in seconds_list if s > third * 2)
    else:
        early, mid, late = count, 0, 0

    # 간격 분석
    gaps = [seconds_list[i + 1] - seconds_list[i] for i in range(len(seconds_list) - 1)]
    avg_gap = round(sum(gaps) / len(gaps), 1) if gaps else 0.0
    max_gap = max(gaps) if gaps else 0

    return {
        'count': count,
        'density_per_1000': density,
        'distribution': {'early': early, 'mid': mid, 'late': late},
        'avg_gap_seconds': avg_gap,
        'max_gap_seconds': max_gap,
    }


def enrich_content_with_links(content: str, video_id: str) -> str:
    """[MM:SS] 마커를 YouTube 타임스탬프 링크로 변환합니다.

    이미 마크다운 링크로 변환된 마커(`[...](url)`)는 건너뜁니다.

    마크다운 형식: [MM:SS](https://youtube.com/watch?v={video_id}&t={seconds}s)

    Args:
        content: 마크다운 콘텐츠
        video_id: YouTube 영상 ID

    Returns:
        링크가 삽입된 마크다운 콘텐츠
    """
    # 이미 링크화된 마커를 건너뛰기 위해 위치 기반 필터링
    _ALREADY_LINKED = re.compile(
        r'\[\[(\d{1,2}:\d{2}(?::\d{2})?)\]\]\(https?://[^\)]+\)'
    )
    linked_positions = set()
    for m in _ALREADY_LINKED.finditer(content):
        linked_positions.add(m.start() + 1)  # 내부 '[' 위치

    def _replace(match: re.Match) -> str:
        if match.start() in linked_positions:
            return match.group(0)
        # 뒤에 바로 '(http'가 오면 이미 마크다운 링크화된 것
        end_pos = match.end()
        if end_pos < len(content) and content[end_pos:end_pos + 5].startswith('(http'):
            return match.group(0)
        marker = match.group(0)
        ts_str = match.group(1)
        seconds = _timestamp_to_seconds(ts_str)
        url = f"https://youtube.com/watch?v={video_id}&t={seconds}s"
        return f'[{marker}]({url})'

    return _CITATION_PATTERN.sub(_replace, content)


def enrich_html_with_links(html_content: str, video_id: str) -> str:
    """HTML 내 [MM:SS] 마커를 클릭 가능한 링크로 변환합니다.

    이미 ``<a>`` 태그 내부에 있는 마커는 건너뛰어 이중 변환을 방지합니다.

    Args:
        html_content: HTML 문자열
        video_id: YouTube 영상 ID

    Returns:
        링크가 삽입된 HTML 문자열
    """
    # 이미 <a> 태그 내부에 있는 마커 위치를 수집
    _INSIDE_A_TAG = re.compile(r'<a\b[^>]*>.*?</a>', re.DOTALL)
    linked_ranges = [(m.start(), m.end()) for m in _INSIDE_A_TAG.finditer(html_content)]

    def _is_inside_link(pos: int) -> bool:
        return any(start <= pos < end for start, end in linked_ranges)

    def _replace(match: re.Match) -> str:
        if _is_inside_link(match.start()):
            return match.group(0)
        marker = match.group(0)
        ts_str = match.group(1)
        seconds = _timestamp_to_seconds(ts_str)
        url = f"https://youtube.com/watch?v={video_id}&t={seconds}s"
        return (
            f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
            f'class="citation-link" title="YouTube {marker}">{marker}</a>'
        )

    return _CITATION_PATTERN.sub(_replace, html_content)


def get_citation_density_grade(content: str) -> dict:
    """인용 밀도를 등급으로 평가합니다.

    1000자당 인용 수 기반으로 sparse/moderate/dense 등급을 매기고,
    개선 제안을 함께 반환합니다.

    Args:
        content: 마크다운 콘텐츠

    Returns:
        grade, density_per_1000, citation_count, char_count,
        suggestion을 포함하는 dict
    """
    if not content or not content.strip():
        return {
            'grade': 'none',
            'density_per_1000': 0.0,
            'citation_count': 0,
            'char_count': 0,
            'suggestion': '콘텐츠가 비어 있습니다.',
        }

    citations = parse_citations(content)
    count = len(citations)
    char_count = len(content)
    density = round(count / max(1, char_count) * 1000, 2)

    if count == 0:
        grade = 'none'
        suggestion = '인용이 없습니다. 주요 주장에 타임스탬프 인용을 추가하세요.'
    elif density < 2.0:
        grade = 'sparse'
        suggestion = '인용 밀도가 낮습니다. 핵심 논점마다 출처 인용을 추가하면 신뢰도가 높아집니다.'
    elif density <= 8.0:
        grade = 'moderate'
        suggestion = '적절한 인용 밀도입니다.'
    else:
        grade = 'dense'
        suggestion = '인용이 매우 많습니다. 과도한 인용은 가독성을 저해할 수 있으니 핵심만 유지하세요.'

    return {
        'grade': grade,
        'density_per_1000': density,
        'citation_count': count,
        'char_count': char_count,
        'suggestion': suggestion,
    }
