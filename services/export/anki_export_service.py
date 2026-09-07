"""Insight Engine 결과를 Anki ``.apkg`` 덱으로 변환합니다.

지원 입력은 두 종류입니다.

* 퀴즈 스타일의 ``질문/보기/정답/해설`` Markdown
* 리텐션 카드의 ``Recall/Answer Key`` 또는 ``앞면/뒷면`` 쌍

외부 라이브러리는 패키지 작성에만 사용하며, 파싱과 입력 검증은 이 모듈에서
결정론적으로 수행합니다.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from html import escape
from pathlib import Path
from typing import Any, Iterable, Sequence
from urllib.parse import urlparse
import io
import os
import re
import tempfile
import unicodedata

import genanki


MAX_CARDS = 500
MAX_FIELD_CHARS = 20_000
MODEL_ID = 1_873_019_139
SUPPORTED_ANKI_STYLES = frozenset({"quiz", "retention_cards"})


class AnkiExportError(ValueError):
    """사용자 입력으로 Anki 덱을 만들 수 없을 때 발생합니다."""


@dataclass(frozen=True)
class AnkiCard:
    front: str
    back: str
    chapter: str = ""
    tags: tuple[str, ...] = ()
    # 표시 앞면에 보기를 추가해도 기존 퀴즈 노트의 식별자는 유지한다.
    identity_front: str = ""


class _StableNote(genanki.Note):
    def __init__(self, *args: Any, stable_guid: str, **kwargs: Any) -> None:
        self._stable_guid = stable_guid
        super().__init__(*args, **kwargs)

    @property
    def guid(self) -> str:
        return self._stable_guid


def _normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFC", str(value or ""))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"[ \t]+", " ", text).strip()


def _clean_field(value: Any) -> str:
    text = _normalize_text(value)
    text = re.sub(r"^#{1,6}\s+", "", text)
    text = re.sub(r"^[-*]\s+", "", text)
    text = text.strip(" \n-*")
    if len(text) > MAX_FIELD_CHARS:
        raise AnkiExportError(f"카드 필드는 {MAX_FIELD_CHARS:,}자를 넘을 수 없습니다.")
    return text


def _nearest_heading(content: str, position: int) -> str:
    heading = ""
    ignored = {"문제", "퀴즈", "리텐션 카드", "복습 카드", "사용법", "카드 세트"}
    for match in re.finditer(r"(?m)^#{2,4}\s+(.+?)\s*$", content[:position]):
        candidate = _clean_field(match.group(1))
        if candidate and candidate not in ignored and not re.fullmatch(r"카드\s*\d+", candidate):
            heading = candidate
    return heading


def _option_lines(block: str) -> list[tuple[str, str]]:
    return [
        (match.group(1).upper(), _clean_field(match.group(2)))
        for match in re.finditer(r"(?m)^\s*([A-Da-d])[.)]\s+(.+?)\s*$", block)
        if _clean_field(match.group(2))
    ]


def _parse_quiz(content: str) -> list[AnkiCard]:
    question_re = re.compile(
        r"(?m)^\s*(\d+)[.)]\s+\*\*질문\*\*\s*[:：]\s*(.+?)\s*$"
    )
    starts = list(question_re.finditer(content))
    cards: list[AnkiCard] = []
    for index, match in enumerate(starts):
        block_end = starts[index + 1].start() if index + 1 < len(starts) else len(content)
        block = content[match.end():block_end]
        answer = re.search(
            r"(?m)^\s*\*\*정답\*\*\s*[:：]\s*([A-Da-d])(?:[.)])?\s*(.*?)\s*$",
            block,
        )
        explanation = re.search(
            r"(?ms)^\s*\*\*해설\*\*\s*[:：]\s*(.+?)(?=^\s*#{1,6}\s|\Z)",
            block,
        )
        options = _option_lines(block[:answer.start()]) if answer else []
        if not answer or len(options) < 2:
            continue
        answer_label = answer.group(1).upper()
        labels = [label for label, _ in options]
        if answer_label not in labels or len(labels) != len(set(labels)):
            continue
        answer_text = next(
            (text for label, text in options if label == answer_label),
            _clean_field(answer.group(2)),
        )
        option_text = "\n".join(f"{label}. {text}" for label, text in options)
        explanation_text = _clean_field(explanation.group(1)) if explanation else ""
        back_parts = [f"정답: {answer_label}. {answer_text}".rstrip()]
        if explanation_text:
            back_parts.append(f"해설: {explanation_text}")
        front = _clean_field(match.group(2))
        if front:
            cards.append(
                AnkiCard(
                    front=f"{front}\n\n{option_text}",
                    back="\n\n".join(part for part in back_parts if part),
                    chapter=_nearest_heading(content, match.start()),
                    tags=("quiz", f"question-{match.group(1)}"),
                    identity_front=front,
                )
            )
    return cards


_RETENTION_SET_START_RE = re.compile(
    r"(?im)^[ \t]*(?P<number>\d+)[.)][ \t]+(?:\*\*)?개념"
    r"(?:\*\*)?[ \t]*[:：]"
)
_RETENTION_CARD_HEADING_RE = re.compile(
    r"(?im)^[ \t]*#{2,6}[ \t]+카드(?:[ \t]+(?P<number>\d+))?[^\n]*$"
)
_FRONT_RE = re.compile(
    r"(?im)^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?"
    r"(?:Recall|질문|앞면|Front)(?:\*\*)?[ \t]*[:：][ \t]*"
)
_FIELD_RE = re.compile(
    r"(?im)^[ \t]*(?:\d+[.)][ \t]+)?(?:[-*][ \t]+)?(?:\*\*)?"
    r"(?P<label>개념|복습[ \t]*간격|Explain|Recall|Apply|Answer[ \t]*Key|"
    r"질문|앞면|Front|정답|뒷면|Back|Source|출처|Chapter|챕터|Tags?|태그)"
    r"(?:\*\*)?[ \t]*[:：][ \t]*"
)
_FIELD_KEYS = {
    "개념": "concept",
    "복습 간격": "interval",
    "explain": "explain",
    "recall": "front",
    "apply": "apply",
    "answer key": "back",
    "질문": "front",
    "앞면": "front",
    "front": "front",
    "정답": "back",
    "뒷면": "back",
    "back": "back",
    "source": "source",
    "출처": "source",
    "chapter": "chapter",
    "챕터": "chapter",
    "tag": "tags",
    "tags": "tags",
    "태그": "tags",
}


def _field_key(label: str) -> str | None:
    compact = re.sub(r"\s+", " ", label.strip()).casefold()
    return _FIELD_KEYS.get(compact)


def _extract_labeled_fields(block: str) -> dict[str, str]:
    # 다음 설명 섹션이 마지막 카드의 정답에 섞이지 않도록 한다.
    block = re.split(r"(?m)^[ \t]*#{1,6}[ \t]+", block, maxsplit=1)[0]
    matches = list(_FIELD_RE.finditer(block))
    fields: dict[str, str] = {}
    for index, match in enumerate(matches):
        block_end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
        key = _field_key(match.group("label"))
        value = _clean_field(block[match.end():block_end])
        if key and value and key not in fields:
            fields[key] = value
    return fields


def _retention_card(
    *,
    content: str,
    position: int,
    fields: dict[str, str],
    number: str = "",
) -> AnkiCard | None:
    front = fields.get("front", "")
    answer = fields.get("back", "")
    if not front or not answer:
        return None

    back_parts = [f"정답: {answer}"]
    if fields.get("concept"):
        back_parts.append(f"개념: {fields['concept']}")
    if fields.get("explain"):
        back_parts.append(f"Explain: {fields['explain']}")
    if fields.get("apply"):
        back_parts.append(f"Apply: {fields['apply']}")
    if fields.get("interval"):
        back_parts.append(f"복습 간격: {fields['interval']}")

    tags = ["retention-card"]
    if number:
        tags.append(f"card-{number}")
    if fields.get("interval"):
        tags.append(f"review:{fields['interval']}")

    return AnkiCard(
        front=front,
        back="\n\n".join(back_parts),
        chapter=fields.get("chapter")
        or _nearest_heading(content, position)
        or fields.get("concept", ""),
        tags=tuple(tags),
    )


def _parse_numbered_retention_sets(content: str) -> list[AnkiCard]:
    starts = list(_RETENTION_SET_START_RE.finditer(content))
    cards: list[AnkiCard] = []
    for index, match in enumerate(starts):
        block_end = starts[index + 1].start() if index + 1 < len(starts) else len(content)
        fields = _extract_labeled_fields(content[match.start():block_end])
        card = _retention_card(
            content=content,
            position=match.start(),
            fields=fields,
            number=match.group("number"),
        )
        if card:
            cards.append(card)
    return cards


def _parse_heading_retention_cards(content: str) -> list[AnkiCard]:
    starts = list(_RETENTION_CARD_HEADING_RE.finditer(content))
    cards: list[AnkiCard] = []
    for index, match in enumerate(starts):
        block_end = starts[index + 1].start() if index + 1 < len(starts) else len(content)
        fields = _extract_labeled_fields(content[match.end():block_end])
        card = _retention_card(
            content=content,
            position=match.start(),
            fields=fields,
            number=match.group("number") or str(index + 1),
        )
        if card:
            cards.append(card)
    return cards


def _parse_unheaded_retention_pairs(content: str) -> list[AnkiCard]:
    starts = list(_FRONT_RE.finditer(content))
    cards: list[AnkiCard] = []
    for index, match in enumerate(starts):
        block_end = starts[index + 1].start() if index + 1 < len(starts) else len(content)
        fields = _extract_labeled_fields(content[match.start():block_end])
        card = _retention_card(
            content=content,
            position=match.start(),
            fields=fields,
            number=str(index + 1),
        )
        if card:
            cards.append(card)
    return cards


def _parse_retention(content: str) -> list[AnkiCard]:
    cards = _parse_numbered_retention_sets(content)
    if cards:
        return cards
    cards = _parse_heading_retention_cards(content)
    if cards:
        return cards
    return _parse_unheaded_retention_pairs(content)


def _structured_cards(raw_cards: Sequence[dict[str, Any]] | None) -> list[AnkiCard]:
    if raw_cards is None:
        return []
    if not isinstance(raw_cards, list):
        raise AnkiExportError("cards는 배열이어야 합니다.")
    cards: list[AnkiCard] = []
    for index, raw in enumerate(raw_cards):
        if not isinstance(raw, dict):
            raise AnkiExportError(f"cards[{index}]는 객체여야 합니다.")
        front = _clean_field(raw.get("front") or raw.get("question") or raw.get("recall"))
        back = _clean_field(raw.get("back") or raw.get("answer") or raw.get("answer_key"))
        if not front or not back:
            raise AnkiExportError(f"cards[{index}]에 앞면과 뒷면이 필요합니다.")
        raw_tags = raw.get("tags") or []
        if isinstance(raw_tags, str):
            raw_tags = [raw_tags]
        if not isinstance(raw_tags, list) or any(not isinstance(tag, str) for tag in raw_tags):
            raise AnkiExportError(f"cards[{index}].tags는 문자열 배열이어야 합니다.")
        cards.append(
            AnkiCard(
                front=front,
                back=back,
                chapter=_clean_field(raw.get("chapter")),
                tags=tuple(_clean_field(tag) for tag in raw_tags if _clean_field(tag)),
            )
        )
    return cards


def parse_anki_cards(
    content: str,
    *,
    style: str = "",
    cards: Sequence[dict[str, Any]] | None = None,
) -> list[AnkiCard]:
    """구조화 카드 또는 지원 스타일 Markdown에서 Anki 카드를 추출합니다."""
    structured = _structured_cards(cards)
    if structured:
        parsed = structured
    else:
        if style and style not in SUPPORTED_ANKI_STYLES:
            raise AnkiExportError(
                "Anki 내보내기는 퀴즈와 리텐션 카드 스타일에서만 지원합니다."
            )
        normalized = _normalize_text(content)
        if style == "quiz":
            parsed = _parse_quiz(normalized)
        elif style == "retention_cards":
            parsed = _parse_retention(normalized)
        else:
            parsed = _parse_quiz(normalized)
            if not parsed:
                parsed = _parse_retention(normalized)

    unique: list[AnkiCard] = []
    seen: set[tuple[str, str]] = set()
    for card in parsed:
        key = _card_content_key(card)
        if key in seen:
            continue
        seen.add(key)
        unique.append(card)

    if not unique:
        raise AnkiExportError(
            "Anki로 내보낼 카드를 찾지 못했습니다. 퀴즈의 질문/정답/해설 또는 "
            "리텐션 카드의 Recall/Answer Key 형식을 확인해주세요."
        )
    if len(unique) > MAX_CARDS:
        raise AnkiExportError(f"한 번에 최대 {MAX_CARDS}장까지 내보낼 수 있습니다.")
    return unique


def _identity_text(value: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", value).casefold()).strip()


def _card_content_key(card: AnkiCard) -> tuple[str, str]:
    # 필드 경계를 보존해야 ('a b', 'c')와 ('a', 'b c')를 구분할 수 있다.
    return _identity_text(card.front), _identity_text(card.back)


def _note_guids(cards: Sequence[AnkiCard], source: str) -> list[str]:
    """보통은 기존 ID를 보존하고, 동일 질문의 복수 카드만 내용으로 구분한다.

    답만 수정한 일반 노트는 Anki에서 업데이트된다. 동일 질문이 여러 장이면
    영구 카드 ID가 없는 입력 특성상 앞·뒷면 내용이 식별 기준이 되며, 순서가
    바뀌어도 같은 ID를 만든다. 복수 카드의 내용 변경/단일↔복수 전환은 새
    노트가 될 수 있다. 기존에 충돌하던 ID를 어느 답에 배정할지 추측하지 않는다.
    """
    base_guids = [
        genanki.guid_for(
            source,
            unicodedata.normalize("NFC", card.chapter).casefold(),
            unicodedata.normalize("NFC", card.identity_front or card.front).casefold(),
        )
        for card in cards
    ]
    counts: dict[str, int] = {}
    for guid in base_guids:
        counts[guid] = counts.get(guid, 0) + 1
    return [
        genanki.guid_for("insight-engine:card-variant:v1", guid, *_card_content_key(card))
        if counts[guid] > 1 else guid
        for card, guid in zip(cards, base_guids)
    ]


def _stable_numeric_id(namespace: str) -> int:
    value = int.from_bytes(sha256(namespace.encode("utf-8")).digest()[:4], "big")
    return 1_000_000_000 + value % 999_999_999


def _safe_url(value: str) -> str:
    value = _normalize_text(value)
    if not value:
        return ""
    parsed = urlparse(value)
    return value if parsed.scheme in {"http", "https"} and parsed.netloc else ""


def _html_field(value: str) -> str:
    return escape(value, quote=True).replace("\n", "<br>")


def _safe_tag(value: str) -> str:
    value = unicodedata.normalize("NFC", _clean_field(value)).replace(" ", "_")
    value = re.sub(r"[^\w가-힣:-]", "-", value, flags=re.UNICODE)
    return value.strip("-_: ")[:80]


def _global_tags(style: str, tags: Iterable[str]) -> list[str]:
    values = ["insight-engine"]
    if style:
        values.append(f"style:{style}")
    values.extend(tags)
    result: list[str] = []
    for value in values:
        tag = _safe_tag(value)
        if tag and tag not in result:
            result.append(tag)
    return result


def build_anki_package(
    *,
    title: str,
    content: str,
    style: str = "",
    source_url: str = "",
    tags: Sequence[str] | None = None,
    cards: Sequence[dict[str, Any]] | None = None,
) -> tuple[io.BytesIO, int]:
    """유효한 ``.apkg`` 파일과 카드 수를 반환합니다."""
    clean_title = _clean_field(title) or "Insight Engine 학습 덱"
    parsed_cards = parse_anki_cards(content, style=style, cards=cards)
    safe_source = _safe_url(source_url)
    deck_id = _stable_numeric_id(f"insight-engine:deck:{clean_title}:{safe_source}")
    model = genanki.Model(
        MODEL_ID,
        "Insight Engine Learning Card",
        fields=[
            {"name": "Front"},
            {"name": "Back"},
            {"name": "Source"},
            {"name": "Chapter"},
        ],
        templates=[
            {
                "name": "Recall",
                "qfmt": '<div class="front">{{Front}}</div>{{#Chapter}}<div class="chapter">{{Chapter}}</div>{{/Chapter}}',
                "afmt": '{{FrontSide}}<hr id="answer"><div class="back">{{Back}}</div>{{#Source}}<div class="source">{{Source}}</div>{{/Source}}',
            }
        ],
        css="""
