# Product Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Insight Engine을 “간단한 학습 입력 + ChatMock(OpenAI 호환) 기반 생성 + LLMWiki형 지식 위키” 중심으로 단순화한다.

**Architecture:** 1차는 제품 표면(UI/설정/API 노출)을 줄이고, 2차는 죽은 백엔드 엔드포인트와 서비스 체인을 제거한다. 데이터 삭제·DB 마이그레이션은 하지 않는다.

**Tech Stack:** Flask, Next.js App Router, TypeScript, Zustand, pytest, tsc.

---

## 결정 사항

- 스타일은 4개만 노출: `summary`, `qna`, `quiz`, `retention_cards`.
- 기본 스타일은 `summary`.
- AI 프로바이더는 ChatMock(OpenAI 호환)만 노출한다.
- 내보내기는 HTML과 Markdown만 노출한다.
- QA/품질 검증 UI와 호출부는 제품 표면에서 제거한다.
- 데드 엔드포인트 정리는 코드 삭제만 수행한다. 데이터 삭제/마이그레이션은 금지한다.
- 지식/RAG는 LLMWiki형 화면(노트 목록, 상세, 관련 노트, 근거 채팅)을 중심으로 강화한다.

## 파일 구조

- Modify: `E:/자동화 프로젝트/insight-engine/config.py` — 프로바이더/스타일 기본 노출 축소.
- Modify: `E:/자동화 프로젝트/insight-engine/frontend/lib/constants.ts` — 스타일 UI 목록 축소.
- Modify: `E:/자동화 프로젝트/insight-engine/frontend/stores/settingsStore.ts` — 기본 스타일 변경.
- Modify: `E:/자동화 프로젝트/insight-engine/frontend/app/page.tsx` — 스타일 토글 기본값 문구 변경.
- Modify: `E:/자동화 프로젝트/insight-engine/frontend/components/mobile/MobileAppShell.tsx` — 모바일 기본값 문구 변경.
- Modify: `E:/자동화 프로젝트/insight-engine/frontend/components/result/ResultCard.tsx` — DOCX/TXT/ZIP/PDF/QA 표면 제거, HTML/MD만 유지.
- Modify: `E:/자동화 프로젝트/insight-engine/frontend/lib/api.ts` — 미노출 export wrapper 정리.
- Modify: `E:/자동화 프로젝트/insight-engine/plans/loop-board.md` — [사람] 게이트 해제 및 신규 백로그 정리.

## Task 1: 제품 표면 단순화

- [ ] `frontend/lib/constants.ts`의 `STYLE_OPTIONS`를 4개로 축소한다.

```ts
export const STYLE_OPTIONS: StyleOption[] = [
  { id: 'summary', label: '요약', emoji: '⚡', description: '핵심만 빠르게 정리' },
  { id: 'qna', label: 'Q&A', emoji: '❓', description: '질문과 답변 정리' },
  { id: 'quiz', label: '퀴즈', emoji: '🧠', description: '객관식 학습 문제' },
  { id: 'retention_cards', label: '리텐션 카드', emoji: '🧩', description: '반복 학습 카드' },
];
```

- [ ] `frontend/stores/settingsStore.ts` 기본 스타일을 `summary`로 바꾼다.

```ts
selectedStyle: 'summary',
```

- [ ] `frontend/app/page.tsx`와 `frontend/components/mobile/MobileAppShell.tsx`의 `blog_seo` 기본 토글을 `summary`로 바꾼다.

```ts
setSelectedStyle(selectedStyle === styleId && styleId !== 'summary' ? 'summary' : styleId);
```

- [ ] `frontend/components/result/ResultCard.tsx`에서 내보내기 메뉴를 HTML/Markdown만 남긴다.

```tsx
<DropdownMenuItem onClick={handleExportHtml}>HTML (.html)</DropdownMenuItem>
<DropdownMenuItem onClick={() => handleExportFormat('markdown')}>마크다운 (.md)</DropdownMenuItem>
```

- [ ] 검증한다.

```powershell
cd frontend; npx.cmd tsc --noEmit
```

Expected: exit code 0.

## Task 2: ChatMock 단일 프로바이더

- [ ] `config.py`의 `SUPPORTED_PROVIDERS`를 ChatMock만 남긴다.

```py
SUPPORTED_PROVIDERS = {
    'chatmock': {
        'name': 'ChatMock (OpenAI 호환)',
        'api_base': os.getenv('CHATMOCK_BASE_URL', 'http://127.0.0.1:8000/v1'),
        'models': [
            {'id': 'chatmock/gpt-5.4-mini', 'name': 'GPT-5.4 Mini', 'max_input_tokens': 128000, 'price_input': 0, 'price_output': 0},
            {'id': 'chatmock/gpt-5.4', 'name': 'GPT-5.4', 'max_input_tokens': 128000, 'price_input': 0, 'price_output': 0},
        ],
    },
}
```

- [ ] `get_provider_from_model()` 기본값을 `openai`로 바꾼다.

```py
return 'chatmock'
```

- [ ] 검증한다.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_utility_routes.py -q -p no:cacheprovider
```

Expected: pass.

## Task 3: 데드 엔드포인트 코드 삭제

- [ ] `routes/export_routes.py`에서 HTML/Markdown 외 라우트 소비자를 grep으로 재검증한다.

```powershell
rg --line-number "/api/export/(docx|txt|zip|epub|slides|srt|infographic|card-news|summary-card|code-image|newsletter-html|interactive-report)" frontend routes tests
```

- [ ] 프론트 소비 0인 라우트와 전용 테스트만 제거한다.
- [ ] `routes/advanced/qa.py` `/api/qa-check` 소비 0 확인 후 라우트와 `QaGateBadge` 연결을 제거한다.
- [ ] 전체 검증한다.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/ -q --tb=no -p no:cacheprovider
cd frontend; npx.cmd tsc --noEmit
```

Expected: pass.

## Task 4: LLMWiki형 지식 화면 강화

- [ ] `frontend/app/notes/page.tsx`를 지식 위키 홈처럼 보이게 정리한다.
- [ ] `frontend/app/notes/[id]/page.tsx`에 관련 노트와 근거 채팅 진입을 더 선명하게 표시한다.
- [ ] 테스트를 추가하거나 기존 타입 검증을 통과시킨다.

## Self-review

- 요구사항 매핑: 스타일 축소(Task 1), OpenAI 단일화(Task 2), 품질/검증 제거(Task 1/3), MD/HTML 내보내기(Task 1/3), 데드 엔드포인트(Task 3), 학습/위키 강화(Task 4).
- 데이터 삭제/마이그레이션 없음.
- ChatMock base URL은 `CHATMOCK_BASE_URL` 환경변수로만 바꾸며, secret은 하드코딩하지 않는다.
