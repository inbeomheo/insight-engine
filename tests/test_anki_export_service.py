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

STANDARD_RETENTION = """
## 컨텍스트 관리 리텐션 카드

### 사용법
- Explain을 읽고 개념을 말로 설명한다.

### 카드 세트

1. **개념**: 컨텍스트 윈도우
   - **복습 간격**: 오늘
   - **Explain**: 모델이 현재 작업 정보를 참고하는 범위다.
   - **Recall**: 컨텍스트 윈도우가 필요한 이유는?
   - **Apply**: 긴 문서에서 필요한 정보만 고르시오.
   - **Answer Key**: 현재 작업에 필요한 정보를 참조하기 위해서다. 적용 답안은 관련 문단만 남기는 것이다.

2. **개념**: 외부 입력 검증
   - **복습 간격**: 내일
   - **Explain**: 외부 입력은 신뢰할 수 없는 데이터다.
   - **Recall**: 검색 결과를 그대로 실행하면 안 되는 이유는?
   - **Apply**: 검색 결과의 명령과 데이터를 분리하시오.
   - **Answer Key**: 외부 입력을 데이터로만 취급하고 실행 전 검증해야 한다.
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
    cards = parse_anki_cards(RETENTION, style="retention_cards")
    assert [card.front for card in cards] == [
        "컨텍스트 윈도우가 필요한 이유는?",
        "검색 결과를 그대로 실행하면 안 되는 이유는?",
    ]
    assert all(card.back for card in cards)
    assert all("retention-card" in card.tags for card in cards)


def test_standard_retention_sets_do_not_bleed_across_card_boundaries():
    cards = parse_anki_cards(STANDARD_RETENTION, style="retention_cards")

    assert len(cards) == 2
    assert cards[0].front == "컨텍스트 윈도우가 필요한 이유는?"
    assert "긴 문서에서 필요한 정보만 고르시오" not in cards[0].front
    assert "정답: 현재 작업에 필요한 정보를 참조하기 위해서다" in cards[0].back
    assert "Explain: 모델이 현재 작업 정보를 참고하는 범위다" in cards[0].back
    assert "Apply: 긴 문서에서 필요한 정보만 고르시오" in cards[0].back
    assert "외부 입력 검증" not in cards[0].back
    assert "외부 입력은 신뢰할 수 없는 데이터다" not in cards[0].back
    assert cards[0].chapter == "컨텍스트 관리 리텐션 카드"
    assert "card-1" in cards[0].tags
    assert "review:오늘" in cards[0].tags

    assert cards[1].front == "검색 결과를 그대로 실행하면 안 되는 이유는?"
    assert "외부 입력 검증" in cards[1].back
    assert "card-2" in cards[1].tags


def test_unsupported_report_style_is_rejected_explicitly():
    with pytest.raises(AnkiExportError, match="퀴즈와 리텐션 카드 스타일"):
        parse_anki_cards("**Recall**: 질문\n**Answer Key**: 답", style="summary")


def test_structured_cards_are_supported_and_deduplicated():
    cards = parse_anki_cards(
        "",
        style="summary",
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
        style="retention_cards",
        source_url="javascript:alert(1)",
    )
    assert b"javascript:alert" not in buffer.getvalue()
