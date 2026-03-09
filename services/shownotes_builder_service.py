"""쇼노트 빌더 + 챕터드 스튜디오 서비스

팟캐스트/영상의 자막 텍스트에서 쇼노트(ShowNotes)와
챕터 기반 에피소드 요약(ChapteredStudio)을 생성합니다.
AI 호출 없이 순수 텍스트 분석으로 동작합니다.
"""
import logging
import re
from dataclasses import dataclass, field, asdict
from typing import List, Optional

logger = logging.getLogger(__name__)

# 타임스탬프 패턴: [MM:SS] 또는 [HH:MM:SS]
_TIMESTAMP_PATTERN = re.compile(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]')

# URL 패턴 (http/https)
_URL_PATTERN = re.compile(
    r'https?://[^\s,)>\]\"\']+',
    re.IGNORECASE,
)

# 인용문 패턴: "..." 또는 "..."
_QUOTE_PATTERN = re.compile(
    r'["\u201c]([^"\u201d]{10,200})["\u201d]'
)

# 문장 분리 패턴
_SENTENCE_SPLIT = re.compile(r'[.!?。！？\n]+')

# 인물 탐지 키워드 (한국어)
_PERSON_INDICATORS_KO = [
    "님", "씨", "대표", "교수", "박사", "작가", "감독", "선생",
    "기자", "아나운서", "PD", "MC", "CEO", "CTO",
]

# 인물 탐지 키워드 (영어)
_PERSON_INDICATORS_EN = [
    "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "CEO", "CTO",
    "Director", "Author", "Host",
]

# 챕터 분할 최소 문장 수
_MIN_SENTENCES_PER_CHAPTER = 3

# 챕터 최소 보장 개수
_MIN_CHAPTERS = 3


@dataclass
class ShowNotes:
    """쇼노트 데이터"""
    title: str
    summary: str
    chapters: List[dict] = field(default_factory=list)       # [{"time": "MM:SS", "title": "...", "summary": "..."}]
    mentioned_people: List[str] = field(default_factory=list)
    mentioned_links: List[str] = field(default_factory=list)
    key_quotes: List[str] = field(default_factory=list)
    transcript_preview: str = ""    # 첫 500자


@dataclass
class ChapteredStudio:
    """챕터드 스튜디오 데이터"""
    video_id: str
    episodes: List[dict] = field(default_factory=list)       # [{"chapter": N, "title": "...", "summary": "...", "timestamp": "MM:SS", "duration": "M:SS"}]
    total_chapters: int = 0
    total_duration: str = "0:00"


def build_shownotes(
    transcript: str,
    metadata: Optional[dict] = None,
) -> ShowNotes:
    """자막 + 메타데이터에서 쇼노트를 생성합니다.

    챕터 3개 이상을 보장합니다. 자막이 짧아도 최소 구조를 생성합니다.

    Args:
        transcript: 자막 전체 텍스트
        metadata: {"title": "...", "author": "...", "date": "..."} (선택)

    Returns:
        ShowNotes 데이터클래스

    Raises:
        ValueError: 자막이 비어있을 때
    """
    if not transcript or not transcript.strip():
        raise ValueError("자막 텍스트가 비어있습니다")

    text = transcript.strip()
    meta = metadata or {}

    # 제목: 메타데이터 우선, 없으면 첫 문장에서 추출
    title = meta.get("title", "").strip()
    if not title:
        title = _extract_title(text)

    # 요약: 앞부분 2~3문장
    summary = _extract_summary(text)

    # 챕터 분할 (3개+ 보장)
    chapters = _split_into_chapters(text)

    # 인물 추출
    mentioned_people = _extract_people(text)

    # 링크 추출
    mentioned_links = _extract_links(text)

    # 인용문 추출
    key_quotes = _extract_quotes(text)

    # 자막 미리보기 (첫 500자)
    transcript_preview = text[:500]

    return ShowNotes(
        title=title,
        summary=summary,
        chapters=chapters,
        mentioned_people=mentioned_people,
        mentioned_links=mentioned_links,
        key_quotes=key_quotes,
        transcript_preview=transcript_preview,
    )


