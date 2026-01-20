"""
베이스 프롬프트 - 모든 스타일에 공통 적용되는 핵심 지침
전문성, 품질 기준, 금지사항을 통합 관리
"""

BASE_PROMPT = '''
# 역할

YouTube 영상 자막을 읽기 좋은 블로그 글로 변환해주세요.

## 입력
- **[자막]**: 영상의 음성 텍스트
- **[댓글]**: 시청자 반응 (있으면 자연스럽게 활용)

## 작성 가이드

**자연스러운 문체로 작성하세요.**
- 독자에게 말하듯 편안하게 써주세요
- 문장 길이나 문단 구성은 내용에 맞게 자유롭게
- 딱딱한 보고서가 아닌 읽고 싶은 글이 되도록

**정보는 정확하게**
- 자막에 있는 내용을 바탕으로 작성
- 수치나 인용은 원문 그대로
- 없는 내용을 지어내지 않기

**읽기 쉽게**
- 적절한 소제목으로 구분
- 중요한 부분은 **볼드** 처리
- 필요하면 목록이나 표 활용

---

'''

# 베이스 프롬프트 조합 함수
def build_prompt(style_prompt: str, modifiers: dict = None) -> str:
    """
    베이스 프롬프트 + 스타일 프롬프트 + 모디파이어를 조합합니다.

    Args:
        style_prompt: 스타일별 프롬프트 (역할 + 출력 형식)
        modifiers: 모디파이어 딕셔너리 {'length': 'medium', 'tone': 'professional', ...}

    Returns:
        조합된 최종 프롬프트
    """
    from .modifiers import MODIFIERS, build_modifier_text

    # 모디파이어 텍스트 생성
    modifier_text = ""
    if modifiers:
        modifier_text = build_modifier_text(modifiers)

    # 최종 프롬프트 조합
    final_prompt = BASE_PROMPT + style_prompt

    if modifier_text:
        final_prompt += f"\n\n# 추가 지침\n{modifier_text}"

    return final_prompt


__all__ = ['BASE_PROMPT', 'build_prompt']
