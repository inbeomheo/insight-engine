# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 작업 규칙

- 모든 커뮤니케이션은 한국어로 한다
- 전문 용어 사용 시 괄호 안에 한 줄 설명 추가
- 에러 발생 시 "왜 났는지 / 어떻게 고치는지 / 다음에 피하려면" 3단계로 설명
- Key/Secret 하드코딩 금지
- 데이터 삭제/교체/마이그레이션은 "경고 + 사용자 확인" 없이 금지

## Project Overview

**Insight Engine** - YouTube 영상 URL로 다양한 AI 모델(Gemini, DeepSeek, Zhipu GLM, Ollama)을 활용해 고품질 다국어(ko/en/ja) 콘텐츠를 자동 생성하는 Flask + Next.js 웹 앱. LiteLLM을 통해 다중 AI 프로바이더를 통합 지원. Gemini가 기본 프로바이더. RAG 지식 참조, 팀 워크스페이스 지원.

## Commands

```bash
# 의존성 설치
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 앱 실행 (개발 모드 — 두 서버 모두 필요)
python app.py                    # Flask 백엔드 → http://localhost:5001
cd frontend && npm run dev       # Next.js 프론트엔드 → http://localhost:3000

# 단위 테스트
python -m pytest tests/ -v
python -m pytest tests/test_rag_service.py -v  # 특정 파일

# 프론트엔드 타입 체크 + 빌드
cd frontend && npx tsc --noEmit
cd frontend && npx next build

# E2E 테스트 (Playwright)
cd tests/e2e && npm install
npx playwright test --workers=1        # 순차 실행 (안정적, 권장)
npx playwright test --ui               # UI 모드
npx playwright test main-page/         # 특정 폴더만

# 커버리지
python -m pytest tests/ --cov=. --cov-report=html
```

## Architecture

### Core Request Flow (단일 생성)

```
[사용자] → POST /generate
    ↓
[@require_auth] → [@require_usage] 인증 + 사용량 체크/차감
    ↓
[content_service] YouTube 자막 추출 (4단계 폴백: youtube-transcript-api → watch 페이지 파싱 → Supadata API → Whisper 로컬 음성인식)
    ↓
[content_service] 댓글 수집 (YOUTUBE_API_KEY 필요)
    ↓
[병렬 AI 호출] ← 댓글이 있을 때
├─ 메인: ai_service.create_content(자막, style_prompt)
└─ 댓글: _generate_comment_summary(댓글, COMMENT_SUMMARY_PROMPT)
    ↓
[_combine_results] 메인 결과 + 댓글 요약 병합
    ↓
JSON 응답 {title, content, html, usage}
```

- 댓글이 없으면 단일 AI 호출로 fallback
- GLM 모델(`zhipuai/`)은 글로벌 락(`_glm_lock`) 충돌 방지를 위해 순차 실행

### Backend Layers

| 레이어 | 파일 | 역할 |
|-------|------|-----|
| 라우트 | `routes/blog_routes.py` | 콘텐츠 생성, 파이프라인(SSE), MCP 발행, 지식 업로드, Ollama 헬스체크 |
| 라우트 | `routes/auth_routes.py` | 인증, API 키, 사용량, 관리자, 워크스페이스, 승인 플로우 API |
| 라우트 | `routes/advanced_routes.py` | 멀티스타일, 퓨전, 마인드맵, 인라인 편집, QA |
| 라우트 | `routes/export_routes.py` | DOCX/MD/TXT/ZIP 내보내기 |
| 라우트 | `routes/utility_routes.py` | 헬스체크, 프로바이더, 캐시, 스타일 추천, 프로바이더 검증 |
| 서비스 | `services/core/ai_service.py` | LiteLLM 래퍼, 다국어 모디파이어, Ollama api_base, RAG 컨텍스트 주입 |
| 서비스 | `services/core/content_service.py` | YouTube 자막/댓글 추출, 4단계 폴백 (Whisper 포함) |
| 서비스 | `services/core/pipeline_service.py` | 파이프라인 자동화 엔진 (SSE 이벤트 스트리밍) |
| 서비스 | `services/core/fusion_service.py` | 다중 소스 퓨전 콘텐츠 생성 |
| 서비스 | `services/transcript/whisper_service.py` | faster-whisper 로컬 음성인식 (yt-dlp 오디오 다운로드) |
| 서비스 | `services/transcript/chapter_service.py` | AI 자막 → 챕터 자동 분할 |
| 서비스 | `services/platform/webhook_service.py` | 웹훅 알림 (SSRF 검증 + 재시도) |
| 서비스 | `services/platform/channel_monitor_service.py` | YouTube 채널 신규 업로드 감지 (30분 폴링) |
| 서비스 | `services/data/scheduler_worker.py` | APScheduler 백그라운드 워커 (채널 모니터링/RSS 구독, 30분 간격) |
| 서비스 | `services/data/workspace_service.py` | 워크스페이스 생성/초대/역할 관리 + 콘텐츠 승인 플로우 |
| 서비스 | `services/data/supabase_service.py` | Supabase 인증, CRUD, 관리자 조회 |
| 서비스 | `services/content/citation_service.py` | 인용 마커 [MM:SS] 파싱 + 검증 + YouTube 링크 변환 |
| 서비스 | `services/quality/qa_gate_service.py` | 발행 전 QA 게이트 (금칙어/구조/중복/링크 검증) |
| 서비스 | `services/agents/` | 멀티에이전트 파이프라인 (Research → Writer → Editor → SEO) |
| 서비스 | `services/mcp/` | MCP Apps SDK (인라인 편집 등 인터랙티브 앱) + MCP 서버(외부 AI 에이전트용 도구). 발행 플러그인 시스템은 제거됨(Dep-5) |
| 서비스 | `services/rag/` | RAG: ChromaDB 벡터 스토어, 텍스트 청킹, 컨텍스트 빌더 |
| 서비스 | `services/usage/` | 사용량 관리 패키지 (`require_usage`, `check_usage`, `UsageService`) |
| 설정 | `config.py` | 토큰 제한, 프로바이더/모델/가격, 스타일별 temperature/max_tokens, RAG 설정 |
| 프롬프트 | `prompts/` | 프롬프트 시스템 v4.0 + GEO/Shorts/Course/Citation 스타일 |

