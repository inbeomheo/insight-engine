# 프롬프트 품질 평가 루브릭 (Frozen Metric)

## 평가 방법
Codex MCP (`mcp__codex__codex`)에 아래 프롬프트를 보내서 점수를 받는다.

## 공통 평가 기준 (5항목 × 20점 = 100점)

### 1. 명확성 (Clarity) — 0~20점
- 지시사항이 모호하지 않고 AI가 정확히 따를 수 있는가?
- "잘 써줘" 같은 모호한 표현 대신 구체적인 행동 지시가 있는가?
- 점수 기준: 20=완벽히 명확, 15=대체로 명확, 10=일부 모호, 5=많이 모호, 0=해석 불가

### 2. 구조 완성도 (Structure) — 0~20점
- 출력 형식(템플릿)이 잘 정의되어 있는가?
- 마크다운 계층(H2/H3/리스트)이 논리적인가?
- 섹션 간 흐름이 자연스러운가?
- 점수 기준: 20=완벽한 구조, 15=양호, 10=보통, 5=부족, 0=구조 없음

### 3. 예시 품질 (Example Quality) — 0~20점
- Few-shot 예시가 실제 좋은 출력 수준을 보여주는가?
- 예시가 형식(템플릿)을 정확히 따르는가?
- 예시가 스타일의 특성을 잘 반영하는가?
- 점수 기준: 20=완벽한 예시, 15=좋은 예시, 10=보통, 5=형식 불일치, 0=예시 없음

### 4. 제약 조건 (Constraints) — 0~20점
- 금지 표현이 명시되어 있는가?
- 댓글 활용 규칙이 있는가?
- 길이/분량 가이드라인이 구체적인가?
- 점수 기준: 20=완벽한 제약, 15=대부분 커버, 10=기본만, 5=부족, 0=제약 없음

### 5. 스타일 특화도 (Style Specificity) — 0~20점
- 해당 스타일만의 고유한 목적이 명확한가?
- 다른 스타일과 차별화되는 구체적 지침이 있는가?
- 타겟 독자/플랫폼에 맞는 톤 가이드가 있는가?
- 점수 기준: 20=완벽히 차별화, 15=양호, 10=일반적, 5=다른 스타일과 구분 어려움, 0=특화 없음

## 스타일별 추가 체크포인트

### tutorial
- Step-by-step 구조가 명확한가?
- 성공 기준/확인 방법이 각 단계에 있는가?
- 트러블슈팅 섹션이 있는가?

### qna
- Q/A 쌍이 자연스러운가?
- 기본/심화 난이도 분리가 있는가?
- 답변이 "핵심 한 줄 + 부연" 구조인가?

### app_ideas
- 신뢰도/난이도/타겟/수익모델 체계가 있는가?
- 각 아이디어가 독립적이고 실현 가능한가?
- 차별점이 구체적인가?

### shorts_script
- 60초 제한이 명확한가?
- 후킹 문구 가이드가 있는가?
- 타임스탬프/오버레이 텍스트 가이드가 있는가?

### geo_seo
- 인용 가능한 단정문 작성 지침이 있는가?
- FAQ 스키마 형식이 명확한가?
- 엔티티 태깅 가이드가 있는가?

### course
- 학습 목표→본문→퀴즈 흐름이 있는가?
- 실습 과제가 구체적인가?
- 섹션 간 연결성 가이드가 있는가?

### newsletter
- 인사말→핵심→마무리 흐름이 있는가?
- 1:1 대화 톤 가이드가 구체적인가?
- CTA/다음 호 예고가 있는가?

### show_notes
- 토픽별 구조화가 명확한가?
- 언급된 도구/인물 정리 형식이 있는가?
- 키워드 태그가 있는가?

### sns_post
- 플랫폼별 톤 차이가 반영되는가?
- 훅→핵심→CTA 구조가 있는가?
- 해시태그 가이드가 구체적인가?

## Codex 평가 프롬프트 템플릿

```
You are a prompt engineering expert. Evaluate the following AI content generation prompt on these 5 criteria. Return ONLY a JSON object with scores and brief justifications.

STYLE: {style_name}
STYLE PURPOSE: {style_description}

--- PROMPT START ---
{prompt_text}
--- PROMPT END ---

Score each criterion 0-20:
1. clarity: How unambiguous and specific are the instructions?
2. structure: How well-defined is the output template?
3. example_quality: How good are the few-shot examples?
4. constraints: How clear are the restrictions (forbidden words, length, rules)?
5. style_specificity: How well does it serve this specific style's unique purpose?

Also check style-specific criteria:
{style_checkpoints}

Return JSON:
{"clarity": N, "structure": N, "example_quality": N, "constraints": N, "style_specificity": N, "total": N, "improvements": ["suggestion1", "suggestion2", "suggestion3"]}
```
