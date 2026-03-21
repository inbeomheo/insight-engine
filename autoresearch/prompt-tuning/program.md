# Prompt Tuning Autoresearch — Program

## 목표
9개 스타일 프롬프트 + 1개 파라미터 최적화 = 10팀 병렬 자가개선

## 팀 구성

| 팀 | 타겟 파일 | 스타일 |
|----|----------|--------|
| 1 | `prompts/styles/tutorial.py` | 튜토리얼 |
| 2 | `prompts/styles/qna.py` | Q&A |
| 3 | `prompts/styles/app_ideas.py` | 앱 아이디어 |
| 4 | `prompts/styles/shorts_script.py` | Shorts 클립 |
| 5 | `prompts/styles/geo_seo.py` | GEO (AI검색) |
| 6 | `prompts/styles/course.py` | AI 코스 |
| 7 | `prompts/styles/newsletter.py` | 뉴스레터 |
| 8 | `prompts/styles/show_notes.py` | 쇼노트 |
| 9 | `prompts/styles/sns_post.py` | SNS 포스트 |
| 10 | `config.py` (STYLE_TEMPERATURE) | 파라미터 최적화 |

## 루프 구조 (per team)

```
for round in 1..100:
    1. 현재 프롬프트 읽기
    2. Codex MCP로 현재 점수 측정 (baseline or previous best)
    3. 개선안 도출 (Codex의 improvements 제안 활용)
    4. 프롬프트 수정 적용
    5. Codex MCP로 수정 후 점수 측정
    6. 점수 비교:
       - 올랐으면 → keep (git commit)
       - 내렸으면 → revert (git checkout)
    7. 점수 로그 기록
```

## 평가 메트릭 (Frozen Metric)
- `eval_rubric.md` 참조
- 5항목 × 20점 = 100점 만점
- Codex MCP (`mcp__codex__codex`)로 채점

## 수렴 조건
- 10연속 revert → 수렴 판정, 조기 종료
- 또는 100라운드 완료

## 제약 조건
- 프롬프트 파일의 Python 변수 구조 유지 (PROMPT = '''...''')
- base.py는 수정 금지 (공통 프롬프트)
- 금지 표현 목록 유지 필수
- 댓글 규칙 유지 필수
- 한국어 프롬프트 유지