### 프롬프트 구조 (v4.0)

```
┌─────────────────────────────────────────┐
│ BASE_PROMPT (prompts/base.py)           │  ← compose_style_prompt()로 결합
│ ├─ 입력 섹션 규칙(자막/댓글/타임코드)   │
│ ├─ 정확성·금지 표현·출력 규칙 (1회만)   │
├─────────────────────────────────────────┤
│ STYLE_PROMPT (prompts/styles/*.py)      │
│ └─ 스타일 목표, 고유 가이드, 출력 형식  │
├─────────────────────────────────────────┤
│ [추가 지시사항] (ai_service가 주입)     │
│ └─ 길이/문체/언어 모디파이어 + 현재시간 │
└─────────────────────────────────────────┘
```

- `compose_style_prompt(style_id, style_prompt)`: 메인 생성 경로의 BASE+STYLE 결합 (`_get_style_prompt`/pipeline/agent가 사용). 변환계 프롬프트(`TRANSFORM_STYLE_IDS`: comment_summary, mindmap, chapter_split)는 BASE를 붙이지 않음
- `build_full_prompt(style_id, modifiers=None)`: BASE+STYLE(+모디파이어) 일괄 조합 (fusion 등). `create_content`에 modifiers를 따로 넘기는 경로에서는 이중 주입 방지를 위해 modifiers 생략
- 모디파이어 텍스트의 단일 소스는 `prompts/modifiers.py` (`config.STYLE_MODIFIERS`는 재export)
- 프롬프트는 지시(스타일)→입력(자막)→가변 지시 순서로 배치 — 프로바이더 프리픽스 캐싱 유지를 위해 가변 내용([현재 시간] 등)은 끝에 둠
- 파서 계약: blog_seo 메타 테이블 행(`**메타 설명**`/`**타겟 키워드**`/`**추천 URL**`)·FAQ(`**Q.**`/`A.`)·해시태그(`**태그**: #태그`), geo_seo의 한 줄 정의/구조화 데이터 표/엔티티 태그/`- ✓` 팩트/CTA_PRIMARY·SECONDARY는 `services/core/ai_metadata.py` 정규식과 1:1 — 프롬프트 출력 형식 수정 시 반드시 함께 확인
- `prompts/styles/comment_summary.py`: 병렬 댓글 요약 전용 프롬프트 (UI 비노출)

### 서비스 도메인 구조 (`services/`)

서비스는 도메인별 서브디렉토리로 구성됨. **루트에 직접 .py 파일 없음**.

```
services/
├── core/           # AI, 콘텐츠 생성, 파이프라인, 캐시 (6개)
├── analysis/       # 텍스트/NLP 분석 — 가독성, 구조, 문장, 감정 (95개)
├── seo/            # 검색 최적화 — 키워드, 메타, SERP, E-E-A-T (26개)
├── quality/        # 품질 검증 — QA, 표절, 팩트체크 (14개)
├── content/        # 콘텐츠 관리 — 인용, FAQ, 요약 (29개)
├── media/          # 미디어 — 썸네일, 이미지, 비디오, TTS (15개)
├── transcript/     # 자막/음성 — Whisper, 챕터, 번역 (6개)
├── export/         # 내보내기 — DOCX, EPUB, Google Docs (5개)
├── platform/       # 외부 플랫폼 — 웹훅, RSS, GitHub, SNS (10개)
├── data/           # 데이터/인프라 — Supabase, 스케줄, 알림 (28개)
├── agents/         # 멀티에이전트 파이프라인 (12개)
├── analytics/      # 분석 대시보드 (17개)
├── auth/           # 인증/OAuth (2개)
├── integrations/   # 외부 서비스 연동 — Slack, Discord (7개)
├── mcp/            # MCP Apps SDK + MCP 서버 (3개)
├── rag/            # RAG 벡터 스토어 (9개)
├── usage/          # 사용량 관리 (5개)
└── exceptions/     # 에러 처리
```

