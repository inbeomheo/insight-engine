"""스타일 레지스트리 동기화 테스트."""
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _frontend_style_ids() -> set[str]:
    text = (ROOT / "frontend" / "lib" / "constants.ts").read_text(encoding="utf-8")
    block = re.search(r"export const STYLE_OPTIONS[^=]*=\s*\[(.*?)\];", text, re.S)
    assert block, "frontend STYLE_OPTIONS 블록을 찾을 수 없습니다."
    return set(re.findall(r"id:\s*'([^']+)'", block.group(1)))


def _frontend_style_entry(style_id: str) -> str:
    text = (ROOT / "frontend" / "lib" / "constants.ts").read_text(encoding="utf-8")
    match = re.search(rf"\{{\s*id:\s*'{re.escape(style_id)}'.*?\}}", text, re.S)
    assert match, f"프론트엔드 STYLE_OPTIONS에 {style_id}가 없습니다."
    return match.group(0)


def _tsx_uses_shared_style_labels(path: str) -> bool:
    text = (ROOT / path).read_text(encoding="utf-8")
    return (
        "import { STYLE_OPTIONS } from '@/lib/constants';" in text
        and "Object.fromEntries(STYLE_OPTIONS.map" in text
    )


def test_ui_style_options_are_registered_prompts():
    """UI 노출 스타일은 STYLE_PROMPTS, temperature, 프론트 상수에 모두 있어야 한다."""
    from config import STYLE_OPTIONS, STYLE_TEMPERATURE
    from prompts.styles import STYLE_PROMPTS, TRANSFORM_STYLE_IDS

    frontend_ids = _frontend_style_ids()
    backend_ui_ids = {style_id for style_id, _label in STYLE_OPTIONS}

    for style_id, _label in STYLE_OPTIONS:
        assert style_id in STYLE_PROMPTS
        assert style_id not in TRANSFORM_STYLE_IDS
        assert style_id in STYLE_TEMPERATURE
        assert style_id in frontend_ids

    assert frontend_ids <= backend_ui_ids


def test_ui_style_options_have_all_display_labels():
    """UI 스타일은 i18n/라벨 맵에도 누락 없이 등록되어야 한다."""
    from config import STYLE_OPTIONS
    from services.data.style_memory_service import STYLE_LABELS as MEMORY_STYLE_LABELS

    backend_ui_ids = {style_id for style_id, _label in STYLE_OPTIONS}

    for locale in ("ko", "en", "ja"):
        data = json.loads(
            (ROOT / "frontend" / "lib" / "i18n" / f"{locale}.json").read_text(encoding="utf-8")
        )
        assert backend_ui_ids <= set(data["styles"])

    assert _tsx_uses_shared_style_labels("frontend/components/settings/SettingsModal.tsx")
    assert _tsx_uses_shared_style_labels("frontend/components/modals/TemplateGalleryModal.tsx")
    assert backend_ui_ids <= set(MEMORY_STYLE_LABELS)


def test_quiz_style_registry_and_metadata():
    """quiz는 UI용 전체 스타일로 등록된다."""
    from config import STYLE_OPTIONS, STYLE_TEMPERATURE
    from prompts.styles import STYLE_PROMPTS, TRANSFORM_STYLE_IDS

    labels = dict(STYLE_OPTIONS)

    assert "quiz" in STYLE_PROMPTS
    assert "quiz" not in TRANSFORM_STYLE_IDS
    assert labels["quiz"] == "🧠 퀴즈"
    assert STYLE_TEMPERATURE["quiz"] == 0.5

    frontend_entry = _frontend_style_entry("quiz")
    assert "label: '퀴즈'" in frontend_entry
    assert "description: '객관식 학습 문제'" in frontend_entry


def test_quiz_prompt_is_parseable_and_grounded():
    """quiz 프롬프트는 객관식/정답/해설 형식과 근거 제한을 명시한다."""
    from prompts.base import FORBIDDEN_EXPRESSIONS, BASE_PROMPT, compose_style_prompt
    from prompts.styles import STYLE_PROMPTS

    prompt = STYLE_PROMPTS["quiz"]
    composed = compose_style_prompt("quiz", prompt)

    assert composed.startswith(BASE_PROMPT)
    assert "5~8문항" in prompt
    assert "A." in prompt and "B." in prompt and "C." in prompt and "D." in prompt
    assert "**정답**:" in prompt
    assert "**해설**:" in prompt
    assert "입력 본문에 근거" in prompt
    assert "만들지 않는다" in prompt

    for expression in FORBIDDEN_EXPRESSIONS:
        assert expression not in prompt


def test_retention_cards_style_registry_and_metadata():
    """retention_cards는 UI용 전체 스타일로 등록된다."""
    from config import STYLE_OPTIONS, STYLE_TEMPERATURE
    from prompts.styles import STYLE_PROMPTS, TRANSFORM_STYLE_IDS

    labels = dict(STYLE_OPTIONS)

    assert "retention_cards" in STYLE_PROMPTS
    assert "retention_cards" not in TRANSFORM_STYLE_IDS
    assert labels["retention_cards"] == "🧩 리텐션 카드"
    assert STYLE_TEMPERATURE["retention_cards"] == 0.5

    frontend_entry = _frontend_style_entry("retention_cards")
    assert "label: '리텐션 카드'" in frontend_entry
    assert "description: '반복 학습 카드'" in frontend_entry


def test_retention_cards_prompt_is_parseable_and_grounded():
    """retention_cards 프롬프트는 반복학습 카드 형식과 근거 제한을 명시한다."""
    from prompts.base import FORBIDDEN_EXPRESSIONS, BASE_PROMPT, compose_style_prompt
    from prompts.styles import STYLE_PROMPTS

    prompt = STYLE_PROMPTS["retention_cards"]
    composed = compose_style_prompt("retention_cards", prompt)

    assert composed.startswith(BASE_PROMPT)
    assert "4~7개의 카드" in prompt
    assert "Explain" in prompt
    assert "Recall" in prompt
    assert "Apply" in prompt
    assert "Answer Key" in prompt
    assert "**개념**:" in prompt
    assert "**복습 간격**:" in prompt
    assert "입력 본문에 근거" in prompt
    assert "만들지 않는다" in prompt

    for expression in FORBIDDEN_EXPRESSIONS:
        assert expression not in prompt
