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
import io
import os
import re
import tempfile
import unicodedata
from urllib.parse import urlparse
from typing import Any, Iterable, Sequence

import genanki


MAX_CARDS = 500
MAX_FIELD_CHARS = 20_000
MODEL_ID = 1_873_019_139


class AnkiExportError(ValueError):
    """사용자 입력으로 Anki 덱을 만들 수 없을 때 발생합니다."""


@dataclass(frozen=True)
class AnkiCard:
    front: str
    back: str
    chapter: str = ""
    tags: tuple[str, ...] = ()


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
    for match in re.finditer(r"(?m)^#{2,4}\s+(.+?)\s*$", content[:position]):
        candidate = _clean_field(match.group(1))
        if candidate and candidate not in {"문제", "퀴즈", "리텐션 카드", "복습 카드"}:
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
        answer = re.search(r"(?m)^\s*\*\*정답\*\*\s*[:：]\s*([A-Da-d])(?:[.)])?\s*(.*?)\s*$", block)
        explanation = re.search(
            r"(?ms)^\s*\*\*해설\*\*\s*[:：]\s*(.+?)(?=^\s*#{1,6}\s|\Z)",
            block,
        )
        options = _option_lines(block)
        if not answer or len(options) < 2:
            continue
        answer_label = answer.group(1).upper()
        answer_text = next((text for label, text in options if label == answer_label), _clean_field(answer.group(2)))
        option_text = "\n".join(f"{label}. {text}" for label, text in options)
        explanation_text = _clean_field(explanation.group(1)) if explanation else ""
        back_parts = [option_text, f"정답: {answer_label}. {answer_text}".rstrip()]
        if explanation_text:
            back_parts.append(f"해설: {explanation_text}")
        front = _clean_field(match.group(2))
        if front:
            cards.append(
                AnkiCard(
                    front=front,
                    back="\n\n".join(part for part in back_parts if part),
                    chapter=_nearest_heading(content, match.start()),
                    tags=("quiz", f"question-{match.group(1)}"),
                )
            )
    return cards


_FRONT_LABEL = r"(?:Recall|질문|앞면|Front)"
_BACK_LABEL = r"(?:Answer\s*Key|정답|뒷면|Back)"
_FRONT_RE = re.compile(
    rf"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?{_FRONT_LABEL}(?:\*\*)?\s*[:：]?\s*"
)
_BACK_RE = re.compile(
    rf"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?{_BACK_LABEL}(?:\*\*)?\s*[:：]?\s*"
)
_META_RE = re.compile(
    r"(?im)^\s*(?:[-*]\s*)?(?:\*\*)?(?:Source|출처|Chapter|챕터|Tags?|태그)(?:\*\*)?\s*[:：]"
)


def _parse_retention(content: str) -> list[AnkiCard]:
    starts = list(_FRONT_RE.finditer(content))
    cards: list[AnkiCard] = []
    for index, match in enumerate(starts):
        block_end = starts[index + 1].start() if index + 1 < len(starts) else len(content)
        block = content[match.end():block_end]
        back_match = _BACK_RE.search(block)
        if not back_match:
            continue
        front = _clean_field(block[:back_match.start()])
        back_tail = block[back_match.end():]
        meta_match = _META_RE.search(back_tail)
        back = _clean_field(back_tail[:meta_match.start()] if meta_match else back_tail)
        if not front or not back:
            continue
        cards.append(
            AnkiCard(
                front=front,
                back=back,
                chapter=_nearest_heading(content, match.start()),
                tags=("retention-card",),
            )
        )
    return cards


def _parse_simple_qa(content: str) -> list[AnkiCard]:
    pattern = re.compile(
        r"(?ims)^\s*(?:[-*]\s*)?(?:\*\*)?Q(?:uestion)?[.:：]\s*(.+?)\s*"
        r"^\s*(?:[-*]\s*)?(?:\*\*)?A(?:nswer)?[.:：]\s*(.+?)"
        r"(?=^\s*(?:[-*]\s*)?(?:\*\*)?Q(?:uestion)?[.:：]|\Z)"
    )
    return [
        AnkiCard(
            front=_clean_field(match.group(1)),
            back=_clean_field(match.group(2)),
            chapter=_nearest_heading(content, match.start()),
            tags=("q-and-a",),
        )
        for match in pattern.finditer(content)
        if _clean_field(match.group(1)) and _clean_field(match.group(2))
    ]


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
    """구조화 카드 또는 Markdown에서 Anki 카드를 추출합니다."""
    structured = _structured_cards(cards)
    if structured:
        parsed = structured
    else:
        normalized = _normalize_text(content)
        parsed = _parse_quiz(normalized) if style == "quiz" or "**정답**" in normalized else []
        if not parsed:
            parsed = _parse_retention(normalized)
        if not parsed:
            parsed = _parse_simple_qa(normalized)

    unique: list[AnkiCard] = []
    seen: set[str] = set()
    for card in parsed:
        key = unicodedata.normalize("NFC", f"{card.front}\n{card.back}").casefold()
        key = re.sub(r"\s+", " ", key).strip()
        if key in seen:
            continue
        seen.add(key)
        unique.append(card)

    if not unique:
        raise AnkiExportError(
            "Anki로 내보낼 카드를 찾지 못했습니다. 퀴즈의 질문/정답/해설 또는 "
            "Recall/Answer Key 형식을 확인해주세요."
        )
    if len(unique) > MAX_CARDS:
        raise AnkiExportError(f"한 번에 최대 {MAX_CARDS}장까지 내보낼 수 있습니다.")
    return unique


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
    for card in parsed_cards:
        source_html = (
            f'<a href="{escape(safe_source, quote=True)}">원문 보기</a>' if safe_source else ""
        )
        stable_guid = genanki.guid_for(
            safe_source or clean_title,
            unicodedata.normalize("NFC", card.chapter).casefold(),
            unicodedata.normalize("NFC", card.front).casefold(),
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


__all__ = ["AnkiCard", "AnkiExportError", "build_anki_package", "parse_anki_cards"]