**import 패턴**: `from services.core import ai_service` 또는 `from services.core.ai_service import create_content`

### Frontend (Next.js — `frontend/`)

> 구 바닐라 JS 프론트엔드(`templates/`, `static/`)는 Next.js 전환 시 제거됨. 프론트엔드 작업은 전부 `frontend/`에서 한다.

- **스택**: Next.js 16 (App Router) + React 19 + TypeScript + Tailwind CSS v4 + shadcn/zustand/react-query
- **상태**: `frontend/stores/` (zustand — settingsStore, resultStore, uiStore). 구독은 셀렉터(`useStore((s) => s.field)`) 또는 `useShallow` 사용 — 스토어 전체 구독 금지 (불필요 리렌더)
- **API 래퍼**: `frontend/lib/api.ts` — Flask 백엔드 호출
- **결과 카드**: `frontend/components/result/ResultCard.tsx` + 서브컴포넌트 (무거운 것은 `dynamic()` 로드)
- **테마**: next-themes + Tailwind v4 (`frontend/app/globals.css`). 폰트(Pretendard CDN)는 비동기 로드 — `layout.tsx`에 동기 `<link rel="stylesheet">` 추가 금지 (렌더 블로킹)
- **PWA**: `frontend/public/sw.js` — 동일 출처 GET만 캐싱, MAX_ENTRIES 상한. 캐시 전략 변경 시 `CACHE_NAME` 버전 올릴 것

### Usage Decorators

```python
# 사용량 체크 + 성공 시 자동 차감 (단일 요청)
@require_usage
def generate(): ...

# 배치 처리: 데코레이터 없이 직접 UsageService.check_can_use() / .decrement() 호출
def generate_batch(): ...
```

## Key Patterns

### API 응답 형식
- 성공: `{"title": "...", "content": "...", "html": "...", "usage": {...}, "comment_summary_included": true/false}`
- 실패: `{"error": "메시지"}` (에러 접두사: `[인증 실패]`, `[사용량 초과]`, `[타임아웃]` 등)

### 스타일 시스템 (v4.0)

UI에 표시되는 15개 스타일: `blog_seo`, `summary`, `tutorial`, `qna`, `app_ideas`, `yozm_it`, `brunch_essay`, `naver_popular`, `sns_post`, `newsletter`, `show_notes`, `shorts_script`, `geo_seo`, `course`, `quiz`

내부 전용: `comment_summary` (병렬 댓글 요약용), `cited_summary` (타임스탬프 인용 모드, `enable_citations=true` 시), `chapter_split` (챕터 분할 전용), `mindmap` (마인드맵 변환)

전체 스타일 목록은 `prompts/styles/__init__.py`의 `STYLE_PROMPTS` dict가 단일 소스. 단일 생성 요청은 `routes/blog_routes.py`의 `_validate_style()`에서 내장 스타일을 정규화하고 커스텀 스타일 ID는 통과시킨다. 멀티 생성은 `routes/advanced_routes.py`에서 `current_app.config['STYLE_PROMPTS']` 기준으로 유효 스타일을 필터링한다. `config.py`의 `STYLE_OPTIONS`/`STYLE_TEMPERATURE`도 함께 갱신할 것.

### 추가 기능

**다중 출력 포맷**: DOCX (`POST /api/export/docx`, python-docx), PDF (프론트엔드 `window.print()`)

**SEO 메타데이터**: `blog_seo` 스타일 응답에 `seo` 필드 자동 포함 (`ai_service.extract_seo_metadata()`)

**GEO 메타데이터**: `geo_seo` 스타일 — AI 검색엔진 최적화 (citations, entity_tags, structured_data, key_facts)

**Shorts 클립**: `shorts_script` 스타일 — 60초 클립 3-5개 추출 (hook_text, script, timestamp)

**Ollama 로컬 LLM**: `OLLAMA_BASE_URL` 설정으로 API 키 없이 로컬 모델 사용

**Whisper 자막 폴백**: `WHISPER_ENABLED=true` 시 faster-whisper로 로컬 음성인식 (4번째 폴백)

**파이프라인 자동화**: `POST /api/pipeline` — 자막→생성→SEO 자동 진행 (SSE 실시간 진행률)

**팀 워크스페이스**: `services/workspace_service.py` — 워크스페이스 생성/초대/역할 관리 (Owner/Editor/Viewer)

**RAG 지식 참조**: `services/rag/` — ChromaDB 벡터 스토어, 파일 업로드 → 콘텐츠 생성 시 자동 주입

**웹훅 알림**: `services/webhook_service.py` — 생성 완료 시 POST (fire-and-forget, 1회 재시도)

