"""문서 AI 리스타일 Import + 답변 블록 컴파일러

텍스트를 카드형 구조로 재구성하고, 긴 원고를 질문-답변 블록으로 분해한다.
"""
from dataclasses import dataclass, field
import re


@dataclass
class ContentCard:
    """콘텐츠 카드 단위"""
    card_type: str      # "heading", "text", "highlight", "quote", "list"
    title: str = ""
    content: str = ""
    order: int = 0


@dataclass
class RestyledContent:
    """리스타일 결과"""
    original_length: int
    cards: list[ContentCard] = field(default_factory=list)
    layout: str = "card"   # "card", "timeline", "grid"


@dataclass
class AnswerBlock:
    """질문-답변 블록"""
    question: str
    answer: str
    source_paragraph: int  # 원본 문단 인덱스
    word_count: int = 0


# 질문 패턴: 물음표 또는 한국어 의문사로 시작
_QUESTION_PATTERN = re.compile(
    r'.*\?$|^(무엇|어떻게|왜|언제|어디|누가|어떤|몇|얼마)',
)

# 마크다운 헤딩 패턴
_HEADING_PATTERN = re.compile(r'^#{1,6}\s+(.+)$')

# 인용문 패턴
_QUOTE_PATTERN = re.compile(r'^>\s*(.+)$')

# 목록 패턴 (-, *, 숫자.)
_LIST_PATTERN = re.compile(r'^[\-\*]\s+.+|^\d+\.\s+.+')

# 강조(하이라이트) 패턴 (**텍스트** 또는 *텍스트*)
_HIGHLIGHT_PATTERN = re.compile(r'^\*{1,2}[^*]+\*{1,2}$')


def _classify_line(line: str) -> str:
    """한 줄의 마크다운 유형을 판별한다."""
    stripped = line.strip()
    if _HEADING_PATTERN.match(stripped):
        return 'heading'
    if _QUOTE_PATTERN.match(stripped):
        return 'quote'
    if _LIST_PATTERN.match(stripped):
        return 'list'
    if _HIGHLIGHT_PATTERN.match(stripped):
        return 'highlight'
    return 'text'


def _extract_heading_title(line: str) -> str:
    """마크다운 헤딩에서 제목 텍스트를 추출한다."""
    m = _HEADING_PATTERN.match(line.strip())
    return m.group(1).strip() if m else line.strip()


def _extract_quote_content(line: str) -> str:
    """인용문에서 > 기호를 제거한다."""
    m = _QUOTE_PATTERN.match(line.strip())
    return m.group(1).strip() if m else line.strip()


def restyle_document(text: str, layout: str = 'card') -> RestyledContent:
    """텍스트를 카드 구조로 분해한다.

    마크다운 기호(#, -, >, *)를 감지하여 적절한 카드 타입으로 분류.
    - 헤딩(#) → heading 카드
    - 긴 문단 → text 카드
    - 짧은 강조(**) → highlight 카드
    - 인용(>) → quote 카드
    - 목록(-, *) → list 카드
    """
    if not text or not text.strip():
        return RestyledContent(original_length=0, cards=[], layout=layout)

    original_length = len(text)
    lines = text.split('\n')
    cards: list[ContentCard] = []
    order = 0

    # 연속 목록 라인을 모아두기 위한 버퍼
    list_buffer: list[str] = []

    def _flush_list_buffer():
        nonlocal order
        if list_buffer:
            cards.append(ContentCard(
                card_type='list',
                content='\n'.join(list_buffer),
                order=order,
            ))
            order += 1
            list_buffer.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            _flush_list_buffer()
            continue

        line_type = _classify_line(stripped)

        if line_type == 'list':
            list_buffer.append(stripped)
            continue

        # 목록이 아닌 줄이 오면 버퍼 플러시
        _flush_list_buffer()

        if line_type == 'heading':
            cards.append(ContentCard(
                card_type='heading',
                title=_extract_heading_title(stripped),
                order=order,
            ))
            order += 1

        elif line_type == 'quote':
            cards.append(ContentCard(
                card_type='quote',
                content=_extract_quote_content(stripped),
                order=order,
            ))
            order += 1

        elif line_type == 'highlight':
            # 마크다운 강조 기호 제거
            clean = stripped.strip('*').strip()
            cards.append(ContentCard(
                card_type='highlight',
                content=clean,
                order=order,
            ))
            order += 1

        else:
            # 일반 텍스트
            cards.append(ContentCard(
                card_type='text',
                content=stripped,
                order=order,
            ))
            order += 1

    # 마지막 목록 버퍼 플러시
    _flush_list_buffer()

    return RestyledContent(
        original_length=original_length,
        cards=cards,
        layout=layout,
    )