def create_chaptered_studio(
    transcript: str,
    video_id: str = "",
) -> ChapteredStudio:
    """자막에서 챕터별 에피소드 요약 + 타임스탬프를 생성합니다.

    Args:
        transcript: 자막 전체 텍스트
        video_id: YouTube 영상 ID (선택)

    Returns:
        ChapteredStudio 데이터클래스

    Raises:
        ValueError: 자막이 비어있을 때
    """
    if not transcript or not transcript.strip():
        raise ValueError("자막 텍스트가 비어있습니다")

    text = transcript.strip()

    # 타임스탬프 포함 세그먼트 파싱
    segments = _parse_timestamped_segments(text)

    # 세그먼트가 없으면 문장 기반 분할
    if not segments:
        segments = _create_segments_from_text(text)

    # 세그먼트를 챕터 단위로 그룹화
    episode_groups = _group_segments_into_episodes(segments)

    # 에피소드 데이터 생성
    episodes = []
    for idx, group in enumerate(episode_groups, start=1):
        ep_title = _generate_episode_title(group)
        ep_summary = _generate_episode_summary(group)
        ep_timestamp = group[0].get("time", "0:00")
        ep_duration = _calculate_duration(group)

        episodes.append({
            "chapter": idx,
            "title": ep_title,
            "summary": ep_summary,
            "timestamp": ep_timestamp,
            "duration": ep_duration,
        })

    # 전체 길이 계산
    total_duration = _calculate_total_duration(segments)

    return ChapteredStudio(
        video_id=video_id,
        episodes=episodes,
        total_chapters=len(episodes),
        total_duration=total_duration,
    )


def shownotes_to_dict(shownotes: ShowNotes) -> dict:
    """ShowNotes를 직렬화 가능한 dict로 변환합니다."""
    return asdict(shownotes)


def chaptered_studio_to_dict(studio: ChapteredStudio) -> dict:
    """ChapteredStudio를 직렬화 가능한 dict로 변환합니다."""
    return asdict(studio)


# ── 내부 헬퍼 함수 ──────────────────────────────────────────


def _extract_title(text: str) -> str:
    """텍스트 첫 문장에서 제목을 추출합니다."""
    # 첫 줄 또는 첫 문장
    first_line = text.split("\n")[0].strip()
    # 타임스탬프 제거
    first_line = _TIMESTAMP_PATTERN.sub("", first_line).strip()
    # 최대 80자
    if len(first_line) > 80:
        first_line = first_line[:77] + "..."
    return first_line if first_line else "제목 없음"


def _extract_summary(text: str) -> str:
    """텍스트 앞부분에서 요약(2~3문장)을 추출합니다."""
    # 타임스탬프 제거
    clean = _TIMESTAMP_PATTERN.sub("", text)
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(clean) if s.strip() and len(s.strip()) >= 10]

    if not sentences:
        return clean[:200]

    # 최대 3문장
    summary_parts = sentences[:3]
    return ". ".join(summary_parts) + "."


def _split_into_chapters(text: str) -> List[dict]:
    """텍스트를 챕터로 분할합니다. 최소 3개 보장.

    타임스탬프가 있으면 타임스탬프 기준으로,
    없으면 문장 수 기반으로 균등 분할합니다.
    """
    # 타임스탬프 기반 분할 시도
    ts_chapters = _split_by_timestamps(text)
    if len(ts_chapters) >= _MIN_CHAPTERS:
        return ts_chapters

    # 문장 기반 균등 분할
    return _split_by_sentences(text)


def _split_by_timestamps(text: str) -> List[dict]:
    """타임스탬프 [MM:SS]를 기준으로 챕터를 분할합니다."""
    matches = list(_TIMESTAMP_PATTERN.finditer(text))
    if len(matches) < _MIN_CHAPTERS:
        return []

    chapters = []
    for i, match in enumerate(matches):
        time_str = match.group(1)
        # 해당 타임스탬프부터 다음 타임스탬프까지의 텍스트
        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        segment_text = text[start_pos:end_pos].strip()

        if not segment_text:
            continue

        # 첫 문장을 챕터 제목으로
        title = _extract_chapter_title(segment_text)
        summary = _extract_chapter_summary(segment_text)

        chapters.append({
            "time": time_str,
            "title": title,
            "summary": summary,
        })

    return chapters


