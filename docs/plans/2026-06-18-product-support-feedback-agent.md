# Product Support Feedback Agent Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Insight Engine 안에 제품 사용법 Q&A, 불편사항 접수, 개선안 분류, 코드 수정 작업 생성까지 이어지는 제품 피드백 에이전트 루프를 만든다.

**Architecture:** 기존 `FileJobStore`/`AgentPipelineJobRunner`를 재사용해 장기 실행 작업을 추적한다. 신규 `support` 도메인은 즉답형 product Q&A와 접수형 feedback ticket을 분리하고, 코드 수정은 자동 배포가 아니라 `proposed_patch` 또는 GitHub issue/PR 생성 단계까지 안전하게 제한한다.

**Tech Stack:** Flask routes, JSON file-backed job store, Next.js 16 UI, Zustand, existing ChatMock/LiteLLM providers, optional GitHub CLI integration.

---

## Product Concept

### 사용자가 기대하는 챗봇

인사이트 엔진 안의 Q&A 챗봇은 영상 내용 질문용이 아니라, 제품 자체를 대상으로 한다.

1. **기능/사용법 Q&A**
   - “OpenRouter 말고 GPT는 어떻게 켜?”
   - “통합 생성이랑 퓨전 분석 차이가 뭐야?”
   - “라이브러리에서 지난 결과는 어디 있어?”
   - “발행 예약은 왜 안 보여?”

2. **불편사항/버그 접수**
   - “모바일에서 버튼이 눌려”
   - “요약/전체/타임라인 글씨가 이상해”
   - “스타일 선택 취소가 안 돼”
   - “결과 공유 URL이 복사가 안 돼”

3. **개선 작업화**
   - 사용자 불편을 `feedback ticket`으로 저장
   - 심각도/영역/재현 정보 자동 분류
   - 필요한 경우 agent job 생성
   - 코드 수정 제안 또는 PR/패치 생성
   - 사용자가 승인하면 배포

---

## Safety Boundary

자동 코드 수정 루프는 아래 단계로 나눠야 한다.

| 단계 | 자동 가능 | 설명 |
|---|---:|---|
| 접수 | ✅ | 사용자 메시지 저장 |
| 분류 | ✅ | bug / usability / feature / question |
| 답변 | ✅ | 문서/기능 맵 기반 즉답 |
| 재현정보 요청 | ✅ | 부족한 정보 질문 |
| 코드 위치 추정 | ✅ | 관련 파일/컴포넌트 추천 |
| 패치 생성 | ✅ | 로컬 브랜치 또는 patch 제안 |
| 테스트 실행 | ✅ | lint/type/build/pytest |
| 배포 | ⚠️ 승인 필요 | 서비스 영향이 있어 사용자 승인 필요 |
| 데이터 삭제/마이그레이션 | ❌ 수동 확인 | 기존 CLAUDE.md 규칙 준수 |

---

## Data Model

### Feedback Ticket

```ts
export interface FeedbackTicket {
  id: string;
  kind: 'question' | 'bug' | 'usability' | 'feature' | 'ops';
  status: 'new' | 'answered' | 'triaged' | 'planned' | 'in_progress' | 'patched' | 'verified' | 'closed';
  severity: 'low' | 'medium' | 'high' | 'critical';
  title: string;
  message: string;
  route?: string;
  viewport?: { width: number; height: number };
  user_agent?: string;
  screenshot_url?: string;
  console_errors?: string[];
  related_files?: string[];
  suggested_fix?: string;
  job_id?: string;
  created_at: string;
  updated_at: string;
}
```

### Support Chat Message

```ts
export interface SupportChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  mode?: 'answer' | 'feedback_intake' | 'triage' | 'fix_proposal';
  ticket_id?: string;
  job_id?: string;
  created_at: string;
}
```

---

## Backend Design

### New service files

- `services/support/product_knowledge_service.py`
  - 정적 제품 기능 맵/FAQ 검색
  - 현재 feature flag/환경 상태 반영
- `services/support/feedback_store.py`
  - JSON file-backed feedback tickets
  - `./data/feedback/items/*.json`
- `services/support/feedback_triage_service.py`
  - 메시지를 question/bug/usability/feature로 분류
  - 심각도/관련 화면/추정 파일 추천
- `services/support/support_agent_service.py`
  - chat endpoint orchestration
  - 즉답 or ticket 생성 or job 생성 결정