def compile_answer_blocks(content: str) -> list[AnswerBlock]:
    """문단을 분석하여 Q&A 블록으로 변환한다.

    질문형 문장(?, 무엇, 어떻게, 왜 등)을 질문으로,
    뒤따르는 내용을 답변으로 매핑한다.
    질문 없는 문단은 주제문을 질문으로 변환한다.
    """
    if not content or not content.strip():
        return []

    # 빈 줄 기준으로 문단 분리
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', content) if p.strip()]
    blocks: list[AnswerBlock] = []

    for idx, para in enumerate(paragraphs):
        sentences = [s.strip() for s in re.split(r'(?<=[.?!。])\s+', para) if s.strip()]
        if not sentences:
            continue

        question = None
        answer_parts: list[str] = []

        for sent in sentences:
            if question is None and _QUESTION_PATTERN.match(sent):
                question = sent
            else:
                answer_parts.append(sent)

        # 질문이 없으면 첫 문장을 질문으로 변환
        if question is None:
            first = sentences[0]
            # 주제문을 의문형으로 변환
            question = _to_question(first)
            answer_parts = sentences[1:] if len(sentences) > 1 else [first]

        answer_text = ' '.join(answer_parts)
        word_count = len(answer_text.split())

        blocks.append(AnswerBlock(
            question=question,
            answer=answer_text,
            source_paragraph=idx,
            word_count=word_count,
        ))

    return blocks


def _to_question(sentence: str) -> str:
    """평서문을 질문 형태로 변환한다."""
    cleaned = sentence.rstrip('.。!').strip()
    # 이미 물음표가 있으면 그대로
    if cleaned.endswith('?'):
        return cleaned
    return cleaned + '?'


def export_blocks(blocks: list[AnswerBlock], format: str = 'html') -> str:
    """AnswerBlock 목록을 html 또는 markdown으로 내보낸다."""
    if not blocks:
        return ''

    if format == 'markdown':
        return _export_markdown(blocks)
    return _export_html(blocks)


def _export_html(blocks: list[AnswerBlock]) -> str:
    """HTML 형식으로 내보내기"""
    parts = ['<div class="qa-blocks">']
    for i, block in enumerate(blocks):
        parts.append(f'  <div class="qa-block" data-index="{i}">')
        parts.append(f'    <h3 class="question">{_escape_html(block.question)}</h3>')
        parts.append(f'    <p class="answer">{_escape_html(block.answer)}</p>')
        parts.append('  </div>')
    parts.append('</div>')
    return '\n'.join(parts)


def _export_markdown(blocks: list[AnswerBlock]) -> str:
    """Markdown 형식으로 내보내기"""
    parts: list[str] = []
    for block in blocks:
        parts.append(f'### {block.question}')
        parts.append('')
        parts.append(block.answer)
        parts.append('')
    return '\n'.join(parts).rstrip('\n')


def _escape_html(text: str) -> str:
    """기본 HTML 이스케이프"""
    return (
        text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
    )


def merge_short_cards(
    cards: list[ContentCard],
    min_length: int = 50,
) -> list[ContentCard]:
    """너무 짧은 인접 카드를 병합한다.

    같은 타입의 연속 카드 중 content 길이가 min_length 미만인 것을
    이전 카드에 병합한다. heading 카드는 병합하지 않는다.
    """
    if not cards:
        return []

    merged: list[ContentCard] = []
    for card in cards:
        # heading은 항상 독립 유지
        if card.card_type == 'heading':
            merged.append(card)
            continue

        content_len = len(card.content)

        # 병합 조건: 짧은 카드 + 이전 카드 존재 + 이전 카드가 heading이 아님
        if (
            content_len < min_length
            and merged
            and merged[-1].card_type != 'heading'
        ):
            prev = merged[-1]
            if prev.content:
                prev.content = prev.content + '\n' + card.content
            else:
                prev.content = card.content
        else:
            merged.append(card)

    # order 재정렬
    for i, card in enumerate(merged):
        card.order = i

    return merged
