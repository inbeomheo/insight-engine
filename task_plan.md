# Task Plan: Insight Engine — TOP 20 기능 구현 로드맵

## Goal

Feature Scout TOP 20 기능을 6개 Phase로 나누어 순차 구현한다.
각 Phase는 독립 배포 가능하며, 이전 Phase의 인프라를 활용한다.

## 메타데이터

- 총 기능: 20개 (Feature Scout 46개 → 임팩트/난이도 기준 선별)
- 총 Phase: 6개 (Quick Wins → Core → Operations → Strategic → Infra → QA)
- 신규 백엔드 파일: 6개, 신규 프론트엔드 컴포넌트: ~18개
- 기존 파일 수정: routes 4개, services 5개, config 1개, hooks ~5개
- 총 변경 규모 추정: 백엔드 ~2,500줄, 프론트엔드 ~3,500줄

## Current Phase

Phase 6

---

## Phase 1: Quick Wins — 설정/프리셋 확장 (난이도 하, 5개)

기존 config.py + 프론트엔드 UI 위에 최소 변경으로 즉시 효과를 내는 기능들.

### F01. 요약 상세도 프리셋 + 토큰 예산 제어

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F01-A | `DETAIL_PRESETS` 딕셔너리 추가 (`brief`/`standard`/`deep` → temperature, max_tokens, prompt_suffix) | `config.py` | 없음 | config import 정상 |
| F01-B | `create_content()`에 `detail_level` 파라미터 수용 + DETAIL_PRESETS 적용 | `services/ai_service.py` | F01-A | 단위 테스트 통과 |
| F01-C | `/generate` 요청 body에 `detail_level` 필드 수용 + 전달 | `routes/blog_routes.py` | F01-B | curl 테스트 |
| F01-D | 상세도 3단 토글 UI (SegmentedControl) | `frontend/components/input/DetailPreset.tsx` (신규) | 없음 | 빌드 성공 |
| F01-E | `useGenerate` 훅에 `detail_level` 포함 | `frontend/hooks/useGenerate.ts` | F01-D | API 요청 확인 |
| F01-F | 통합 테스트: `detail_level=brief` 시 토큰 < 2000, `deep` 시 > 6000 | `tests/test_detail_presets.py` (신규) | F01-A~C | pytest 통과 |

### F02. 톤 프리셋 + 길이 프리셋 결합 UX

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F02-A | 모디파이어 프리셋 카드 컴포넌트 (자주 쓰는 조합 표시) | `frontend/components/input/ModifierPresets.tsx` (신규) | 없음 | 빌드 성공 |
| F02-B | 프리셋 저장/로드 (localStorage → Supabase 선택) | `frontend/hooks/useModifierPresets.ts` (신규) | F02-A | 저장/로드 동작 |
| F02-C | 기존 모디파이어 선택 영역에 프리셋 카드 통합 | `frontend/app/page.tsx` 또는 입력 영역 | F02-A | UI 렌더링 |

### F03. 스니펫 라이브러리 (인트로/CTA/해시태그)

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F03-A | Supabase `ie_snippets` 테이블 스키마 작성 | `supabase/migrations/` (신규) | 없음 | SQL 실행 성공 |
| F03-B | 스니펫 CRUD API (`POST/GET/DELETE /api/user/snippets`) | `routes/auth_routes.py` | F03-A | curl 테스트 |
| F03-C | `supabase_service.py`에 snippets 쿼리 함수 추가 | `services/supabase_service.py` | F03-A | 단위 테스트 |
| F03-D | 스니펫 관리 UI (추가/편집/삭제/카테고리 필터) | `frontend/components/settings/SnippetLibrary.tsx` (신규) | 없음 | 빌드 성공 |
| F03-E | `useSnippets` 훅 (CRUD + localStorage 폴백) | `frontend/hooks/useSnippets.ts` (신규) | F03-D | 동작 확인 |
| F03-F | 결과 카드 더보기 메뉴에 "스니펫 삽입" 옵션 | `frontend/components/result/ResultCard.tsx` | F03-D,E | 삽입 동작 |

