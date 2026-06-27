# Insight Engine

YouTube 영상 URL 하나로 14가지 스타일의 고품질 콘텐츠를 자동 생성하는 AI 콘텐츠 엔진.
5개 AI 프로바이더(Gemini, DeepSeek, Zhipu GLM, Ollama, OpenRouter) 통합, 다국어(한/영/일) 지원, RAG 지식 참조, MCP 자동 발행, 팀 워크스페이스까지.

Flask + Next.js 풀스택 · LiteLLM 멀티프로바이더 · 323개 서비스 · 1,659개 테스트(99.94% pass)

---

## Features

### Core
- **14가지 출력 스타일** — 블로그+SEO, 요약, 튜토리얼, Q&A, 앱 아이디어, 요즘IT, 브런치, 네이버 인기글, SNS, 뉴스레터, 쇼노트, Shorts 클립, GEO(AI검색 최적화), AI 코스
- **5개 AI 프로바이더** — Gemini, DeepSeek, Zhipu GLM, Ollama(로컬), OpenRouter(2600+ 모델)
- **다국어 출력** — 한국어, 영어, 일본어
- **4단계 자막 폴백** — youtube-transcript-api → watch 페이지 파싱 → Supadata API → Whisper 로컬 음성인식

### Content Generation
- **배치 처리** — 최대 10개 URL 동시 분석
- **멀티스타일** — 1 URL × N 스타일 동시 생성 (사용량 1회 차감)
- **캠페인 팩** — 블로그+SNS+뉴스레터 묶음 자동 생성
- **퓨전 분석** — 다중 소스 교차 분석 콘텐츠
- **파이프라인 자동화** — 자막 추출 → 생성 → SEO 최적화 (SSE 실시간 진행률)
- **소스 인용 모드** — 모든 주장에 [MM:SS] 타임스탬프 인용 + YouTube 링크 변환
- **챕터 자동 분할** — AI가 자막을 주제별 챕터로 분할
- **댓글 병렬 분석** — 메인 콘텐츠와 댓글 요약 동시 생성

### Post-Processing
- **플랫폼 리라이트** — Twitter/LinkedIn/Instagram/Threads 형식 변환
- **인라인 AI 편집** — 텍스트 선택 영역 부분 재생성 (축약/확장/톤변경/번역)
- **마인드맵** — 콘텐츠 → 마인드맵 마크다운 변환
- **QA 게이트** — 발행 전 금칙어/구조/중복/링크 품질 검증

### Publishing & Collaboration
- **MCP 자동 발행** — Naver Blog, WordPress 플러그인
- **예약 캘린더** — APScheduler 기반 예약 발행 + 캘린더 UI
- **발행 큐** — 인메모리 큐 + 재시도 정책 (3회, 지수 백오프)
- **팀 워크스페이스** — 멤버 관리 (Owner/Editor/Viewer) + 콘텐츠 승인 플로우
- **채널 모니터링** — YouTube 채널 신규 업로드 자동 감지 (30분 폴링)

### Intelligence
- **RAG 지식 참조** — ChromaDB 벡터 스토어, 파일 업로드 → 생성 시 자동 주입
- **웹 검색 보강** — Tavily API로 자막 내용을 웹 검색으로 보강
- **멀티에이전트** — Research → Writer → Editor → SEO 파이프라인
- **95개 텍스트 분석 서비스** — 가독성, 구조, 감정, NLP 분석

### Export & Integration
- **다중 내보내기** — DOCX, PDF, Markdown, TXT, ZIP(전체 패키지)
- **웹훅 알림** — 생성 완료 시 n8n/Make/Zapier 연동
- **외부 서비스** — Slack, Discord, RSS, GitHub 연동
- **GraphQL API** — 유연한 쿼리 지원

---

## Quick Start

### 요구사항
- Python 3.8+
- Node.js 18+
- AI Provider API 키 최소 하나

### 설치

```bash
git clone https://github.com/inbeomheo/insight-engine.git
cd insight-engine

# 가상환경 (권장)
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux

# 의존성
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### 환경변수

```bash
cp .env.example .env
```

`.env`에 최소 하나의 AI API 키를 설정하세요:

```env
# 최소 하나 필수 — 설정된 프로바이더만 UI에 표시
GEMINI_API_KEY=AIza...          # Google Gemini (기본 권장)
DEEPSEEK_API_KEY=sk-...         # DeepSeek
ZAI_API_KEY=...                 # Zhipu AI (GLM)
OLLAMA_BASE_URL=http://localhost:11434  # Ollama (로컬, API 키 불필요)
OPENROUTER_API_KEY=sk-or-...    # OpenRouter (2600+ 모델)

# 선택
YOUTUBE_API_KEY=...             # 댓글 수집
SUPADATA_API_KEY=...            # 자막 백업 서비스
TAVILY_API_KEY=...              # 웹 검색 보강
```

> 전체 환경변수 목록은 [.env.example](.env.example) 참조

### 실행

두 서버 모두 실행해야 합니다:

```bash
# 터미널 1 — 백엔드
python app.py                    # → http://localhost:5001

