# insight-engine 루프 보드

> dev-loop 스킬(.claude/skills/dev-loop/SKILL.md)의 상태 파일.
> 컨텍스트는 세션마다 사라지지만 이 파일은 남는다 — 루프의 척추.
> 규칙: 항목마다 "완료 기준" 필수 / 사람 결정이 필요한 항목은 `[사람]` 태그 / 사이클당 1항목.

## 진행중

(없음)

## 백로그

- [ ] [제품] 앱 고도화 및 업그레이드 — 사용자가 2026-07-10 요청.
  1차: 커맨드 팔레트의 미동작 명령을 실제 이동으로 연결하고 `/dashboard` 운영 페이지를 추가.
  2차: `/notes/[id]`의 끊긴 `?note=` 홈 이동 대신 노트 상세 내부 근거 Q&A 패널로 연결.
  3차: 데스크톱 사이드바에 `/dashboard` 직접 진입 링크 추가.
  4차: `/dashboard`에 브라우저 로컬 생성 결과 요약을 추가해 관리자 API 실패와 별개로 개인 작업 현황을 표시.
  5차: `/dashboard` 최근 로컬 결과에서 홈의 해당 결과 카드로 복귀하는 딥링크 추가.
  6차: `/dashboard`에 `/health` 기반 시스템 건강도 카드 추가.
  7차: 시스템 건강도 카드에 진단 정보 복사 기능 추가.
  8차: `/dashboard`에 로컬 저장 공간 사용률과 최대 보관 개수 안내 추가.
  9차: 시스템 건강도 카드에 수동 새로고침과 마지막 확인 시각 표시 추가.
  10차: `/dashboard` 내 작업 요약을 Markdown으로 복사하는 빠른 내보내기 추가.
  11차: `/dashboard` 내 작업 요약에 최근 7일 로컬 생성 흐름 카드 추가.
  12차: `/dashboard` 상단에 새 콘텐츠·지식위키·최근 결과 빠른 실행 카드 추가.
  13차: `/dashboard` 내 작업 요약에 고정 결과 패널과 Markdown 고정 결과 섹션 추가.
  14차: 대시보드 로컬 통계/Markdown 생성 로직을 순수 함수로 분리하고 단위 테스트 추가.
  15차: 모바일 대시보드의 샘플 QA/일별 지표를 실제 로컬 통계·고정 결과로 교체.
  16차: 모바일 결과 상세의 레거시 스타일 칩을 단순화된 4개 스타일로 교체하고, 모바일에서 학습 노트 저장·중복 노트 열기·지식위키 진입을 연결.
  17차: URL 없는 직접 텍스트 생성 결과도 데스크톱/모바일에서 지식위키 학습 노트로 저장되도록 `text` 노트 소스와 공용 프론트 저장 소스 유틸을 추가.
  18차: 저장 성공 또는 중복 감지 후 결과 카드에 학습 노트 ID를 기억해 이후에는 저장 대신 바로 노트 열기를 제공.
  19차: 대시보드와 모바일 목록/대시보드에 학습 노트 연결 수·최근 연결 노트·노트 연결 배지를 노출.
  20차: `/notes/[id]`에서 연결된 로컬 결과 카드를 감지해 홈의 원본 결과로 되돌아가는 CTA를 제공.
  21차: 홈에 커맨드 팔레트를 다시 렌더링하고, 실제 화면이 없는 재생목록 명령을 제거해 Cmd/Ctrl+K 진입을 복구.
  22차: 템플릿/설정/온보딩/파이프라인의 레거시 15개 스타일 노출을 4개 학습 스타일 기준으로 정리.
  23차: 결과 카드/번역/E2E 기대값의 내보내기 노출을 HTML/Markdown 전용으로 정리.
  24차: 생성/스트리밍/에이전트/영상 Q&A 호출부의 Gemini/Zhipu/OpenRouter 전용 분기를 제거하고 ChatMock(OpenAI 호환) 단일 모델 경로로 단순화.
  완료 기준: 프론트 타입 체크 통과 + 주요 진입점이 실제 페이지/동작으로 연결됨.
- [ ] [정리] 데드 엔드포인트 잔여 코드 정리 — 사용자 2026-07-09 승인:
  "사람이 필요한곳 없으니까 알아서 진행". 데이터 삭제/DB 마이그레이션 없이 코드/테스트/문서만 제거.
  착수 시 `plans/dead-code-audit-2026-06-10.md` 기준으로 프론트 소비자·테스트 소비자 grep 재검증.
  2026-07-09 1차: export/QA 표면 제거 완료. 2차: Ollama 헬스 엔드포인트와 다중 프로바이더 잔여 UI/테스트 제거 완료.
  3차: GraphQL/OAuth 공급자/외부 자동화 웹훅 그룹 제거 완료.
  4차: Agent helper/auth me/content-score 그룹 정리 진행 중. 다음 배치는 남은 감사 목록에서 프론트 소비 0 체인을 재검증해 소형 묶음으로 처리.
  5차: 최종 라우트 감사 `NO_FRONT_NO_TEST_COUNT 0` 확인 완료.
  6차: 결과 카드에서 소비되지 않는 레거시 품질/미디어/미리보기 프론트 컴포넌트 13개 제거 완료.
  7차: 입력 영역에서 소비되지 않는 레거시 북마크/파일/상세도/퓨전/모드/추천 컴포넌트 6개 제거 완료.
  8차: 설정/협업 영역에서 소비되지 않는 레거시 설정·구독·협업 컴포넌트 6개 제거 완료.
  9차: 운영/피드백/워크스페이스 영역에서 소비되지 않는 레거시 프론트 컴포넌트 8개 제거 완료.
  10차: 설정 영역에서 소비되지 않는 레거시 메모리·스니펫·지식그래프 컴포넌트와 전용 훅 제거 완료.
  11차: 프론트에서 소비되지 않는 레거시 훅 7개와 고아 playlist 모달 상태 제거 완료.
  12차: 프론트에서 소비되지 않는 레거시 결과/입력/위키/파이프라인 컴포넌트 15개 제거 완료.
  13차: 프론트 소비 0인 `/api/content/<id>/versions*`, `/api/search`, `/api/notifications*`, `/api/collab/session*` 라우트와 전용 인메모리 서비스/테스트 제거 완료.
  14차: 프론트 소비 0인 Notion 임포트, RSS 구독, 북마크 파싱 라우트와 전용 서비스/테스트, RSS 구독 스케줄러 작업 제거 완료.
  완료 기준: 전체 pytest 0 fail + `cd frontend && npx.cmd tsc --noEmit` 통과 + 제거 엔드포인트 소비 grep 0.
- [ ] [제품] 학습 고도화 — 입력 자료를 요약보다 "학습 가능한 노트"로 구조화.
  중복 소스 경고, 관련 노트, RAG 근거 트레이와 연결해 저장 전 미리보기/태그/핵심 개념을 강화.
  2026-07-09 1차: 학습 포인트/복습 질문 스키마, 검색 색인 보강, 중복 경고 next_action 추가 완료.
  2차: 생성 결과 더보기 메뉴에서 URL 기반 결과를 바로 학습 노트로 저장하고, 중복 경고 시 기존 노트 열기로 연결 완료.
  3차: 데스크톱/모바일 결과 상세에 저장 전 학습 노트 미리보기, 태그, 핵심 개념, 학습 포인트를 표시.
  4차: 노트 상세의 학습 포인트/복습 질문에 브라우저 로컬 복습 체크와 진행률 카드를 추가.
  5차: 노트 상세 복습 진행 상태를 Markdown 체크리스트로 복사하는 기능 추가.
  6차: 노트 상세 복습 질문 답변을 가리고 열어보는 능동 회상 학습 흐름 추가.
  7차: 노트 상세에서 완료한 학습 포인트/복습 질문을 숨기고 남은 항목에 집중하는 필터 추가.
  8차: `/notes` 홈에 진행률이 낮은 미완료 노트를 우선 노출하는 `복습 필요` 카드를 추가.
  9차: `/notes` 홈에 아직 체크하지 않은 최근 학습 노트를 시작하도록 안내하는 `복습 시작` 카드를 추가.
  10차: `/notes/[id]` 복습 완료 시 세션 완료 요약과 `다시 복습` 버튼을 표시.
  11차: `/notes/[id]` 복습 진행 카드에 다음 미완료 학습 포인트/복습 질문을 안내하는 `다음 복습` CTA 추가.
  12차: `/notes` 홈 학습 큐 상단에 진행 중 노트 우선, 미시작 노트 후순위로 묶은 `오늘의 복습 플랜` 추가.
  13차: `/notes` 홈 오늘의 복습 플랜을 Markdown으로 복사하는 빠른 액션 추가.
  완료 기준: 노트 생성/검색 테스트 추가 + 전체 pytest 0 fail + tsc 통과.