- `services/agents/feedback_fix_runner.py`
  - 기존 `FileJobStore`를 사용해서 feedback fix job 실행
  - 단계: `triage → locate → patch_plan → implement → verify`

### New route file

- `routes/support_routes.py`

### API endpoints

```http
POST /api/support/chat
GET  /api/support/tickets
GET  /api/support/tickets/:ticket_id
POST /api/support/tickets/:ticket_id/start-fix
GET  /api/support/jobs/:job_id
POST /api/support/jobs/:job_id/approve-deploy
```

### `/api/support/chat` request

```json
{
  "message": "요약 전체 타임라인 글씨가 찌그러져 보여",
  "route": "/",
  "viewport": { "width": 1440, "height": 900 },
  "user_agent": "...",
  "console_errors": [],
  "mode": "auto"
}
```

### `/api/support/chat` response

```json
{
  "reply": "이건 결과 뷰 모드 버튼의 폰트가 signal-meta라 한글에 안 맞는 문제로 보여. 불편사항으로 접수했고 관련 파일은 frontend/components/result/ViewModeSelector.tsx야.",
  "action": "ticket_created",
  "ticket": {
    "id": "fb_...",
    "kind": "usability",
    "severity": "medium",
    "status": "triaged"
  },
  "suggested_next_actions": ["수정 작업 시작", "스크린샷 추가", "닫기"]
}
```

---

## Frontend Design

### New components

- `frontend/components/support/SupportAssistantButton.tsx`
  - 우하단 고정 버튼
  - 모바일에서는 bottom nav 위에 표시
- `frontend/components/support/SupportAssistantPanel.tsx`
  - 채팅 패널
  - 모드: `질문하기`, `불편 접수`, `수정 진행상황`
- `frontend/components/support/FeedbackTicketCard.tsx`
  - 접수된 불편사항 카드
  - 상태/심각도/job 링크 표시
- `frontend/components/support/FixJobTimeline.tsx`
  - agent job events 표시

### Placement

- 전역 앱 레벨: `frontend/app/page.tsx` 또는 layout shell에 `SupportAssistantButton`
- 대시보드 탭: “피드백” 섹션 추가 가능
- 결과 카드별이 아니라 앱 전체 기능으로 제공

---

## Task 1: Restore clear terminology

**Objective:** 기존 “Video Q&A”와 새 “Product Support Assistant”를 이름으로 명확히 분리한다.

**Files:**
- Inspect: `frontend/components/chat/VideoChatPanel.tsx`
- Inspect: `services/media/video_qa_service.py`
- Create: `docs/plans/2026-06-18-product-support-feedback-agent.md`

**Verification:**
- 영상 자막 Q&A와 제품 지원 챗봇의 API/컴포넌트 이름이 섞이지 않는다.

---

## Task 2: Add feedback store with tests

**Objective:** 불편사항을 JSON 파일로 안전하게 저장/조회한다.

**Files:**
- Create: `services/support/feedback_store.py`
- Create: `tests/test_feedback_store.py`

**Test cases:**
- ticket 생성 시 id/status/timestamps가 채워진다.
- list가 최신순으로 반환된다.
- update 시 status/updated_at이 바뀐다.

**Commands:**

```bash
python -m pytest tests/test_feedback_store.py -q
```

---

## Task 3: Add product knowledge service

**Objective:** 기능 질문에 즉답할 수 있는 최소 제품 지식 베이스를 만든다.

**Files:**
- Create: `services/support/product_knowledge_service.py`
- Create: `tests/test_product_knowledge_service.py`

**Knowledge source MVP:**
- hardcoded feature map
- current feature flags from env
- common FAQ

**Example questions:**
- “퓨전 분석이 뭐야?”
- “캘린더가 안 보여”
- “OpenRouter 말고 GPT는?”

---

## Task 4: Add triage service

**Objective:** 사용자 메시지를 question/bug/usability/feature로 분류한다.

**Files:**
- Create: `services/support/feedback_triage_service.py`
- Create: `tests/test_feedback_triage_service.py`

**Rules MVP:**
- “안 보여”, “안 됨”, “찌그러져”, “눌러도” → bug/usability
- “어떻게”, “뭐야”, “차이” → question
- “넣어줘”, “만들고싶어” → feature

---

## Task 5: Add support chat route

**Objective:** 제품 Q&A와 불편 접수를 하나의 `/api/support/chat`로 제공한다.

**Files:**
- Create: `routes/support_routes.py`
- Modify: `app.py` to register blueprint
- Create: `tests/test_support_routes.py`