**채널/재생목록 처리**: `POST /api/playlist-videos` — 채널/재생목록 URL → 영상 목록 추출 (YOUTUBE_API_KEY 필수)

**멀티포맷 리퍼포징**: `POST /api/generate-multi` — 1 URL × N 스타일 동시 생성 (사용량 1회 차감)

**상세도 프리셋**: `detail_level` 파라미터 (brief/standard/deep) — temperature 오프셋 + max_tokens 배율 적용 (`config.DETAIL_PRESETS`)

**챕터 자동 분할**: `/generate` 응답의 `chapters[]` 필드 — AI가 자막을 주제별 챕터로 분할 (`chapter_service.py`)

**인라인 AI 편집**: `POST /api/inline-edit` — 텍스트 선택 영역만 부분 재생성 (축약/확장/톤변경/번역)

**QA 게이트**: `POST /api/qa-check` — 발행 전 품질 검증 (금칙어, 섹션 구조, 중복, 링크 검증)

**운영 대시보드**: `GET /api/admin/dashboard` — 7일 집계 (생성 수, 성공률, 스타일 분포, 일별 사용량)

**다중 내보내기 포맷**: `POST /api/export/markdown`, `/api/export/txt`, `/api/export/zip` (DOCX+MD+TXT+meta.json 패키지)

**콘텐츠 승인 플로우**: `ContentApprovalService` — 상태 머신 (draft→review→approved→published/rejected)

**자막 소스 품질 메타**: `source_meta` (source_type, quality_score, is_auto) — 4단계 폴백별 품질 정보

**3단 뷰 모드**: ViewModeSelector — Compact(100자 미리보기)/Full(기존)/Timeline(챕터 연동)

**프로바이더 검증**: `POST /api/providers/validate` — API 키 소량 토큰 호출 유효성 테스트

**소스 인용 모드**: `enable_citations=true` → 모든 주장에 [MM:SS] 타임스탬프 인용 + YouTube 링크 변환

**텍스트 붙여넣기 학습**: URL 없이 `content` 필드로 텍스트 직접 입력 → 동일 생성 파이프라인 (`config.DIRECT_TEXT_MAX_CHARS` 상한, `source_type: 'text'`)

### 새 스타일 추가 방법
1. `prompts/styles/` 디렉토리에 새 파일 생성 (예: `new_style.py`)
2. `prompts/styles/__init__.py`에서 import 및 `STYLE_PROMPTS`에 추가
3. `config.py`의 `STYLE_OPTIONS`에 메타데이터 추가
4. `frontend/lib/constants.ts`의 `STYLE_OPTIONS`에 UI 라벨/이모지/설명 추가
5. `frontend/app/page.tsx`의 스타일 그리드 렌더링을 확인하고, 필요하면 모바일/설정/필터 등 `STYLE_OPTIONS` 소비 컴포넌트도 갱신

### 지원 모델 (LiteLLM 형식)

| 프로바이더 | 모델 ID | 특이사항 |
|-----------|---------|---------|
| Gemini (기본) | `gemini/gemini-3-flash-preview` | `reasoning_effort="minimal"` |
| Gemini | `gemini/gemini-2.5-flash-lite-preview-09-2025` | reasoning_effort 미지원 |
| DeepSeek | `deepseek/deepseek-chat`, `deepseek/deepseek-reasoner` | |
| Zhipu AI | `zhipuai/GLM-4.7`, `zhipuai/GLM-4.5-Air` | OpenAI 호환 API 사용 |
| Ollama (로컬) | `ollama_chat/llama3.2`, `ollama_chat/mistral`, `ollama_chat/gemma2` | API 키 불필요, OLLAMA_BASE_URL 설정 |

- 모델 추가 시 `config.py`의 `SUPPORTED_PROVIDERS`에 `price_input`, `price_output` 필수

### 스타일 프롬프트 규칙 (`prompts/styles/`)

모든 스타일 프롬프트에 공통 적용:
- **금지 표현**: 놀라운, 혁신적, 획기적, 최고의, 게임체인저, 압도적, 경이로운, 드디어, 탁월한, 인상적, 뛰어난, 강력한
- **댓글 활용**: `[댓글]` 섹션이 입력에 없으면 시청자 반응 절대 언급 금지
- **원칙**: 자막에 있는 정보만 사용 (창작/추측 절대 금지)

### 모디파이어 (3개 지원)

| 모디파이어 | 값 | 설명 |
|-----------|-----|------|
| `length` | short/medium/long | 글 길이 (500-800 / 1000-1500 / 2000-3000자) |
| `writing_style` | conversational/explanatory/casual/expert | 문체 |
| `language` | ko/en/ja | 출력 언어 (한국어/영어/일본어) |

기본값: `length: medium`, `writing_style: conversational`, `language: ko`.

### AI 생성 파라미터 튜닝 (`config.py`)