- [ ] [제품] LLMWiki형 지식위키 화면 강화 — `/notes`와 `/notes/[id]`를 위키 홈/문서 상세처럼 정리.
  관련 노트, 인용/출처, 근거 기반 채팅 진입을 더 선명하게 노출.
  2026-07-09 1차: `/notes` 지식위키 홈 통계/카드 강화, `/notes/[id]` 학습 포인트·복습 질문·근거 채팅 CTA 추가 완료.
  2차: `/notes` 홈에 개념 지도, 태그 탐색, 출처 구성, 최근 학습 흐름 추가 완료.
  3차: `/notes/[id]`에 문서 목차와 섹션 앵커를 추가해 위키 문서처럼 이동 가능하게 개선 완료.
  4차: `/notes` 홈의 개념·태그·출처를 로컬 필터로 연결하고 활성 필터 요약/해제 UX를 추가.
  5차: `/notes` 홈에 브라우저 로컬 복습 기록 기반 이어 복습 카드와 노트별 복습 질문 수 표시를 추가.
  6차: `/notes` 홈에 미시작/진행중/완료 학습 상태 필터와 노트별 상태 배지를 추가.
  7차: `/notes/[id]` 문서 브리핑 카드로 출처·문서 구성·학습 상태·근거 연결을 한눈에 요약.
  8차: `/notes/[id]` 문서 브리핑에 다음 행동 카드를 추가해 복습 시작/남은 항목/완료 상태를 바로 안내.
  9차: `/notes/[id]` 문서 브리핑 빠른 액션을 학습 상태와 맞추고 첫 액션을 추천 CTA로 강조.
  10차: `/notes` 홈의 `복습 필요`와 `최근 복습` 목록을 분리해 같은 노트가 반복 노출되지 않도록 정리.
  11차: `/notes` 홈에 최근 완료한 복습 노트를 모아 보여주는 `완료 학습` 섹션 추가.
  12차: `/notes` 홈 복습 카드 4종을 `복습 필요 → 복습 시작 → 완료 학습 → 최근 복습` 우선순위로 정렬.
  13차: `/notes` 홈 복습 카드 4종을 접을 수 있는 `학습 큐` 패널로 묶어 지식위키 홈을 단순화.
  14차: `학습 큐` 접힘/펼침 상태를 브라우저 로컬 저장소에 보존해 지식위키 홈 단순화 상태를 유지.
  15차: `/notes` 홈의 개념·태그·출처 필터를 접을 수 있는 `지식 탐색` 패널로 묶어 초기 화면 밀도를 낮춤.
  16차: `/notes` 홈의 지식 탐색 패널에 개념별 관련 문서를 묶어 보여주는 `위키 인덱스`를 추가.
  17차: `/notes/[id]`의 핵심 개념·태그를 `/notes` 필터 딥링크로 연결해 노트 상세에서 위키 인덱스로 되돌아가는 탐색 흐름 추가.
  18차: `/notes/[id]` 문서 브리핑 아래에 관련 노트를 점수순으로 안내하는 `위키 읽기 경로` 카드 추가.
  19차: `/notes/[id]` 위키 읽기 경로를 Markdown으로 복사하는 빠른 액션 추가.
  완료 기준: 프론트 타입 체크 통과 + 가능하면 컴포넌트 테스트 추가.

## Done

