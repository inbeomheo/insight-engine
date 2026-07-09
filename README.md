# Insight Engine

YouTube/문서/텍스트를 학습하고 LLMWiki형 지식 위키로 쌓는 AI 학습 엔진.
ChatMock(OpenAI 호환) 기반 생성, 다국어(한/영/일) 지원, RAG 지식 참조, 팀 워크스페이스까지.

Flask + Next.js 풀스택 · LiteLLM · ChatMock 호환 · 4,300+ 테스트(pass)

---

## Features

### Core
- **4가지 출력 스타일** — 요약, Q&A, 퀴즈, 리텐션 카드
- **ChatMock 단일 프로바이더** — ChatGPT 계정을 OpenAI 호환 API로 사용하는 로컬 프록시
- **다국어 출력** — 한국어, 영어, 일본어
- **4단계 자막 폴백** — youtube-transcript-api → watch 페이지 파싱 → Supadata API → Whisper 로컬 음성인식

### Content Generation
- **배치 처리** — 최대 10개 URL 동시 분석
- **멀티스타일** — 1 URL × N 스타일 동시 생성
- **퓨전 분석** — 다중 소스 교차 분석 콘텐츠
- **파이프라인 자동화** — 자막 추출 → 학습 노트 생성 (SSE 실시간 진행률)
- **소스 인용 모드** — 모든 주장에 [MM:SS] 타임스탬프 인용 + YouTube 링크 변환
- **챕터 자동 분할** — AI가 자막을 주제별 챕터로 분할
- **댓글 병렬 분석** — 메인 콘텐츠와 댓글 요약 동시 생성

### Post-Processing
- **인라인 AI 편집** — 텍스트 선택 영역 부분 재생성 (축약/확장/톤변경/번역)
- **마인드맵** — 콘텐츠 → 마인드맵 마크다운 변환

### Publishing & Collaboration
- **팀 워크스페이스** — 멤버 관리 (Owner/Editor/Viewer) + 콘텐츠 승인 플로우
- **채널 모니터링** — YouTube 채널 신규 업로드 자동 감지 (30분 폴링)

### Intelligence
- **RAG 지식 참조** — ChromaDB 벡터 스토어, 파일 업로드 → 생성 시 자동 주입
- **웹 검색 보강** — Tavily API로 자막 내용을 웹 검색으로 보강
- **멀티에이전트** — Research → Writer → Editor → SEO 파이프라인
- **지식 위키** — 노트 저장, 관련 노트 추천, 근거 기반 채팅

### Export & Integration
- **단순 내보내기** — HTML, Markdown
- **웹훅 알림** — 생성 완료 시 n8n/Make/Zapier 연동
- **외부 서비스** — Slack, Discord, RSS, GitHub 연동
- **GraphQL API** — 유연한 쿼리 지원

---

## Quick Start

### 요구사항
- Python 3.8+
- Node.js 18+
- ChatMock 서버

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

ChatMock을 설치·로그인·실행하고 `.env`에 base URL을 설정하세요:

```bash
pipx install chatmock              # 또는 brew tap RayBytes/chatmock && brew install chatmock
chatmock login
chatmock serve                     # 기본 API: http://127.0.0.1:8000/v1
```

