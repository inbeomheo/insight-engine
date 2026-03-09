"""
보도자료 팩토리 서비스

영상 데이터로부터 보도자료 키트(헤드라인, 인용문, 팩트시트 등)를 생성하고
표준 보도자료 양식으로 포맷팅합니다. 순수 파이썬, 규칙 기반.
"""
import re
from dataclasses import dataclass, field
from datetime import date
from typing import List, Dict


@dataclass
class Quote:
    """보도자료 인용문"""
    text: str
    speaker: str
    title: str


@dataclass
class PressKit:
    """보도자료 키트 — 보도자료 구성에 필요한 모든 요소"""
    headline: str
    subheadline: str
    body: str
    quotes: List[Quote]
    speaker_bio: str
    key_facts: List[str]
    still_timestamps: List[str]
    contact_info: Dict[str, str]


# 따옴표로 감싼 직접 인용문 패턴 (한국어 큰따옴표 포함)
_QUOTE_PATTERN = re.compile(
    r'["\u201C\u201D]([^"\u201C\u201D]{10,200})["\u201C\u201D]'
)

# 숫자/통계 포함 문장 패턴 (%, 달러, 원, 배, 만, 억 등)
_STAT_PATTERN = re.compile(
    r'[^.!?\n]*\d+[\d,.]*\s*(?:%|퍼센트|달러|원|배|만|억|조|건|명|개|회|년|월|일|시간|분|초|kg|km|m|g|ml|GB|MB|TB)[^.!?\n]*[.!?]?'
)

# 타임스탬프 패턴 — 자막 세그먼트 형식 [MM:SS] 또는 [HH:MM:SS]
_TIMESTAMP_PATTERN = re.compile(
    r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]'
)

# 전환 키워드 — 주제 변경 시점을 나타내는 단어
_TRANSITION_KEYWORDS = [
    '다음으로', '한편', '또한', '그런데', '그래서', '결론적으로',
    '마지막으로', '첫째', '둘째', '셋째', '정리하면', '요약하면',
    '중요한 것은', '핵심은', 'next', 'however', 'finally',
    'in conclusion', 'first', 'second', 'third', 'let me',
    '그러면', '이제', '자 그럼', '살펴보면',
]


def _extract_sentences(text: str) -> List[str]:
    """텍스트를 문장 단위로 분리합니다."""
    # 마침표/느낌표/물음표 기준 분리, 빈 문장 제거
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]


def _extract_quotes(transcript: str, speaker: str, company: str) -> List[Quote]:
    """트랜스크립트에서 따옴표 포함 문장을 인용문으로 추출합니다."""
    quotes = []
    seen = set()
    for match in _QUOTE_PATTERN.finditer(transcript):
        quote_text = match.group(1).strip()
        if quote_text in seen:
            continue
        seen.add(quote_text)
        title = f"{company} 대표" if company else "발표자"
        quotes.append(Quote(
            text=quote_text,
            speaker=speaker or "발표자",
            title=title,
        ))
    return quotes


def _extract_key_facts(transcript: str) -> List[str]:
    """숫자/통계 포함 문장을 팩트로 추출합니다."""
    facts = []
    seen = set()
    for match in _STAT_PATTERN.finditer(transcript):
        fact = match.group(0).strip()
        # 너무 짧거나 긴 팩트 제외
        if len(fact) < 10 or len(fact) > 300:
            continue
        if fact in seen:
            continue
        seen.add(fact)
        facts.append(fact)
    return facts


def _extract_still_timestamps(transcript: str) -> List[str]:
    """자막에서 주요 전환점 시점을 추출합니다.

    타임스탬프가 포함된 자막이면 해당 시점을,
    아니면 전환 키워드가 등장하는 위치 기반으로 추정합니다.
    """
    timestamps = []
    seen = set()

    # 방법 1: 명시적 타임스탬프에서 전환 키워드 근처 추출
    lines = transcript.split('\n')
    for line in lines:
        ts_match = _TIMESTAMP_PATTERN.search(line)
        if not ts_match:
            continue
        ts = ts_match.group(1)
        # 전환 키워드 포함 여부 확인
        line_lower = line.lower()
        for keyword in _TRANSITION_KEYWORDS:
            if keyword in line_lower and ts not in seen:
                seen.add(ts)
                timestamps.append(ts)
                break

    # 방법 2: 타임스탬프 없으면 전환 키워드 등장 순서로 인덱스 표기
    if not timestamps:
        total_len = len(transcript)
        if total_len == 0:
            return []
        for i, line in enumerate(lines):
            line_lower = line.lower()
            for keyword in _TRANSITION_KEYWORDS:
                if keyword in line_lower:
                    # 전체 대비 위치를 비율로 추정 (분:초 형태)
                    position = sum(len(l) for l in lines[:i])
                    ratio = position / total_len
                    # 가정: 평균 10분 영상
                    est_seconds = int(ratio * 600)
                    minutes = est_seconds // 60
                    seconds = est_seconds % 60
                    ts = f"{minutes}:{seconds:02d}"
                    if ts not in seen:
                        seen.add(ts)
                        timestamps.append(ts)
                    break

    return timestamps


