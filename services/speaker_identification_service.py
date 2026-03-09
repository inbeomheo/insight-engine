"""화자 식별 서비스

자막 텍스트에서 화자별 발화 구간을 식별합니다.
후보 화자의 키워드 목록을 기반으로 텍스트 패턴 매칭을 수행하고,
각 구간에 화자 라벨과 신뢰도를 부여합니다.
"""
import re
from dataclasses import dataclass, field


@dataclass
class SpeakerCandidate:
    """화자 후보 정보"""
    name: str
    keywords: list[str] = field(default_factory=list)  # 화자 식별 키워드


@dataclass
class LabeledSegment:
    """화자가 라벨링된 자막 구간"""
    start_time: str       # "MM:SS" 형식
    end_time: str         # "MM:SS" 형식
    text: str             # 발화 텍스트
    speaker: str          # 식별된 화자 이름
    confidence: float     # 신뢰도 0.0~1.0


# 타임스탬프 패턴: [MM:SS] 또는 [HH:MM:SS]
_TIMESTAMP_PATTERN = re.compile(
    r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]'
)

# 화자 표시 패턴: "화자이름:" 또는 "화자이름 :" (줄 시작)
_SPEAKER_LABEL_PATTERN = re.compile(
    r'^([^:\[\]\n]{1,30})\s*:\s*', re.MULTILINE
)


def _normalize_time(time_str: str) -> str:
    """타임스탬프를 MM:SS 형식으로 정규화합니다.

    Args:
        time_str: "MM:SS" 또는 "HH:MM:SS" 형식

    Returns:
        "MM:SS" 형식 문자열 (1시간 이상이면 "HH:MM:SS")
    """
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
        if h > 0:
            return f'{h}:{m:02d}:{s:02d}'
        return f'{m}:{s:02d}'
    elif len(parts) == 2:
        m, s = int(parts[0]), int(parts[1])
        return f'{m}:{s:02d}'
    return time_str


def _time_to_seconds(time_str: str) -> int:
    """타임스탬프 문자열을 초 단위로 변환합니다.

    Args:
        time_str: "MM:SS" 또는 "HH:MM:SS" 형식

    Returns:
        초 단위 정수
    """
    parts = time_str.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def _seconds_to_time(seconds: int) -> str:
    """초를 MM:SS 형식으로 변환합니다.

    Args:
        seconds: 초 단위 정수

    Returns:
        "MM:SS" 형식 (1시간 이상이면 "H:MM:SS")
    """
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f'{h}:{m:02d}:{s:02d}'
    return f'{m}:{s:02d}'


def _parse_timestamped_lines(transcript: str) -> list[dict]:
    """타임스탬프가 포함된 자막을 구간별로 파싱합니다.

    Args:
        transcript: "[MM:SS] 텍스트" 형식의 자막

    Returns:
        [{"start": "MM:SS", "text": "..."}, ...]
    """
    lines = []
    # 타임스탬프 위치 찾기
    matches = list(_TIMESTAMP_PATTERN.finditer(transcript))

    if not matches:
        # 타임스탬프 없으면 전체를 하나의 구간으로
        stripped = transcript.strip()
        if stripped:
            lines.append({'start': '0:00', 'text': stripped})
        return lines

    for i, match in enumerate(matches):
        ts = match.group(1)
        # 현재 타임스탬프 다음부터 다음 타임스탬프 전까지
        text_start = match.end()
        text_end = matches[i + 1].start() if i + 1 < len(matches) else len(transcript)
        text = transcript[text_start:text_end].strip()

        if text:
            lines.append({'start': _normalize_time(ts), 'text': text})

    return lines


def _match_speaker(text: str, candidates: list[SpeakerCandidate]) -> tuple[str, float]:
    """텍스트에서 화자를 매칭합니다.

    매칭 우선순위:
    1. "화자이름:" 패턴이 텍스트에 있으면 높은 신뢰도 (0.9)
    2. 키워드 매칭 횟수 기반 신뢰도 계산

    Args:
        text: 발화 텍스트
        candidates: 화자 후보 목록

    Returns:
        (화자 이름, 신뢰도) 튜플. 매칭 실패 시 ("Unknown", 0.0)
    """
    text_lower = text.lower()
    best_speaker = 'Unknown'
    best_score = 0.0

    for candidate in candidates:
        score = 0.0

        # 1단계: "이름:" 패턴 직접 매칭
        name_pattern = re.compile(
            re.escape(candidate.name) + r'\s*:', re.IGNORECASE
        )
        if name_pattern.search(text):
            score = 0.9

        # 2단계: 키워드 매칭 (1단계보다 낮은 신뢰도)
        if score < 0.9 and candidate.keywords:
            matched_keywords = sum(
                1 for kw in candidate.keywords
                if kw.lower() in text_lower
            )
            if matched_keywords > 0:
                # 키워드 매칭 비율 기반 신뢰도 (최대 0.8)
                keyword_ratio = matched_keywords / len(candidate.keywords)
                keyword_score = min(0.8, 0.3 + keyword_ratio * 0.5)
                score = max(score, keyword_score)

        if score > best_score:
            best_score = score
            best_speaker = candidate.name

    return best_speaker, best_score


def identify_speakers(
    transcript: str,
    candidates: list[dict],
) -> list[LabeledSegment]:
    """자막에서 화자를 식별하여 라벨링된 구간 목록을 반환합니다.

    Args:
        transcript: 자막 텍스트 (타임스탬프 포함 또는 미포함)
        candidates: 화자 후보 목록 [{"name": "...", "keywords": ["..."]}]

    Returns:
        화자가 라벨링된 구간 목록. 빈 자막이면 빈 리스트.
    """
    if not transcript or not transcript.strip():
        return []

    # 후보 데이터 변환
    speaker_candidates = [
        SpeakerCandidate(
            name=c.get('name', 'Unknown'),
            keywords=c.get('keywords', []),
        )
        for c in (candidates or [])
    ]

    # 자막을 구간별로 파싱
    parsed_lines = _parse_timestamped_lines(transcript)
    if not parsed_lines:
        return []

    segments = []
    for i, line in enumerate(parsed_lines):
        start = line['start']
        text = line['text']

        # 다음 구간의 시작을 현재 구간의 종료 시간으로 사용
        if i + 1 < len(parsed_lines):
            end = parsed_lines[i + 1]['start']
        else:
            # 마지막 구간: 시작 + 30초 (추정)
            end_seconds = _time_to_seconds(start) + 30
            end = _seconds_to_time(end_seconds)

        # 화자 매칭
        if speaker_candidates:
            speaker, confidence = _match_speaker(text, speaker_candidates)
        else:
            speaker = 'Unknown'
            confidence = 0.0

        # 화자 라벨 패턴 제거 ("이름: 텍스트" → "텍스트")
        clean_text = _SPEAKER_LABEL_PATTERN.sub('', text).strip()
        if not clean_text:
            clean_text = text

        segments.append(LabeledSegment(
            start_time=start,
            end_time=end,
            text=clean_text,
            speaker=speaker,
            confidence=round(confidence, 2),
        ))

    return segments