**Behavior:**
- question이면 즉답
- bug/usability/feature이면 ticket 생성 + 답변
- `start_fix=true`이면 background job 생성 준비

---

## Task 6: Add support assistant UI

**Objective:** 앱 우하단에서 항상 접근 가능한 지원 챗봇을 만든다.

**Files:**
- Create: `frontend/components/support/SupportAssistantButton.tsx`
- Create: `frontend/components/support/SupportAssistantPanel.tsx`
- Modify: `frontend/lib/api.ts`
- Modify: `frontend/app/page.tsx`

**UI behavior:**
- 질문 입력
- 답변 표시
- 불편사항이면 “접수됨” 카드 표시
- “수정 작업 시작” 버튼 노출

---

## Task 7: Add feedback fix job runner

**Objective:** 접수된 ticket을 코드 수정 작업으로 넘길 수 있는 job runner를 만든다.

**Files:**
- Create: `services/agents/feedback_fix_runner.py`
- Modify: `routes/support_routes.py`
- Create: `tests/test_feedback_fix_runner.py`

**Pipeline:**
1. `triage`: ticket 정리
2. `locate`: 관련 파일 후보 찾기
3. `patch_plan`: 수정 계획 작성
4. `implement`: 패치 생성
5. `verify`: 테스트 명령 실행

**Important:**
- MVP에서는 자동 배포 금지
- `patch_summary`, `changed_files`, `test_output`만 반환

---

## Task 8: Add deployment approval gate

**Objective:** agent가 코드를 고친 뒤 사용자가 승인해야 배포되게 한다.

**Files:**
- Modify: `routes/support_routes.py`
- Modify: `frontend/components/support/FixJobTimeline.tsx`

**Rules:**
- `status=patched`까지는 자동
- `approve-deploy`는 사용자가 직접 눌러야 함
- 배포 전 `npm run lint && npx tsc --noEmit && npx next build` 필수

---

## MVP Scope Recommendation

1차 MVP는 아래까지만 한다.

- ✅ 제품 기능 Q&A
- ✅ 불편사항 접수
- ✅ 자동 분류
- ✅ ticket 저장
- ✅ 관련 화면/파일 추정
- ✅ “수정 작업 시작” job 생성
- ✅ 테스트 결과 표시
- ❌ 자동 배포는 아직 안 함

배포 자동화는 2차에서 승인 게이트 붙인 뒤 진행한다.

---

## Verification Commands

```bash
python -m pytest tests/test_feedback_store.py tests/test_product_knowledge_service.py tests/test_feedback_triage_service.py tests/test_support_routes.py -q
cd frontend && npm run lint && npx tsc --noEmit && npx next build
```

---

## Final UX Target

사용자 입장에서는 이렇게 보여야 한다.

1. 우하단 “도움말/피드백” 버튼 클릭
2. “퓨전 분석이 뭐야?” → 바로 설명
3. “모바일에서 버튼이 잘려” → 불편사항 접수
4. 챗봇: “접수했어. 모바일 레이아웃 문제로 분류했고 관련 파일은 MobileAppShell.tsx로 보여.”
5. 사용자: “GitHub 이슈 올리기” 클릭
6. 챗봇: “이슈 #123으로 올렸어. `needs-agent` 라벨을 붙였어.”
7. 별도 작업 에이전트가 issue queue에서 가져가 구현
8. 작업 에이전트가 PR을 올리고 `Fixes #123`로 연결

---

## 2026-06-18 Decision Update: GitHub Handoff, No Direct Fixing

사용자 결정: 인앱 Q&A/피드백 챗봇은 코드를 직접 고치지 않는다. 대신 GitHub Issue 또는 Draft PR을 만들어 작업을 분리하고, 별도 작업 에이전트가 그 이슈/PR을 받아 구현한다.

### Revised Loop

```txt
사용자 피드백/질문
  ↓
인앱 Support Assistant
  ↓
질문이면 즉답
불편/버그/기능요청이면 Feedback Ticket 생성
  ↓
GitHub Issue 생성 또는 Draft PR 생성
  ↓
needs-agent / support-feedback 라벨 부여
  ↓
별도 Worker Agent가 queue에서 가져감
  ↓
브랜치 생성 → 구현 → 테스트 → PR 업데이트
  ↓
Head Agent/Human Review
  ↓
승인 후 merge/deploy
```

### Why This Is Better