def _split_by_sentences(text: str) -> List[dict]:
    """문장 수 기반으로 균등 분할합니다. 최소 3개 보장."""
    clean = _TIMESTAMP_PATTERN.sub("", text)
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(clean) if s.strip() and len(s.strip()) >= 5]

    if not sentences:
        # 문장 분리 실패 시 줄바꿈 기준
        sentences = [s.strip() for s in text.split("\n") if s.strip() and len(s.strip()) >= 5]

    if not sentences:
        return [{"time": "0:00", "title": "전체 내용", "summary": text[:200]}]

    # 최소 3개 챕터, 챕터당 최소 1문장
    num_chapters = max(_MIN_CHAPTERS, len(sentences) // _MIN_SENTENCES_PER_CHAPTER)
    num_chapters = min(num_chapters, 10)  # 최대 10개

    chunk_size = max(1, len(sentences) // num_chapters)
    chapters = []

    for i in range(num_chapters):
        start_idx = i * chunk_size
        end_idx = start_idx + chunk_size if i < num_chapters - 1 else len(sentences)

        if start_idx >= len(sentences):
            break

        chunk = sentences[start_idx:end_idx]
        if not chunk:
            continue

        # 추정 타임스탬프 (전체 시간을 균등 분할)
        estimated_minutes = i * 2  # 2분 간격 추정
        time_str = f"{estimated_minutes}:{0:02d}"

        title = _extract_chapter_title(" ".join(chunk))
        summary = _extract_chapter_summary(" ".join(chunk))

        chapters.append({
            "time": time_str,
            "title": title,
            "summary": summary,
        })

    # 3개 미만이면 기본 구조 보장
    while len(chapters) < _MIN_CHAPTERS:
        idx = len(chapters)
        chapters.append({
            "time": f"{idx * 2}:{0:02d}",
            "title": f"섹션 {idx + 1}",
            "summary": "내용 없음",
        })

    return chapters


def _extract_chapter_title(text: str) -> str:
    """챕터 텍스트에서 제목(첫 문장, 최대 50자)을 추출합니다."""
    # 첫 줄 또는 첫 50자
    first = text.split("\n")[0].strip()
    if len(first) > 50:
        first = first[:47] + "..."
    return first if first else "제목 없음"


def _extract_chapter_summary(text: str) -> str:
    """챕터 텍스트에서 요약(최대 150자)을 추출합니다."""
    clean = text.replace("\n", " ").strip()
    if len(clean) > 150:
        clean = clean[:147] + "..."
    return clean if clean else ""


def _extract_people(text: str) -> List[str]:
    """텍스트에서 인물명을 추출합니다.

    한국어: "홍길동 님", "김 박사" 등 패턴
    영어: "Dr. Smith", "Mr. Johnson" 등 패턴
    """
    people = set()

    # 한국어 인물 패턴: "이름 + 직함" (2~4자 이름 + 직함)
    for indicator in _PERSON_INDICATORS_KO:
        # "홍길동님", "홍길동 님" 패턴
        pattern = re.compile(
            rf'([가-힣]{{2,4}})\s*{re.escape(indicator)}',
        )
        for match in pattern.finditer(text):
            name = match.group(1)
            people.add(name)

    # 영어 인물 패턴: "Title Name" (대문자로 시작하는 이름)
    for indicator in _PERSON_INDICATORS_EN:
        pattern = re.compile(
            rf'{re.escape(indicator)}\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
        )
        for match in pattern.finditer(text):
            name = match.group(1)
            people.add(name)

    return sorted(people)


def _extract_links(text: str) -> List[str]:
    """텍스트에서 URL을 추출합니다."""
    links = _URL_PATTERN.findall(text)
    # 중복 제거, 순서 유지
    seen = set()
    unique = []
    for link in links:
        if link not in seen:
            seen.add(link)
            unique.append(link)
    return unique


def _extract_quotes(text: str) -> List[str]:
    """텍스트에서 인용문을 추출합니다 (10~200자 범위)."""
    quotes = []
    seen = set()
    for match in _QUOTE_PATTERN.finditer(text):
        quote = match.group(1).strip()
        if quote and quote not in seen:
            seen.add(quote)
            quotes.append(quote)
    return quotes


def _parse_timestamped_segments(text: str) -> List[dict]:
    """타임스탬프가 포함된 텍스트를 세그먼트로 파싱합니다.

    Returns:
        [{"time": "MM:SS", "seconds": int, "text": "..."}, ...]
    """
    matches = list(_TIMESTAMP_PATTERN.finditer(text))
    if not matches:
        return []

    segments = []
    for i, match in enumerate(matches):
        time_str = match.group(1)
        seconds = _timestamp_to_seconds(time_str)

        start_pos = match.end()
        end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        segment_text = text[start_pos:end_pos].strip()

        if segment_text:
            segments.append({
                "time": time_str,
                "seconds": seconds,
                "text": segment_text,
            })

    return segments


def _create_segments_from_text(text: str) -> List[dict]:
    """타임스탬프 없는 텍스트를 균등 분할하여 세그먼트를 생성합니다."""
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip() and len(s.strip()) >= 5]

    if not sentences:
        sentences = [s.strip() for s in text.split("\n") if s.strip()]

    if not sentences:
        return [{"time": "0:00", "seconds": 0, "text": text[:200]}]

    segments = []
    estimated_seconds_per_sentence = 15  # 문장당 약 15초 추정

    for i, sent in enumerate(sentences):
        seconds = i * estimated_seconds_per_sentence
        time_str = _seconds_to_timestamp(seconds)
        segments.append({
            "time": time_str,
            "seconds": seconds,
            "text": sent,
        })

    return segments


def _group_segments_into_episodes(segments: List[dict]) -> List[List[dict]]:
    """세그먼트를 챕터(에피소드) 단위로 그룹화합니다. 최소 3개 보장."""
    if not segments:
        return []

    total = len(segments)
    num_groups = max(_MIN_CHAPTERS, total // _MIN_SENTENCES_PER_CHAPTER)
    num_groups = min(num_groups, 10)
    chunk_size = max(1, total // num_groups)

    groups = []
    for i in range(num_groups):
        start = i * chunk_size
        end = start + chunk_size if i < num_groups - 1 else total

        if start >= total:
            break

        group = segments[start:end]
        if group:
            groups.append(group)

    # 3개 미만이면 보장
    while len(groups) < _MIN_CHAPTERS and segments:
        # 가장 큰 그룹을 반으로 분할
        largest_idx = max(range(len(groups)), key=lambda i: len(groups[i]))
        largest = groups[largest_idx]
        if len(largest) < 2:
            break
        mid = len(largest) // 2
        groups[largest_idx] = largest[:mid]
        groups.insert(largest_idx + 1, largest[mid:])

    return groups


def _generate_episode_title(segments: List[dict]) -> str:
    """세그먼트 그룹에서 에피소드 제목을 생성합니다."""
    if not segments:
        return "제목 없음"

    # 첫 세그먼트의 텍스트에서 추출
    first_text = segments[0].get("text", "")
    title = first_text.split("\n")[0].strip()
    if len(title) > 50:
        title = title[:47] + "..."
    return title if title else "제목 없음"


def _generate_episode_summary(segments: List[dict]) -> str:
    """세그먼트 그룹에서 에피소드 요약을 생성합니다."""
    texts = [seg.get("text", "") for seg in segments]
    combined = " ".join(texts).strip()
    if len(combined) > 200:
        combined = combined[:197] + "..."
    return combined if combined else ""


def _calculate_duration(segments: List[dict]) -> str:
    """세그먼트 그룹의 시간 범위를 계산합니다."""
    if not segments:
        return "0:00"

    times = [seg.get("seconds", 0) for seg in segments]
    start = min(times)
    end = max(times)

    # 마지막 세그먼트에 15초 추정 추가
    duration_seconds = (end - start) + 15
    return _seconds_to_timestamp(duration_seconds)


def _calculate_total_duration(segments: List[dict]) -> str:
    """전체 세그먼트의 총 길이를 계산합니다."""
    if not segments:
        return "0:00"

    times = [seg.get("seconds", 0) for seg in segments]
    # 마지막 세그먼트에 15초 추정 추가
    total = max(times) + 15
    return _seconds_to_timestamp(total)


def _timestamp_to_seconds(ts: str) -> int:
    """타임스탬프 문자열(MM:SS 또는 HH:MM:SS)을 초로 변환합니다."""
    parts = ts.split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0


def _seconds_to_timestamp(seconds: int) -> str:
    """초를 MM:SS 또는 H:MM:SS 형식으로 변환합니다."""
    seconds = max(0, int(seconds))
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"