### F04. Summary/Transcript 듀얼 모드 토글

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F04-A | `/generate` 응답에 `transcript_segments` 필드 추가 (`include_transcript=true` 시) | `routes/blog_routes.py` | 없음 | API 응답에 segments 포함 |
| F04-B | `content_service.py`에서 자막 세그먼트를 구조화 반환 | `services/content_service.py` | 없음 | 타임스탬프 + 텍스트 배열 |
| F04-C | 자막 패널 UI (타임스탬프 + 텍스트 리스트) | `frontend/components/result/TranscriptPanel.tsx` (신규) | 없음 | 빌드 성공 |
| F04-D | ResultCard에 요약↔자막 토글 버튼 추가 | `frontend/components/result/ResultCard.tsx` | F04-C | 토글 동작 |

### F05. 요약 API 품질 파라미터 표준화

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F05-A | `/generate`에 `output_format` (html/markdown/plain), `max_chars` 파라미터 추가 | `routes/blog_routes.py` | 없음 | 파라미터 수용 확인 |
| F05-B | `output_format=plain` 시 마크다운 제거 로직 | `routes/generation_helpers.py` | F05-A | plain 응답에 # 등 없음 |
| F05-C | `GET /api/schema` — API 파라미터 OpenAPI 스키마 반환 | `routes/utility_routes.py` | 없음 | JSON 스키마 반환 |
| F05-D | 테스트: 각 output_format 동작 확인 | `tests/test_api_params.py` (신규) | F05-A,B | pytest 통과 |

- **Phase 1 Status:** complete
- **완료 신규 파일**: DetailPreset.tsx, ModifierPresets.tsx, useModifierPresets.ts, TranscriptPanel.tsx, SnippetLibrary.tsx, useSnippets.ts, 003_snippets.sql
- **완료 수정 파일**: config.py, ai_service.py, blog_routes.py, auth_routes.py, generation_helpers.py, utility_routes.py, supabase_service.py, useGenerate.ts, settingsStore.ts, types.ts, ResultCard.tsx

---

## Phase 2: Core Differentiation — 핵심 차별화 (난이도 중, 5개)

### F06. 챕터 자동 분할 + 타임라인 네비게이션

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F06-A | 챕터 분할 전용 프롬프트 작성 (title, start, end, summary) | `prompts/styles/chapter_split.py` (신규) | 없음 | 프롬프트 구조 확인 |
| F06-B | `chapter_service.py` — AI로 자막 → 챕터 분할 | `services/chapter_service.py` (신규) | F06-A | 단위 테스트 |
| F06-C | `/generate` 응답에 `chapters[]` 필드 추가 | `routes/blog_routes.py` | F06-B | API 응답 확인 |
| F06-D | 가로 타임라인 바 + 챕터 카드 UI | `frontend/components/result/ChapterTimeline.tsx` (신규) | 없음 | 빌드 성공 |
| F06-E | 챕터 클릭 → YouTube 해당 시간 이동 연동 | F06-D 내 | F06-D | 클릭 동작 |
| F06-F | 테스트: 30분+ 영상 → 5~8개 챕터 분할 | `tests/test_chapter.py` (신규) | F06-B | pytest 통과 |

### F07. 플랫폼별 카피 리라이트

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F07-A | `PLATFORM_PRESETS` 정의 (twitter:280자, linkedin:3000자, instagram:2200자, threads:500자) | `config.py` | 없음 | config 로드 |
| F07-B | `rewrite_service.py` — 플랫폼별 톤/길이/포맷 변환 (AI 호출) | `services/rewrite_service.py` (신규) | F07-A | 단위 테스트 |
| F07-C | `POST /api/rewrite` 엔드포인트 | `routes/advanced_routes.py` | F07-B | curl 테스트 |
| F07-D | 결과 카드 더보기 → "플랫폼 변환" 서브메뉴 | `frontend/components/result/ResultCard.tsx` | 없음 | UI 표시 |
| F07-E | 플랫폼 선택 → 미리보기 → 복사 모달 | `frontend/components/result/PlatformRewriteModal.tsx` (신규) | F07-D | 변환 결과 표시 |
| F07-F | 테스트: blog_seo → Twitter 280자 이내 + 해시태그 | `tests/test_rewrite.py` (신규) | F07-B,C | pytest 통과 |