def _build_body(transcript: str, title: str) -> str:
    """트랜스크립트에서 보도자료 본문을 구성합니다."""
    sentences = _extract_sentences(transcript)
    if not sentences:
        return f"{title}에 대한 상세 내용입니다."

    # 리드문: 첫 2-3문장
    lead_count = min(3, len(sentences))
    lead = ' '.join(sentences[:lead_count])

    # 본문: 나머지 문장 중 핵심 발췌 (최대 10문장)
    body_sentences = sentences[lead_count:lead_count + 10]
    body = ' '.join(body_sentences) if body_sentences else ""

    return f"{lead}\n\n{body}" if body else lead


def generate_press_kit(video_data: dict) -> PressKit:
    """영상 데이터로부터 보도자료 키트를 생성합니다.

    Args:
        video_data: {
            "title": "영상 제목",
            "transcript": "자막 전체 텍스트",
            "speaker": "발표자 이름" (선택),
            "company": "소속 회사/기관" (선택),
        }

    Returns:
        PressKit 데이터클래스 인스턴스
    """
    title = video_data.get("title", "").strip()
    transcript = video_data.get("transcript", "").strip()
    speaker = video_data.get("speaker", "").strip()
    company = video_data.get("company", "").strip()

    # 헤드라인: 제목 기반
    headline = title or "보도자료"
    # 서브헤드라인: 제목 축약 + 회사명
    if company:
        subheadline = f"{company}, {headline} 발표"
    else:
        subheadline = f"{headline} — 주요 내용 안내"

    # 본문 구성
    body = _build_body(transcript, title)

    # 인용문 추출
    quotes = _extract_quotes(transcript, speaker, company)

    # 발표자 소개
    if speaker and company:
        speaker_bio = f"{speaker}은(는) {company}에서 활동하고 있습니다."
    elif speaker:
        speaker_bio = f"{speaker}은(는) 해당 분야의 전문가입니다."
    else:
        speaker_bio = ""

    # 핵심 팩트
    key_facts = _extract_key_facts(transcript)

    # 스틸컷 시점
    still_timestamps = _extract_still_timestamps(transcript)

    # 연락처 정보 (기본 템플릿)
    contact_info = {}
    if company:
        contact_info["organization"] = company
    if speaker:
        contact_info["contact_person"] = speaker

    return PressKit(
        headline=headline,
        subheadline=subheadline,
        body=body,
        quotes=quotes,
        speaker_bio=speaker_bio,
        key_facts=key_facts,
        still_timestamps=still_timestamps,
        contact_info=contact_info,
    )


def format_press_release(kit: PressKit) -> str:
    """PressKit을 표준 보도자료 텍스트로 포맷팅합니다.

    Args:
        kit: generate_press_kit()의 반환값

    Returns:
        보도자료 텍스트 (날짜 + 헤드라인 + 리드문 + 본문 + 인용문 + 팩트시트)
    """
    today = date.today().strftime("%Y년 %m월 %d일")
    parts = []

    # 날짜
    parts.append(f"보도일자: {today}")
    parts.append("")

    # 헤드라인
    parts.append(f"# {kit.headline}")
    parts.append(f"## {kit.subheadline}")
    parts.append("")

    # 본문
    parts.append(kit.body)
    parts.append("")

    # 인용문
    if kit.quotes:
        parts.append("### 주요 인용")
        for q in kit.quotes:
            parts.append(f'> "{q.text}"')
            parts.append(f"> — {q.speaker}, {q.title}")
            parts.append("")

    # 팩트시트
    if kit.key_facts:
        parts.append("### 핵심 팩트")
        for fact in kit.key_facts:
            parts.append(f"- {fact}")
        parts.append("")

    # 발표자 소개
    if kit.speaker_bio:
        parts.append("### 발표자 소개")
        parts.append(kit.speaker_bio)
        parts.append("")

    # 스틸컷 참고 시점
    if kit.still_timestamps:
        parts.append("### 스틸컷 참고 시점")
        for ts in kit.still_timestamps:
            parts.append(f"- [{ts}]")
        parts.append("")

    # 연락처
    if kit.contact_info:
        parts.append("### 문의처")
        for key, value in kit.contact_info.items():
            parts.append(f"- {key}: {value}")
        parts.append("")

    # 보도자료 종료 표시
    parts.append("###")

    return '\n'.join(parts)