```env
CHATMOCK_BASE_URL=http://127.0.0.1:8000/v1
CHATMOCK_API_KEY=dummy

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
│  Port 3000                │◀────│  LiteLLM + ChatMock      │
└───────────────────────────┘     └────────┬────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    ▼                      ▼                      ▼
             ┌─────────────┐      ┌──────────────┐      ┌──────────────┐
             │ YouTube API  │      │ ChatMock      │      │ Supabase     │
             │ Transcript   │      │ OpenAI Compat │      │ Auth, DB     │
             │ Comments     │      │ Local Proxy   │      │ Usage        │
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
│   ├── blog_routes.py             # 콘텐츠 생성, 파이프라인, MCP
│   ├── auth_routes.py             # 인증, API 키, 사용량, 워크스페이스
│   ├── advanced_routes.py         # 멀티스타일, 퓨전, QA
│   ├── export_routes.py           # HTML/MD 내보내기 중심
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
│   ├── content/                   # 인용, FAQ (26개)
│   ├── media/                     # 이미지, TTS, 썸네일 (15개)
│   ├── transcript/                # Whisper, 챕터, 번역 (6개)
│   ├── agents/                    # 멀티에이전트 파이프라인 (12개)
│   ├── analytics/                 # 분석 대시보드 (17개)
│   ├── rag/                       # ChromaDB 벡터 스토어 (9개)
│   ├── mcp/                       # MCP Apps SDK + MCP 서버 (3개)
│   ├── platform/                  # 웹훅, RSS, 채널 모니터링 (11개)
│   ├── data/                      # Supabase, 스케줄, 알림 (33개)
│   ├── integrations/              # Slack, Discord (7개)
│   ├── payment/                   # 결제/구독 (9개)
│   ├── export/                    # 내보내기 유틸
│   ├── auth/                      # 인증/OAuth (2개)
│   ├── usage/                     # 사용량 관리 (5개)
│   └── exceptions/                # 에러 처리
│
├── prompts/                       # 프롬프트 시스템 v3.4
│   ├── base.py                    # 기본 프롬프트 (Chain-of-Thought)
│   └── styles/                    # 4개 UI 스타일 + 내부 변환 스타일
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
| **ChatMock** (기본) | gpt-5.4-mini, gpt-5.4, gpt-5.5, gpt-5.3-codex-spark | OpenAI 호환 로컬 프록시 |

---

## Styles

| Style | Description |
|-------|-------------|
| Summary | 핵심 요약 |
| Q&A | 질문-답변 형식 |
| Quiz | 객관식 학습 퀴즈 |
| Retention Cards | 반복 학습 카드 |

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
| `/api/inline-edit` | POST | 인라인 AI 편집 |

### Content Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/mindmap` | POST | 마인드맵 생성 |
| `/api/extract-document` | POST | PDF/DOCX/PPTX 텍스트 추출 |
| `/api/extract-audio` | POST | MP3/WAV/M4A/OGG/FLAC/AAC 음성 전사 |
| `/api/export/html` | POST | HTML 내보내기 |
| `/api/export/markdown` | POST | Markdown 내보내기 |

### Platform & Publishing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/workspaces` | GET/POST | 워크스페이스 관리 |

### System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/providers` | GET | 사용 가능한 AI 목록 |
| `/api/providers/validate` | POST | API 키 유효성 검증 |
| `/api/knowledge/upload` | POST | RAG 문서 업로드 |
| `/api/admin/dashboard` | GET | 운영 대시보드 |

---

## Environment Variables

### AI Provider

| Variable | Provider | Get Key |
|----------|----------|---------|
| `CHATMOCK_BASE_URL` | ChatMock | `http://127.0.0.1:8000/v1` |
| `CHATMOCK_API_KEY` | ChatMock | `dummy` |

### Optional

| Variable | Description |
|----------|-------------|
| `YOUTUBE_API_KEY` | YouTube 댓글 수집 |
| `SUPADATA_API_KEY` | 자막 백업 서비스 |
| `TAVILY_API_KEY` | 웹 검색 보강 |
| `SUPABASE_URL` + `SUPABASE_ANON_KEY` | 클라우드 DB/인증 |
| `WHISPER_ENABLED` | Whisper 자막 폴백 (`true`/`false`) |
| `DOCUMENT_UPLOAD_MAX_BYTES` | 문서 텍스트 추출 업로드 최대 바이트 |
| `AUDIO_UPLOAD_MAX_BYTES` | 오디오 전사 업로드 최대 바이트 |
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
| AI 서비스가 표시되지 않음 | `chatmock login` 후 `chatmock serve` 실행 및 `CHATMOCK_BASE_URL` 확인 |
| YouTube 자막 수집 실패 | `SUPADATA_API_KEY` 설정 또는 프록시(`YT_HTTP_PROXY`) 사용 |
| 댓글이 수집되지 않음 | `YOUTUBE_API_KEY` 설정 + YouTube Data API v3 활성화 확인 |
| 프론트엔드 빈 화면 | 백엔드(`python app.py`)가 실행 중인지 확인 |

---

## Tech Stack

**Backend:** Python 3.8+ · Flask 3.0 · LiteLLM · APScheduler · ChromaDB · faster-whisper · Supabase

**Frontend:** Next.js 16 · React 19 · TypeScript · Tailwind CSS v4 · Zustand · TanStack Query · shadcn/ui · Radix UI

**Testing:** pytest (271 tests) · Playwright E2E · MSW

---

## License

MIT License