### F08. 채널 신규 업로드 감지 → 자동 트리거

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F08-A | `ie_channel_monitors` 테이블 스키마 (channel_id, style_id, modifiers, interval_minutes, last_checked) | `supabase/migrations/` (신규) | 없음 | SQL 실행 |
| F08-B | `channel_monitor_service.py` — YouTube API 채널 최신 영상 폴링 | `services/channel_monitor_service.py` (신규) | 없음 | 단위 테스트 |
| F08-C | APScheduler에 채널 모니터링 잡 등록 | `services/scheduler_worker.py` | F08-B | 스케줄러 로그 확인 |
| F08-D | `POST/GET/DELETE /api/channel-monitors` CRUD | `routes/integration_routes.py` | F08-B | curl 테스트 |
| F08-E | 채널 등록/상태 확인 UI | `frontend/components/settings/ChannelMonitorSettings.tsx` (신규) | 없음 | 빌드 성공 |
| F08-F | 테스트: 채널 등록 → 폴링 → 신규 감지 시뮬레이션 | `tests/test_channel_monitor.py` (신규) | F08-B,C | pytest 통과 |

### F09. AI 에디터 코파일럿 (인라인 명령)

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F09-A | `ai_service.py`에 `inline_edit()` 메서드 추가 (선택 영역 + 지시 → 부분 재생성) | `services/ai_service.py` | 없음 | 단위 테스트 |
| F09-B | `POST /api/inline-edit` — `{content, selection, instruction, context}` | `routes/advanced_routes.py` | F09-A | curl 테스트 |
| F09-C | 텍스트 선택 → 플로팅 툴바 (축약/확장/톤변경/번역) | `frontend/components/result/InlineEditor.tsx` (신규) | 없음 | 빌드 성공 |
| F09-D | 선택 영역만 교체 후 결과 업데이트 연동 | F09-C + ResultCard | F09-C | 부분 교체 동작 |

### F10. 발행 전 QA 게이트

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F10-A | `QA_FORBIDDEN_WORDS`, `QA_MIN_SECTIONS` 설정 추가 | `config.py` | 없음 | config 로드 |
| F10-B | `qa_gate_service.py` — 규칙 기반(금칙어/구조) + AI 기반(팩트 체크) 검증 | `services/qa_gate_service.py` (신규) | F10-A | 단위 테스트 |
| F10-C | `POST /api/qa-check` — `{content, rules}` → `{passed, issues[]}` | `routes/advanced_routes.py` | F10-B | curl 테스트 |
| F10-D | 결과 카드에 QA 통과/미통과 뱃지 | `frontend/components/result/QaGateBadge.tsx` (신규) | 없음 | 빌드 성공 |
| F10-E | 금칙어/규칙 편집 UI | `frontend/components/settings/QaRulesEditor.tsx` (신규) | 없음 | 빌드 성공 |
| F10-F | 테스트: 금칙어 포함 → 미통과 + 이슈 목록 | `tests/test_qa_gate.py` (신규) | F10-B,C | pytest 통과 |

- **Phase 2 Status:** complete
- **완료 서비스**: chapter_service.py, rewrite_service.py, channel_monitor_service.py, qa_gate_service.py
- **완료 프론트엔드**: ChapterTimeline.tsx, PlatformRewriteModal.tsx, ChannelMonitorSettings.tsx, InlineEditor.tsx, QaGateBadge.tsx, QaRulesEditor.tsx

---