# 터미널 2 — 프론트엔드
cd frontend && npm run dev       # → http://localhost:3000
```

브라우저에서 **http://localhost:3000** 접속

---

## Architecture

```
┌───────────────────────────┐     ┌─────────────────────────┐
│  Next.js 16 Frontend      │────▶│  Flask Backend           │
│  React 19 + Tailwind v4   │     │  Port 5001               │
│  Zustand + TanStack Query │     │                           │
│  Port 3000                │◀────│  LiteLLM Multi-Provider  │
└───────────────────────────┘     └────────┬────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
             ┌─────────────┐      ┌──────────────┐      ┌──────────────┐
             │ YouTube API  │      │ AI Providers  │      │ Supabase     │
             │ Transcript   │      │ Gemini,DeepSeek│     │ Auth, DB     │
             │ Comments     │      │ GLM,Ollama,OR │      │ Usage        │
             └─────────────┘      └──────────────┘      └──────────────┘
```

### 프로젝트 구조

```
insight-engine/
├── app.py                         # Flask 진입점 (포트 5001)
├── config.py                      # 프로바이더/스타일/모디파이어 설정
├── requirements.txt               # Python 의존성
├── .env.example                   # 환경변수 템플릿
│
├── routes/                        # API 라우트 (13개 모듈)
│   ├── blog_routes.py             # 콘텐츠 생성, 파이프라인, MCP, 예약
│   ├── auth_routes.py             # 인증, API 키, 사용량, 워크스페이스
│   ├── advanced_routes.py         # 멀티스타일, 퓨전, 리라이트, QA
│   ├── export_routes.py           # DOCX/MD/TXT/ZIP 내보내기
│   ├── utility_routes.py          # 헬스체크, 프로바이더, 캐시
│   ├── analytics_routes.py        # 분석 대시보드
│   ├── graphql_routes.py          # GraphQL API
│   ├── payment_routes.py          # 결제/구독
│   └── ...
│
├── services/                      # 비즈니스 로직 (23개 도메인, 323개 파일)
│   ├── core/                      # AI, 콘텐츠, 파이프라인, 캐시
│   ├── analysis/                  # 텍스트/NLP 분석 (95개)
│   ├── seo/                       # SEO 최적화 (28개)
│   ├── quality/                   # QA 검증 (14개)
│   ├── content/                   # 인용, 리라이트, FAQ (27개)
│   ├── media/                     # 이미지, TTS, 썸네일 (15개)
│   ├── transcript/                # Whisper, 챕터, 번역 (6개)
│   ├── agents/                    # 멀티에이전트 파이프라인 (12개)
│   ├── analytics/                 # 분석 대시보드 (17개)
│   ├── rag/                       # ChromaDB 벡터 스토어 (9개)
│   ├── mcp/                       # MCP 플러그인 (6개)
│   ├── platform/                  # 웹훅, RSS, 채널 모니터링 (11개)
│   ├── data/                      # Supabase, 스케줄, 알림 (33개)
│   ├── integrations/              # Slack, Discord (7개)
│   ├── payment/                   # 결제/구독 (9개)
│   ├── export/                    # DOCX, EPUB (5개)
│   ├── auth/                      # 인증/OAuth (2개)
│   ├── usage/                     # 사용량 관리 (5개)
│   ├── finetune/                  # AI 파인튜닝 (3개)
│   └── exceptions/                # 에러 처리
│
├── prompts/                       # 프롬프트 시스템 v3.4
│   ├── base.py                    # 기본 프롬프트 (Chain-of-Thought)
│   └── styles/                    # 14개 UI 스타일 + 4개 내부 스타일
│
├── frontend/                      # Next.js 16 + Tailwind v4 + shadcn
│   ├── app/                       # App Router 페이지
│   ├── components/                # React 컴포넌트
│   ├── hooks/                     # 커스텀 훅
│   ├── stores/                    # Zustand 상태 관리
│   └── lib/                       # API, 타입, 유틸
│
├── tests/                         # 271개 단위 테스트 + E2E
│   ├── test_*.py                  # pytest 단위 테스트
│   ├── e2e/                       # Playwright E2E
│   └── load/                      # 부하 테스트
│
└── supabase/schema.sql            # DB 스키마
```

---

## Supported Models

| Provider | Models | Notes |
|----------|--------|-------|
| **Gemini** (기본) | gemini-3.1-flash-lite | reasoning_effort 지원 |
| **DeepSeek** | deepseek-chat (V3), deepseek-reasoner (R1) | |
| **Zhipu AI** | GLM-4.7, GLM-4.5-Air | OpenAI 호환 API |
| **Ollama** (로컬) | llama3.2, mistral, gemma2 | API 키 불필요 |
| **OpenRouter** | 2600+ 모델 (Claude, GPT, Llama 등) | 단일 키로 모든 모델 접근 |

---

## Styles

| Style | Description |
|-------|-------------|
| Blog+SEO | 검색 최적화 블로그 포스트 |
| Summary | 핵심 요약 |
| Tutorial | 단계별 튜토리얼 |
| Q&A | 질문-답변 형식 |
| App Ideas | 앱/서비스 아이디어 도출 |
| YozmIT | IT 미디어 스타일 |
| Brunch | 에세이/칼럼 |
| Naver Popular | 네이버 인기글 스타일 |
| SNS Post | 소셜 미디어용 |
| Newsletter | 이메일 뉴스레터 |
| Show Notes | 팟캐스트 쇼노트 |
| Shorts Clip | 60초 Shorts 스크립트 (3-5개 클립) |
| GEO | AI 검색엔진 최적화 (citations, entity tags) |
| AI Course | 교육 코스 콘텐츠 |

각 스타일은 독립 프롬프트 + 최적화된 temperature/max_tokens 설정.

---

## API

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate` | POST | 단일 URL 콘텐츠 생성 |
| `/generate-batch` | POST | 다중 URL 배치 (최대 10개) |
| `/api/generate-multi` | POST | 1 URL × N 스타일 동시 생성 |
| `/api/generate-campaign` | POST | 캠페인 팩 생성 |
| `/api/pipeline` | POST | 파이프라인 자동화 (SSE) |
| `/api/rewrite` | POST | 플랫폼별 리라이트 |
| `/api/inline-edit` | POST | 인라인 AI 편집 |

