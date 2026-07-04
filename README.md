# Insight Engine

YouTube 영상 URL 하나로 15가지 스타일의 고품질 콘텐츠를 자동 생성하는 AI 콘텐츠 엔진.
5개 AI 프로바이더(Gemini, DeepSeek, Zhipu GLM, Ollama, OpenRouter) 통합, 다국어(한/영/일) 지원, RAG 지식 참조, MCP 자동 발행, 팀 워크스페이스까지.

Flask + Next.js 풀스택 · LiteLLM 멀티프로바이더 · 323개 서비스 · 1,659개 테스트(99.94% pass)

---

## Features

### Core
- **15가지 출력 스타일** — 블로그+SEO, 요약, 튜토리얼, Q&A, 앱 아이디어, 요즘IT, 브런치, 네이버 인기글, SNS, 뉴스레터, 쇼노트, Shorts 클립, GEO(AI검색 최적화), AI 코스, 퀴즈
- **5개 AI 프로바이더** — Gemini, DeepSeek, Zhipu GLM, Ollama(로컬), OpenRouter(2600+ 모델)
- **다국어 출력** — 한국어, 영어, 일본어
- **4단계 자막 폴백** — youtube-transcript-api → watch 페이지 파싱 → Supadata API → Whisper 로컬 음성인식

### Content Generation
- **배치 처리** — 최대 10개 URL 동시 분석
- **멀티스타일** — 1 URL × N 스타일 동시 생성 (사용량 1회 차감)
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
│   └── styles/                    # 15개 UI 스타일 + 4개 내부 스타일
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
| Quiz | 객관식 학습 퀴즈 |

각 스타일은 독립 프롬프트 + 최적화된 temperature/max_tokens 설정.

---

## API

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/generate` | POST | 단일 URL 콘텐츠 생성 |
| `/generate-batch` | POST | 다중 URL 배치 (최대 10개) |
| `/api/generate-multi` | POST | 1 URL × N 스타일 동시 생성 |
| `/api/pipeline` | POST | 파이프라인 자동화 (SSE) |
| `/api/rewrite` | POST | 플랫폼별 리라이트 |
| `/api/inline-edit` | POST | 인라인 AI 편집 |

### Content Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mindmap` | POST | 마인드맵 생성 |
| `/api/qa-check` | POST | QA 게이트 검증 |
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

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/providers` | GET | 사용 가능한 AI 목록 |
| `/api/providers/validate` | POST | API 키 유효성 검증 |
| `/api/ollama/health` | GET | Ollama 상태 확인 |
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
| `WEBHOOK_URL` + `WEBHOOK_ENABLED` | 웹훅 알림 |
| `REDIS_URL` | Rate Limiter 저장소 |
| `YT_HTTP_PROXY` / `YT_HTTPS_PROXY` | YouTube 차단 우회 프록시 |

전체 목록: [.env.example](.env.example)

---

## Testing

```bash
# 단위 테스트 (271개)
python -m pytest tests/ -v

# E2E 테스트 (Playwright)
cd tests/e2e && npx playwright test --workers=1

# 커버리지
python -m pytest tests/ --cov=. --cov-report=html

# 프론트엔드 타입 체크
cd frontend && npx tsc --noEmit
```

---

## Deployment

### Docker

```bash
docker build -t insight-engine .
docker run -p 5001:5001 --env-file .env insight-engine
```

### Railway

1. GitHub 저장소 연결
2. Variables 탭에서 환경변수 설정
3. 자동 배포

### Manual

```bash
export FLASK_ENV=production
export FLASK_DEBUG=0
gunicorn app:app -b 0.0.0.0:5001
```

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
