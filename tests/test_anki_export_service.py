from __future__ import annotations

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