## Phase 3: Operations — 운영 도구 (난이도 중, 2개)

### F11. 콘텐츠 운영 대시보드

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F11-A | `GET /api/admin/dashboard` — 집계 데이터 (일별 생성, 스타일 분포, 성공/실패율, 평균 시간) | `routes/auth_routes.py` | 없음 | JSON 응답 구조 |
| F11-B | 기존 `ie_histories`, `ie_usage` + 스케줄/모니터 데이터 집계 쿼리 | `services/supabase_service.py` | 없음 | 쿼리 정상 |
| F11-C | 운영 대시보드 메인 페이지 (차트 + 요약 카드) | `frontend/components/dashboard/OperationsDashboard.tsx` (신규) | 없음 | 빌드 성공 |
| F11-D | 서브 컴포넌트: 큐 상태, 실패 로그, 프로바이더 헬스 | `frontend/components/dashboard/QueueStatus.tsx`, `FailureLog.tsx`, `ProviderHealth.tsx` (각 신규) | F11-C | 빌드 성공 |
| F11-E | 사이드바에 "운영" 메뉴 추가 | `frontend/components/layout/Sidebar.tsx` | F11-C | 메뉴 표시 |

### F12. 결과물 패키지 일괄 출력 (MD/TXT/ZIP)

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F12-A | `export_service.py`에 `export_markdown()`, `export_txt()` 추가 | `services/export_service.py` | 없음 | 단위 테스트 |
| F12-B | `export_zip()` — DOCX+MD+TXT+meta.json 묶음 | `services/export_service.py` | F12-A | ZIP 파일 생성 |
| F12-C | `POST /api/export/markdown`, `/api/export/txt`, `/api/export/zip` | `routes/export_routes.py` | F12-A,B | curl 다운로드 |
| F12-D | 결과 카드 내보내기 서브메뉴에 포맷 옵션 추가 | `frontend/components/result/ResultCard.tsx` | 없음 | UI 표시 |
| F12-E | `useExport` 훅 확장 (MD/TXT/ZIP) | `frontend/hooks/useExport.ts` | F12-D | 다운로드 동작 |
| F12-F | 테스트: ZIP → 4개 파일 존재 + 각 포맷 정합성 | `tests/test_export_formats.py` (신규) | F12-A~C | pytest 통과 |

- **Phase 3 Status:** complete
- **완료 서비스**: export_service.py (export_markdown, export_txt, export_zip)
- **완료 라우트**: auth_routes.py (/api/admin/dashboard), export_routes.py (3 endpoints)
- **완료 프론트엔드**: OperationsDashboard.tsx, ResultCard.tsx (export menu)

---

## Phase 4: Strategic Expansion — 전략적 확장 (난이도 중, 4개)

### F13. 트랜스크립트 워크스페이스

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F13-A | `transcript_workspace_service.py` — 자막 파싱 → 문장 단위 분리 + 타임스탬프 매핑 | `services/transcript_workspace_service.py` (신규) | 없음 | 단위 테스트 |
| F13-B | `GET /api/transcript/{video_id}` — 구조화 자막 데이터 반환 | `routes/blog_routes.py` | F13-A | API 응답 |
| F13-C | 문장 리스트 + 검색/하이라이트/편집 UI | `frontend/components/workspace/TranscriptEditor.tsx` (신규) | 없음 | 빌드 성공 |
| F13-D | 수정된 자막으로 재생성 연동 | F13-C + useGenerate | F13-C | 재생성 동작 |

### F14. 워크스페이스 승인 플로우

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F14-A | 콘텐츠 상태 머신 (draft→review→approved→published) | `services/workspace_service.py` | 없음 | 상태 전이 로직 |
| F14-B | `ie_workspace_contents` 테이블 (content_id, status, reviewer_id) | `supabase/migrations/` (신규) | 없음 | SQL 실행 |
| F14-C | 상태 전이 API (`/approve`, `/reject`, `/submit-review`) | `routes/auth_routes.py` | F14-A,B | curl 테스트 |
| F14-D | 승인 플로우 UI (상태별 필터 + 승인/반려 버튼 + 뱃지) | `frontend/components/workspace/ApprovalFlow.tsx` (신규) | 없음 | 빌드 성공 |