**스타일별 temperature** (`STYLE_TEMPERATURE`):
- 정밀형 0.5: `summary`, `tutorial`, `qna`, `show_notes`, `quiz`, `comment_summary`
- 균형형 0.7: `blog_seo`, `yozm_it`, `app_ideas`, `newsletter`
- 창의형 0.8~0.85: `sns_post`(0.8), `brunch_essay`(0.85), `naver_popular`(0.85)

**길이별 max_tokens** (`LENGTH_MAX_TOKENS`, 한국어 2~3토큰/자 + 마크다운 오버헤드 ~40% 감안):
- `short`: 4,000 (약 1,300~2,000자)
- `medium`: 8,000 (약 2,600~4,000자)
- `long`: 16,000 (약 5,300~8,000자)

> **주의**: `ai_service.create_content()`에 `style_id` 파라미터를 반드시 전달해야 temperature가 적용됨. 누락 시 기본 0.7.

### 병렬 댓글 요약

`/generate` 엔드포인트에서 댓글이 있으면 `ThreadPoolExecutor(max_workers=2)`로 메인 콘텐츠와 댓글 요약을 병렬 생성 후 `_combine_results()`로 병합. 댓글 요약 실패 시 graceful degradation (메인 결과만 반환).

## Testing

### 단위 테스트 - Supabase 인증 우회 (필수 패턴)

```python
@patch('services.supabase_service.is_supabase_enabled', return_value=False)
def test_example(self, mock_enabled):
    # 테스트 코드
```

### E2E 테스트 (`tests/e2e/`)

Playwright 기반. `playwright.config.ts`에서 webServer가 Flask 앱 자동 실행 (Supabase 비활성화 상태).

**테스트 그룹:** `no-auth-chromium`, `content-generation`, `batch-generation`, `authenticated-tests`, `error-handling`, `performance`

**Fixtures (`fixtures/test-fixtures.ts`):**
- `mainPage.goto()`: 페이지 이동 + 온보딩 모달 자동 닫기
- `urlInput.addUrl(url)`: URL 입력 후 Enter
- `contentGenerator.clickGenerate()`: `#run-analysis-btn` 클릭

**자주 발생하는 테스트 오류:**
- `strict mode violation`: 더 구체적인 선택자 사용
- 서버 타임아웃: `--workers=1`로 실행
- E2E 병렬 실행 시 Flask 서버 충돌 → 항상 `--workers=1` 권장

## Configuration

`.env.example` → `.env` 복사. 상세 환경변수 설명은 `README.md` 참조.

**필수**: AI Provider API 키 최소 하나 (`GEMINI_API_KEY`, `DEEPSEEK_API_KEY`, `ZHIPUAI_API_KEY` 등). API 키가 설정된 프로바이더만 UI에 표시.

**선택**: `SUPADATA_API_KEY` (자막 마지막 폴백 - 유료), `YOUTUBE_API_KEY` (댓글), `SUPABASE_URL` + `SUPABASE_ANON_KEY` (클라우드 저장), `YT_HTTP_PROXY` / `YT_HTTPS_PROXY` (차단 우회), `SCHEDULER_ENABLED=false` (APScheduler 기동 끄기 — 테스트/스크립트용, 기본 true)

## Supabase 설정

### 테이블 (ie_ 접두사)

`ie_usage` (일일 사용량), `ie_histories` (분석 히스토리), `ie_api_keys` (사용자별 API 키), `ie_custom_styles` (커스텀 프롬프트), `ie_admins` (관리자 목록)

### 뷰 (관리자용)

`ie_usage_with_email`, `ie_histories_with_email`

### RPC 함수

```sql
SELECT decrement_usage_safe('user-uuid');
-- 반환: {"success": true, "new_count": 19} 또는 {"success": false, "reason": "no_usage_left"}
```

### 스키마: `supabase/schema.sql`을 Supabase SQL Editor에서 실행

## Security

- XSS 방지: HTML 콘텐츠 렌더링 시 DOMPurify로 sanitize (`frontend/components/result/ResultCard.tsx` 등)
- 에러 응답 시 내부 정보(traceback, DB 연결 정보 등) 노출 차단: `_handle_error_response()`에서 필터링

### autoresearch 정리 (2026-03-18)

176라운드 autoresearch 결과 중 불필요 코드 정리 완료:
- 제거됨: 미사용 응답 필드 14개, Dead Code 함수 9개, API 엔드포인트 12개, 테스트 49개
- 현재 테스트: 4,278 passed
- 제거된 엔드포인트: `/api/arxiv/*`, `/api/health/detailed`, `/api/github/readme`, `/api/styles`, `/api/cache/stats`, `/api/cache/purge`, `/api/content/stats`, `/api/version`, `/api/prompts/info`, `/api/rate-limit/status`, `/api/admin/system-info`
- 제거된 함수: `get_citation_stats`, `generate_numbered_toc`, `generate_ab_hooks`, `suggest_fixes`, `get_citation_density_grade`, `generate_themed_card`, `shuffle_quiz`, `generate_mixed_difficulty_quiz`, `analyze_debate_balance`
- 이 엔드포인트/함수를 다시 추가하려면 프론트엔드 소비 코드도 함께 작성할 것

