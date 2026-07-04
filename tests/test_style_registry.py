"""스타일 레지스트리 동기화 테스트."""
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _frontend_style_ids() -> set[str]:
    text = (ROOT / "frontend" / "lib" / "constants.ts").read_text(encoding="utf-8")
    block = re.search(r"export const STYLE_OPTIONS[^=]*=\s*\[(.*?)\];", text, re.S)
    assert block, "frontend STYLE_OPTIONS 블록을 찾을 수 없습니다."
    return set(re.findall(r"id:\s*'([^']+)'", block.group(1)))


def _frontend_quiz_entry() -> str:
    text = (ROOT / "frontend" / "lib" / "constants.ts").read_text(encoding="utf-8")
    match = re.search(r"\{\s*id:\s*'quiz'.*?\}", text, re.S)
    assert match, "프론트엔드 STYLE_OPTIONS에 quiz가 없습니다."
    return match.group(0)


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


def test_quiz_style_registry_and_metadata():
    """quiz는 UI용 전체 스타일로 등록된다."""
    from config import STYLE_OPTIONS, STYLE_TEMPERATURE
    from prompts.styles import STYLE_PROMPTS, TRANSFORM_STYLE_IDS

    labels = dict(STYLE_OPTIONS)

    assert "quiz" in STYLE_PROMPTS
    assert "quiz" not in TRANSFORM_STYLE_IDS
    assert labels["quiz"] == "🧠 퀴즈"
    assert STYLE_TEMPERATURE["quiz"] == 0.5

    frontend_entry = _frontend_quiz_entry()
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
