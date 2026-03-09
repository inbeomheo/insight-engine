"""하이라이트 그래프 서비스

영상 자막 텍스트를 분석하여 시간대별 관심도(interest level)를 계산하고,
타임라인 그래프 데이터를 생성합니다.
프리뷰 클립 구간을 자동 추출하는 기능도 제공합니다.
"""
import re
from dataclasses import dataclass, field


@dataclass
class TimelinePoint:
    """타임라인 그래프의 단일 포인트"""
    time: str                     # "MM:SS" 형식
    interest_level: float         # 0.0~1.0 관심도
    label: str | None = None      # 하이라이트 라벨 (피크 구간에만)


@dataclass
class InterestTimeline:
    """영상 전체 관심도 타임라인"""
    video_id: str
    points: list[TimelinePoint] = field(default_factory=list)
    peak_moments: list[dict] = field(default_factory=list)   # 최고 관심 구간
    average_interest: float = 0.0


@dataclass
class PreviewClip:
    """프리뷰 클립 구간"""
    start_time: str           # "MM:SS" 형식
    end_time: str             # "MM:SS" 형식
    interest_level: float     # 0.0~1.0
    description: str          # 클립 설명


# 관심도를 높이는 키워드/패턴 (한국어 + 영어)
_HIGH_INTEREST_KEYWORDS = [
    # 핵심 전환 키워드
    '중요', '핵심', '비밀', '꿀팁', '주의', '결론', '요약',
    '드디어', '마침내', '놀랍', '충격', '반전', '실화',
    # 감정 키워드
    '대박', '미쳤', '최고', '역대급', '레전드',
    # 액션 키워드
    '지금부터', '시작', '공개', '발표',
    # 영어 키워드
    'important', 'key', 'secret', 'tip', 'conclusion',
    'finally', 'amazing', 'shocking', 'reveal',
]

# 관심도를 높이는 문장 패턴
_HIGH_INTEREST_PATTERNS = [
    re.compile(r'[!?]{2,}'),                    # 느낌표/물음표 2개 이상
    re.compile(r'[A-Z]{3,}'),                    # 대문자 3자 이상 연속
    re.compile(r'\d+[%만억천]'),                  # 숫자+단위 (통계/수치)
    re.compile(r'첫\s*번째|두\s*번째|세\s*번째'),   # 순서 나열
    re.compile(r'왜\s.*[?？]'),                   # 의문문
]

# 질문 패턴 (청중 참여 신호)
_QUESTION_PATTERN = re.compile(r'[?？]')

# 타임스탬프 패턴
_TIMESTAMP_PATTERN = re.compile(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]')