### dead-code 제거 batch 2 (2026-07-05)

`plans/dead-code-audit-2026-06-10.md`의 `routes/advanced_routes.py` 9건은 이미 PR #81(Dep-2 batch 1)에서 라우트 자체가 제거되어 있었음(재검증 완료). 이번 배치는 그 라우트들이 유일하게 호출하던 백엔드 서비스 `services/finetune/`(data_collector, dataset_builder, reward_model)가 완전히 고아 상태임을 확인하고 제거:
- 제거된 서비스: `services/finetune/` 패키지 전체 (data_collector.py, dataset_builder.py, reward_model.py)
- 제거된 테스트: `tests/test_data_collector.py`, `tests/test_dataset_builder.py`, `tests/test_reward_model.py`

### dead-code 제거 batch 3 (2026-07-05)

`plans/dead-code-audit-2026-06-10.md` 잔여 그룹(payment/marketplace 제외)을 엔드포인트 단위 재검증 후 제거:
- 제거된 엔드포인트: `POST/GET /api/content`(create/list), `GET/PATCH/DELETE /api/content/<item_id>`, `/api/content/bulk`, `/api/content/<item_id>/{clone,archive,unarchive,lock*,expiry,fields*,links,seo-check,share,comments*}`, `/api/content/{archive,media*,fields,links/<id>,share/<token>,workflows*,roles*}`, `/api/content/{backup,export/<fmt>,import/<fmt>}` (F8 콘텐츠 관리/라이브러리 기능군 전체), `POST /api/rag/graph/search/local`, `GET /api/rag/graph/search/global`, `POST /api/rag/multimodal/{detect-type,ingest,query}`
- 제거된 파일: `routes/content_mgmt_routes.py`, `routes/content_mgmt/`(backup_io.py, _shared.py, __init__.py) 전체, `services/rag/multimodal_rag.py`
- 제거된 서비스: `services/data/{content_library,archive,lock,expiry,custom_field,workflow,rbac,backup,data_migration,trash}_service.py`, `services/media/media_library_service.py`, `services/seo/{link_manager,seo_checklist}_service.py`, `services/platform/share_service.py`, `services/content/comment_service.py`
- 제거된 메서드: `GraphRAGEngine.global_search` (`services/rag/graph_rag_engine.py`) — `local_search`/`ingest`는 유지 (build_context는 2026-07-05 고아 정리 c29b에서 후속 제거)
- 이 엔드포인트/서비스를 다시 추가하려면 프론트엔드 소비 코드도 함께 작성할 것
- `app.py`에서 `content_mgmt_bp` 블루프린트 등록 제거
- 재검증 중 `routes/integrations/{automation,content_workspace,imports,misc}.py`, `routes/utility/{external,feedback_quality,operations}.py`, `routes/blog_routes.py`의 감사 목록 대상 엔드포인트는 이미 다른 사이클에서 삭제되어 있었음(파일 자체는 다른 활성 기능으로 재구성됨) — 코드 변경 없음, 문서만 갱신
- 남은 항목이었던 auth 그룹 + openapi는 batch 4(아래, 2026-07-05)에서 제거 완료

### 고아 정리 c29b (2026-07-05)

- 제거: `frontend/components/library/BulkActions.tsx` (import 0, 소비 대상 `/api/content/bulk`는 batch 3에서 백엔드 제거됨), `GraphRAGEngine.build_context` (외부 호출자 0 — 유일 소비처였던 graph/search 라우트가 batch 3에서 제거됨) + 전용 테스트 3건
- 의도적 유지: `GraphRAGEngine.local_search` — 이 제거로 프로덕션 소비자 0이 되지만, `graph/ingest` 라우트 유지판정 + 제품 비전 기둥 2(위키 그래프)의 소비 예정 경로라 보존 (다음 정리 사이클에서 재판정)

### dead-code 제거 batch 4 (2026-07-05, dev-loop cycle 29a)