### Content Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mindmap` | POST | 마인드맵 생성 |
| `/api/qa-check` | POST | QA 게이트 검증 |
| `/api/transcript/<id>` | GET | 자막 워크스페이스 |
| `/api/export/docx` | POST | DOCX 내보내기 |
| `/api/export/markdown` | POST | Markdown 내보내기 |
| `/api/export/zip` | POST | ZIP 패키지 (전체 포맷) |

### Platform & Publishing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mcp/plugins` | GET | MCP 플러그인 목록 |
| `/api/mcp/publish` | POST | MCP 플러그인 발행 |
| `/api/schedule` | POST/GET/DELETE | 예약 발행 관리 |
| `/api/publish-queue` | POST/GET | 발행 큐 관리 |
| `/api/workspaces` | GET/POST | 워크스페이스 관리 |
| `/graphql` | GET/POST | Basic Auth edge 뒤에서 제공되는 GraphQL API |
| `/graphql/schema` | GET | GraphQL SDL schema |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/providers` | GET | 사용 가능한 AI 목록 |
| `/api/providers/validate` | POST | API 키 유효성 검증 |
| `/api/ollama/health` | GET | Ollama 상태 확인 |
| `/health` | GET | liveness 상태 확인 |
| `/ready` | GET | Redis/app_data/backup 등 runtime readiness 확인 |
| `/api/knowledge/upload` | POST | RAG 문서 업로드 |
| `/api/admin/dashboard` | GET | 운영 대시보드 |

---

## Environment Variables

### AI Provider Keys (최소 하나 필수)

| Variable | Provider | Get Key |
|----------|----------|---------|
| `GEMINI_API_KEY` | Google Gemini | [aistudio.google.com](https://aistudio.google.com/apikey) |
| `DEEPSEEK_API_KEY` | DeepSeek | [platform.deepseek.com](https://platform.deepseek.com/api_keys) |
| `ZAI_API_KEY` | Zhipu AI (GLM) | [open.bigmodel.cn](https://open.bigmodel.cn/usercenter/apikeys) |
| `OLLAMA_BASE_URL` | Ollama (로컬) | `http://localhost:11434` |
| `OPENROUTER_API_KEY` | OpenRouter | [openrouter.ai](https://openrouter.ai/keys) |
| `OPENAI_API_KEY` | OpenAI | [platform.openai.com](https://platform.openai.com/api-keys) |
| `ANTHROPIC_API_KEY` | Anthropic | [console.anthropic.com](https://console.anthropic.com/settings/keys) |

### Optional

| Variable | Description |
|----------|-------------|
| `YOUTUBE_API_KEY` | YouTube 댓글 수집 |
| `SUPADATA_API_KEY` | 자막 백업 서비스 |
| `TAVILY_API_KEY` | 웹 검색 보강 |
| `SUPABASE_URL` + `SUPABASE_ANON_KEY` | 클라우드 DB/인증 |
| `WHISPER_ENABLED` | Whisper 자막 폴백 (`true`/`false`) |
| `RAG_ENABLED` | RAG 지식 참조 (`true`/`false`) |
| `WEBHOOK_URL` + `WEBHOOK_ENABLED` | 웹훅 알림. production에서 활성화하거나 URL을 설정하면 HTTPS public URL이어야 함 |
| `AUTOMATION_WEBHOOK_SECRET` | Zapier/Make/IFTTT inbound 호출용 `X-Insight-Webhook-Secret` |
| `TELEGRAM_BOT_TOKEN` + `TELEGRAM_WEBHOOK_SECRET` | Telegram bot webhook 및 provider secret-token 검증 |
| `REDIS_URL` | Rate Limiter 저장소 |
| `YT_HTTP_PROXY` / `YT_HTTPS_PROXY` | YouTube 차단 우회 프록시 |

### Production Required

`FLASK_ENV=production`에서는 앱이 안전하지 않은 설정으로 부팅되지 않도록 fail-closed 합니다.

| Variable | Description |
|----------|-------------|
| `CORS_ORIGINS` | HTTPS origin 목록. path/query/fragment/credentials, 로컬/와일드카드/private IP origin은 production에서 거부 |
| `INSIGHT_BASE_URL` / `APP_BASE_URL` | 배포 모니터링과 외부 링크용 공개 HTTPS base URL. 설정하면 로컬/private IP/credentials 포함 URL을 production readiness가 거부 |
| `PUBLIC_ORIGIN` | 선택값. 공유 URL을 별도 origin으로 만들 때 사용하며 production에서는 HTTPS public origin만 허용 |
| `TRUSTED_HOSTS` | 선택값. `CORS_ORIGINS` 외 추가 public host allowlist. wildcard/local/private IP host는 production에서 거부 |
| `METRICS_AUTH_TOKEN` | `/metrics` 보호 토큰. 32자 이상 랜덤 값이며 다른 시크릿과 재사용 금지 |
| `AUTH_MODE` | `edge` 또는 `supabase`. `edge`는 Basic Auth로 보호되는 private deployment, `supabase`는 명시된 public/auth/webhook/share 경로 외 모든 backend 경로에 Bearer JWT 인증을 fail-closed로 강제 |
| `CONTENT_SECURITY_POLICY` | 선택값. 미설정 시 backend API에 production-safe 기본 CSP 적용 |
| `SESSION_COOKIE_SECURE` | 선택값. production에서는 기본 `true`; 세션 쿠키는 `HttpOnly`, `SameSite=Lax` |
| `BASIC_AUTH_USER` / `BASIC_AUTH_HASH` | Caddy edge Basic Auth 계정. 해시는 `caddy hash-password --plaintext <password>`로 생성하고 `.env`에서는 single quote로 감싸기 |
| `SECRET_KEY` | Flask 세션/서명용 32자 이상 랜덤 시크릿. 다른 시크릿과 재사용 금지 |
| `ENCRYPTION_SECRET` | 32자 이상 랜덤 시크릿. `SECRET_KEY`/metrics 토큰과 재사용 금지 |
| `REDIS_URL` | rate limit 및 Redis publish queue 공유 저장소. production에서는 `redis://` 또는 `rediss://` 필요 |
| `PUBLISH_QUEUE_BACKEND` | production에서는 `redis` |
| `DEFAULT_GENERATION_MODEL` / `VIDEO_QA_DEFAULT_MODEL` | 운영 기본 모델. production에서는 `chatmock/*` 기본값 거부 |
| `AUTO_BACKUP_INTERVAL_HOURS` | app_data 자동 백업 주기 |
| `APP_CACHE_DIR` | transcript/comment/AI 캐시 디렉터리. 컨테이너 배포에서는 writable cache volume(`/app/cache`) 사용 |
| `AI_CACHE_DB` | AI 결과 캐시 SQLite 파일. production에서는 `APP_CACHE_DIR` 안의 경로 사용 |
| `APP_DATA_BACKUP_DIR` | `APP_DATA_DIR` 바깥의 백업 디렉터리 |
| `APP_DATA_BACKUP_REPLICA_DIR` | 백업 zip을 추가 복제할 별도 디렉터리. 운영에서는 별도 디스크/네트워크 스토리지/오프호스트 마운트 권장 |
| `CONTENT_BACKUP_DIR` | 콘텐츠 라이브러리 수동 백업 디렉터리. production에서는 `APP_DATA_BACKUP_DIR` 안이나 별도 외부 백업 볼륨 사용 |
| `APP_DATA_BACKUP_MAX_AGE_HOURS` | 선택값. `/ready`가 허용하는 최신 backup/replica archive 최대 나이. 미설정 시 `AUTO_BACKUP_INTERVAL_HOURS * 2` |
| `MAX_BACKUPS` | app_data 백업 보존 개수. 오래된 `app_data_backup_*.zip`은 자동 pruning |
| `APP_DATA_BACKUP_REPLICA_MAX_BACKUPS` | replica 디렉터리 백업 보존 개수. 미설정 시 `MAX_BACKUPS` 사용 |
| `AGENT_DB_PATH` / `CHROMA_DB_PATH` / `GRAPH_STORE_PATH` / `USER_MEMORY_PATH` / `SHARE_PAGE_DIR` / `FEEDBACK_DATA_DIR` / `FEEDBACK_STORE_DIR` / `FINETUNE_OUTPUT_DIR` / `JOB_STORE_DIR` / `PREFERENCE_DATA_PATH` | 파일 기반 런타임 데이터 경로. production에서는 모두 `APP_DATA_DIR` 안의 경로 사용 |
| `SCHEDULER_HEARTBEAT_FILE` | `/ready`가 background scheduler 생존을 확인할 heartbeat 파일 경로. backend container 기본값은 `/tmp/insight-engine-scheduler.heartbeat` |
| `APP_VERSION` / `APP_RELEASE` / `GIT_SHA` / `BUILD_TIME` | `/health`, access log, Docker image label에 노출되는 릴리즈 식별자 |
| `ERROR_TRACKING_REQUIRED` / `SENTRY_DSN` | `true`로 설정하면 Sentry DSN 누락 시 readiness와 배포 검증 실패 |
| `SENTRY_TRACES_SAMPLE_RATE` / `SENTRY_PROFILES_SAMPLE_RATE` | Sentry 성능/프로파일링 샘플링 비율 (`0`-`1`) |
| `ALERT_WEBHOOK_REQUIRED` / `ALERT_WEBHOOK_URL` | `true`로 설정하면 HTTPS alert webhook 누락 시 readiness와 배포 검증 실패 |
| `WEBHOOK_ENABLED` / `WEBHOOK_URL` / `SLACK_WEBHOOK_URL` / `DISCORD_WEBHOOK_URL` | outbound webhook을 사용하면 production에서 HTTPS public URL만 허용 |
| `SUPPORT_HANDOFF_SECRET` | Support Assistant GitHub handoff 관리자 승인키. GitHub handoff를 설정할 때 32자 이상 랜덤 값 필수 |
| `SUPPORT_GITHUB_REPO` / `SUPPORT_GITHUB_TOKEN` | GitHub Issue/Draft PR 생성용 repo/token. 둘 중 하나를 설정하면 handoff secret까지 완전한 조합 필요 |
| `AUTOMATION_WEBHOOK_SECRET` | 설정 시 32자 이상 랜덤 값이어야 하며 핵심 앱 secret과 재사용 금지 |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_WEBHOOK_SECRET` | Telegram bot webhook을 사용하면 둘 다 필요하며 webhook secret은 32자 이상 랜덤 값 권장 |

배포 전 확인:

```bash
set -a && . ./.env && set +a
npm run verify:production
npm run verify:app-data-backup
```

`verify:app-data-backup`은 원본 백업 round-trip과 실제 replica archive restore drill을 함께 실행하고, CI/배포 로그에는 per-file manifest 없이 요약만 출력합니다.
각 `app_data_backup_*.zip` 옆에는 `*.manifest.json` sidecar가 생성되어 archive sha256, 크기, 파일 manifest를 보존합니다.
운영 중 최신 replica archive만 별도로 복원 검증하려면 `npm run ops:restore-drill`을 실행합니다.
`python3 scripts/backup_app_data.py restore <archive> --target <dir>`는 기본적으로 sidecar sha256/size/file manifest를 검증한 뒤에만 파일을 씁니다.
신뢰할 수 있는 legacy archive만 `--skip-verify-sidecar`로 수동 우회하세요.
상세 manifest가 필요한 수동 점검에서는 `python3 scripts/backup_app_data.py rehearse`처럼 `--summary` 없이 실행합니다.

전체 목록: [.env.example](.env.example)

---

## Testing

```bash
# 백엔드 pytest + fatal lint
npm run verify:backend

# 프론트엔드 타입 체크 + production build
npm run verify:frontend

# Playwright smoke
npm run verify:e2e

# 추적 파일 secret scan
npm run verify:secrets

# Python dependency vulnerability audit
npm run verify:python-audit

# Dependabot/update automation + Docker context hygiene
npm run verify:maintenance

# backend + frontend + E2E smoke
npm run verify:all

# npm audit + secret scan + production env + backup rehearsal + compose config
npm run verify:release
```

CI는 PR/브랜치 푸시마다 backend, frontend, Playwright smoke, npm audit, Python dependency audit,
secret scan, production readiness, app data backup rehearsal, Docker Compose config,
Caddy config, Kubernetes manifest validation, GitHub Actions workflow validation, maintenance config validation, Docker image build를 실행합니다. workflow token 권한은 `contents: read`로 제한하고,
외부 GitHub Actions는 moving tag가 아닌 검토된 commit SHA로 고정하고, 각 `uses:` 줄에는 Dependabot이 추적할 major/version 주석을 남깁니다.
`main` push에서는 Docker image publish와 Railway deploy가
추가로 실행되며, 배포 후 public HTTPS `/health`/`/ready`/release metadata/TLS/webhook monitor까지 통과해야 CI가 성공합니다.
게시되는 Docker image는 immutable `github.sha` tag와 함께 SBOM/provenance attestation을 생성하고, production deploy job은
`insight-engine-production` concurrency group으로 직렬화되어 동시에 두 배포가 실행되지 않습니다.
Dependabot은 GitHub Actions, root/frontend/E2E npm, Python requirements, Dockerfile, Docker Compose, Kubernetes image manifests를 매주 UTC 월요일에 staggered schedule로 점검합니다.
Python audit 도구는 `requirements-ci.txt`에만 두고 production image에는 포함하지 않습니다. fix version이 없는 취약점은
`security/pip-audit-ignore.json`에 package, 사유, 만료일을 기록해야 하며, 만료된 exception은 release gate에서 실패합니다.
로컬 환경에서 `pip-audit`가 없으면 `python -m pip install -r requirements-ci.txt`로 감사 도구를 먼저 설치합니다.
결제 provider는 선택 기능이지만, production에서 Stripe/Paddle/Coinbase 관련 값 중 하나라도 설정하면 live key, webhook secret,
Stripe HTTPS 성공/취소 URL까지 완전해야 `verify:production`을 통과합니다. 서명 검증을 하는 결제 웹훅 경로는 browser CSRF 대신 provider signature로 검증됩니다.
Slack/Discord bot webhook도 edge Basic Auth 앞에서 열리지만, production에서는 signing secret/public key가 없으면 fail-closed로 거부됩니다.

---

## Deployment

### Docker

```bash
npm run verify:release
npm run deploy:local
INSIGHT_BASE_URL=http://127.0.0.1:8090 npm run ops:monitor
```

`deploy:local`은 compose healthcheck가 통과할 때까지 기다리고, profile-disabled orphan 컨테이너를 제거하고, readiness monitor를 통과한 뒤
실행 중인 backend 이미지 태그를 보존하고 dangling 이미지를 정리한 뒤 BuildKit 캐시를 pruning합니다.
Git 작업트리에서는 `APP_RELEASE`, `GIT_SHA`, `BUILD_TIME`을 자동으로 채우고, 배포 후 monitor가 `/health`의 release metadata와 같은 값인지 확인합니다.
배포 직후 backend 컨테이너 안에서 `scripts/backup_app_data.py backup --summary`를 실행해 `/ready`가 최신 backup/replica archive까지 확인하게 합니다.
배포 시작 전에 현재 정상 backend 이미지를 `insight-engine:rollback`으로 보존합니다. compose/backup/monitor 단계가 실패하면 기본적으로 자동 rollback을 시도하며,
수동 rollback은 `npm run ops:rollback-local`로 실행합니다. rollback은 보존된 이미지의 OCI release label이 검증 가능할 때만 실행되고,
rollback monitor는 그 metadata가 실제 `/health` 응답과 일치하는지도 확인합니다.
자동 rollback을 끄려면 `AUTO_ROLLBACK_ON_DEPLOY_FAILURE=false npm run deploy:local`을 사용합니다.
기본값은 `PRUNE_BUILD_CACHE=until=168h`라 최근 의존성/빌드 레이어는 재사용됩니다. 디스크 압박으로 전체 캐시를 비울 때는
`PRUNE_BUILD_CACHE=all npm run docker:cleanup`, 캐시 pruning을 건너뛸 때는 `PRUNE_BUILD_CACHE=0 npm run docker:cleanup`을 사용합니다.
`docker-compose.deploy.yml`의 런타임 서비스는 `no-new-privileges`, Docker init, pids limit, graceful stop window를 적용합니다.
backend/frontend/chatmock은 `cap_drop: ALL`을 사용하고, backend/frontend/edge/redis는 read-only root filesystem으로 실행합니다.
모든 runtime 서비스는 Docker `json-file` 로그가 무한정 커지지 않도록 기본 `DOCKER_LOG_MAX_SIZE=10m`, `DOCKER_LOG_MAX_FILE=5` 회전을 적용합니다.
frontend는 `/tmp`, `.next/cache`, `.next/diagnostics`만 tmpfs로 열고, edge는 Caddy autosave/TLS storage를 위해 `/config`, `/data` named volume만 쓰기 가능하게 둡니다.
Redis는 `/data` volume과 `/tmp` tmpfs만 씁니다.
운영에서 백업을 named volume이 아닌 host/external mount에 저장하려면 `APP_DATA_BACKUP_VOLUME=/var/backups/insight-engine`,
`APP_DATA_BACKUP_REPLICA_VOLUME=/mnt/backup-replica/insight-engine`처럼 compose source를 절대 경로로 지정합니다.
strict host check는 두 경로가 app workspace와 서로 다른 마운트에 있는지, 그리고 `tmpfs`/`overlay` 같은 휘발성 파일시스템이 아닌 durable storage인지 확인합니다.
운영 호스트에서는 Redis background save/AOF 안정성을 위해 `vm.overcommit_memory=1`을 런타임과 영구 sysctl 설정에 모두 적용하세요.
호스트 전제 조건은 다음 명령으로 점검할 수 있습니다. 운영에서는 strict 옵션을 켜서 Redis sysctl, persistent sysctl, external backup mount를 배포 게이트로 삼습니다.

```bash
printf '%s\n' 'vm.overcommit_memory = 1' | sudo tee /etc/sysctl.d/99-insight-engine.conf >/dev/null
sudo sysctl --system
npm run ops:host-check
HOST_CHECK_REQUIRE_OVERCOMMIT=true \
HOST_CHECK_REQUIRE_PERSISTENT_OVERCOMMIT=true \
HOST_CHECK_REQUIRE_EXTERNAL_BACKUPS=true \
HOST_CHECK_REQUIRE_BACKUP_MOUNTS=true \
npm run ops:host-check
```

ChatMock은 production stack의 필수 의존성이 아니며, 로컬 테스트가 필요할 때만 `docker compose -f docker-compose.deploy.yml --profile chatmock up -d chatmock`으로 실행합니다.

### Kubernetes

`k8s/deployment.yaml`은 Docker Compose와 같은 운영 계약을 따르는 reference manifest입니다. backend/frontend는 고정 UID `999`,
read-only root filesystem, dropped capabilities, `/ready` readiness, `/health` liveness를 사용하고, app data 백업과 replica는 별도 PVC에 저장합니다.
`/health`, `/ready`, `/share/*`, `/api/shares/<id>` 조회와 signed inbound webhook은 unauthenticated public ingress로 분리하고, share 생성용 `POST /api/shares`를 포함한 나머지 app/API 경로는 ingress basic auth 뒤에 둡니다.
replicated backend pod에서는 `SCHEDULER_ENABLED=false`로 background scheduler를 끄고, 단일 `insight-worker` deployment가 예약 발행,
publish queue, RSS/channel monitor, app_data 자동 백업을 담당합니다. worker는 heartbeat 기반 exec probe로 scheduler loop 정지를 감지합니다.
backend replica와 worker가 `app_data`/backup PVC를 함께 마운트하므로 `insight-data-pvc`, `insight-backups-pvc`, `insight-backup-replica-pvc`는
`ReadWriteMany`를 지원하는 storage class로 교체해야 합니다.
적용 전 이미지 `ghcr.io/your-org/insight-engine:replace-with-git-sha`를 실제 immutable tag 또는 digest로 바꾸고,
`CORS_ORIGINS`, `INSIGHT_BASE_URL`, `APP_BASE_URL`, `TRUSTED_HOSTS`, ingress host를 실제 공개 도메인으로 교체하세요. `insight-secrets`와
ingress basic auth secret은 클러스터 secret store에서 별도로 생성하세요.

```bash
npm run verify:k8s
kubectl apply -f k8s/deployment.yaml
```

### Production Cutover

실제 공개 도메인으로 전환하기 직전에는 strict cutover gate를 실행합니다. 이 명령은 전체 release gate(npm/Python audit,
secret scan, production env, backup rehearsal/drill, Compose/Caddy/Kubernetes/CI/maintenance validation)를 먼저 통과시킨 뒤
clean Git source state, Docker image hygiene, OCI revision label, Sentry DSN, alert webhook, Redis host sysctl, external backup/replica mount,
최신 backup restore drill, public DNS/HTTPS/TLS/release metadata monitor, webhook test alert를 한 번에 검증합니다.

```bash
INSIGHT_BASE_URL=https://insight.example.com \
RELEASE_REQUIRE_CLEAN_GIT=true \
HOST_CHECK_REQUIRE_OVERCOMMIT=true \
HOST_CHECK_REQUIRE_PERSISTENT_OVERCOMMIT=true \
HOST_CHECK_REQUIRE_EXTERNAL_BACKUPS=true \
HOST_CHECK_REQUIRE_BACKUP_MOUNTS=true \
ERROR_TRACKING_REQUIRED=true \
ALERT_WEBHOOK_REQUIRED=true \
MONITOR_TLS_MIN_DAYS=21 \
IMAGE_REF=insight-engine:local \
npm run ops:cutover-check
```

### Railway

1. GitHub 저장소 연결
2. Variables 탭에서 환경변수 설정
3. GitHub Actions production environment secret 설정
   - `RAILWAY_TOKEN`
   - `DOCKER_USERNAME`
   - `DOCKER_PASSWORD`
   - `INSIGHT_BASE_URL` (`https://insight.example.com` 형식)
   - `ALERT_WEBHOOK_URL`
4. 자동 배포

Railway deploy action은 `RAILWAY_TOKEN`을 action input이 아니라 environment variable로 읽습니다. `main` 배포 후 CI는 `INSIGHT_BASE_URL`에 대해 public DNS, HTTPS, TLS 만료 21일 이상, `/ready`, 보안 헤더, edge auth,
`APP_RELEASE/GIT_SHA == github.sha`, alert webhook 설정을 검증합니다.

### Manual

```bash
export FLASK_ENV=production
export FLASK_DEBUG=0
export AUTH_MODE=edge
export CORS_ORIGINS=https://insight.example.com
export INSIGHT_BASE_URL=https://insight.example.com
export METRICS_AUTH_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export ENCRYPTION_SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export REDIS_URL=redis://localhost:6379/0
export PUBLISH_QUEUE_BACKEND=redis
export PUBLISH_QUEUE_REDIS_URL="$REDIS_URL"
export APP_DATA_DIR=/app/data
export AGENT_DB_PATH=/app/data/agent_state.db
export CHROMA_DB_PATH=/app/data/chroma_db
export FEEDBACK_DATA_DIR=/app/data/feedback
export FEEDBACK_STORE_DIR=/app/data/feedback
export FINETUNE_OUTPUT_DIR=/app/data/finetune
export GRAPH_STORE_PATH=/app/data/graph_store
export JOB_STORE_DIR=/app/data/jobs
export PREFERENCE_DATA_PATH=/app/data/preferences.jsonl
export SHARE_PAGE_DIR=/app/data/shared_pages
export USER_MEMORY_PATH=/app/data/user_memory
export APP_CACHE_DIR=/app/cache
export AI_CACHE_DB=/app/cache/ai_cache.db
export APP_DATA_BACKUP_DIR=/app/backups
export APP_DATA_BACKUP_REPLICA_DIR=/app/backup-replica
export CONTENT_BACKUP_DIR=/app/backups/content-library
export APP_DATA_BACKUP_VOLUME=/var/backups/insight-engine
export APP_DATA_BACKUP_REPLICA_VOLUME=/mnt/backup-replica/insight-engine
export AUTO_BACKUP_INTERVAL_HOURS=6
export SCHEDULER_HEARTBEAT_FILE=/tmp/insight-engine-scheduler.heartbeat
export BASIC_AUTH_USER=admin
export BASIC_AUTH_HASH='<caddy hash-password output>'
export APP_RELEASE="$(git rev-parse HEAD)"
export GIT_SHA="$APP_RELEASE"
export BUILD_TIME="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
# export ERROR_TRACKING_REQUIRED=true
# export SENTRY_DSN=https://<your-sentry-dsn>
gunicorn 'app:app' --workers=2 --threads=4 --timeout=300 -b 0.0.0.0:5001
```

---

## Operations

### Readiness Monitoring

`/health`는 프로세스 liveness, `/ready`는 production 설정, Redis, app_data와 파일 기반 runtime 하위 경로, app/content backup 디렉터리 쓰기 가능 여부, scheduler heartbeat, 오류 추적 필수 설정을 확인합니다.
production에서 인증 없는 `/ready` 응답은 공개 모니터링용으로 `status`만 반환하며, 컴포넌트별 진단은 `/metrics`와 같은 `METRICS_AUTH_TOKEN` bearer token 또는 `X-Metrics-Auth-Token` 헤더가 있는 요청에만 포함됩니다.
모든 backend 응답에는 `X-Request-ID`가 포함되며, 클라이언트가 안전한 `X-Request-ID` 또는 `X-Correlation-ID`를 보내면 그대로 전파합니다.
500 응답 JSON에도 `requestId`가 포함되므로 사용자 문의, access log, Sentry 이벤트를 같은 ID로 묶어 추적할 수 있습니다.
`/health`의 `release` 객체는 `APP_VERSION`, `APP_RELEASE`, `GIT_SHA`, `BUILD_TIME`을 반환합니다. Docker 이미지도 같은 값을 OCI label로 포함하므로
실행 중인 컨테이너, 로그, 오류 추적 이벤트, 이미지 태그를 같은 릴리즈로 묶을 수 있습니다.
배포 후 또는 cron/external monitor에서 다음 명령을 실행하면 JSON 리포트를 반환하고 실패 시 exit code `2`로 종료합니다.

```bash
INSIGHT_BASE_URL=https://insight.example.com npm run ops:monitor
```

Caddy edge 뒤에서 실행할 때는 기본적으로 루트 경로가 Basic Auth `401` challenge를 반환하는지와
`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy` 등 공통 보안 헤더도 확인합니다.
또한 `/health` 응답의 `X-Request-ID`가 존재하고 안전한 형식인지 확인합니다.
`METRICS_AUTH_TOKEN` 또는 `MONITOR_METRICS_AUTH_TOKEN`이 있으면 `/ready`를 bearer token으로 확인해 Redis, backup, scheduler 등 컴포넌트 진단이 실제로 노출되는지도 검증합니다.
실제 공개 도메인에서는 HTTPS와 인증서 만료일을 배포 게이트로 함께 확인합니다.

```bash
python3 scripts/monitor_readiness.py \
  --base-url https://insight.example.com \
  --require-public-host \
  --require-https \
  --tls-min-days 21
```

배포한 commit이 실제로 서비스 중인지까지 확인하려면 expected release 값을 함께 넘깁니다.

```bash
python3 scripts/monitor_readiness.py \
  --base-url https://insight.example.com \
  --expected-release "$(git rev-parse HEAD)" \
  --expected-git-sha "$(git rev-parse HEAD)"
```

직접 백엔드나 프론트엔드 포트를 점검할 때는 edge auth 검사를 끌 수 있습니다.

```bash
python3 scripts/monitor_readiness.py \
  --base-url http://127.0.0.1:5001 \
  --skip-edge-auth
```

Slack, Discord, n8n 등 webhook으로 실패 알림을 보내려면 `ALERT_WEBHOOK_URL`을 설정합니다.
운영에서 알림 채널을 필수 게이트로 삼으려면 `ALERT_WEBHOOK_REQUIRED=true`와 HTTPS webhook을 함께 설정합니다.

```bash
INSIGHT_BASE_URL=https://insight.example.com \
ALERT_WEBHOOK_URL=https://hooks.example.com/insight-engine \
npm run ops:monitor
```

알림 채널 자체가 살아있는지 배포 직후 검증하려면 테스트 알림을 한 번 보냅니다.

```bash
INSIGHT_BASE_URL=https://insight.example.com \
ALERT_WEBHOOK_URL=https://hooks.example.com/insight-engine \
python3 scripts/monitor_readiness.py --send-test-alert
```

### Error Tracking

`SENTRY_DSN`을 설정하면 Flask 앱 부팅 시 Sentry가 초기화됩니다. 기본값은 `send_default_pii=false`이며,
전송 직전 `Authorization`, cookie, token, secret, password, API key, 요청 body/query 값을 필터링합니다.
운영에서 오류 추적 누락을 배포 실패로 처리하려면 `ERROR_TRACKING_REQUIRED=true`를 함께 설정합니다.

---

## Troubleshooting

| 문제 | 해결 |
|------|------|
| AI 서비스가 표시되지 않음 | `.env`에 해당 프로바이더 API 키 설정 확인 |
| YouTube 자막 수집 실패 | `SUPADATA_API_KEY` 설정 또는 프록시(`YT_HTTP_PROXY`) 사용 |
| 댓글이 수집되지 않음 | `YOUTUBE_API_KEY` 설정 + YouTube Data API v3 활성화 확인 |
| Ollama 연결 실패 | Ollama 서버 실행 확인 (`ollama serve`), URL 설정 확인 |
| 프론트엔드 빈 화면 | 백엔드(`python app.py`)가 실행 중인지 확인 |

---

## Tech Stack

**Backend:** Python 3.8+ · Flask 3.0 · LiteLLM · APScheduler · ChromaDB · faster-whisper · Supabase

**Frontend:** Next.js 16 · React 19 · TypeScript · Tailwind CSS v4 · Zustand · TanStack Query · shadcn/ui · Radix UI

**Testing:** pytest (271 tests) · Playwright E2E · MSW

---

## License

MIT License