- [x] 2026-07-10 feat(notes): 오늘의 복습 플랜 Markdown 복사 추가.
  `/notes` 홈의 `오늘의 복습 플랜` 카드에 플랜 복사 버튼을 추가해 복습 순서·행동·남은 항목·진행률·노트 링크를 Markdown으로 저장할 수 있게 개선.
  공용 `note-list` 유틸에 일일 복습 플랜 Markdown 생성 함수를 추가하고, 공백 정리·빈 플랜·노트 링크 인코딩을 단위 테스트로 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 37 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 위키 읽기 경로 Markdown 복사 추가.
  `/notes/[id]`의 `위키 읽기 경로` 카드에 경로 복사 버튼을 추가해 관련 문서 순서·관련도·이유를 Markdown으로 저장할 수 있게 개선.
  공용 `note-wiki-brief` 유틸에 읽기 경로 Markdown 생성 함수를 추가하고, 공백 정리·빈 경로·Markdown 링크 텍스트 이스케이프를 단위 테스트로 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-wiki-brief.test.ts note-outline.test.ts note-study-progress.test.ts note-review-session.test.ts note-list.test.ts` 36 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 chore(dead-code): 외부 임포트 죽은 라우트 그룹 제거.
  프론트 소비 0·테스트/스케줄러 전용으로 남은 Notion 임포트, RSS 구독, 북마크 파싱 라우트 그룹을 제거.
  Notion/RSS/북마크 전용 서비스 3종, 전용 테스트, RSS 구독 스케줄러 작업, 미사용 Notion API 키 설정 잔여를 함께 정리하고 단일 RSS URL 파싱 경로는 보존.
  README/CLAUDE/TASKS/데드코드 감사 문서의 해당 잔여 설명도 현재 상태에 맞게 갱신.
  검증: 제거 대상 경로/서비스명 grep 0 +
  `.venv\Scripts\python.exe -m pytest tests/test_integration_routes.py tests/test_scheduler_worker.py tests/test_rss_service.py tests/test_multi_source_collector.py -q -p no:cacheprovider` 37 passed +
  `.venv\Scripts\python.exe -m py_compile app.py routes\integration_routes.py routes\integrations\__init__.py services\data\scheduler_worker.py config.py` 통과 +
  `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 위키 읽기 경로 추가.
  `/notes/[id]` 문서 브리핑 아래에 관련 노트를 관련도 점수순으로 보여주는 `위키 읽기 경로` 카드를 추가하고, 문서 브리핑 빠른 액션도 해당 카드로 연결.
  공용 `note-wiki-brief` 유틸에 읽기 경로 계산을 추가하고, 빈 ID 제외·점수 정렬·점수 상한 보정·스니펫 설명을 단위 테스트로 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-wiki-brief.test.ts note-outline.test.ts note-study-progress.test.ts note-review-session.test.ts note-list.test.ts` 35 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 오늘의 복습 플랜 추가.
  `/notes` 홈 학습 큐 상단에 진행 중 노트를 먼저 이어가고 미시작 노트를 뒤에 배치하는 `오늘의 복습 플랜` 카드를 추가.
  공용 `note-list` 유틸에 일일 학습 플랜 계산 함수를 추가하고, 진행 중/미시작/완료/빈 노트 우선순위를 단위 테스트로 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 34 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 chore(dead-code): content_workspace 죽은 라우트 그룹 제거.
  프론트 소비 0·테스트 전용으로 남은 `routes/integrations/content_workspace.py`의 버전 히스토리/검색/알림/협업 세션 라우트 그룹을 제거.
  전용 인메모리 서비스(`version_service`, `search_service`, `notification_service`, `collaboration_service`)와 해당 전용 테스트를 함께 삭제하고 통합 라우트 shim 문서를 갱신.
  검증: 제거 대상 경로/서비스명 grep 0 +
  `.venv\Scripts\python.exe -m pytest tests/test_integration_routes.py -q -p no:cacheprovider` 25 passed +
  `.venv\Scripts\python.exe -m py_compile app.py routes\integration_routes.py routes\integrations\__init__.py` 통과 +
  `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 위키 필터 딥링크 추가.
  `/notes/[id]`의 핵심 개념·태그 배지를 `/notes?concept=...`, `/notes?tag=...` 딥링크로 연결하고, `/notes` 홈이 URL 쿼리에서 개념/태그/출처 필터를 복원하도록 개선.
  공용 `note-list` 유틸에 위키 필터 링크 생성/파싱 함수를 추가하고, 인코딩·우선순위·빈 값 경로를 단위 테스트로 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 33 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 다음 복습 CTA 추가.
  `/notes/[id]` 복습 진행 카드에 첫 미완료 학습 포인트/복습 질문을 자동 안내하는 `다음 복습` CTA를 추가.
  공용 `note-study-progress` 유틸에 다음 학습 대상 계산을 추가하고, 학습 우선/질문 폴백/전체 완료 상태를 단위 테스트로 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-study-progress.test.ts note-list.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 32 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 위키 인덱스 추가.
  `/notes` 홈의 지식 탐색 패널에 반복 등장하는 핵심 개념별 관련 문서 묶음(`위키 인덱스`)을 추가해 개념→문서 흐름을 바로 탐색할 수 있게 개선.
  공용 `note-list` 유틸에 개념 클러스터 계산을 추가하고, 같은 노트 내 중복 개념 제거·대문자 약어 표시·최근 문서 우선 정렬을 단위 테스트로 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 29 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(provider): ChatMock 단일 생성 경로로 단순화.
  `config.py`의 활성 프로바이더 키를 ChatMock으로 축소하고, 생성/스트리밍/에이전트/영상 Q&A 호출부에서 Gemini/Zhipu/OpenRouter 전용 변환·락·폴백 분기를 제거.
  설정 팝오버는 서비스 선택 대신 ChatMock 단일 서비스 안내와 모델 선택만 노출하도록 정리하고, 부하/E2E/단위 테스트 샘플 모델을 ChatMock 기준으로 갱신.
  ChatMock README 기준 기본 OpenAI 호환 base URL(`http://127.0.0.1:8000/v1`)과 지원 모델(`gpt-5.5`, `gpt-5.4`, `gpt-5.4-mini`, `gpt-5.3-codex-spark`)을 재확인.
  검증: `python -m py_compile ...` 통과 + `.venv\\Scripts\\python.exe -m pytest tests/test_ai_service.py tests/test_ai_service_extended.py tests/test_base_agent.py tests/test_generate_stream_delta.py tests/test_advanced_routes_cov.py tests/test_article_generate_route.py tests/test_blog_routes_cov.py tests/test_video_qa_service.py tests/test_cost_tracker_service.py tests/test_dashboard_service.py tests/test_utility_routes.py tests/test_provider_validate_latency.py -q -p no:cacheprovider` 237 passed, 11 subtests passed +
  `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- ResultChatPanel.test.tsx useGenerate.test.tsx note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 34 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(export): HTML/Markdown 내보내기만 노출.
  백엔드 export 라우트는 이미 HTML/Markdown 전용임을 재검증하고, 프론트 번역/E2E 기대값/API 주석의 DOCX/PDF/EPUB 잔여 노출을 제거.
  결과 카드 메뉴는 `HTML 내보내기`와 `마크다운 (.md)`만 검증하도록 업데이트.
  검증: 비필수 내보내기 활성 노출 grep 0(부재 검증 테스트 제외) + `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts useGenerate.test.tsx` 32 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(styles): 레거시 스타일 노출 단순화.
  템플릿 갤러리/커스텀 스타일/설정 모달/온보딩/파이프라인의 15개 스타일 잔여 노출을 공용 `STYLE_OPTIONS` 4개 기준으로 정리.
  기존 결과 렌더링 호환 조건은 유지하되, 사용자에게 보이는 블로그/튜토리얼 중심 문구는 학습 노트/요약/Q&A/퀴즈/리텐션 카드 중심으로 교체.
  검증: 레거시 스타일명 grep 결과가 기존 결과 호환 조건문만 남음 + `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts useGenerate.test.tsx` 32 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 chore(dead-code): 레거시 프론트 컴포넌트 15개 제거.
  프론트 앱/테스트 전수 grep으로 실제 참조가 없는 레거시 컴포넌트 15개를 삭제.
  삭제 대상: PresenceCursors, ModifierPresets, GraphVisualization, PipelineMonitor, AudioPlayer, ChannelAnalysis, CitationLink, CompareView, ContextMenu, FavoriteButton, InlineEditor, MultiLangView, ProgressiveSummary, TranscriptSourceBadge, VersionHistory.
  검증: 삭제 대상명 grep 0 + `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 28 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 지식 탐색 패널 접기.
  `/notes` 홈의 개념 지도와 출처 구성을 `지식 탐색` 패널로 묶고 접힘/펼침 상태를 브라우저 로컬 저장소에 보존해 홈 화면 밀도를 낮춤.
  공용 `note-list` 유틸의 패널 열림 상태 직렬화/파싱 함수를 재사용하도록 정리하고 단위 테스트로 기본/비정상 저장값 경로를 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 28 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 학습 큐 상태 저장.
  `/notes` 홈의 `학습 큐` 접힘/펼침 상태를 브라우저 로컬 저장소에 저장해 다음 방문에도 사용자가 선택한 단순화 상태가 유지되도록 개선.
  공용 `note-list` 유틸에 저장 문자열 직렬화/파싱 함수를 추가하고 잘못된 값은 기본값으로 되돌리는 경로를 단위 테스트로 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 28 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 학습 큐 패널 추가.
  `/notes` 홈의 복습 시작/복습 필요/완료 학습/최근 복습 카드 4종을 접을 수 있는 `학습 큐` 패널로 묶어 화면 복잡도를 낮춤.
  공용 `note-list` 유틸에 표시되는 학습 큐 항목 수 계산을 추가하고, 빈 카드가 카운트에 섞이지 않는지 단위 테스트로 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 27 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 복습 카드 우선순위 정렬.
  `/notes` 홈의 복습 카드 4종 표시 순서를 행동 우선순위 기준(`복습 필요 → 복습 시작 → 완료 학습 → 최근 복습`)으로 고정.
  공용 `note-list` 유틸에 카드 우선순위 계산을 추가하고, 비어 있는 카드는 제외되는지 단위 테스트로 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 26 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 완료 학습 섹션 추가.
  `/notes` 홈에 최근 완료한 복습 노트를 별도 `완료 학습` 카드로 분리하고, `최근 복습`에서는 우선·완료 목록과 중복되지 않게 정리.
  공용 `note-list` 유틸에 완료 학습 목록 계산을 추가하고 완료/진행중/학습 항목 없음 제외와 최신 완료순 정렬을 단위 테스트로 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 25 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 복습 완료 요약 추가.
  `/notes/[id]` 복습 진행 카드에서 모든 학습 포인트/복습 질문을 완료하면 `복습 세션 완료` 요약과 `다시 복습` 버튼을 표시.
  공용 `note-study-progress` 유틸에 완료/미시작/진행중 상태 요약 계산을 추가하고 단위 테스트로 각 상태를 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts note-list.test.ts` 24 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 복습 시작 추천 카드 추가.
  `/notes` 홈에 아직 복습을 시작하지 않은 최근 학습 노트를 최대 3개 보여주는 `복습 시작` 카드를 추가.
  공용 `note-list` 유틸에 미시작 학습 후보 계산을 추가하고, 학습 항목 없음/이미 시작한 노트 제외와 최신순 정렬을 단위 테스트로 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 23 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 복습 카드 중복 노출 정리.
  `/notes` 홈에서 `복습 필요` 우선순위 카드에 표시된 노트를 `최근 복습` 카드에서 제외해 같은 노트가 반복되지 않도록 정리.
  최근 복습 카드는 완료 노트를 `완료` 배지로 표시하고, 공용 `note-list` 유틸에 제외 목록 기반 최근 복습 계산을 추가.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 22 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 복습 필요 우선순위 추가.
  `/notes` 홈에 완료하지 못한 학습 노트만 모아 진행률 낮은 순(동률이면 최근 체크 순)으로 보여주는 `복습 필요` 카드를 추가.
  공용 `note-list` 유틸에 미완료 복습 우선순위 함수를 추가하고, 완료/미시작 노트 제외와 정렬 기준을 단위 테스트로 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts` 21 passed.
- [x] 2026-07-10 feat(notes): 문서 브리핑 추천 액션 강화.
  `/notes/[id]` 문서 브리핑의 첫 빠른 액션을 `추천:` CTA로 강조하고, 복습이 완료된 노트는 다시 복습으로 보내지 않고 근거 Q&A/관련 노트/인용 확장으로 이어지게 조정.
  공용 `note-wiki-brief` 테스트에 완료 상태 빠른 액션 경로를 추가해 학습 상태와 추천 액션이 어긋나지 않도록 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-wiki-brief.test.ts note-outline.test.ts note-study-progress.test.ts note-review-session.test.ts note-list.test.ts` 20 passed.
- [x] 2026-07-10 feat(notes): 문서 브리핑 다음 행동 추가.
  `/notes/[id]` 문서 브리핑에 `다음 행동` 카드를 추가해 미시작이면 복습 시작, 진행 중이면 남은 항목 수, 완료면 전체 완료 상태를 바로 보여줌.
  공용 `note-wiki-brief` 유틸과 테스트를 갱신해 진행 중/미시작/완료/학습 항목 없음 경로를 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-wiki-brief.test.ts note-outline.test.ts note-study-progress.test.ts note-review-session.test.ts note-list.test.ts` 19 passed.
- [x] 2026-07-10 chore(dead-code): 레거시 미사용 훅 7개 제거.
  프론트 소스 전수 grep으로 실제 import/호출이 없는 훅 7개를 삭제하고, 함께 고아가 된 `playlist` 모달 상태를 UI 스토어에서 제거.
  삭제 대상: useApiCall, useInfiniteHistory, useKeyboardShortcuts, useMindmap, useModal, useModifierPresets, usePipeline.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts note-list.test.ts useGenerate.test.tsx` 22 passed +
  제거 대상 grep 0.
- [x] 2026-07-10 feat(app): 커맨드 팔레트 진입 복구.
  `CommandPalette`가 import 0인 고아 상태라 Cmd/Ctrl+K 진입이 실제 앱에 나타나지 않던 문제를 홈에 동적 렌더링으로 복구.
  팔레트 내부에서 실제 모달이 없는 `재생목록 가져오기` 명령은 제거하고, 새 콘텐츠·LLMWiki·설정·템플릿·대시보드처럼 실제 동작하는 명령만 유지.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts note-list.test.ts` 18 passed.