`plans/dead-code-audit-2026-06-10.md`의 auth 그룹 + openapi를 캐스케이드 포함 일괄 제거:
- 제거된 엔드포인트: `GET /api/admin/{check,users,stats,contents,contents/<report_id>}`, `POST /api/admin/users/<user_id>/reset` (admin.py 6건), `GET/PUT/DELETE /api/user/history*`, `PUT /api/user/{profile,password}`, `DELETE /api/user/account` (history_account.py 7건), `GET /api/admin/audit-logs`, `GET/POST /api/user/usage-alerts*`, `POST/GET /api/sso/<workspace_id>/{config,login,disable,callback}` (misc.py 9건), `GET/POST/DELETE /api/user/{keys,styles}*`, `GET /api/user/usage` (user_settings.py 6건), `GET /api/auth/{status,config}` (auth_routes.py 2건), `GET /api/openapi.json`, `GET /api/docs` (integrations/misc.py 2건)
- 제거된 파일: `routes/auth/{admin,history_account,user_settings}.py`, `services/usage/usage_alert_service.py`, `services/auth/sso_service.py`, `services/data/audit_log_service.py`, `services/data/openapi_service.py`, `services/data/{content_admin_facade,account_admin_facade,api_key_storage_facade,custom_style_facade}.py`
- 제거된 함수: `services/data/supabase_admin/admin_queries.py`의 `get_admin_permissions`/`get_all_users_usage`/`reset_user_usage`/`get_usage_stats`/`get_all_contents`/`get_content_detail` (is_admin은 usage_service.py가 계속 사용하므로 유지), `services/data/supabase_service.py`의 `delete_user_account`/`update_user_profile`/`update_user_password`/`save_api_keys`/`get_api_keys`/`save_custom_style`/`get_custom_styles`/`delete_custom_style`
- `routes/auth/misc.py`는 스타일 메모리/스니펫/활동피드 라우트만 남기고 유지(프론트 소비자 있음), `routes/integrations/misc.py`는 앱 피드백/OAuth 2.0 라우트만 남기고 유지
- 이 엔드포인트/서비스를 다시 추가하려면 프론트엔드 소비 코드도 함께 작성할 것

### dead-code 제거 batch 5 — payment/marketplace (2026-07-05, dev-loop cycle 30b)

`plans/dead-code-audit-2026-06-10.md`에서 유일하게 남아있던 payment/marketplace 그룹을 엔드포인트 단위로 재검증(1개월 경과로 실제 라우트 수가 감사 시점과 달라짐: payment_routes.py는 29개 라우트(고유 경로 26개), crypto.py/paddle.py는 각 3개, marketplace_routes.py는 3개)한 뒤 전량 제거. 프론트엔드에 `frontend/components/billing/*`, `frontend/components/marketplace/*`, `ApiKeyManager.tsx`가 각 엔드포인트를 호출하는 코드는 있었으나, 이 컴포넌트들 자체가 앱의 어느 페이지에서도 import되지 않는 고아였음(진입점 없음, `.env.example`에 Stripe/Paddle/Coinbase 설정 문서화도 없음) — Stripe/Coinbase/Paddle webhook 3개도 프로바이더가 미설정이라 트리거 불가능한 죽은 코드로 판정.
- 제거된 엔드포인트: `/api/credits/{balance,purchase,plans}`, `/api/payment/{checkout,webhook}`, `/api/subscription`, `/api/subscription/{upgrade,cancel}`, `/api/trial/{start,status}`, `/api/usage/my-usage`, `/api/referral/{info,apply}`, `/api/keys`, `/api/keys/<key_id>`, `/api/invoices`, `/api/invoices/<invoice_id>/pay`, `/api/coupons`, `/api/coupons/{validate,redeem}`, `/api/team-billing/<team_id>`, `/api/team-billing/<team_id>/members`, `/api/billing/{setup,consume,summary,reset-monthly}` (payment_routes.py 29건), `/api/crypto/charge`, `/api/crypto/charge/<charge_id>`, `/api/crypto/webhook` (crypto.py 3건), `/api/paddle/{status,webhook}`, `/api/paddle/subscription/<subscription_id>` (paddle.py 3건), `GET/POST /api/marketplace`, `POST /api/marketplace/<template_id>/download` (marketplace_routes.py 3건)
- 제거된 파일: `routes/payment_routes.py`, `routes/payment/`(crypto.py, paddle.py, _shared.py, __init__.py) 전체, `routes/marketplace_routes.py`, `services/payment/` 패키지 전체(stripe/subscription/trial/coupon/invoice/paddle/crypto/team_billing/hybrid_billing_service.py + __init__.py), `services/platform/marketplace_service.py`, `services/platform/referral_service.py`, `services/data/api_key_service.py`
- 제거된 프론트엔드: `frontend/components/billing/`(CreditBalance, PricingPage, ReferralCard, SubscriptionManager, UsageDashboard, CouponInput, UsageAlert) 전체, `frontend/components/marketplace/MarketplaceBrowser.tsx`, `frontend/components/settings/ApiKeyManager.tsx` — 전부 import 0
- 제거된 테스트: `tests/test_{coupon,crypto,hybrid_billing,invoice,marketplace,paddle,stripe,subscription,team_billing,trial,api_key,referral}_service.py`, `tests/test_{crypto,paddle,hybrid_billing,payment}_routes*.py`
- `app.py`에서 `routes.payment_routes` import + `marketplace_bp` 블루프린트 등록 제거
- 서비스 도메인 구조 표에서 `payment/` 행 제거(디렉토리 자체 삭제)
- 이 엔드포인트/서비스를 다시 추가하려면 프론트엔드 소비 코드(결제 진입 페이지)와 `.env.example` 설정 문서화를 함께 작성할 것

