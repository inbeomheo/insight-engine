"""
코멘터리 팟캐스트 대본 생성 서비스

콘텐츠를 기반으로 팟캐스트 코멘터리 대본(인트로/본론/코멘터리/아웃트로)을 생성합니다.
외부 API 없이 텍스트 구조 분석으로 동작합니다.
"""
import re
import logging
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)

# 예상 읽기 속도 (분당 단어 수)
_WORDS_PER_MINUTE = 150

# 세그먼트 타입
SEGMENT_TYPES = ('intro', 'main', 'commentary', 'outro')


@dataclass
class PodcastSegment:
    """팟캐스트 세그먼트"""
    segment_type: str  # "intro", "main", "commentary", "outro"
    text: str
    duration_minutes: float


@dataclass
class PodcastScript:
    """팟캐스트 대본"""
    title: str
    host: str
    segments: List[PodcastSegment] = field(default_factory=list)
    total_duration_minutes: float = 0.0


def _estimate_duration(text: str) -> float:
    """텍스트 읽기 소요 시간(분)을 추정합니다."""
    word_count = len(text.split())
    if word_count == 0:
        return 0.0
    return round(word_count / _WORDS_PER_MINUTE, 2)


def _extract_title(content: str) -> str:
    """콘텐츠에서 제목을 추출합니다."""
    lines = content.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        # 마크다운 헤딩 제거
        cleaned = re.sub(r'^#+\s*', '', line).strip()
        if cleaned:
            return cleaned[:80]
    return '팟캐스트 에피소드'


def _split_into_paragraphs(content: str) -> List[str]:
    """콘텐츠를 문단 단위로 분리합니다."""
    paragraphs = []
    current = []
    for line in content.split('\n'):
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(' '.join(current))
                current = []
        else:
            # 마크다운 헤딩 제거
            cleaned = re.sub(r'^#+\s*', '', stripped)
            current.append(cleaned)
    if current:
        paragraphs.append(' '.join(current))
    return [p for p in paragraphs if p.strip()]


def _build_intro(host: str, title: str) -> PodcastSegment:
    """인트로 세그먼트를 생성합니다."""
    text = (
        f'안녕하세요, {host}입니다. '
        f'오늘은 "{title}"에 대해 이야기해 보겠습니다. '
        f'끝까지 함께 해주세요.'
    )
    return PodcastSegment(
        segment_type='intro',
        text=text,
        duration_minutes=_estimate_duration(text),
    )


def _build_main_segments(paragraphs: List[str]) -> List[PodcastSegment]:
    """본론 세그먼트를 생성합니다."""
    segments = []
    for para in paragraphs:
        segments.append(PodcastSegment(
            segment_type='main',
            text=para,
            duration_minutes=_estimate_duration(para),
        ))
    return segments


def _build_commentary(paragraphs: List[str], host: str) -> PodcastSegment:
    """코멘터리 세그먼트를 생성합니다."""
    # 각 문단의 첫 문장을 요약 포인트로 활용
    points = []
    for para in paragraphs[:5]:
        sentences = re.split(r'[.!?。]\s*', para)
        first = sentences[0].strip() if sentences else ''
        if first:
            points.append(first)

    if not points:
        commentary_text = f'{host}의 코멘터리: 흥미로운 내용이었습니다.'
    else:
        summary = '; '.join(points[:3])
        commentary_text = (
            f'{host}의 코멘터리입니다. '
            f'주요 포인트를 정리하면: {summary}. '
            f'이런 관점에서 생각해 볼 만한 주제라고 봅니다.'
        )

    return PodcastSegment(
        segment_type='commentary',
        text=commentary_text,
        duration_minutes=_estimate_duration(commentary_text),
    )


def _build_outro(host: str) -> PodcastSegment:
    """아웃트로 세그먼트를 생성합니다."""
    text = (
        f'오늘도 들어주셔서 감사합니다. '
        f'{host}였습니다. 다음 에피소드에서 만나요!'
    )
    return PodcastSegment(
        segment_type='outro',
        text=text,
        duration_minutes=_estimate_duration(text),
    )


def generate_commentary(
    content: str,
    host_name: str = 'Host',
) -> PodcastScript:
    """
    콘텐츠를 기반으로 코멘터리 팟캐스트 대본을 생성합니다.

    Args:
        content: 원본 콘텐츠 텍스트
        host_name: 호스트 이름 (기본: 'Host')

    Returns:
        PodcastScript 대본 객체
    """
    if not content or not content.strip():
        return PodcastScript(
            title='빈 에피소드',
            host=host_name,
            segments=[],
            total_duration_minutes=0.0,
        )

    title = _extract_title(content)
    paragraphs = _split_into_paragraphs(content)

    segments = []
    # 인트로
    segments.append(_build_intro(host_name, title))
    # 본론
    segments.extend(_build_main_segments(paragraphs))
    # 코멘터리
    segments.append(_build_commentary(paragraphs, host_name))
    # 아웃트로
    segments.append(_build_outro(host_name))

    total_duration = round(sum(s.duration_minutes for s in segments), 2)

    return PodcastScript(
        title=title,
        host=host_name,
        segments=segments,
        total_duration_minutes=total_duration,
    )