- [x] 2026-07-10 feat(notes): 완료한 복습 항목 숨기기 추가.
  `/notes/[id]` 복습 진행 카드에 `완료 숨기기/전체 보기` 토글을 추가해 체크 완료한 학습 포인트와 복습 질문을 숨기고 남은 항목에 집중할 수 있게 개선.
  공용 `note-study-progress` 유틸에 표시 인덱스 계산 함수를 추가하고 단위 테스트로 전체 보기/미완료만 보기 경로를 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-study-progress.test.ts note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts note-list.test.ts` 18 passed.
- [x] 2026-07-10 feat(notes): 복습 질문 답변 가리기 추가.
  `/notes/[id]` 복습 질문에서 답변을 기본으로 가리고, 사용자가 먼저 떠올린 뒤 개별/전체 답을 열어볼 수 있게 개선.
  공용 `note-review-session` 유틸과 테스트를 추가해 답변 표시 상태 정규화, 개별 토글, 전체 표시 전환을 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-review-session.test.ts note-wiki-brief.test.ts note-outline.test.ts note-study-progress.test.ts note-list.test.ts` 17 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 chore(dead-code): 레거시 설정 고아 컴포넌트 5개 제거.
  프론트 소스 전수 grep으로 현재 앱 진입점에서 소비되지 않는 설정 영역 컴포넌트/훅 5개를 삭제.
  삭제 대상: MemoryManager, SnippetLibrary, KnowledgeGraph, useSnippets, useListManager. 활성 `KnowledgeGraphPanel`은 별도 소비 가능성이 있어 보존.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-wiki-brief.test.ts note-outline.test.ts note-study-progress.test.ts note-list.test.ts` 14 passed +
  제거 대상 import/훅 grep 0.
- [x] 2026-07-10 feat(notes): 노트 상세 문서 브리핑 추가.
  `/notes/[id]` 상단 목차 아래에 문서 브리핑 카드를 추가해 출처, 목차 섹션 수, 복습 진행률, 원본 결과·관련 노트·인용 연결 수를 한눈에 표시.
  문서 목차에 `문서 브리핑` 앵커를 추가하고, 공용 `note-wiki-brief` 유틸/테스트로 브리핑 값과 빠른 액션 구성을 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-wiki-brief.test.ts note-outline.test.ts note-study-progress.test.ts note-list.test.ts` 14 passed.
- [x] 2026-07-10 feat(notes): 복습 진행 Markdown 복사 추가.
  `/notes/[id]` 복습 진행 카드에서 학습 포인트/복습 질문 체크 상태를 Markdown 체크리스트로 복사 가능하게 연결.
  공용 `note-study-progress` 유틸에 Markdown 생성 함수를 추가하고 단위 테스트로 완료/미완료 체크 출력과 답변 포함 경로를 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-study-progress.test.ts note-outline.test.ts note-list.test.ts` 12 passed +
  `git diff --check` 통과.
- [x] 2026-07-10 feat(notes): 지식위키 학습 상태 필터 추가.
  `/notes` 홈에 브라우저 로컬 복습 진행률 기준의 미시작/진행중/완료 필터를 추가하고, 노트 카드에 학습 상태 배지를 표시.
  `note-list` 유틸에 학습 상태 분류/집계/필터 함수를 추가하고 단위 테스트로 진행중·완료·미시작 경로를 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-outline.test.ts` 11 passed.
- [x] 2026-07-10 feat(notes): 지식위키 홈 이어 복습 카드 추가.
  노트 상세에서 저장한 브라우저 로컬 복습 진행 상태를 `/notes` 홈에서 읽어 최근 체크한 노트를 이어 복습 카드로 노출.
  노트 목록 API와 프론트 타입에 `review_question_count`를 추가해 학습 포인트+복습 질문 기준의 진행률 계산을 안정화.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-study-progress.test.ts note-outline.test.ts` 10 passed +
  `.venv\Scripts\python.exe -m pytest tests/test_note_service.py tests/test_notes_routes.py -q -p no:cacheprovider` 30 passed.
- [x] 2026-07-10 feat(notes): 노트 상세 복습 진행 상태 추가.
  `/notes/[id]`에서 학습 포인트와 복습 질문을 체크하며 학습 진행률을 볼 수 있게 하고, 진행 상태를 브라우저 로컬 저장소에 보존.
  공용 `note-study-progress` 유틸과 단위 테스트를 추가해 인덱스 정규화, 토글, 저장/초기화 경로를 검증.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-study-progress.test.ts note-outline.test.ts knowledge-note-source.test.ts dashboard-summary.test.ts` 12 passed.
- [x] 2026-07-10 chore(dead-code): 레거시 운영/피드백/워크스페이스 컴포넌트 8개 제거.
  프론트 소스 전수 grep으로 자기 자신 외 참조 0을 재검증한 뒤 현재 앱 진입점에서 사용하지 않는 운영/피드백/검색/워크스페이스 컴포넌트 8개를 삭제.
  삭제 대상: ReportBuilder, FeedbackWidget, NpsSurvey, NotificationCenter, OnboardingFlow, GlobalSearch, ActivityFeed, ApprovalFlow.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts knowledge-note-source.test.ts dashboard-summary.test.ts ResultChatPanel.test.tsx` 13 passed.
- [x] 2026-07-10 chore(dead-code): 레거시 설정/협업 컴포넌트 6개 제거.
  프론트 소스 전수 grep으로 자기 자신 외 참조 0을 재검증한 뒤 설정/협업 영역에서 사용하지 않는 컴포넌트 6개를 삭제.
  삭제 대상: CollaborativeEditor, ChannelMonitorSettings, NotionConnect, ProviderSetup, RssSubscription, TranscriptSourcePriority.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts knowledge-note-source.test.ts dashboard-summary.test.ts ResultChatPanel.test.tsx` 13 passed.
- [x] 2026-07-10 chore(dead-code): 레거시 입력 컴포넌트 6개 제거.
  프론트 소스 전수 grep으로 자기 자신 외 참조 0을 재검증한 뒤 현재 입력 플로우에서 사용하지 않는 북마크/파일/상세도/퓨전/모드/추천 컴포넌트 6개를 삭제.
  삭제 대상: BookmarkImport, DetailPreset, FileUpload, FusionOptions, GenerationModeSelector, SourceRecommender. DropZone은 KnowledgeManager 소비자가 있어 유지.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- ClipboardPaste.test.tsx note-list.test.ts knowledge-note-source.test.ts dashboard-summary.test.ts` 17 passed.
- [x] 2026-07-10 chore(dead-code): 레거시 결과 컴포넌트 13개 제거.
  프론트 소스 전수 grep으로 import/동적 참조 0을 재검증한 뒤 결과 카드에서 더 이상 소비하지 않는 품질·미디어·미리보기 컴포넌트 13개를 삭제.
  삭제 대상: ABTitleSelector, AutoTags, FactCheckBadge, FeedbackButtons, NewsletterPreview, PlagiarismScore, PodcastPlayer, ReadabilityGauge, SlidePreview, SocialCardPreview, ThumbnailPreview, VideoClipPlayer, WordCloud.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- ResultChatPanel.test.tsx note-list.test.ts knowledge-note-source.test.ts dashboard-summary.test.ts` 13 passed.
- [x] 2026-07-10 feat(notes): 지식위키 로컬 필터 강화.
  `/notes` 홈의 개념 지도, 태그, 출처 구성을 즉시 적용되는 로컬 필터로 연결하고 활성 필터 요약/해제 바를 추가.
  `note-list` 유틸로 출처 라벨, 필터 매칭, 최신순 정렬을 분리하고 단위 테스트를 추가해 검색/탐색 흐름을 안정화.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-list.test.ts note-outline.test.ts knowledge-note-source.test.ts dashboard-summary.test.ts` 13 passed.
- [x] 2026-07-10 feat(notes): 저장 전 학습 노트 미리보기 추가.
  결과 카드와 모바일 결과 상세에서 학습 노트 저장 전 태그·핵심 개념·학습 포인트·분량을 확인할 수 있게 미리보기 카드를 추가.
  공용 `knowledge-note-source` 유틸이 저장 소스와 콘텐츠에서 미리보기 메타를 계산하도록 확장하고 단위 테스트를 추가.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- knowledge-note-source.test.ts dashboard-summary.test.ts note-outline.test.ts` 9 passed.
- [x] 2026-07-10 feat(notes): 지식 노트 문서 목차 추가.
  `/notes/[id]` 상세에 출처·원본 결과·핵심 개념·학습 포인트·복습 질문·요약·근거 Q&A·관련 노트·근거 인용으로 이동하는 문서 목차를 추가.
  표시 가능한 섹션만 목차에 노출하도록 공용 outline 유틸과 단위 테스트를 추가해 LLMWiki형 문서 탐색 경험을 강화.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- note-outline.test.ts knowledge-note-source.test.ts dashboard-summary.test.ts` 8 passed.
- [x] 2026-07-10 feat(notes): 노트 상세 원본 결과 복귀 연결.
  로컬 결과 목록에서 현재 노트 ID와 연결된 결과 카드를 찾아 `/notes/[id]` 상단에 `원본 결과 카드` CTA를 표시.
  버튼은 기존 홈 딥링크 `/?report=<id>`를 사용해 생성 결과 카드로 복귀하도록 연결하고, 공용 유틸에 역조회 테스트를 추가.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- knowledge-note-source.test.ts dashboard-summary.test.ts` 6 passed.