def _time_to_seconds(time_str: str) -> int:
    """타임스탬프 문자열을 초 단위로 변환합니다."""
    parts = time_str.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def _seconds_to_time(seconds: int) -> str:
    """초를 MM:SS 형식으로 변환합니다."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f'{h}:{m:02d}:{s:02d}'
    return f'{m}:{s:02d}'


def _normalize_time(time_str: str) -> str:
    """타임스탬프를 정규화합니다."""
    return _seconds_to_time(_time_to_seconds(time_str))


def _parse_segments(transcript: str) -> list[dict]:
    """자막을 타임스탬프 기반 세그먼트로 파싱합니다.

    Args:
        transcript: "[MM:SS] 텍스트" 형식 자막

    Returns:
        [{"time_seconds": int, "time": "MM:SS", "text": "..."}, ...]
    """
    segments = []
    matches = list(_TIMESTAMP_PATTERN.finditer(transcript))

    if not matches:
        # 타임스탬프 없으면 줄 단위로 균등 분할
        lines = [line.strip() for line in transcript.split('\n') if line.strip()]
        if not lines:
            return []
        for i, line in enumerate(lines):
            # 30초 간격으로 가상 타임스탬프 부여
            time_sec = i * 30
            segments.append({
                'time_seconds': time_sec,
                'time': _seconds_to_time(time_sec),
                'text': line,
            })
        return segments

    for i, match in enumerate(matches):
        ts = match.group(1)
        text_start = match.end()
        text_end = matches[i + 1].start() if i + 1 < len(matches) else len(transcript)
        text = transcript[text_start:text_end].strip()

        if text:
            time_sec = _time_to_seconds(ts)
            segments.append({
                'time_seconds': time_sec,
                'time': _normalize_time(ts),
                'text': text,
            })

    return segments


def _calculate_interest(text: str) -> float:
    """텍스트의 관심도를 0.0~1.0 범위로 계산합니다.

    관심도 요소:
    - 키워드 매칭 (각 0.1, 최대 0.4)
    - 패턴 매칭 (각 0.08, 최대 0.3)
    - 텍스트 길이 (긴 텍스트 = 밀도 높은 정보)
    - 질문 포함 (청중 참여 신호)
    - 기본 관심도 0.2

    Args:
        text: 분석할 텍스트

    Returns:
        0.0~1.0 범위의 관심도 값
    """
    if not text:
        return 0.0

    score = 0.2  # 기본 관심도

    text_lower = text.lower()

    # 키워드 매칭 (각 0.1, 최대 0.4)
    keyword_hits = sum(
        1 for kw in _HIGH_INTEREST_KEYWORDS
        if kw in text_lower
    )
    score += min(0.4, keyword_hits * 0.1)

    # 패턴 매칭 (각 0.08, 최대 0.3)
    pattern_hits = sum(
        1 for p in _HIGH_INTEREST_PATTERNS
        if p.search(text)
    )
    score += min(0.3, pattern_hits * 0.08)

    # 질문 포함 보너스 (0.05)
    if _QUESTION_PATTERN.search(text):
        score += 0.05

    # 텍스트 길이 보너스 (100자 이상 시 최대 0.1)
    length_bonus = min(0.1, len(text) / 1000)
    score += length_bonus

    return round(min(1.0, score), 2)


def _find_peak_moments(
    points: list[TimelinePoint],
    threshold: float = 0.6,
) -> list[dict]:
    """타임라인에서 피크 구간을 추출합니다.

    연속된 고관심도 포인트를 하나의 피크 구간으로 병합합니다.

    Args:
        points: 타임라인 포인트 목록
        threshold: 피크 판정 기준값

    Returns:
        [{"start": "MM:SS", "end": "MM:SS", "peak_interest": float, "label": str}, ...]
    """
    if not points:
        return []

    peaks = []
    current_peak = None

    for point in points:
        if point.interest_level >= threshold:
            if current_peak is None:
                current_peak = {
                    'start': point.time,
                    'end': point.time,
                    'peak_interest': point.interest_level,
                    'label': point.label or '',
                }
            else:
                current_peak['end'] = point.time
                if point.interest_level > current_peak['peak_interest']:
                    current_peak['peak_interest'] = point.interest_level
                    if point.label:
                        current_peak['label'] = point.label
        else:
            if current_peak is not None:
                peaks.append(current_peak)
                current_peak = None

    # 마지막 피크 처리
    if current_peak is not None:
        peaks.append(current_peak)

    return peaks


def _generate_label(text: str) -> str | None:
    """관심도가 높은 구간에 대한 라벨을 생성합니다.

    텍스트에서 핵심 키워드를 추출하여 짧은 라벨을 만듭니다.

    Args:
        text: 구간 텍스트

    Returns:
        라벨 문자열 또는 None
    """
    text_lower = text.lower()

    # 매칭된 키워드 수집
    matched = [
        kw for kw in _HIGH_INTEREST_KEYWORDS
        if kw in text_lower
    ]

    if not matched:
        return None

    # 처음 2개 키워드로 라벨 구성
    label_parts = matched[:2]
    return ' / '.join(label_parts)


def build_interest_timeline(
    transcript: str,
    video_id: str = '',
) -> InterestTimeline:
    """영상 전체 관심도 타임라인 그래프 데이터를 생성합니다.

    Args:
        transcript: 자막 텍스트 (타임스탬프 포함 또는 미포함)
        video_id: YouTube 영상 ID (선택)

    Returns:
        InterestTimeline 객체 (빈 자막이면 빈 타임라인)
    """
    if not transcript or not transcript.strip():
        return InterestTimeline(video_id=video_id)

    segments = _parse_segments(transcript)
    if not segments:
        return InterestTimeline(video_id=video_id)

    # 각 세그먼트의 관심도 계산
    points = []
    total_interest = 0.0

    for seg in segments:
        interest = _calculate_interest(seg['text'])
        label = _generate_label(seg['text']) if interest >= 0.5 else None

        points.append(TimelinePoint(
            time=seg['time'],
            interest_level=interest,
            label=label,
        ))
        total_interest += interest

    # 평균 관심도
    avg_interest = round(total_interest / len(points), 2) if points else 0.0

    # 피크 구간 추출
    peak_moments = _find_peak_moments(points)

    return InterestTimeline(
        video_id=video_id,
        points=points,
        peak_moments=peak_moments,
        average_interest=avg_interest,
    )


def generate_preview(
    timeline: InterestTimeline,
    top_n: int = 3,
) -> list[PreviewClip]:
    """타임라인에서 상위 N개 프리뷰 클립을 추출합니다.

    관심도가 가장 높은 구간을 선택하여 프리뷰 클립으로 반환합니다.
    각 클립은 해당 포인트의 시작부터 30초 구간입니다.

    Args:
        timeline: InterestTimeline 객체
        top_n: 추출할 클립 수 (기본 3)

    Returns:
        관심도 높은 순으로 정렬된 PreviewClip 목록
    """
    if not timeline.points:
        return []

    # 관심도 기준 내림차순 정렬
    sorted_points = sorted(
        timeline.points,
        key=lambda p: p.interest_level,
        reverse=True,
    )

    clips = []
    used_times = set()  # 중복 구간 방지

    for point in sorted_points:
        if len(clips) >= top_n:
            break

        start_sec = _time_to_seconds(point.time)

        # 이미 사용된 구간과 30초 이내 겹침 방지
        overlap = any(
            abs(start_sec - t) < 30
            for t in used_times
        )
        if overlap:
            continue

        end_sec = start_sec + 30
        used_times.add(start_sec)

        description = point.label or f'관심도 {point.interest_level:.0%} 구간'

        clips.append(PreviewClip(
            start_time=point.time,
            end_time=_seconds_to_time(end_sec),
            interest_level=point.interest_level,
            description=description,
        ))

    return clips
