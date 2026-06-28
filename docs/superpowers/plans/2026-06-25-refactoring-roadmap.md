# Insight Engine 리팩토링 로드맵 (진단 결과)

> 작성일: 2026-06-25
> 방법론: 15개 에이전트 fan-out 진단 (11개 코드 영역 + 3개 횡단 관심사 + 1개 종합) → 후보 80건 수집 → 영향도/노력/위험 우선순위 종합
> 상태: **실행 중** (2026-06-25, 브랜치 `refactor/roadmap-2026-06-25`). 진행 현황은 아래 참조.

---

## 진행 현황 (2026-06-25)

**완료 (PR #68, 11커밋):**
- ✅ **1단계 무위험 청소** — middleware/workers/빌드스크립트/cov_report 삭제, ResultCard 도달불가 dead state(audioBlob/ttsLoading), HelpPanel/GuidedTour 제거(사용자 승인)
- ✅ **2단계 소규모 중복 흡수** — 봇 정규식→_shared, routes 에러헬퍼+content_mgmt 중복, useExport triggerDownload, config 미사용심볼+__all__, Slack/Discord 웹훅 헬퍼, FAQ JSON-LD 스키마
- ✅ **3단계 보안 #2** — SSRF 방어 `utils/url_safety.py` 추출 + social_scraper 4개 진입점 적용

**완료 (PR #69, 5커밋):**
- ✅ **3단계 #1 jsonify 에러응답 → api_error** — 약 270건 치환(integrations 107, advanced 51, 나머지 라우트 전반). 보안 분리 커밋(NotebookLM/agent 500 예외 노출 차단, utility videoId sanitize). 베이스라인 회귀 0건(master 79 fail → 78 fail). 의도적 보존: OAuth 멀티키, GitHubHandoffError 멀티키, 멀티라인 sanitize 호출.

**별도 트랙:**
- ⏭ resultStore 용량경고 버그 (spawn_task) — dead code가 아닌 잠복 버그라 분리
- ⏭ NotebookLM 서비스 `result.stderr` raise 임베드 → 소스 레벨 내부 로깅 분리 (spawn_task)

**남음:**
- 4단계: 스타일 단일소스(#3), 타임스탬프/video_id 유틸 통합(#10), zustand 셀렉터(#5), raw fetch 흡수(#6)
- 5단계: Supabase 데코레이터(#4), LiteLLM kwargs(#8), MCP 등록 일원화(#9), ResultCard god-component 분리(#7)
- 6단계 대형(설계 선행): routes god-file 분리(#2), agents 이중 프레임워크 통합(#3, 용도 확정 선행), **DDD 평행구조+사용량 단일권위(#4 — 결제 정합성 위험, 사용자 합의 필수)**

> **검증된 교훈**: dead_code 삭제 전 반드시 동적 등록(importlib/pkgutil) 재확인. `services/{analysis,seo,content,quality,media,transcript,rag,platform}`은 AGENT_MODE 도구 백엔드라 정적 import 0건이어도 살아있음.

---

## ⚠️ 가장 중요한 교정 — "고아 서비스 145개" 는 삭제 금지

종합 리포트가 1순위 부채로 꼽은 **"services/analysis·seo·analytics·content·quality 고아 서비스 145개(약 1.7만 줄) 삭제"** 는 **위험한 false positive** 다. 검증 결과:

- `app.py:212` → `AGENT_MODE_ENABLED=true` 일 때 `discover_tools()` 호출
- `agent/tools/__init__.py` → 모든 `*_tools.py` 동적 import
- `agent/tools/{analysis,seo,content,quality,media,transcript,rag,platform}_tools.py` → 각자 `_register_tools()` 가 **해당 `services/<도메인>/` 디렉토리 전체를 `pkgutil`+`importlib`로 동적 스캔·등록**

즉 이 서비스들은 **정적 import 0건이 맞지만, 에이전트 모드의 동적 도구 백엔드**다. agent 라우트(`/api/agent/chat`·`/stream`·`/sdk`·`/tools`)와 프론트 `AgentPipeline.tsx`까지 연결된 실제 기능이다. 삭제하면 AGENT_MODE 기능이 통째로 깨진다.

**판정:**
| 도메인 | 자동등록 대상? | 처리 |
|--------|----------------|------|
| analysis, seo, content, quality, media, transcript, rag, platform | ✅ (각 `*_tools.py` 존재) | **삭제 금지.** AGENT_MODE 도구 백엔드 |
| analytics (18개) | ❌ (`analytics_tools.py` 없음) | 별도 검증 후 후보 가능 |

> **만약 AGENT_MODE 기능 자체를 영구 폐기할 계획이라면** 이 서비스군 정리가 의미 있다 — 하지만 그건 "리팩토링"이 아니라 "기능 제거 결정"이므로 사용자와 별도 합의가 필요하다.

이 교정은 리팩토링 준비의 핵심 산출물이다: **정적 분석만으로 "import 0건 = 죽음"으로 단정하면 동적 등록 메커니즘을 놓친다.** 아래 모든 dead_code 항목은 실행 직전 동적 로딩(importlib/pkgutil/레지스트리) 가능성을 grep으로 재확인할 것.

---

## 핵심 테마 (반복 패턴)

1. **공통 유틸은 있는데 채택률이 낮은 중복** — 가장 실속 있는 정리 대상
   - 에러 응답: `jsonify({'error':...})` 직접 호출 274건+ (sanitize 헬퍼 `utils/responses.py` 미채택 → traceback/시크릿 노출 위험)
   - 프론트 raw fetch 140건 (`lib/api.ts`의 `request<T>()` 우회 → 타임아웃/에러파싱 누락)
   - 타임스탬프 변환·`video_id` 검증 정규식 4곳 중복
   - Supabase 보일러플레이트 (`get_supabase`+guard+try/except+`_db_operation`) 50회+
   - LiteLLM 프로바이더 분기 kwargs 4개 파일 재구현 (동작 불일치 존재)

2. **god-file 미완성 분리** — 분리 패턴은 이미 검증됨(auth/payment), 완주만 필요
   - `routes/blog_routes.py` 1138줄 · `advanced_routes.py` 1053줄 · `content_mgmt_routes.py` 814줄
   - `frontend/components/result/ResultCard.tsx` 1249줄

3. **DDD(src/contexts) ↔ 절차형(services/) 미완 마이그레이션 공존**
   - `transcript`/`knowledge` 컨텍스트는 production import 0건 박제
   - `content_library`/`identity` 의 infrastructure가 다시 `services/`로 역위임(의존 역전)
   - 사용량 차감이 3경로(`supabase_service`/`UsageService`/identity gateway)로 분산 → **결제 정합성 위험**

4. **완전한 죽은 코드 (실행 시 깨짐/도달 불가)** — 동적 로딩 없음 확인 필요
   - `middleware/` 패키지(app.py가 CSRF/요청크기/요청ID를 자체 인라인 구현 → 기능 중복). 단 `VALID_STYLES` 흡수 선행
   - `build_exe.py`/`run_app_hidden.py`/`robot_icon.py` (제거된 templates/static 참조 → 실행 시 깨짐)
   - 프론트 dead state: `audioBlob`/`ttsLoading`(AudioPlayer 분기 도달 불가), `HelpPanel`/`GuidedTour`(트리거 0건)
   - 루트 산출물: `nul`(0바이트), `cov_report.json`(1.9MB 추적됨)

5. **zustand 전체구독 (CLAUDE.md 금지 패턴)** — 컴포넌트 14곳+훅 다수
6. **보안 사각지대** — SSRF 검증이 `webhook_service`에만, `social_scraper`/`web_scraper`는 미적용

---

## 우선순위 로드맵

### 🟢 Quick Wins (낮은 노력 · 낮은 위험 · 즉효)

| # | 항목 | 파일 | 비고 |
|---|------|------|------|
| 1 | `middleware/` 패키지 삭제 | `middleware/*` | **선행**: `VALID_STYLES` 흡수 + 0참조 직접 재확인 |
| 2 | 루트 산출물 정리 | `nul`, `cov_report.json` | nul 삭제 + .gitignore 추가, 산출물 추적 해제 |
| 3 | 빌드/실행 스크립트 잔재 제거 | `build_exe.py`, `run_app_hidden.py`, `robot_icon.py` | templates/static 참조 → 실행 시 깨짐. 재확인 후 |
| 4 | 프론트 죽은 유틸 제거 | `frontend/lib/webgpu-inference.ts`(214줄), `workers/content_worker.py` | import 0건 재확인 후 |
| 5 | 프론트 도달불가 dead state 제거 | `ResultCard.tsx`(audioBlob/ttsLoading), `page.tsx`(HelpPanel/GuidedTour), `resultStore.ts` 죽은 분기 | ResultCard 분리의 선행 정리 |
| 6 | 에러 sanitize 헬퍼 중복 제거 | `routes/advanced*`, `content_mgmt*` | `utils/responses`로 단일화 (순수 함수) |
| 7 | `content_mgmt_routes` 중복 헬퍼 → `_shared.py` | `routes/content_mgmt/*` | 바이트 동일 복붙 → import 치환 |
| 8 | 봇 `YOUTUBE_URL_RE` 정규식 3중 중복 | `services/integrations/{telegram,slack,discord}_bot_service.py` | 공용 상수 |
| 9 | `useExport.ts` Blob 다운로드 3중 반복 | `frontend/hooks/useExport.ts` | `triggerDownload` 헬퍼 |
| 10 | `config.py` 미사용 심볼 제거 + `__all__` 위치 교정 | `config.py` | 외부 참조 0건 재확인 후 |
| 11 | Slack/Discord 웹훅 공통 베이스 추출 | `services/integrations/{slack,discord}_service.py` | `WebhookNotifier` 베이스 |
| 12 | FAQ JSON-LD 스키마 이중 구현 통합 | `services/content/faq_generator_service.py`, `services/core/ai_metadata.py` | 공통 빌더 |

### 🟡 Medium (중간 노력)

| # | 항목 | 핵심 | 위험 |
|---|------|------|------|
| 1 | **에러 응답 `jsonify` → `utils/responses` 마이그레이션** | 274건+, 보안(시크릿 sanitize) + 일관성 | medium |
| 2 | **스크래퍼 SSRF 검증 적용** | `social_scraper`/`web_scraper`에 URL 안전성 강제, `utils/url_safety` 추출 | medium (보안 우선) |
| 3 | 스타일 목록 단일소스화 | `STYLE_PROMPTS` 기준, 나머지 4곳 파생 생성 | medium |
| 4 | Supabase 데이터 레이어 보일러플레이트 추출 | `@supabase_op` 데코레이터 + JSON폴백 통합 | medium |
| 5 | 프론트 zustand 전체구독 → 셀렉터/useShallow | 컴포넌트 14곳+훅, 순수 교체 | low |
| 6 | 프론트 raw fetch → `lib/api.ts` 래퍼 흡수 | 43개 컴포넌트 140건 | medium |
| 7 | `ResultCard.tsx` god-component 분리 | 순수함수→lib, 핸들러→`useResultActions` | medium |
| 8 | LiteLLM 프로바이더 kwargs 빌더 통합 | `ai_service` 캐노니컬로 수렴 | medium |
| 9 | MCP 플러그인 등록 일원화 | 레지스트리 경유로 통일, 라우트 핸들러 ~280줄 제거 | medium |
| 10 | 타임스탬프/`video_id` 검증 유틸 통합 | `utils/timestamp_utils`·`utils/youtube` | low |

### 🔴 Large (설계 선행 필요)

| # | 항목 | 위험 | 비고 |
|---|------|------|------|
| 1 | ~~고아 서비스 145개 정리~~ | — | **❌ 무효화** (위 교정 참조). analytics 18개만 별도 검토 |
| 2 | `routes/` god-file 분리 완주 | medium | advanced/content_mgmt/blog → 응집 그룹별 서브패키지. 패턴은 검증됨 |
| 3 | `services/agents` 이중 프레임워크 통합 | medium | BaseAgent/WriterAgent 등 클래스명 충돌. 용도 확정 선행 |
| 4 | `src/contexts` DDD 평행구조 정리 + 사용량 단일권위 확정 | **high** | 결제 정합성 위험. **방향(채택 완주 vs 박제 제거) 사용자 합의 필수** |

---

## 추천 진행 순서

1. **즉시·무위험 청소** — Quick Wins #1~5 (middleware, 루트 산출물, 빌드 스크립트, 프론트 죽은 유틸/state). 표면적부터 줄여 이후 작업 탐색성 확보. *각 삭제 전 동적 로딩 0건 직접 재확인.*
2. **소규모 중복 흡수** — Quick Wins #6~12 (순수 추출/이동)
3. **보안 우선 medium** — Medium #2(스크래퍼 SSRF) → #1(jsonify 에러응답 헬퍼)
4. **일관성 medium** — Medium #3(스타일 단일소스) → #10(유틸 통합) → #5(zustand) → #6(raw fetch)
5. **구조 medium** — Medium #4(Supabase 데코레이터) → #8(LiteLLM) → #9(MCP) → #7(ResultCard 분리)
6. **대형 설계 선행** — Large #2(routes 분리) → #3(agents 통합) → #4(DDD 평행구조, 최고 위험·테스트 동반)
7. **별도 결정 사항** — AGENT_MODE 존폐(→ analysis 등 서비스군 운명 좌우), analytics 18개 실사용 검증

---

## 실행 원칙

- **삭제·dead_code 항목은 실행 직전 직접 재검증**: `grep -rn`으로 정적 참조 + `importlib`/`pkgutil`/레지스트리 동적 로딩 0건을 모두 확인. AGENT_MODE 교훈 재발 방지.
- **작은 단위 커밋**: 영역/도메인별로 PR을 쪼갠다. god-file 분리는 응집 그룹 단위.
- **테스트 동반**: 삭제 시 짝 테스트 동반 제거, 구조 변경 시 회귀 테스트. `python -m pytest tests/ -v`.
- **데이터/결제/인증 변경(Large #4)은 경고+확인 후**: CLAUDE.md 보안 규칙 준수.
- **단일소스 갱신**: 스타일 추가/변경 시 `STYLE_PROMPTS`·`STYLE_OPTIONS`·`VALID_STYLES`·`STYLE_TEMPERATURE` 동기화 (→ Medium #3로 근본 해소).

---

## 부록 — 영역별 진단 요약

- **라우트**: 도메인별 서브패키지 분리 진행 중이나 미완성. blog/advanced/content_mgmt god-file 잔류. 생성 헬퍼는 잘 추출됨.
- **분석 서비스(analysis)**: god-file 없음, 컨벤션 일관(첫 공개함수=메인 분석기). **AGENT_MODE 도구 백엔드** — 삭제 금지. 텍스트 전처리 중복만 개선 여지.
- **SEO+콘텐츠**: 500줄 이하로 잘 분해. (고아 판단은 위 교정으로 무효). FAQ 스키마·문장분리 헬퍼 중복.
- **품질+미디어**: RAG/whisper 잘 구조화. LiteLLM kwargs·텍스트 원시함수 재구현 중복.
- **데이터/인프라**: 동작 견고하나 Supabase 보일러플레이트 50회+ 복붙. `supabase_service.py`(551줄) 5개 도메인 혼재.
- **AI코어/에이전트**: core/prompts 잘 구조화. `services/agents/` 이중 프레임워크 클래스명 충돌이 최대 부채.
- **나머지 서비스**: 잘 분리됨. support는 최근 PR로 깔끔(후보 아님). MCP 등록 이원화가 핵심.
- **DDD 컨텍스트(src/)**: content_library/channel_monitoring/identity는 ACL로 정상 연결+아키텍처 테스트 보유. transcript/knowledge는 박제. 사용량 3경로 분산.
- **프론트 컴포넌트**: dynamic()/셀렉터/타이머정리 잘 적용, any 0건. ResultCard god-component + dead state가 핵심.
- **프론트 로직**: api.ts/storage.ts 헬퍼 우수. zustand 전체구독·localStorage 직접접근이 추상화 우회.
- **루트/설정**: app.py 앱팩토리 적절. config.py(571줄) 환경변수/스타일/가격 혼재. middleware/빌드스크립트 죽은 코드.
