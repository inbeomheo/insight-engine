"""
베이스 프롬프트 v4.0
모든 콘텐츠 스타일에 공통 적용되는 핵심 규칙.

v4 변경점:
- 메인 생성 경로에 실제로 주입되도록 compose_style_prompt() 도입
  (v3까지는 build_full_prompt가 fusion에서만 쓰여 베이스 규칙이 누락됐음)
- SELF_CHECK / FORBIDDEN_REMINDER 블록 제거 (금지 표현 3중 반복 → 1회로 통합)
- 미사용 KEYWORDS HTML 주석 출력 지시 제거 (파서가 호출되지 않는 죽은 계약이었음)
"""

# 금지 표현 목록 (모든 스타일에 공통 적용)
FORBIDDEN_EXPRESSIONS = [
    "놀라운", "혁신적", "획기적", "최고의", "게임체인저",
    "압도적", "경이로운", "드디어", "탁월한", "인상적",
    "뛰어난", "강력한", "엄청난", "대단한", "극대화",
    "우수한", "새 기준", "새로운 기준", "경쟁 우위"
]

BASE_PROMPT = '''# 공통 규칙

주어진 입력 본문을 바탕으로 콘텐츠를 작성합니다. 아래 규칙은 모든 스타일 지침에 우선합니다.

## 입력 섹션
- **[자막]**, **[영상 자막]**, **[음성 전사]**, **[문서 본문]**, **[웹페이지 본문]**, **[사용자 입력 텍스트]** 등 본문 섹션: 유일한 사실 출처입니다
- **[댓글]**: 이 섹션이 있을 때만 시청자 반응을 활용하고, 없으면 시청자 반응을 절대 언급하지 않습니다
- **[타임스탬프 자막]**: 이 섹션이 있을 때만 주요 섹션 시작에 `[HH:MM:SS]` 타임코드를 표기합니다. 없으면 타임코드를 만들지 않습니다
- **[참고자료]** / **[웹 참고 자료]**: 보조 자료입니다. 본문 섹션과 충돌하면 본문이 우선합니다

## 정확성
- 입력 본문에 있는 내용만 사용합니다. 없는 사실·수치·사례를 지어내지 않습니다
- 수치와 인용은 원문 그대로 옮깁니다
- 불확실한 내용은 "~로 보입니다"처럼 단정을 피하고, 모르는 것은 생략합니다
- 스폰서십·광고·할인 코드·"구독/좋아요/알림 설정" 류 홍보 문구는 제외합니다

## 문장
- 실제 사람에게 이야기하듯 자연스럽게 쓰되, 정보 전달은 명확하게 합니다
- 다음 과장 표현은 사용 금지: 놀라운, 혁신적, 획기적, 최고의, 게임체인저, 압도적, 경이로운, 드디어, 탁월한, 인상적, 뛰어난, 강력한
- 소제목·**볼드**·목록·표를 활용해 읽기 쉽게 구성합니다

## 출력
- 첫 줄은 반드시 `## 제목` 형식의 실제 제목으로 시작합니다 (대괄호·플레이스홀더 금지)
- 스타일의 "출력 형식"을 따르되, 괄호 안내문과 대괄호 자리표시는 실제 내용으로 채웁니다
- 출력 언어가 한국어가 아니어도, 출력 형식에 명시된 시스템 라벨(표의 항목명, **Q.**/A., CTA_PRIMARY 등)은 표기된 그대로 유지합니다
- 본문 외 사족(작성 과정 설명, 체크리스트 echo)은 출력하지 않습니다

---

'''


def compose_style_prompt(style_id: str, style_prompt: str) -> str:
    """콘텐츠 스타일 프롬프트에 베이스 규칙을 결합합니다.

    변환계 프롬프트(comment_summary, mindmap, chapter_split)는 글쓰기 규칙이
    맞지 않으므로 베이스를 붙이지 않고 그대로 반환합니다.
    """
    from .styles import TRANSFORM_STYLE_IDS

    if not style_prompt or style_id in TRANSFORM_STYLE_IDS:
        return style_prompt
    return BASE_PROMPT + style_prompt


def build_prompt(style_prompt: str, modifiers: dict = None) -> str:
    """베이스 프롬프트 + 스타일 프롬프트 + 모디파이어를 조합합니다.

    Args:
        style_prompt: 스타일별 프롬프트
        modifiers: 모디파이어 딕셔너리 {'length': 'medium', 'writing_style': 'conversational'}

    Returns:
        조합된 최종 프롬프트
    """
    from .modifiers import build_modifier_text

    final_prompt = BASE_PROMPT + style_prompt

    if modifiers:
        modifier_text = build_modifier_text(modifiers)
        if modifier_text:
            final_prompt += f"\n\n# 추가 지침\n{modifier_text}"

    return final_prompt


__all__ = ['BASE_PROMPT', 'FORBIDDEN_EXPRESSIONS', 'compose_style_prompt', 'build_prompt']
