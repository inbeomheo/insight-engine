"""
인용 마커 파싱 + 검증 서비스

[MM:SS] 또는 [HH:MM:SS] 형식의 타임스탬프 인용을 파싱하고,
실제 자막 범위와 대조 검증하며, YouTube 타임스탬프 링크로 변환합니다.
"""
import logging
import re
from typing import List, Dict


logger = logging.getLogger(__name__)

# YouTube video_id 형식: 11자 영숫자 + 하이픈 + 언더스코어
_VIDEO_ID_RE = re.compile(r'^[A-Za-z0-9_-]{11}$')

# [MM:SS] 또는 [HH:MM:SS] 패턴
_CITATION_PATTERN = re.compile(
    r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]'
)

# 이미 마크다운 링크로 변환된 인용 마커 (모듈 레벨 사전 컴파일)
_ALREADY_LINKED_RE = re.compile(
    r'\[\[(\d{1,2}:\d{2}(?::\d{2})?)\]\]\(https?://[^\)]+\)'
)

# 이미 <a> 태그 내부의 마커 (모듈 레벨 사전 컴파일)
_INSIDE_A_TAG_RE = re.compile(r'<a\b[^>]*>.*?</a>', re.DOTALL)


def _validate_video_id(video_id: str) -> str:
    """video_id 형식을 검증하여 XSS/인젝션을 방지합니다.

    Args:
        video_id: YouTube 비디오 ID

    Returns:
        검증된 video_id

    Raises:
        ValueError: 유효하지 않은 video_id 형식
    """
    if not video_id or not _VIDEO_ID_RE.match(video_id):
        raise ValueError(f"유효하지 않은 video_id 형식: {video_id!r}")
    return video_id


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
            minutes, seconds = int(parts[0]), int(float(parts[1]))
            if seconds < 0 or seconds >= 60 or minutes < 0:
                return 0
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours, minutes, seconds = int(parts[0]), int(parts[1]), int(float(parts[2]))
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


def enrich_content_with_links(content: str, video_id: str) -> str:
    """[MM:SS] 마커를 YouTube 타임스탬프 링크로 변환합니다.

    이미 마크다운 링크로 변환된 마커(`[...](url)`)는 건너뜁니다.

    마크다운 형식: [MM:SS](https://youtube.com/watch?v={video_id}&t={seconds}s)

    Args:
        content: 마크다운 콘텐츠
        video_id: YouTube 영상 ID

    Returns:
        링크가 삽입된 마크다운 콘텐츠

    Raises:
        ValueError: 유효하지 않은 video_id 형식
    """
    video_id = _validate_video_id(video_id)
    # 이미 링크화된 마커를 건너뛰기 위해 위치 기반 필터링
    linked_positions = set()
    for m in _ALREADY_LINKED_RE.finditer(content):
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

    Raises:
        ValueError: 유효하지 않은 video_id 형식
    """
    video_id = _validate_video_id(video_id)
    # 이미 <a> 태그 내부에 있는 마커 위치를 수집
    linked_ranges = [(m.start(), m.end()) for m in _INSIDE_A_TAG_RE.finditer(html_content)]

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
