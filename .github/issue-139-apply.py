from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8-sig")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one anchor in {path}, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


service = r'''"""Insight Engine 결과를 Anki ``.apkg`` 덱으로 변환합니다.

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
'''
(ROOT / "services" / "export" / "anki_export_service.py").write_text(service, encoding="utf-8")

route_path = ROOT / "routes" / "export_routes.py"
route_text = route_path.read_text(encoding="utf-8-sig")
if "def export_anki" in route_text:
    raise SystemExit("Anki route already exists")
route_append = r'''


@blog_bp.route('/api/export/anki', methods=['POST'])
@require_auth
def export_anki():
    """퀴즈·리텐션 카드를 Anki .apkg 덱으로 내보냅니다."""
    from services.export.anki_export_service import AnkiExportError, build_anki_package

    try:
        data = request.get_json(silent=True) or {}
        title = data.get('title', 'Insight Engine 학습 덱')
        content = data.get('content', '')
        cards = data.get('cards')
        if not content and not cards:
            return api_error('Anki로 변환할 콘텐츠나 카드가 없습니다.', 400)

        buffer, card_count = build_anki_package(
            title=title,
            content=content,
            style=data.get('style', ''),
            source_url=data.get('source_url') or data.get('url', ''),
            tags=data.get('tags') or [],
            cards=cards,
        )
        safe_title = re_module.sub(r'[^\w\s가-힣-]', '', title)[:50].strip() or 'insight-engine-deck'
        response = send_file(
            buffer,
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=f'{safe_title}.apkg',
        )
        response.headers['X-Anki-Card-Count'] = str(card_count)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response
    except AnkiExportError as exc:
        return api_error(str(exc), 400)
    except Exception as exc:
        current_app.logger.exception('Anki export failed')
        return api_error('Anki 내보내기 실패', 500)
'''
route_path.write_text(route_text.rstrip() + route_append + "\n", encoding="utf-8")

requirements_path = ROOT / "requirements.txt"
requirements = requirements_path.read_text(encoding="utf-8")
if "genanki" not in requirements.lower():
    requirements_path.write_text(requirements.rstrip() + "\ngenanki==0.13.1\n", encoding="utf-8")

api_path = ROOT / "frontend" / "lib" / "api.ts"
replace_once(
    api_path,
    "// 포맷별 내보내기 (MD)\nexport async function exportFormat(format: 'markdown', title: string, content: string): Promise<Blob> {\n  return requestBlob(`/api/export/${format}`, { method: 'POST', body: JSON.stringify({ title, content }) });\n}",
    """// 포맷별 내보내기 (Markdown / Anki)
export interface ExportMetadata {
  style?: string;
  source_url?: string;
  tags?: string[];
  cards?: Array<{ front: string; back: string; chapter?: string; tags?: string[] }>;
}

export async function exportFormat(
  format: 'markdown' | 'anki',
  title: string,
  content: string,
  metadata: ExportMetadata = {},
): Promise<Blob> {
  return requestBlob(`/api/export/${format}`, {
    method: 'POST',
    body: JSON.stringify({ title, content, ...metadata }),
  });
}""",
    "frontend export API",
)

card_path = ROOT / "frontend" / "components" / "result" / "ResultCard.tsx"
replace_once(
    card_path,
    """  async function handleExportFormat(format: 'markdown') {
    try {
      const blob = await exportFormat(format, report.title, report.content);
      const ext = format === 'markdown' ? 'md' : format;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title.slice(0, 50)}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`${ext.toUpperCase()} 내보내기 완료`);
    } catch {
      toast.error('내보내기에 실패했습니다.');
    }
  }""",
    """  async function handleExportFormat(format: 'markdown' | 'anki') {
    try {
      const blob = await exportFormat(format, report.title, report.content, {
        style: report.style,
        source_url: report.url,
        tags: [report.style, 'generated-content'],
      });
      const ext = format === 'markdown' ? 'md' : 'apkg';
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${report.title.slice(0, 50)}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(format === 'anki' ? 'Anki 덱 내보내기 완료' : 'MD 내보내기 완료');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : '내보내기에 실패했습니다.');
    }
  }""",
    "ResultCard export handler",
)
replace_once(
    card_path,
    """              <DropdownMenuItem onClick={() => handleExportFormat('markdown')}>
                <FileText className=\"h-3.5 w-3.5 mr-2\" />
                마크다운 (.md)
              </DropdownMenuItem>""",
    """              <DropdownMenuItem onClick={() => handleExportFormat('markdown')}>
                <FileText className=\"h-3.5 w-3.5 mr-2\" />
                마크다운 (.md)
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => handleExportFormat('anki')}>
                <Layers className=\"h-3.5 w-3.5 mr-2\" />
                Anki 덱 (.apkg)
              </DropdownMenuItem>""",
    "ResultCard Anki menu",
)