- [x] 2026-07-10 feat(dashboard): 학습 노트 연결 상태 노출.
  로컬 대시보드 통계에 학습 노트 연결 수와 최근 연결 노트 목록을 추가하고 Markdown 요약에도 노트 링크 섹션을 포함.
  모바일 라이브러리에는 노트 연결 수/배지를, 모바일 대시보드에는 연결 노트 카드와 바로 열기 링크를 추가.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- dashboard-summary.test.ts knowledge-note-source.test.ts` 5 passed.
- [x] 2026-07-10 feat(notes): 결과 카드와 학습 노트 연결 상태 저장.
  학습 노트 저장 성공 또는 중복 노트 감지 시 결과 카드에 노트 ID·제목·저장 시각을 로컬로 기록.
  이후 데스크톱/모바일 결과 카드에서는 재저장 대신 `학습 노트 열기`를 제공해 지식위키 재진입을 단축.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- knowledge-note-source.test.ts dashboard-summary.test.ts` 5 passed.
- [x] 2026-07-10 feat(notes): 직접 텍스트 결과 학습 노트 저장 지원.
  노트 소스에 URL이 없는 `text` 타입을 추가하고, 직접 텍스트 생성 응답에 원문 일부와 소스 제목을 포함.
  데스크톱/모바일 결과 카드가 공용 유틸로 URL·텍스트 소스를 판단해 학습 노트 저장을 노출하게 연결.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- knowledge-note-source.test.ts dashboard-summary.test.ts` 5 passed +
  `.venv\Scripts\python.exe -m pytest tests/test_note_service.py tests/test_notes_routes.py -q -p no:cacheprovider` 30 passed.
- [x] 2026-07-10 feat(mobile): 결과 상세 학습 노트 저장 연결.
  모바일 결과 상세의 레거시 스타일 칩을 단순화된 4개 스타일 목록으로 교체하고,
  URL 기반 결과에서 데스크톱과 동일하게 학습 노트 저장·중복 노트 열기·지식위키 진입을 연결.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- dashboard-summary.test.ts` 3 passed.
- [x] 2026-07-10 feat(mobile): 모바일 대시보드 실제 지표화.
  모바일 대시보드의 고정 샘플 일별 막대와 QA 통과율 카드를 제거하고,
  공용 로컬 요약 함수 기반의 실제 저장 공간·최근 7일 생성 흐름·스타일 분포·고정 결과 패널로 교체.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- dashboard-summary.test.ts` 3 passed.
- [x] 2026-07-10 refactor(dashboard): 로컬 요약 계산 로직 분리.
  `/dashboard`의 로컬 통계, 최근 7일 흐름, 고정 결과, Markdown 생성 로직을
  `frontend/lib/dashboard-summary.ts` 순수 함수로 분리하고 단위 테스트를 추가.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- dashboard-summary.test.ts` 3 passed.
- [x] 2026-07-10 feat(dashboard): 고정 결과 패널 추가.
  `/dashboard` 내 작업 요약에 카드에서 핀 고정한 로컬 결과를 모아 보여주는 패널을 추가하고,
  Markdown 복사 내용에도 고정 결과 섹션을 포함.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과.
- [x] 2026-07-10 feat(dashboard): 빠른 실행 카드 추가.
  `/dashboard` 상단에 새 콘텐츠 만들기, 지식위키 열기, 최근 결과 이어보기 카드를 추가해
  통계 확인 후 바로 다음 작업으로 이동할 수 있게 개선.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과.
- [x] 2026-07-10 feat(dashboard): 최근 7일 로컬 생성 흐름 추가.
  `/dashboard` 내 작업 요약에 브라우저 로컬 결과 기준의 최근 7일 생성 건수 막대 카드를 추가하고,
  Markdown 복사 내용에도 일별 생성 흐름을 포함.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과.
- [x] 2026-07-10 feat(dashboard): 내 작업 요약 Markdown 복사 추가.
  `/dashboard` 내 작업 요약에서 저장 결과 수, 저장 공간, 누적 토큰, 스타일 분포,
  최근 결과 목록을 Markdown으로 복사할 수 있게 추가.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과.
- [x] 2026-07-10 feat(dashboard): 시스템 건강도 수동 새로고침 추가.
  `/dashboard` 시스템 건강도 카드에 새로고침 버튼, 로딩 상태, 마지막 확인 시각을 추가하고,
  진단 복사 JSON에 상태 조회 시각과 로딩 여부를 포함.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과.
