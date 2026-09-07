from pathlib import Path

from prompts.styles.quiz import QUIZ_PROMPT
from prompts.styles.retention_cards import RETENTION_CARDS_PROMPT
from services.export.anki_export_service import parse_anki_cards

ROOT = Path(__file__).resolve().parents[1]


def test_anki_route_and_frontend_contract_are_connected():
    routes = (ROOT / "routes" / "export_routes.py").read_text(encoding="utf-8")
    api = (ROOT / "frontend" / "lib" / "api.ts").read_text(encoding="utf-8")
    card = (ROOT / "frontend" / "components" / "result" / "ResultCard.tsx").read_text(encoding="utf-8")

    assert "@blog_bp.route('/api/export/anki', methods=['POST'])" in routes
    assert "@require_auth\ndef export_anki" in routes
    assert "X-Anki-Card-Count" in routes
    assert "format: 'markdown' | 'anki'" in api
    assert "const ANKI_EXPORT_STYLES = new Set(['quiz', 'retention_cards'])" in card
    assert "const canExportAnki = ANKI_EXPORT_STYLES.has(report.style)" in card
    assert "{canExportAnki && (" in card
    assert "Anki 덱 (.apkg)" in card
    assert "source_url: report.url" in card


def test_quiz_prompt_output_format_can_be_exported():
    sample = QUIZ_PROMPT.split("# 출력 형식", 1)[1].split("(같은 형식", 1)[0]
    sample = sample.replace("[A/B/C/D 중 하나]", "B")
    # 프롬프트 예시는 동일한 질문이므로 하나로 중복 제거된다.
    cards = parse_anki_cards(sample, style="quiz")
    assert len(cards) == 1
    assert "A. [보기 A]" in cards[0].front
    assert "D. [보기 D]" in cards[0].front
    assert "정답: B. [보기 B]" in cards[0].back


def test_retention_prompt_output_format_can_be_exported():
    sample = RETENTION_CARDS_PROMPT.split("# 출력 형식", 1)[1].split("(같은 형식", 1)[0]
    cards = parse_anki_cards(sample, style="retention_cards")
    assert len(cards) == 1
    assert cards[0].front == "[핵심을 떠올리는 질문]"
    assert "정답: [Recall 정답 + Apply 기준 답안]" in cards[0].back
    assert "Explain: [개념 설명 2~3문장]" in cards[0].back
    assert "Apply: [입력 본문 기준 적용 과제]" in cards[0].back