### F15. 자막 소스 품질 메타 노출 + 사용자 선택

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F15-A | `get_transcript()` 반환에 `source_meta` 추가 (source_type, quality_score, is_auto) | `services/content_service.py` | 없음 | 메타 데이터 포함 |
| F15-B | `/generate` 응답에 `transcript_source` 필드 노출 | `routes/blog_routes.py` | F15-A | API 응답 |
| F15-C | 소스 품질 뱃지 UI (수동/자동/Whisper) | `frontend/components/result/TranscriptSourceBadge.tsx` (신규) | 없음 | 빌드 성공 |
| F15-D | 설정에서 자막 소스 우선순위 드래그 정렬 | `frontend/components/settings/` 영역 | 없음 | 정렬 저장 |

### F16. Compact/Full/Timeline 3단 뷰

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F16-A | 3단 뷰 모드 전환 셀렉터 | `frontend/components/result/ViewModeSelector.tsx` (신규) | 없음 | 빌드 성공 |
| F16-B | Compact 뷰: 제목 + 100자 미리보기 + 메타 칩 | `frontend/components/result/ResultCard.tsx` 수정 | F16-A | 렌더링 |
| F16-C | Timeline 뷰: F06 챕터 연동 세로 스크롤 | F16-A + ChapterTimeline | F06, F16-A | 렌더링 |
| F16-D | 뷰 모드 localStorage 저장/복원 | F16-A 내 | F16-A | 새로고침 후 유지 |

- **Phase 4 Status:** complete
- **완료 서비스**: transcript_workspace_service.py, workspace_service.py (ContentApprovalService)
- **완료 프론트엔드**: TranscriptEditor.tsx, ApprovalFlow.tsx, TranscriptSourceBadge.tsx, TranscriptSourcePriority.tsx, ViewModeSelector.tsx
- **완료 수정**: content_service.py (source_meta), blog_routes.py (transcript API), auth_routes.py (approval API), ResultCard.tsx (3-view), types.ts

---

## Phase 5: Infrastructure — 인프라 강화 (난이도 중~상, 4개)

### F17. 발행 워크플로우 강화 (큐/재시도 정책)

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F17-A | `publish_queue_service.py` — 발행 큐 (queued→publishing→success/failed→retry) | `services/publish_queue_service.py` (신규) | 없음 | 단위 테스트 |
| F17-B | 재시도 정책: 최대 3회, 지수 백오프 (1m/5m/30m) | F17-A 내 | F17-A | 재시도 로직 |
| F17-C | 스케줄러에 큐 소비자 잡 등록 | `services/scheduler_worker.py` | F17-A | 큐 처리 로그 |
| F17-D | `GET /api/publish-queue` 큐 상태 조회 | `routes/integration_routes.py` | F17-A | API 응답 |
| F17-E | 큐 목록 + 재시도/취소 UI | `frontend/components/dashboard/PublishQueue.tsx` (신규) | F11-C | 빌드 성공 |

### F18. 플러그인형 LLM 제공자 설정 UX

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F18-A | `POST /api/providers/validate` — API 키 유효성 테스트 (소량 토큰 호출) | `routes/utility_routes.py` | 없음 | 검증 결과 반환 |
| F18-B | 사용자별 fallback 체인 커스텀 (Supabase `ie_api_keys` 확장) | `services/supabase_service.py` | 없음 | fallback 저장/로드 |
| F18-C | 프로바이더 설정 UI 리디자인 (키 입력→검증→상태) | `frontend/components/settings/ProviderSetup.tsx` (신규 또는 리디자인) | 없음 | 빌드 성공 |
| F18-D | Fallback 우선순위 드래그 정렬 + 상태 인디케이터 | F18-C 내 | F18-C | 정렬 저장 |