### 고아 정리 c31a (2026-07-05)

- 제거: `services/data/supabase_service.py`의 legacy history 조회/수정/즐겨찾기/삭제 헬퍼(`get_histories`/`update_history`/`toggle_favorite`/`delete_history`)와 전용 테스트 — PR #113 이후 프로덕션 호출자 0.
- 제거: `/api/folders*` 백엔드 라우트와 인메모리 `services/data/folder_service.py`, 전용 라우트/서비스 테스트 — 유일 프론트 소비자 `FolderTree.tsx` 삭제 이후 `frontend/` 호출 0.
- 제거: `services/usage/credit_plan.py`의 `get_plan_credits`/`get_plan_features` 및 export/전용 테스트 — PR #114 이후 결제 라우트 소비자 0, 사용량/크레딧 핵심 로직은 유지.
- 제거: `config.py`의 `STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET` 설정 블록 — config 소비자 0.
- 변경: `app.py` CSRF 우회 조건에서 `X-API-Key` 헤더만 제거, `Authorization` 우회는 유지 — `/api/keys` 발급 라우트 삭제로 IE 발급 API 키 경로 없음.

### dead-code 제거 batch 6 — Dep-7 배치 B (2026-07-05)

`plans/dep7-seo-geo-split-plan.md` §4 배치 B 실행. 이미 생성된 콘텐츠의 SEO 점수/제안을 반환하는 3단 죽은 체인(서비스→라우트→프론트 래퍼)을 재검증 후 제거:
- 제거된 서비스: `services/agents/seo_optimize_agent.py`(`optimize_seo()`) 전체
- 제거된 라우트: `routes/utility/feedback_quality.py`의 `POST /api/seo-optimize`(`api_seo_optimize`) — 파일 내 다른 라우트(피드백/팩트체크/표절/가독성/감정흐름/NPS)는 그대로 유지
- 제거된 프론트: `frontend/lib/api.ts`의 `seoOptimize()` 래퍼 + `SeoOptimizeResponse` import, `frontend/lib/types/api.ts`의 `SeoOptimizeResponse` 타입
- 제거된 테스트: `tests/test_seo_optimize_agent.py`(파일 전체), `tests/test_utility_routes.py`의 `_CONTENT_ENDPOINTS` 목록·`simple_services` 서브테스트 중 `/api/seo-optimize` 케이스만 삭제(파일 자체는 다른 분석 엔드포인트 테스트가 있어 유지)
- 이 3단 모두 재검증 결과 프로덕션/프론트 어디서도 호출자가 없었음(`services/agents/seo_agent.py`의 활성 `SEOAgent`와는 다른 파일이며, `services/seo/`(Dep-7 배치 A 대상)와도 무관)
- 이 엔드포인트/서비스를 다시 추가하려면 프론트엔드 소비 코드도 함께 작성할 것
- 스킵: 없음.

### dead-code 제거 batch 6 — Dep-7 배치 A (2026-07-05)

`plans/dep7-seo-geo-split-plan.md` §4 배치 A에 따라 프로덕션 import 0으로 재검증된 `services/seo/` 고아 분석 서비스 24개와 전용 테스트 24개를 제거.
- 제거된 서비스: `aeo_optimizer_service`, `anchor_text_service`, `cannibalization_service`, `competitor_analysis_service`, `content_freshness_indicator_service`, `content_performance_predictor_service`, `cta_optimizer_service`, `eeat_analyzer_service`, `engagement_scorer_service`, `entity_coverage_service`, `freshness_monitor_service`, `headline_optimizer_service`, `image_seo_auditor_service`, `internal_link_service`, `keyword_density_service`, `keyword_stuffing_detector_service`, `meta_description_quality_service`, `schema_opportunity_service`, `search_intent_service`, `serp_feature_service`, `title_tag_length_service`, `topic_cluster_service`, `topic_gap_service`, `url_health_checker_service`.
- 제거된 테스트: 위 24개 서비스의 `tests/test_<name>.py` 전용 테스트 전체.
- agent 계층 정리: `agent/prompts/roles.py`의 SEO_PROMPT에서 삭제된 도구명(`analyze_density`, `analyze_search_intent`, `analyze_eeat`, `analyze_aeo`, `analyze_serp_features`, `find_link_opportunities`, `cluster_contents`)을 제거하고, `agent/core.py`의 `PARALLEL_SAFE_TOOLS`에서 `check_keyword_density`를 제거(이 이름은 실제 등록된 적 없는 유령 항목 — keyword_density_service의 실제 도구명은 `analyze_density`였음. 무해한 스테일 항목 정리).
- 스킵: 없음. `agent/tools/seo_tools.py`는 `services/seo/` 디렉터리 pkgutil 스캔 방식이라 하드코딩 수정 없음.
- `search_service.py`, `seo_metadata_service.py`, SEO/GEO 스타일 계열은 사람-gated 배치 C/D 대상으로 유지.