.card { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 20px; text-align: left; color: #172033; background: #fff; line-height: 1.55; padding: 24px; }
.front { font-weight: 700; }
.back { white-space: normal; }
.chapter, .source { margin-top: 16px; font-size: 12px; color: #667085; }
.source a { color: #2563eb; }
""".strip(),
    )
    deck = genanki.Deck(deck_id, clean_title)
    base_tags = _global_tags(style, tags or [])
    note_guids = _note_guids(parsed_cards, safe_source or clean_title)
    for card, stable_guid in zip(parsed_cards, note_guids):
        source_html = (
            f'<a href="{escape(safe_source, quote=True)}">원문 보기</a>' if safe_source else ""
        )
        note_tags = list(base_tags)
        for value in card.tags:
            tag = _safe_tag(value)
            if tag and tag not in note_tags:
                note_tags.append(tag)
        deck.add_note(
            _StableNote(
                model=model,
                fields=[
                    _html_field(card.front),
                    _html_field(card.back),
                    source_html,
                    _html_field(card.chapter),
                ],
                tags=note_tags,
                stable_guid=stable_guid,
            )
        )

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".apkg", delete=False) as tmp:
            temp_path = tmp.name
        genanki.Package(deck).write_to_file(temp_path)
        payload = Path(temp_path).read_bytes()
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except FileNotFoundError:
                pass

    if not payload.startswith(b"PK"):
        raise RuntimeError("생성된 Anki 패키지가 ZIP 형식이 아닙니다.")
    buffer = io.BytesIO(payload)
    buffer.seek(0)
    return buffer, len(parsed_cards)


__all__ = [
    "AnkiCard",
    "AnkiExportError",
    "SUPPORTED_ANKI_STYLES",
    "build_anki_package",
    "parse_anki_cards",
]