### F19. 소스 신뢰도/근거 링크 포함 요약 모드

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F19-A | 인용 프롬프트: "모든 주장에 [MM:SS] 타임스탬프 인용" | `prompts/styles/cited_summary.py` (신규) | 없음 | 프롬프트 확인 |
| F19-B | `citation_service.py` — 생성 결과에서 인용 마커 파싱 + 검증 | `services/citation_service.py` (신규) | F19-A | 단위 테스트 |
| F19-C | `/generate`에 `enable_citations=true` 옵션 | `routes/blog_routes.py` | F19-B | API 응답에 인용 포함 |
| F19-D | 인용 마커 클릭 → YouTube 시간 이동 | `frontend/components/result/CitationLink.tsx` (신규) | F06 | 클릭 동작 |

### F20. 캠페인 팩 원클릭 생성

| ID | 태스크 | 파일 | 의존성 | 검증 기준 |
|----|--------|------|--------|----------|
| F20-A | `CAMPAIGN_PACKS` 정의 (예: "full": [blog_seo, newsletter, shorts_script, sns_post]) | `config.py` | 없음 | config 로드 |
| F20-B | `POST /api/generate-campaign` — 또는 `/api/generate-multi`에 `mode=campaign` 추가 | `routes/advanced_routes.py` | F20-A | 4종 동시 생성 |
| F20-C | 사용량 1회만 차감 로직 | `routes/advanced_routes.py` + `services/usage/` | F20-B | 차감 횟수 확인 |
| F20-D | 캠페인 팩 선택 UI | `frontend/components/input/CampaignPackSelector.tsx` (신규) | 없음 | 빌드 성공 |
| F20-E | 결과: 4개 카드를 탭 그룹 표시 + ZIP 다운로드 (F12 연동) | ResultCard 영역 | F12, F20-D | 탭 전환 동작 |

- **Phase 5 Status:** complete
- **완료 서비스**: publish_queue_service.py, citation_service.py
- **완료 프론트엔드**: PublishQueue.tsx, ProviderSetup.tsx, CampaignPackSelector.tsx, CitationLink.tsx
- **완료 수정**: scheduler_worker.py (큐 소비자), integration_routes.py (큐 API), utility_routes.py (validate), advanced_routes.py (campaign), config.py (CAMPAIGN_PACKS), blog_routes.py (citations), prompts/styles/ (cited_summary)

---

## Phase 6: Testing & Polish — 통합 QA

| ID | 태스크 | 검증 기준 |
|----|--------|----------|
| P6-A | 20개 기능 단위 테스트 전체 실행 | pytest 전체 통과 |
| P6-B | E2E 시나리오: 상세도 선택 → 생성 → 챕터 → 리라이트 → QA → 발행 | Playwright 통과 |
| P6-C | 성능: 캠페인 팩 4종 동시 생성 ≤ 60초 | 시간 측정 |
| P6-D | 다크모드/모바일 호환성 확인 | UI 검수 |
| P6-E | CLAUDE.md 업데이트 (신규 API, 컴포넌트, 패턴 반영) | 파일 갱신 |

- **Phase 6 Status:** complete
- **P6-A**: pytest 752 passed, 0 failed
- **P6-E**: CLAUDE.md 신규 API/서비스/컴포넌트/스타일 반영 완료

---

## Feature × File 종합 매핑

### 신규 백엔드 파일 (6개)

| 파일 | Feature | 역할 |
|------|---------|------|
| `services/chapter_service.py` | F06 | AI 자막 → 챕터 분할 |
| `services/rewrite_service.py` | F07 | 플랫폼별 카피 변환 |
| `services/channel_monitor_service.py` | F08 | 채널 신규 업로드 감지 |
| `services/qa_gate_service.py` | F10 | 발행 전 QA 검증 |
| `services/publish_queue_service.py` | F17 | 발행 큐/재시도 |
| `services/citation_service.py` | F19 | 인용 마커 파싱 |