| 항목 | 인앱 챗봇 직접 수정 | GitHub handoff |
|---|---:|---:|
| 책임 분리 | 약함 | 강함 |
| 추적성 | 앱 내부 로그 의존 | GitHub Issue/PR 기록 |
| 리뷰 | 놓치기 쉬움 | PR 리뷰 가능 |
| 여러 에이전트 협업 | 어려움 | 쉬움 |
| 롤백/감사 | 약함 | 커밋/PR 기반 |
| 운영 안전성 | 낮음 | 높음 |

### Updated Safety Rule

Support Assistant는 아래까지만 수행한다.

- 제품 기능 질문 답변
- 불편사항/버그/기능요청 접수
- 자동 분류/심각도 판단
- 재현정보/환경/스크린샷/콘솔 에러 수집
- 관련 파일 후보 추정
- GitHub Issue 생성
- 선택적으로 Draft PR 생성
- 작업 에이전트가 읽을 수 있는 구현 지시문 작성

Support Assistant는 아래를 하지 않는다.

- 직접 코드 수정
- 직접 테스트 실행
- 직접 배포
- secrets/raw credentials를 GitHub에 업로드
- 데이터 삭제/마이그레이션 제안 자동 실행

### New API Endpoints

```http
POST /api/support/chat
GET  /api/support/tickets
GET  /api/support/tickets/:ticket_id
POST /api/support/tickets/:ticket_id/create-github-issue
POST /api/support/tickets/:ticket_id/create-draft-pr
```

### GitHub Labels

기본 라벨:

- `support-feedback`
- `needs-agent`
- `needs-triage`
- `bug`
- `usability`
- `feature-request`
- `question`
- `priority:low`
- `priority:medium`
- `priority:high`
- `priority:critical`

### Issue Body Template

```md
## 사용자 피드백
<원문 메시지>

## 자동 분류
- 유형: bug | usability | feature | question | ops
- 심각도: low | medium | high | critical
- 화면: <route>
- 환경: <viewport / user-agent>

## 재현 정보
1. <자동 수집 또는 사용자 입력>
2. <...>

## 기대 동작
<expected behavior>

## 실제 동작
<actual behavior>

## 첨부 정보
- 스크린샷: <optional>
- 콘솔 에러: <optional>
- 네트워크 에러: <optional>

## 관련 파일 후보
- `frontend/components/...`
- `routes/...`
- `services/...`

## 작업 에이전트 지시
- 이 이슈 기준으로 새 브랜치 생성
- 가능하면 실패 테스트 먼저 작성
- 최소 수정으로 구현
- `npm run lint`, `npx tsc --noEmit`, `npx next build` 또는 관련 pytest 결과를 PR 본문에 첨부
- PR 본문에 `Fixes #<issue-number>` 포함
```

### Draft PR Option

권장 기본값은 **Issue-first**다. Draft PR은 작업 범위가 이미 명확하고 에이전트가 바로 브랜치 기반으로 이어받아야 할 때만 사용한다.

Draft PR을 쓴다면 초기에는 코드 변경 없이 아래 중 하나로 제한한다.

- `docs/feedback/<ticket-id>.md` 스펙 파일 추가
- 재현 테스트 TODO 추가
- PR 본문에 구현 체크리스트 작성

### Worker Agent Contract

별도 작업 에이전트는 다음 규약을 따른다.

1. `needs-agent` + `support-feedback` 라벨 이슈를 조회한다.
2. 하나를 claim한다. 예: 댓글 `@agent claimed` 또는 라벨 `agent:in-progress` 추가.
3. `gh issue develop <number> --checkout` 또는 `fix/support-<number>-slug` 브랜치 생성.
4. 테스트 먼저 추가.
5. 구현.
6. 검증 명령 실행.
7. PR 생성 또는 기존 draft PR 업데이트.
8. 이슈에 PR 링크 댓글 작성.
9. 라벨을 `agent:review-needed`로 변경.

### MVP Change

기존 MVP의 “수정 작업 시작 job 생성”은 제거하고, 아래로 대체한다.

- ✅ 제품 기능 Q&A
- ✅ 불편사항 접수
- ✅ 자동 분류
- ✅ ticket 저장
- ✅ GitHub Issue 생성
- ✅ 별도 작업 에이전트용 라벨/본문 생성
- ✅ 필요 시 Draft PR 생성
- ❌ 인앱 챗봇 직접 코드 수정 없음
- ❌ 자동 배포 없음
