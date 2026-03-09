"""
슬라이드 스토리보드 + 프레임 카드 생성 서비스

자막 텍스트에서 규칙 기반으로 발표용 슬라이드 스토리보드와
캐러셀 프레임 카드를 생성합니다.
외부 AI API 호출 없이 순수 Python 로직만 사용합니다.
"""
import re
from dataclasses import dataclass, field


# ── 슬라이드 구분 신호어 (주제 전환 감지) ──
_TOPIC_SHIFT_SIGNALS = [
    '다음으로', '두 번째', '세 번째', '네 번째', '다섯 번째',
    '먼저', '그 다음', '이어서', '또한', '마지막으로',
    '첫째', '둘째', '셋째', '넷째', '다섯째',
    'first', 'second', 'third', 'next', 'finally',
    'additionally', 'moreover', 'lastly', 'furthermore',
    'now let\'s', 'moving on', 'let\'s talk about',
]

# ── 핵심 포인트 신호어 ──
_KEY_POINT_SIGNALS = [
    '핵심은', '중요한 점은', '기억해야 할', '포인트는', '요점은',
    '정리하면', '결론은', '요약하면', '한마디로', '간단히 말하면',
    'the key is', 'important point', 'remember', 'the takeaway',
    'in summary', 'to sum up', 'the bottom line', 'in short',
]

# ── 통계/데이터 신호어 ──
_STAT_SIGNALS = [
    '%', '퍼센트', '배', '증가', '감소', '성장',
    '매출', '수익', '비용', '투자', '달러', '원',
    'percent', 'increase', 'decrease', 'growth', 'revenue',
    'million', 'billion', 'doubled', 'tripled',
]

# ── 인용/명언 신호어 ──
_QUOTE_SIGNALS = [
    '말했', '말한', '했다고', '했습니다', '라고',
    '인용', '명언', '격언', '속담',
    'said', 'quote', 'according to', 'stated',
]

# ── 비주얼 타입 매핑 ──
_VISUAL_TYPES = ['quote', 'stat', 'list', 'image_placeholder']
_ASPECT_RATIOS = ['1:1', '4:5', '16:9']

# ── 타임스탬프 패턴 ──
_TIMESTAMP_RE = re.compile(r'\[(\d{1,2}:\d{2}(?::\d{2})?)\]')


@dataclass
class SlideOutline:
    """슬라이드 1장의 구조"""
    slide_number: int
    title: str
    bullet_points: list = field(default_factory=list)
    speaker_notes: str = ''
    visual_suggestion: str = ''


@dataclass
class Storyboard:
    """전체 스토리보드"""
    video_id: str
    total_slides: int = 0
    slides: list = field(default_factory=list)  # list[SlideOutline]
    estimated_duration: int = 0  # 분


@dataclass
class FrameCard:
    """캐러셀 프레임 카드 1장"""
    card_number: int
    headline: str = ''
    body_text: str = ''
    visual_type: str = 'list'  # "quote" | "stat" | "list" | "image_placeholder"
    aspect_ratio: str = '1:1'  # "1:1" | "4:5" | "16:9"


def _split_sentences(text: str) -> list[str]:
    """텍스트를 문장 단위로 분리합니다."""
    sentences = re.split(r'(?<=[.!?。])\s+', text)
    return [s.strip() for s in sentences if s.strip() and len(s.strip()) > 1]


def _contains_signal(text: str, signals: list[str]) -> bool:
    """텍스트에 신호어가 포함되어 있는지 확인합니다."""
    text_lower = text.lower()
    return any(sig.lower() in text_lower for sig in signals)


def _chunk_by_topic(sentences: list[str]) -> list[list[str]]:
    """문장 목록을 주제 전환 신호어 기준으로 청크 분할합니다.

    최소 5개 청크를 보장합니다.
    """
    if not sentences:
        return []

    chunks: list[list[str]] = []
    current_chunk: list[str] = []

    for sentence in sentences:
        # 주제 전환 신호어 감지 시 새 청크 시작
        if current_chunk and _contains_signal(sentence, _TOPIC_SHIFT_SIGNALS):
            chunks.append(current_chunk)
            current_chunk = [sentence]
        else:
            current_chunk.append(sentence)

    # 마지막 청크 추가
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _ensure_min_chunks(chunks: list[list[str]], min_count: int) -> list[list[str]]:
    """최소 청크 개수를 보장합니다.

    청크가 부족하면 가장 긴 청크를 반으로 분할합니다.
    더 이상 분할 불가하면 빈 청크를 추가하여 최소 개수를 보장합니다.
    """
    while len(chunks) < min_count and chunks:
        # 가장 긴 청크 찾기
        longest_idx = max(range(len(chunks)), key=lambda i: len(chunks[i]))
        longest = chunks[longest_idx]

        if len(longest) < 2:
            break  # 더 이상 분할 불가

        mid = len(longest) // 2
        first_half = longest[:mid]
        second_half = longest[mid:]

        chunks[longest_idx] = first_half
        chunks.insert(longest_idx + 1, second_half)

    # 분할로도 부족하면 빈 청크 추가 (슬라이드 최소 개수 보장)
    while len(chunks) < min_count:
        chunks.append([])

    return chunks