### 신규 프론트엔드 파일 (~18개)

| 파일 | Feature |
|------|---------|
| `components/input/DetailPreset.tsx` | F01 |
| `components/input/ModifierPresets.tsx` | F02 |
| `hooks/useModifierPresets.ts` | F02 |
| `components/settings/SnippetLibrary.tsx` | F03 |
| `hooks/useSnippets.ts` | F03 |
| `components/result/TranscriptPanel.tsx` | F04 |
| `components/result/ChapterTimeline.tsx` | F06 |
| `components/result/PlatformRewriteModal.tsx` | F07 |
| `components/settings/ChannelMonitorSettings.tsx` | F08 |
| `components/result/InlineEditor.tsx` | F09 |
| `components/result/QaGateBadge.tsx` | F10 |
| `components/settings/QaRulesEditor.tsx` | F10 |
| `components/dashboard/OperationsDashboard.tsx` | F11 |
| `components/dashboard/QueueStatus.tsx` | F11 |
| `components/workspace/TranscriptEditor.tsx` | F13 |
| `components/workspace/ApprovalFlow.tsx` | F14 |
| `components/result/TranscriptSourceBadge.tsx` | F15 |
| `components/result/ViewModeSelector.tsx` | F16 |
| `components/result/CitationLink.tsx` | F19 |
| `components/input/CampaignPackSelector.tsx` | F20 |

### 수정 대상 기존 파일

| 파일 | Features |
|------|----------|
| `config.py` | F01, F07, F10, F20 |
| `services/ai_service.py` | F01, F09 |
| `services/content_service.py` | F04, F15 |
| `services/export_service.py` | F12 |
| `services/workspace_service.py` | F14 |
| `services/supabase_service.py` | F03, F11, F18 |
| `services/scheduler_worker.py` | F08, F17 |
| `routes/blog_routes.py` | F01, F04, F05, F06, F13, F15, F19 |
| `routes/advanced_routes.py` | F07, F09, F10, F20 |
| `routes/auth_routes.py` | F03, F11, F14 |
| `routes/utility_routes.py` | F05, F18 |
| `routes/export_routes.py` | F12 |
| `routes/integration_routes.py` | F08, F17 |
| `frontend/hooks/useGenerate.ts` | F01 |
| `frontend/hooks/useExport.ts` | F12 |
| `frontend/components/result/ResultCard.tsx` | F03, F04, F07, F12, F16 |
| `frontend/components/layout/Sidebar.tsx` | F11 |

---

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Phase 1을 config 확장 중심으로 구성 | 백엔드 변경 최소화, 즉시 사용자 가치 제공 |
| F06(챕터)을 Phase 2 첫 번째로 배치 | F16(3단뷰), F19(인용)의 의존성 기반 |
| 발행 큐를 별도 서비스로 분리 | 기존 schedule_service와 역할 분리, 재시도 정책 독립 관리 |
| 캠페인 팩은 generate-multi 확장 | 신규 엔드포인트보다 기존 인프라 활용이 효율적 |
| F13(트랜스크립트 WS)를 Phase 4로 | F04(듀얼 토글)의 간이 버전을 먼저 제공 후 고도화 |
| Supabase 마이그레이션은 Phase별 점진 적용 | 한 번에 하면 롤백 어려움 |
| 채널 모니터링 기본 주기 30분 (최소 10분) | YouTube API 쿼터 일일 10,000회 보호 |

## Key Questions

1. ~~Supabase 스키마 마이그레이션 방식~~ → Phase별 점진 적용으로 결정
2. ~~F08 YouTube API 쿼터~~ → 기본 30분, 최소 10분으로 결정
3. ~~F20 캠페인 팩 사용량 차감~~ → **1회만 차감으로 확정** (4종 생성이지만 1 URL 기준 1회 차감)

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| (아직 없음) | - | - |