tests = r'''from __future__ import annotations

import io
import zipfile

import pytest

from services.export.anki_export_service import (
    AnkiExportError,
    build_anki_package,
    parse_anki_cards,
)


QUIZ = """
## AI 에이전트 학습 퀴즈

### 문제

1. **질문**: 에이전트의 핵심 반복 구조는 무엇인가?
   A. 계획만 세운다
   B. 관찰하고 행동한 뒤 다시 평가한다
   C. 한 번만 검색한다
   D. 메모리를 삭제한다
   **정답**: B
   **해설**: 에이전트는 관찰, 행동, 평가의 반복으로 목표를 수행한다.

2. **질문**: 도구 호출 전 필요한 것은?
   A. 권한 확인
   B. 무조건 실행
   C. 로그 삭제
   D. 입력 무시
   **정답**: A
   **해설**: 권한과 입력 경계를 먼저 확인해야 한다.
"""

RETENTION = """
## 컨텍스트 관리

### 카드 1
**Recall**: 컨텍스트 윈도우가 필요한 이유는?
**Answer Key**: 모델이 현재 작업에 필요한 정보를 참조하기 위해서다.

### 카드 2
**앞면**: 검색 결과를 그대로 실행하면 안 되는 이유는?
**뒷면**: 외부 입력은 신뢰할 수 없는 데이터이므로 검증해야 한다.
"""


def test_parse_quiz_cards_preserves_options_answer_and_explanation():
    cards = parse_anki_cards(QUIZ, style="quiz")
    assert len(cards) == 2
    assert cards[0].front == "에이전트의 핵심 반복 구조는 무엇인가?"
    assert "B. 관찰하고 행동한 뒤 다시 평가한다" in cards[0].back
    assert "정답: B." in cards[0].back
    assert "해설:" in cards[0].back
    assert "quiz" in cards[0].tags


def test_parse_retention_cards_supports_korean_and_english_labels():
    cards = parse_anki_cards(RETENTION, style="summary")
    assert [card.front for card in cards] == [
        "컨텍스트 윈도우가 필요한 이유는?",
        "검색 결과를 그대로 실행하면 안 되는 이유는?",
    ]
    assert all(card.back for card in cards)
    assert all("retention-card" in card.tags for card in cards)


def test_structured_cards_are_supported_and_deduplicated():
    cards = parse_anki_cards(
        "",
        cards=[
            {"front": "Q", "back": "A", "chapter": "1장", "tags": ["핵심"]},
            {"front": "Q", "back": "A"},
        ],
    )
    assert len(cards) == 1
    assert cards[0].chapter == "1장"


def test_empty_or_unparseable_content_fails_instead_of_creating_empty_deck():
    with pytest.raises(AnkiExportError, match="카드를 찾지 못했습니다"):
        parse_anki_cards("일반 본문입니다.")


def test_build_package_creates_importable_apkg_container_with_metadata():
    buffer, count = build_anki_package(
        title="에이전트 복습",
        content=QUIZ,
        style="quiz",
        source_url="https://www.youtube.com/watch?v=abcdefghijk",
        tags=["1장", "AI 학습"],
    )
    assert count == 2
    assert isinstance(buffer, io.BytesIO)
    with zipfile.ZipFile(buffer) as archive:
        names = set(archive.namelist())
        assert "collection.anki2" in names or "collection.anki21" in names
        assert "media" in names


def test_unsafe_source_scheme_is_not_embedded():
    buffer, _ = build_anki_package(
        title="안전 테스트",
        content=RETENTION,
        source_url="javascript:alert(1)",
    )
    assert b"javascript:alert" not in buffer.getvalue()
'''
(ROOT / "tests" / "test_anki_export_service.py").write_text(tests, encoding="utf-8")

contract = r'''from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_anki_route_and_frontend_contract_are_connected():
    routes = (ROOT / "routes" / "export_routes.py").read_text(encoding="utf-8")
    api = (ROOT / "frontend" / "lib" / "api.ts").read_text(encoding="utf-8")
    card = (ROOT / "frontend" / "components" / "result" / "ResultCard.tsx").read_text(encoding="utf-8")

    assert "@blog_bp.route('/api/export/anki', methods=['POST'])" in routes
    assert "@require_auth\ndef export_anki" in routes
    assert "X-Anki-Card-Count" in routes
    assert "format: 'markdown' | 'anki'" in api
    assert "Anki 덱 (.apkg)" in card
    assert "source_url: report.url" in card
'''
(ROOT / "tests" / "test_anki_export_contract.py").write_text(contract, encoding="utf-8")

print("[OK] issue #139 implementation generated")