def _extract_bullet_points(sentences: list[str], max_points: int = 4) -> list[str]:
    """문장 목록에서 핵심 불릿 포인트를 추출합니다.

    핵심 포인트 신호어가 있는 문장을 우선 선택하고,
    부족하면 일반 문장에서 보충합니다.
    """
    key_sentences = [s for s in sentences if _contains_signal(s, _KEY_POINT_SIGNALS)]
    other_sentences = [s for s in sentences if s not in key_sentences]

    bullets = key_sentences[:max_points]
    remaining = max_points - len(bullets)
    if remaining > 0 and other_sentences:
        bullets.extend(other_sentences[:remaining])

    # 각 불릿을 간결하게 정리 (100자 초과 시 잘라냄)
    result = []
    for b in bullets:
        # 타임스탬프 제거
        clean = _TIMESTAMP_RE.sub('', b).strip()
        if len(clean) > 100:
            clean = clean[:97] + '...'
        if clean:
            result.append(clean)

    return result


def _generate_slide_title(sentences: list[str], slide_idx: int) -> str:
    """청크 문장에서 슬라이드 제목을 생성합니다.

    첫 문장에서 핵심 키워드를 추출하여 간결한 제목을 만듭니다.
    """
    if not sentences:
        return f'슬라이드 {slide_idx + 1}'

    first = sentences[0]
    # 타임스탬프 제거
    clean = _TIMESTAMP_RE.sub('', first).strip()

    # 주제 전환 신호어를 제목에서 제거
    for sig in _TOPIC_SHIFT_SIGNALS:
        if clean.lower().startswith(sig.lower()):
            clean = clean[len(sig):].strip()
            # 접속 조사 제거
            clean = re.sub(r'^[,\s은는이가을를에의로]+', '', clean)
            break

    # 30자 이내로 자르기
    if len(clean) > 30:
        # 쉼표나 조사 기준으로 잘라냄
        cut = clean[:30]
        last_comma = cut.rfind(',')
        last_space = cut.rfind(' ')
        cut_pos = max(last_comma, last_space)
        if cut_pos > 10:
            clean = cut[:cut_pos].strip()
        else:
            clean = cut.strip() + '...'

    return clean if clean else f'슬라이드 {slide_idx + 1}'


def _suggest_visual(sentences: list[str]) -> str:
    """청크 내용에 따라 슬라이드 비주얼을 제안합니다."""
    combined = ' '.join(sentences)
    if _contains_signal(combined, _STAT_SIGNALS):
        return '차트/그래프: 핵심 수치를 시각화'
    if _contains_signal(combined, _QUOTE_SIGNALS):
        return '인용구 카드: 핵심 발언 강조'
    if any(s.strip().startswith(('-', '•', '*')) for s in sentences):
        return '리스트 다이어그램: 항목별 아이콘 배치'
    if len(sentences) >= 3:
        return '플로우차트: 단계별 흐름 도식화'
    return '핵심 키워드 + 배경 이미지'


def _build_speaker_notes(sentences: list[str]) -> str:
    """청크 문장을 발표자 노트로 정리합니다."""
    if not sentences:
        return ''

    # 전체 문장을 연결하되 400자 제한
    notes = ' '.join(_TIMESTAMP_RE.sub('', s).strip() for s in sentences)
    if len(notes) > 400:
        notes = notes[:397] + '...'
    return notes


def generate_storyboard(transcript: str, video_id: str = '') -> Storyboard:
    """자막에서 발표용 슬라이드 스토리보드를 생성합니다 (5장+ 보장).

    Args:
        transcript: 자막 전체 텍스트 (타임스탬프 [MM:SS] 포함 가능)
        video_id: YouTube 영상 ID (선택)

    Returns:
        Storyboard 데이터클래스 (5장 이상의 SlideOutline 포함)
    """
    if not transcript or not transcript.strip():
        # 빈 입력이어도 최소 5장 슬라이드 보장
        slides = []
        default_titles = ['소개', '배경', '핵심 내용', '상세 설명', '결론 및 요약']
        for i, title in enumerate(default_titles):
            slides.append(SlideOutline(
                slide_number=i + 1,
                title=title,
                bullet_points=['내용을 추가해 주세요.'],
                speaker_notes='자막 데이터가 부족하여 기본 템플릿으로 생성되었습니다.',
                visual_suggestion='텍스트 + 배경 이미지',
            ))
        return Storyboard(
            video_id=video_id,
            total_slides=5,
            slides=slides,
            estimated_duration=5,
        )

    sentences = _split_sentences(transcript)
    chunks = _chunk_by_topic(sentences)
    # 최소 5개 청크 보장
    chunks = _ensure_min_chunks(chunks, 5)

    slides: list[SlideOutline] = []
    for idx, chunk in enumerate(chunks):
        title = _generate_slide_title(chunk, idx)
        bullets = _extract_bullet_points(chunk)
        visual = _suggest_visual(chunk)
        notes = _build_speaker_notes(chunk)

        slides.append(SlideOutline(
            slide_number=idx + 1,
            title=title,
            bullet_points=bullets if bullets else ['핵심 내용 요약'],
            speaker_notes=notes,
            visual_suggestion=visual,
        ))

    # 발표 시간 추정: 슬라이드당 약 2분
    estimated_duration = max(len(slides) * 2, 5)

    return Storyboard(
        video_id=video_id,
        total_slides=len(slides),
        slides=slides,
        estimated_duration=estimated_duration,
    )


