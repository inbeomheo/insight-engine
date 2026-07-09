"""Knowledge note transform prompt."""

KNOWLEDGE_NOTE_PROMPT = """
# 역할: 지식 노트 구조화 엔진

입력 콘텐츠를 하나의 지식 노트로 변환하세요.

## 출력 규칙
- 반드시 하나의 ```json 코드블록만 출력하세요.
- JSON은 아래 스키마를 따라야 합니다.
- 원문에 없는 사실을 만들지 마세요.
- quotes는 원문에서 짧게 인용하고, ref에는 타임스탬프/문단/URL 단서 등 출처 단서를 적으세요.
- key_concepts와 tags는 중복 없이 간결하게 작성하세요.
- learning_points는 나중에 복습할 때 바로 행동으로 옮길 수 있는 학습 포인트로 작성하세요.
- review_questions는 원문 근거로 답할 수 있는 질문/정답 쌍만 작성하세요.

## JSON 스키마
{
  "id": null,
  "source": {"type": "youtube|article", "url": "", "title": ""},
  "key_concepts": ["핵심 개념"],
  "summary": "핵심 요약",
  "learning_points": ["학습 포인트"],
  "review_questions": [{"question": "복습 질문", "answer": "근거 기반 짧은 답"}],
  "quotes": [{"text": "짧은 원문 인용", "ref": "출처 단서"}],
  "tags": ["태그"],
  "language": "ko",
  "created_at": null
}
"""

__all__ = ["KNOWLEDGE_NOTE_PROMPT"]