- [x] 2026-07-10 feat(dashboard): 로컬 저장 공간 상태 표시.
  결과 저장 한도(`MAX_LOCAL_REPORTS=20`)를 `resultStore` 상수로 노출하고,
  `/dashboard` 내 작업 요약에 저장 공간 사용률/상태/자동 밀림 안내를 추가.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- resultStore.test.ts` 5 passed.
- [x] 2026-07-10 feat(dashboard): 시스템 진단 정보 복사 추가.
  `/dashboard` 시스템 건강도 카드에서 현재 `/health` 응답, 에러, API base, user agent, 캡처 시간을
  JSON으로 복사할 수 있게 추가. 지원 요청/디버깅 시 상태 정보를 바로 전달할 수 있음.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과.
- [x] 2026-07-10 feat(dashboard): 시스템 건강도 카드 추가.
  `/dashboard`에서 `/health`를 조회해 API 상태, 환경, 버전, 에러율, 메모리, 요청/에러 수를 표시.
  API 서버 확인 실패 시 “확인 필요” 안내 카드로 원인을 바로 보여줌.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과.
- [x] 2026-07-10 feat(dashboard): 최근 결과에서 원본 카드로 복귀.
  `/dashboard`의 최근 로컬 결과 항목을 `/?report=<id>` 링크로 바꾸고,
  홈 화면은 `report` 쿼리를 감지해 필터를 초기화한 뒤 해당 결과 카드를 렌더 범위에 포함·강조·스크롤.
  대시보드가 단순 통계가 아니라 실제 작업으로 돌아가는 허브가 되도록 개선.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과.
- [x] 2026-07-10 feat(dashboard): 로컬 작업 요약 추가.
  `/dashboard` 상단에 브라우저 저장 결과 기준의 저장 결과 수, 누적 토큰, 평균 길이,
  로컬 스타일 분포, 최근 결과 목록을 추가.
  관리자 API/Supabase가 막혀도 개인 작업 현황은 즉시 볼 수 있게 개선.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과.
- [x] 2026-07-10 feat(app): 사이드바 대시보드 진입 추가.
  데스크톱 사이드바 하단 탐색 영역에 운영 대시보드 링크를 추가하고,
  ko/en/ja 번역 키를 갱신해 커맨드 팔레트 외에도 `/dashboard`에 바로 접근 가능하게 함.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과.
- [x] 2026-07-10 feat(notes): 노트 상세 근거 Q&A 직접 연결.
  `/notes/[id]`의 “이 노트로 질문 시작” 흐름을 홈 쿼리스트링 이동 대신 상세 화면 내 Q&A 패널로 교체.
  노트 요약, 핵심 개념, 학습 포인트, 복습 질문, 근거 인용, 관련 노트를 질문 컨텍스트로 묶어 전달.
  `ResultChatPanel`은 제목/빈 상태/placeholder를 옵션화해 결과 카드와 노트 상세에서 재사용.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `cd frontend && npm.cmd test -- ResultChatPanel.test.tsx` 2 passed.
- [x] 2026-07-10 feat(app): 운영 대시보드 페이지와 커맨드 이동 연결.
  `/dashboard` 페이지를 추가해 기존 `OperationsDashboard`를 실제 라우트로 노출하고,
  관리자/Supabase 미연결 오류는 안내 카드로 표시.
  커맨드 팔레트(Ctrl/Cmd+K)의 새 콘텐츠, LLMWiki, 운영 대시보드 명령을 실제 이동으로 연결하고,
  미동작 파이프라인 명령은 제거.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과.
- [x] 2026-07-09 chore(chatmock): ChatMock 단일 표면 최종 정리.
  지원 FAQ/피드백 분류/설정 UI 잔여 문구를 ChatMock 기준으로 정리하고,
  보조 생성·RAG·번역·리퍼포즈 기본 모델을 `chatmock/gpt-5.4-mini`로 통일.
  내부 레거시 모델 분기(사용자가 직접 구 모델 ID를 넣었을 때의 방어 코드)는 유지.
  데드 엔드포인트 감사: `NO_FRONT_NO_TEST_COUNT 0`.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  관련 테스트 86 passed, 11 subtests passed +
  `.venv\Scripts\python.exe -m pytest tests/ -q --tb=no -p no:cacheprovider` 4083 passed, 1 skipped, 11 subtests passed.
- [x] 2026-07-09 feat(notes): LLMWiki 홈 개념 지도 강화.
  `/notes` 홈에 반복 개념/태그를 집계한 개념 지도와 클릭 검색, 출처 구성, 최근 학습 흐름을 추가.
  “읽고 끝”이 아니라 쌓인 노트를 개념별로 다시 탐색하는 위키 홈 경험을 강화.
  데이터/DB/마이그레이션은 건드리지 않음.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과.
- [x] 2026-07-09 feat(notes): 생성 결과에서 학습 노트 저장 UX 연결.
  `frontend/lib/api.ts`에 노트 생성 래퍼와 API 에러 본문 전달을 추가하고,
  `ResultCard` 더보기 메뉴에 `학습 노트로 저장` 액션을 추가.
  저장 성공 시 생성된 노트로 바로 이동할 수 있고, 409 재학습 경고는 기존 노트 열기 액션으로 자연스럽게 연결.
  데이터/DB/마이그레이션은 건드리지 않음.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `.venv\Scripts\python.exe -m pytest tests/test_notes_routes.py tests/test_note_service.py tests/test_note_index_service.py -q -p no:cacheprovider` 34 passed.
- [x] 2026-07-09 chore(dead-code): Agent helper/auth me/content-score 데드 엔드포인트 정리.
  프론트/테스트 직접 소비 0으로 재검증된 `/api/agent/{sdk,sessions,tools,toolsets}`,
  `/api/agent/pipeline`, `/api/content-score`, `/api/auth/me` 라우트를 제거.
  `/api/agent/sdk`의 유일 구현체였던 `agent/sdk_agent.py`도 고아 파일로 확인 후 제거.
  데이터/DB/마이그레이션은 건드리지 않음.
  소비자 grep: 제거 엔드포인트/함수/서비스 참조 0.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `.venv\Scripts\python.exe -m pytest tests/test_route_duplicates.py tests/test_advanced_routes_cov.py tests/test_auth_routes_cov.py tests/test_agent_e2e.py -q -p no:cacheprovider`
  120 passed +
  `.venv\Scripts\python.exe -m pytest tests/ -q --tb=no -p no:cacheprovider` 4083 passed, 1 skipped, 11 subtests passed.
- [x] 2026-07-09 feat(chatmock): ChatMock 실행 UX 정리 + Ollama 잔여 엔드포인트 제거.
  README 기준 `pipx install chatmock`/`chatmock login`/`chatmock serve` 흐름을 온보딩·설정 UI·에러 메시지에 반영.
  `/api/ollama/health`와 동적 Ollama 모델 조회, Ollama 전용 프론트 저장소/설정 UI, DeepSeek 전용 E2E 테스트를 제거.
  에이전트/NLP/품질/비디오 QA의 기본 호출 경로를 ChatMock(OpenAI 호환)으로 맞춤.
  데이터/DB/마이그레이션은 건드리지 않음.
  소비자 grep: `OLLAMA_BASE_URL|ollama_chat|/api/ollama|api_ollama_health|_fetch_ollama_models` 프로덕션 참조 0.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `.venv\Scripts\python.exe -m pytest tests/ -q --tb=no -p no:cacheprovider` 4198 passed, 1 skipped, 11 subtests passed.
- [x] 2026-07-09 feat(notes): 학습 노트 구조와 LLMWiki 화면 1차 강화.
  `knowledge_note` 프롬프트/파서/검증에 `learning_points`와 `review_questions`를 추가하고,
  노트 검색 색인에 학습 포인트·복습 질문·근거 인용을 포함. 중복 학습 409 응답에 `next_action`을 추가.
  `/notes`는 지식위키 홈처럼 노트/개념/인용/학습 포인트 통계와 요약 카드로 강화하고,
  `/notes/[id]`는 학습 포인트·복습 질문·근거 기반 채팅 CTA·관련 노트·근거 인용을 전면 노출.
  데이터/DB/마이그레이션은 건드리지 않음.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `.venv\Scripts\python.exe -m pytest tests/test_note_service.py tests/test_note_index_service.py tests/test_notes_routes.py -q -p no:cacheprovider` 34 passed +
  `.venv\Scripts\python.exe -m pytest tests/ -q --tb=no -p no:cacheprovider` 4198 passed, 1 skipped, 11 subtests passed.
- [x] 2026-07-09 chore(dead-code): 외부 자동화/OAuth/GraphQL 데드 엔드포인트 정리.
  프론트/테스트 직접 소비 0으로 재검증된 `/graphql`, `/graphql/schema`,
  `/oauth/{authorize,clients,register,revoke,token}`,
  `/api/webhooks/{slack,discord,telegram}`, `/api/webhooks/telegram/setwebhook`,
  `/api/zapier/{trigger,auth/test}`, `/api/make/webhook`, `/api/ifttt/trigger`, `/api/webhook-relay` 제거.
  연쇄 고아 서비스 `services/integrations/`, `services/auth/oauth_provider_service.py`,
  `services/platform/webhook_relay_service.py`와 전용 테스트 9개도 제거.
  데이터/DB/마이그레이션은 건드리지 않음.
  소비자 grep: 제거 경로/서비스 참조 0.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `.venv\Scripts\python.exe -m pytest tests/ -q --tb=no -p no:cacheprovider` 4083 passed, 1 skipped, 11 subtests passed.
- [x] 2026-07-09 chore(dead-code): export/QA 데드 엔드포인트 1차 정리.
  `/api/export/{docx,epub,txt,zip,slides,srt,infographic,card-news,summary-card,code-image,newsletter-html,interactive-report}`와
  `/api/qa-check` 라우트 제거. 프론트 고아 컴포넌트 `InfographicPreview`, `QaRulesEditor`,
  서비스 `qa_gate_service`, `epub_service`, export 서비스의 DOCX/TXT/ZIP 경로 및 전용 테스트 제거.
  데이터/DB/마이그레이션은 건드리지 않음.
  소비자 grep: 제거 엔드포인트/서비스 참조 0.
  검증: `python -m pytest tests/ -q --tb=no -p no:cacheprovider` 4199 passed, 1 skipped, 11 subtests passed +
  `cd frontend && npx.cmd tsc --noEmit` 통과.
- [x] 2026-07-09 feat(product): 제품 표면 1차 단순화.
  스타일 UI를 요약/Q&A/퀴즈/리텐션 카드 4개로 축소하고 기본 스타일을 `summary`로 변경.
  프로바이더 노출은 ChatMock(OpenAI 호환) 단일로 정리, 기본 모델은 `chatmock/gpt-5.4-mini`.
  내보내기 UI/API wrapper는 HTML/Markdown만 남기고 DOCX/TXT/ZIP/PDF 표면 제거. QA 게이트 프론트 표면도 제거.
  README/.env.example/구현 계획 문서(`docs/superpowers/plans/2026-07-09-product-simplification.md`) 갱신.
  검증: `cd frontend && npx.cmd tsc --noEmit` 통과 +
  `python -m pytest tests/ -q --tb=no -p no:cacheprovider` 4351 passed, 1 skipped, 11 subtests passed.
- [x] 2026-07-09 feat(chat): RAG 답변의 “근거 부족” 자동 차단과 출처 경계 검사.
  `/api/chat`에서 검색 노트가 모두 `score < 0.25`이거나 비숫자/NaN 점수면 LLM(대형 언어 모델) 호출 없이
  `[근거 부족]` 답변을 반환. 혼합 결과는 낮은 score 출처를 프롬프트/응답에서 제외하고,
  검색 결과 없음/검색 실패 경로는 기존처럼 답변 생성 유지.
  검증: `python -m pytest tests/test_chat_routes.py -q -p no:cacheprovider` 18 passed +
  `npm test -- ResultChatPanel.test.tsx` 2 passed + `cd frontend && npx tsc --noEmit` 통과 +
  `npm run verify:frontend` 통과 + `npm run verify:e2e` 1 passed.
  code-reviewer BLOCKER/IMPORTANT 0, NIT 없음. 로컬 커밋: fe0453c. PR/푸시는 사용자 승인 전 보류.
- [x] 2026-07-09 feat(chat): 생성/채팅 결과 근거 트레이(rag_sources) 표시.
  `/api/chat` 응답에 `rag_sources[]`를 추가하고 기존 `notes[]`는 호환 유지. ResultChatPanel에 지식 노트
  근거 트레이를 표시하며, history(대화 기록)는 role/content만 전송해 근거 스니펫 재전송을 방지.
  score는 유한 숫자일 때만 응답에 포함.
  검증: `python -m pytest tests/test_chat_routes.py -q -p no:cacheprovider` 14 passed +
  `npm test -- ResultChatPanel.test.tsx` 2 passed + `cd frontend && npx tsc --noEmit` 통과 +
  `npm run verify:frontend` 통과 + `npm run verify:e2e` 1 passed.
  code-reviewer BLOCKER/IMPORTANT 0, NIT 반영 완료. 로컬 커밋: 34708f1. PR/푸시는 사용자 승인 전 보류.
- [x] 2026-07-09 feat(notes): 학습 소스 중복 감지/재학습 경고 추가.
  `/api/notes` 생성 전에 동일 URL 또는 `score > 0.92` 유사 노트를 탐지하면 AI 호출/저장 전에
  `[재학습 경고]` 409 응답과 `duplicate_notes[]`를 반환. 유사도 조회 실패 시에는 기존 저장 흐름을 유지.
  YouTube 단축 URL·utm 파라미터 URL 정규화와 invalid source 400 회귀 테스트 포함.
  검증: `python -m pytest tests/test_notes_routes.py tests/test_note_index_service.py -q -p no:cacheprovider`
  28 passed + `cd frontend && npx tsc --noEmit` 통과 + `npm run verify:e2e` 1 passed.
  code-reviewer BLOCKER/IMPORTANT/NIT 0. 로컬 커밋: c55dfb1. PR/푸시는 사용자 승인 전 보류.
- [x] 2026-07-09 feat(notes): 관련 노트 3개 자동 추천 + 상세 화면 링크 표시.
  `services/content/note_index_service.py`에 자기 자신 제외 유사 노트 조회를 추가하고,
  `routes/notes_routes.py` 상세 응답에 `related_notes[]`를 graceful degradation(부가 기능 실패 시 핵심 응답 유지)으로
  포함. `frontend/app/notes/[id]/page.tsx`에서 최대 3개 관련 노트를 카드 링크로 표시.
  검증: `python -m pytest tests/test_notes_routes.py tests/test_note_index_service.py -q -p no:cacheprovider`
  21 passed + `cd frontend && npx tsc --noEmit` 통과 + `npm run verify:frontend` 통과 +
  `npm run verify:e2e` 1 passed. code-reviewer BLOCKER/IMPORTANT 0, NIT 반영 완료.
  로컬 커밋: 4e31768. PR/푸시는 사용자 승인 전 보류.
- [x] 2026-07-09 feat(input): 전역 Ctrl+V/Cmd+V 붙여넣기 라우팅 활성화. 기존
  `frontend/components/input/ClipboardPaste.tsx`를 `frontend/app/page.tsx`에 연결해
  URL은 URL 탭/큐로, 긴 텍스트는 텍스트 탭으로 전환. 입력 필드 포커스 중에는 기본 붙여넣기 보존.
  검증: `npm test -- ClipboardPaste.test.tsx` 6 passed + `npm run verify:frontend` 통과 +
  `npm run verify:e2e` 1 passed. code-reviewer BLOCKER/IMPORTANT 0.
- [x] 2026-07-09 보드 백로그 재검증/정리. NotebookLM download 준비 전 400 매핑은
  `routes/notebooklm_routes.py`에 반영되어 `tests/test_notebooklm_routes.py` 7 passed.
  ruff 정리 항목은 현재 dev 의존성/검증 게이트에서 ruff가 빠졌고(`requirements-dev.txt`=pytest/flake8),
  지정 F401/F841 잔여도 현재 코드에서 재현되지 않아 백로그에서 제거. CI master 트리거/flake8 권고/vitest
  스텝/duckduckgo-search 의존성은 origin/master PR #119 및 `requirements.txt`로 반영됨.
  docker/deploy/coverage의 `refs/heads/main` 게이트는 `.github/workflows/ci.yml` 주석상 의도적 유지 결정.
- [x] 2026-07-04 로컬 master 21커밋 뒤처짐 해소 (사이클 10, Codex 위임 1호). 46개 테스트 컬렉션 에러를
  fcntl 회귀로 오진 → Codex 위임으로 수정·PR #75 생성했으나, 원격 master에는 이미 PR #50(더 완전한
  fcntl 가드)이 머지돼 있었음 — 진짜 원인은 master 푸시 거부로 로컬 master가 원격 대비 21커밋 뒤처진 것.
  PR #75 닫음 + 로컬 master를 origin/master에 rebase(보드 커밋 10개 보존) — import OK + 보드 diff 0.
  utcnow 잔존 오진 건도 원격 커밋이 기해결이라 백로그에서 제거
- [x] 2026-06-27 ruff F841 프로덕션 미사용 변수 4건 검토 (사이클 9). app.py:28 `base_dir` / support_agent_service.py:66 `forced_feedback` / supabase_history_repository.py:44 `data` / supabase_api_key_vault.py:81 `res` — **모두 무해**(의도적 결과 무시 / legacy fallback / 예외 기반 에러 처리). 진짜 버거 0건. 정리는 백록 ruff cleanup NIT로 이관
- [x] 2026-06-27 PR #70 리뷰 (test: resultStore 회귀 테스트 + vitest 도입). code-reviewer 실측 검증(tsc/test 4 passed/lint/build exit 0) → IMPORTANT(CI npm test 스텝 누락, [사람] CI 항목으로 이관) + NIT 2건. GitHub 리뷰 코멘트 게시(reviews:2)
- [x] 2026-06-27 PR #69 BLOCKER 2건 수정 (refactor/jsonify-error-responses 97751a6). notebooklm download RuntimeError → api_error_from_exception(stderr 노출 차단) + agent_routes sessions/tools/toolsets → logger.error + api_error("[서버 오류]...",500)(로깅+노출 차단). 검증: ruff All passed + import OK
- [x] 2026-06-27 PR #69 리뷰 (refactor: 에러 응답 api_error 일관화). code-reviewer 리뷰 → BLOCKER 2건(notebooklm download stderr 노출 / agent_routes sessions-tools-toolsets str(e) 500 + 로깅 누락) + SUGGESTION 1건. GitHub 리뷰 코멘트 게시(reviews:1) — 사이클 7에서 BLOCKER 수정
- [x] 2026-06-27 fix(mcp): inline_editor 미정의 logger로 except 블록 NameError 버그 (PR #74, base master). ruff F821(진짜 런타임 버그 — 에러 처리 마스킹) 수정, get_logger 추가. code-reviewer 지적(get_logger '짧은명' 패턴 통일) 반영 — ruff 클린 + import/logger 동작 OK. ruff 367 위반 중 F821(진짜 버그)만 선별 처리
- [x] 2026-06-27 fix(test): datetime.utcnow() deprecation 제거 (PR #73, stacked base PR #71). test_account_service.py:108 datetime.utcnow() → datetime.now(timezone.utc). code-reviewer 승인(-W error::DeprecationWarning 통과, 외과적/회귀 없음) — pytest DeprecationWarning 0 + 전체 5,445 passed/0 fail
- [x] 2026-06-27 fix(logging): logging_config cp949 UnicodeEncodeError 근본 차단 (PR #72, stacked base PR #71). _ensure_utf8_stdout()로 sys.stdout을 utf-8/errors='replace'로 재구성 → get_logger 시점 buffer 고정 회피 + surrogate 안전. code-reviewer 지적(reconfigure 전환+errors=replace+테스트+타입힌트) 반영 — em-dash/이모지/surrogate 로깅 에러 0 + test_logging_config 12 passed + 전체 5,448 passed/0 fail
- [x] 2026-06-27 fix(scheduler): scheduler_worker cp949 로깅 em-dash UnicodeEncodeError 핫픽스 (PR #71 추가 커밋 9682c78+065420e). em-dash 3곳 ASCII 교정 + test 기대값 동기화 + 주석 공백 복원 — app import 에러 제거 + scheduler_worker 테스트 7 passed + ruff 통과. code-reviewer [CRITICAL](근본 미해결, services/ 123개 파일)은 사이클 3 logging_config 근본으로 이관
- [x] 2026-06-27 fix(scheduler): scheduler_worker 모듈 최상단 `import fcntl`(PR #42) → Windows에서 app import 실패, 테스트 46개 파일 컬렉션 에러 회귀 수정 (PR #71). fcntl 조건부 import + Windows 리더 락 우회, Unix flock 로직 보존 — pytest 5,445 passed(0 fail, 46 컬렉션 에러 해소) + code-reviewer 클린
- [x] 2026-06-22 feat(ui): SupportAssistant shadow #15171F → Signal 토큰 (PR #54, 다크모드 그림자 누락 버그 수정) — tsc 0 + build 성공 + code-reviewer 클린
- [x] 2026-06-23 refactor(export): <style> → 공유 모듈 + Signal 정규화 (PR #62, PR #60/#61 대체 + useExport 인쇄 #111 처리) — tsc+build 성공 + code-reviewer 클린
- [x] 2026-06-23 feat(ui): ResultCard 인쇄 템플릿 #111 → Signal foreground (PR #61, handlePrint 누락분) — build 성공 + code-reviewer 클린
- [x] 2026-06-22 feat(ui): 내보내기 HTML CSS 구식 색 → Signal 정규화 (PR #60, useExport + ResultCard 5종 색) — build 성공 + code-reviewer 클린
- [x] 2026-06-22 feat(ui): global-error/layout 구식 인디고 → Signal primary (PR #59, #6366f1/#4F46E5/#6b7280 정규화) — build 성공 + code-reviewer 클린
- [x] 2026-06-22 feat(ui): MobileAppShell warm beige #F1EDE5 → Signal 토큰 (PR #58, L176 bg-card / L219 bg-muted, 구식 warm 제거+다크모드 버그) — build 성공 + code-reviewer 클린
- [x] 2026-06-22 feat(ui): MobileAppShell 배경 #F5F6F8 → bg-background 토큰 (PR #57, 4곳, 다크모드 버그 수정) — build 성공 + code-reviewer 클린
- [x] 2026-06-22 feat(ui): #2F54EB 사용처 → --primary 토큰 (PR #56, page shadow + prose border + gradient) — build 성공 + code-reviewer 클린
- [x] 2026-06-22 feat(ui): page/MobileAppShell shadow 5곳 → Signal 토큰 (PR #55, 동일 패턴) — build 성공 + code-reviewer 클린
- [x] 2026-06-10 PR #23 Codex P2 리뷰 지적 3건 반영 (캐시 히트 자막 재추출 폴백 / GLM 챕터 병렬 제외 / BASE 프롬프트 소스 중립화) — 전체 5,414 passed + code-reviewer 통과
- [x] 2026-06-10 데드 엔드포인트 ~200개 제거 + 깨진 테스트 142개 정리 — 커밋 6e2da90, 전체 5,414 passed / 0 fail
- [x] 2026-06-10 성능 최적화 + 프롬프트 v4 재작성 + 정리 — 5커밋, PR #23 푸시됨

## 학습/메모

- 2026-07-09 05:12 점검 — 사용자 `dev-loop 100번` 요청 중 1회차 수행. 스킬 규칙상 1회 호출=1사이클.
  추가 변경 없음. 비`[사람]` 백로그 0건, 기능 탐색은 2026-07-09 실행으로 7일 쿨다운 유지.
  검증: `python -m pytest tests/ -q --tb=no -p no:cacheprovider` 4353 passed, 1 skipped,
  11 subtests passed + `cd frontend && npx.cmd tsc --noEmit` 통과. 열린 PR 없음, 최근 CI 최신 2건 성공.
- 2026-07-09 02:18 중단 — 동일 조건 3회 이상 반복 확인. 비`[사람]` 백로그 0건,
  기능 탐색은 2026-07-09 실행으로 7일 쿨다운 중, 남은 항목은 데드 엔드포인트 335건 제품 결정/삭제 확인
  필요 항목뿐이라 사용자 결정 없이는 의미 있는 추가 개발 진행 불가.
- 2026-07-09 02:17 점검 — 추가 변경 없음. 비`[사람]` 백로그 0건, 기능 탐색 쿨다운 유지.
  검증: `python -m pytest tests/ -q --tb=no -p no:cacheprovider` 4353 passed, 1 skipped,
  11 subtests passed + `cd frontend && npx tsc --noEmit` 통과. 열린 PR 없음, 최근 CI 최신 2건 성공.
- 2026-07-09 02:13 점검 — 추가 변경 없음. 비`[사람]` 백로그 0건, 기능 탐색 쿨다운 유지.
  검증: `python -m pytest tests/ -q --tb=no -p no:cacheprovider` 4353 passed, 1 skipped,
  11 subtests passed + `cd frontend && npx tsc --noEmit` 통과. 열린 PR 없음, 최근 CI 최신 2건 성공.
- 2026-07-09 점검 — 비`[사람]` 백로그 0건, 기능 탐색은 2026-07-09 실행 완료로 7일 쿨다운 중.
  전체 검증: `python -m pytest tests/ -q --tb=no -p no:cacheprovider` 4353 passed, 1 skipped,
  11 subtests passed + `cd frontend && npx tsc --noEmit` 통과. 열린 PR 없음, 최근 CI 최신 2건 성공.
- 2026-07-09 기능 탐색 — 후보 4건 적재. 출처: Khoj/claude-obsidian(관련 노트), FastGPT(중복 소스 경고),
  AnythingLLM(근거 트레이), SecuritySkills issue(RAG 근거 부족 차단). 발행 계열·대형 L/XL 후보 제외.
- 2026-07-04 [NIT, code-reviewer] Windows + FLASK_DEBUG=true 시 werkzeug 리로더가 부모/자식 프로세스에서
  app.py를 각각 import → Windows 리더 락 우회 경로에서 스케줄러 2개 기동 가능. 필요 시 WERKZEUG_RUN_MAIN
  체크로 해결 — 개발 환경 한정이라 지금은 미적용(Simplicity First).
- 2026-07-04 **트리아지 전 `git fetch` + origin/master 비교 필수**: master 직접 푸시가 권한 정책으로 거부되어
  보드 커밋이 로컬에만 쌓임 → 로컬 master가 원격 대비 21커밋 뒤처짐 → 이미 원격에서 고쳐진 문제(fcntl,
  utcnow)를 회귀로 오진해 중복 PR #75까지 생성. dev-loop 0단계에 fetch+비교를 추가해야 재발 방지.
  보드는 로컬 master에 계속 커밋하되 주기적으로 rebase — 또는 [사람] master 푸시 허용/보드 별도 브랜치 결정.

- 2026-06-22 프론트엔드 디자인 루프 시작 (/loop 20m + dev-loop, cron 0bfd9f6d). 백로그를 디자인 항목으로 채워 dev-loop이 화면 단위 리디자인을 잡도록 구성.
- 2026-06-22 보드 정책 수정: loop-board.md는 master에 직접 추적(루프 상태=인프라). 코드는 작업 브랜치/PR로 분리. 보드를 코드 PR에 넣으면 작업 브랜치에 갇혀 master 기반 새 브랜치가 백로그를 못 봄(cycle 1에서 발견).
- 2026-06-22 MobileAppShell CATEGORY_DOTS(#E90043/#7C5CFF/#20C997/#2F80ED/#F2B705) 데이터 팔레트는 의도적 유지 결정 — 한 파일 로컬 + 소스 타입 구분은 테마 독립이 맞음, 토큰화는 과잉(Simplicity First).
- 2026-06-22 settings/billing/marketplace/library/analytics/schedule/search/modals/input 영역 Signal 감정 완료 — 전부 hex 0, 이미 토큰화됨. 남은 hex는 데이터 시각화(GraphVisualization/ResultCard 차트/api og) + 구식 인디고 잔재뿐.
- 2026-06-22 GraphVisualization NODE_COLORS(#6366f1/#10b981/#f59e0b/#ef4444)는 데이터 시각화 범주 팔레트로 의도적 유지 결정 — 4 노드 타입 구분이 핵심, --chart-*와 부분 일치(entity=#f59e0b)하지만 topic red 대응 없어 로컬 유지(CATEGORY_DOTS와 동일 결정).
- 2026-06-23 ResultCard 감정 완료 — UI hex는 handlePrint 인쇄 템플릿 #111 한 곳(PR #61 처리). 나머지는 내보내기 CSS(PR #60) 또는 GRADE_STYLES Tailwind 색 이름(hex 아님). ResultCard 토큰 마이그레이션 완료.
- 2026-06-23 cycle 9 트리아지: PR #54~#61 전부 미머지 → `<style>` 리팩터 블로커(PR #60/#61과 같은 인라인 영역, 충돌). 디자인 토큰 마이그레이션은 완료. 남은 산물 = PR 8개 머지 + 리팩터 1건(머지 후).
- 2026-06-23 cycle 10: <style> 공유 모듈(lib/exportHtmlTemplate.ts) 추출 + Signal 정규화 — PR #62. PR #60/#61 supersede + useExport 인쇄 #111 미발견분 처리. **디자인 토큰 루프 백로그 완전 종료.** PR #54~#62(#60/#61은 #62가 대체) 머지 대기 — 머지 후 루프 종료.
- 2026-06-23 cycle 11 점검 — 이상 없음 (PR 리뷰 0 / CI main 게이트로 PR 미실행 / ESLint 0경고 / tsc 통과). 디자인 백로그 비어 루프 자연 종료 상태. 새 방향 없으면 빈 사이클 반복.
- 2026-06-23 **디자인 토큰 루프 종료** (cron 0bfd9f6d 삭제). 11사이클(PR #54~#62, #60/#61은 #62가 대체) 완료. 머지 대기.
- 2026-06-11 00:26·00:58·01:59·02:59 야간 루프 점검 — 이상 없음 (새 리뷰 코멘트·CI 런·워킹트리 변경 없음)

- 멀티라인 커밋 메시지는 Bash heredoc(`git commit -F - <<'EOF'`) 사용 — PowerShell here-string 금지 (2026-06-10)
- (사이클에서 얻은 짧은 메모를 여기에. 일반 규칙이 되면 ~/.claude/session-learnings/로 증류)