def _determine_visual_type(text: str) -> str:
    """텍스트 내용에 따라 프레임 카드의 비주얼 타입을 결정합니다.

    통계/데이터가 인용보다 우선 (숫자가 있는 문장은 stat 우선 판정).
    """
    if _contains_signal(text, _STAT_SIGNALS):
        return 'stat'
    if _contains_signal(text, _QUOTE_SIGNALS):
        return 'quote'
    if any(marker in text for marker in ['-', '•', '*', '1.', '2.']):
        return 'list'
    return 'image_placeholder'


def _determine_aspect_ratio(visual_type: str, card_idx: int) -> str:
    """비주얼 타입과 카드 순서에 따라 종횡비를 결정합니다."""
    if visual_type == 'stat':
        return '16:9'  # 통계/차트는 가로형
    if visual_type == 'quote':
        return '1:1'  # 인용은 정사각형
    if card_idx == 0:
        return '4:5'  # 첫 카드는 세로형 (Instagram 커버)
    return '1:1'  # 기본 정사각형


def _extract_headline(sentences: list[str]) -> str:
    """문장 목록에서 카드 헤드라인을 추출합니다."""
    if not sentences:
        return '핵심 포인트'

    # 핵심 포인트 신호어가 있는 문장 우선
    for s in sentences:
        if _contains_signal(s, _KEY_POINT_SIGNALS):
            clean = _TIMESTAMP_RE.sub('', s).strip()
            if len(clean) > 50:
                clean = clean[:47] + '...'
            return clean

    # 없으면 첫 문장 사용
    clean = _TIMESTAMP_RE.sub('', sentences[0]).strip()
    if len(clean) > 50:
        clean = clean[:47] + '...'
    return clean if clean else '핵심 포인트'


def _extract_body_text(sentences: list[str], max_length: int = 200) -> str:
    """문장 목록에서 카드 본문 텍스트를 추출합니다."""
    if not sentences:
        return ''

    body_parts = []
    total_len = 0
    for s in sentences:
        clean = _TIMESTAMP_RE.sub('', s).strip()
        if not clean:
            continue
        if total_len + len(clean) > max_length:
            break
        body_parts.append(clean)
        total_len += len(clean)

    return ' '.join(body_parts)


def create_frame_cards(transcript: str, max_cards: int = 5) -> list[FrameCard]:
    """자막에서 캐러셀 카드 비주얼 설계를 생성합니다 (3장+ 보장).

    Args:
        transcript: 자막 전체 텍스트
        max_cards: 최대 카드 수 (기본 5, 최소 3 보장)

    Returns:
        FrameCard 리스트 (3장 이상)
    """
    if max_cards < 3:
        max_cards = 3

    if not transcript or not transcript.strip():
        # 빈 입력이어도 최소 3장 보장
        cards = []
        default_headlines = ['소개', '핵심 내용', '결론']
        for i, headline in enumerate(default_headlines):
            cards.append(FrameCard(
                card_number=i + 1,
                headline=headline,
                body_text='내용을 추가해 주세요.',
                visual_type='list',
                aspect_ratio='1:1' if i > 0 else '4:5',
            ))
        return cards

    sentences = _split_sentences(transcript)
    chunks = _chunk_by_topic(sentences)
    # 최소 3개 청크 보장
    chunks = _ensure_min_chunks(chunks, 3)

    # max_cards 이내로 제한
    if len(chunks) > max_cards:
        # 균등하게 병합
        merged: list[list[str]] = []
        step = len(chunks) / max_cards
        for i in range(max_cards):
            start = int(i * step)
            end = int((i + 1) * step)
            combined = []
            for c in chunks[start:end]:
                combined.extend(c)
            merged.append(combined)
        chunks = merged

    cards: list[FrameCard] = []
    for idx, chunk in enumerate(chunks):
        headline = _extract_headline(chunk)
        body = _extract_body_text(chunk)
        visual_type = _determine_visual_type(' '.join(chunk))
        aspect_ratio = _determine_aspect_ratio(visual_type, idx)

        cards.append(FrameCard(
            card_number=idx + 1,
            headline=headline,
            body_text=body,
            visual_type=visual_type,
            aspect_ratio=aspect_ratio,
        ))

    return cards
