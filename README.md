# Insight Engine

YouTube/문서/텍스트를 학습하고 LLMWiki형 지식 위키로 쌓는 AI 학습 엔진.
ChatMock(OpenAI 호환) 기반 생성, 다국어(한/영/일) 지원, RAG 지식 참조, 팀 워크스페이스까지.

Flask + Next.js 풀스택 · LiteLLM · ChatMock 호환 · pytest + Vitest + Playwright

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
- **결과 직접 편집** — 생성된 제목·마크다운을 수정하고 HTML·공유 결과까지 동기화
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
- **웹훅 알림** — 생성 완료 시 설정한 Webhook URL로 결과 전송
- **학습 소스** — YouTube URL, 문서 업로드, 직접 텍스트 입력

---

## Quick Start

### 요구사항
- Python 3.11+
- Node.js 22.19+
- ChatMock 서버

### 설치

```bash
git clone https://github.com/inbeomheo/insight-engine.git
cd insight-engine

# 가상환경 (권장)
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux

# 런타임·검증 의존성
pip install -r requirements.txt -r requirements-dev.txt
npm ci
npm --prefix frontend ci
npm --prefix tests/e2e ci
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
FLASK_ENV=development
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
├── routes/                        # API 라우트
│   ├── blog_routes.py             # 콘텐츠 생성, 파이프라인, MCP
│   ├── auth_routes.py             # 인증, API 키, 사용량, 워크스페이스
│   ├── advanced_routes.py         # 멀티스타일, 퓨전, QA
│   ├── export_routes.py           # HTML/MD 내보내기 중심
│   ├── utility_routes.py          # 헬스체크, 프로바이더, 캐시
│   └── ...
│
├── services/                      # 비즈니스 로직
│   ├── core/                      # AI, 콘텐츠, 파이프라인, 캐시
│   ├── analysis/                  # 텍스트/NLP 분석
│   ├── content/                   # 인용, FAQ, 공유
│   ├── data/                      # Supabase, 스케줄, 알림
│   ├── rag/                       # ChromaDB 벡터 스토어
│   ├── export/                    # 내보내기 유틸
│   ├── usage/                     # 원자적 사용량 예약·환불
│   └── exceptions/                # 에러 처리
│
├── prompts/                       # 프롬프트 시스템 v4.0
│   ├── base.py                    # 기본 프롬프트 (Chain-of-Thought)
│   └── styles/                    # UI 기본 스타일 + 내부/변환 스타일
│
├── frontend/                      # Next.js 16 + Tailwind v4 + shadcn
│   ├── app/                       # App Router 페이지
│   ├── components/                # React 컴포넌트
│   ├── hooks/                     # 커스텀 훅
│   ├── stores/                    # Zustand 상태 관리
│   └── lib/                       # API, 타입, 유틸
│
├── tests/                         # pytest + Playwright E2E
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
| `/api/knowledge/upload` | POST | RAG 문서 업로드 |
| `/api/admin/dashboard` | GET | 운영 대시보드 |

---

## Environment Variables

### AI Provider

| Variable | Provider | Get Key |
|----------|----------|---------|
| `CHATMOCK_BASE_URL` | ChatMock | `http://127.0.0.1:8000/v1` |
| `CHATMOCK_API_KEY` | ChatMock | `dummy` |

### 주요 설정

| Variable | Description |
|----------|-------------|
| `YOUTUBE_API_KEY` | YouTube 댓글 수집 |
| `SUPADATA_API_KEY` | 자막 백업 서비스 |
| `TAVILY_API_KEY` | 웹 검색 보강 |
| `SUPABASE_URL` + `SUPABASE_PUBLISHABLE_KEY` | 운영 DB/인증 필수 (`SUPABASE_ANON_KEY` legacy 호환) |
| `SUPABASE_SECRET_KEY` | 운영 서버 관리자·백그라운드 작업 필수 (`SUPABASE_SERVICE_ROLE_KEY` legacy 호환) |
| `PUBLIC_ORIGIN` | 운영 서비스의 canonical HTTPS origin |
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
# 전체 로컬 검증(백엔드·프론트·E2E 스모크)
npm run verify:all

# 전체 로컬 Chromium E2E(인증 미설정 항목은 자동 skip, 단일 worker)
cd tests/e2e
npm ci
npx --no-install playwright install chromium
npm run test:ci

# 커버리지
node scripts/run_python.cjs -m pytest tests/ --cov=. --cov-report=html

# 프론트엔드 타입 체크
npm --prefix frontend exec -- tsc --noEmit
```

---

## Deployment

### Docker

```bash
# 로컬용 백엔드, 프론트엔드, Redis, Nginx를 함께 실행
docker compose up --build -d

# http://localhost 에서 접속
docker compose ps
```

표준 `docker-compose.yml`은 인증 우회가 허용되는 `development` 모드이며,
백엔드·프론트엔드·Redis·Nginx 포트를 모두 `127.0.0.1`에만 바인딩합니다.
따라서 같은 컴퓨터에서는 사용할 수 있지만 LAN이나 인터넷에는 기본 공개되지 않습니다.
외부 공개가 필요한 경우 이 개발 구성을 재사용하지 말고 아래 운영 구성을 사용하세요.

운영 배포 전에는 `.env.example`을 기준으로 실제 비밀값을 설정하고
`npm run verify:production -- --env-file <운영-env-파일>`로 필수 설정을 검사하세요.
운영 인증과 원자적 사용량 예약에는 `SUPABASE_URL`,
`SUPABASE_PUBLISHABLE_KEY`가 필수이며(기존 `SUPABASE_ANON_KEY`도 호환),
관리자 판별·전체 통계·백그라운드 채널 모니터에는 브라우저에 절대 노출하지 않는
`SUPABASE_SECRET_KEY`도 필수입니다(기존 `SUPABASE_SERVICE_ROLE_KEY`도 호환).
`SUPABASE_URL`은 루프백/로컬 주소가 아닌 운영용 `https://` URL이어야 합니다.
`PUBLIC_ORIGIN`도 경로가 없는 단일 운영 `https://` origin으로 지정해야 합니다.
새 Supabase 프로젝트는 통합본 [`supabase/schema.sql`](supabase/schema.sql)을 한 번
실행하세요. 기존 프로젝트는 `supabase/migrations/`에서 아직 적용하지 않은 파일을
`003`부터 `009`까지 번호 순서대로 적용해야 합니다. 이미 `007`까지 적용한 환경이라면
[`008_usage_reservation_idempotency.sql`](supabase/migrations/008_usage_reservation_idempotency.sql)과
[`009_workspace_rls_security.sql`](supabase/migrations/009_workspace_rls_security.sql)만 이어서
적용하면 됩니다. 통합 스키마와 증분 마이그레이션을 같은 새 프로젝트에 중복 실행하지
마세요. `/ready`는 anon 키로 읽기 전용
`insight_engine_schema_version()` RPC(원격 데이터베이스 함수)를 호출하며, 버전 `9`를
확인할 수 없으면 `503`으로 실패 폐쇄됩니다. 이 검사는 데이터를 생성·수정하지 않으며
`SUPABASE_SECRET_KEY`/`SUPABASE_SERVICE_ROLE_KEY`도 요구하지 않습니다.
운영용 Compose 구성은 `docker-compose.deploy.yml`이며, 앱 데이터·백업·캐시·로그를
하나의 `insight_app_persist` 볼륨 아래 `data/`, `backups/`, `cache/`, `logs/`로
분리합니다. 실패한 사용량 환불 재시도 원장도 `data/`에 기록되므로 이
단일 볼륨 전체를 영속 저장·백업해야 합니다.

> **경고 — 기존 볼륨 전환:** 기존 `insight_app_data`/`insight_app_backups` 볼륨의
> 데이터는 새 `insight_app_persist` 볼륨으로 자동 이동되지 않습니다. 서비스를
> 멈추고 기존 볼륨을 백업한 뒤 `data/`와 필요한 백업을 복사·검증하기 전에는
> 기존 볼륨을 삭제하지 마세요.

포터블 ZIP 백업은 기본으로 꺼져 있으며 `AUTO_BACKUP_ENABLED=true`로 명시적으로
켤 때만 실행됩니다. 첫 실행은 `BACKUP_INITIAL_DELAY_SECONDS`(기본 300초) 뒤로
미뤄 배포 준비 시간과 겹치지 않습니다. Linux에서 백업 시 백엔드 프로세스 그룹을 `SIGSTOP`으로
일시 정지해 Chroma/SQLite WAL(쓰기 선행 로그) 포함 스냅샷을 만들고, 항상
`SIGCONT`로 재개합니다. 정지 상한은 `BACKUP_QUIESCE_TIMEOUT_SECONDS`(기본 600초)이며,
아카이브를 실제로 풀어 파일 해시와 SQLite `PRAGMA quick_check`를 통과한 후에만 최신
`MAX_BACKUPS`개 외의 이전 백업을 정리합니다. 연속 실패는 제한된 backoff로 세 번
재시도한 뒤 비정상 종료 코드와 supervisor 로그로 드러나므로 운영 경보를 연결하세요.
이 스냅샷 구간에는 새 API 요청 처리가 일시 정지되며, 복원 검증에는 압축을 풀 수
있는 충분한 `/tmp` 임시 디스크가 필요합니다. 따라서 대용량 볼륨은 포터블 ZIP 대신
플랫폼 볼륨 백업을 사용하세요. Linux 외 환경에서 `backup`/`rehearse` 명령을 수동으로
실행할 때는 반드시 쓰기 서비스를 먼저 멈춘 상태에서 수행하세요.

복원도 백엔드·백업 데몬 등 대상 디렉터리에 쓰는 프로세스를 모두 멈춘 뒤 실행해야
합니다. `python scripts/backup_app_data.py restore <archive.zip> --target <data-dir> --overwrite`
명령은 아카이브 경로·CRC·파일 형식·내장 SHA-256 manifest와 SQLite 무결성을 별도
staging 디렉터리에서 검증한 다음 대상 디렉터리를 원자적으로 교체합니다. 검증이나
교체가 실패하면 기존 대상을 유지하거나 되돌리며, archive는 복원 대상 밖에 두세요.

운영 Compose의 ChatMock은 빌드 시 `1.40`으로 고정되며 비루트 사용자로 실행됩니다.
호스트의 `.codex`를 마운트하지 않고 `insight_chatmock_credentials` 전용 named volume을
사용하므로, 최초 로그인과 토큰 갱신은 다음 명령으로 수행하세요.

```bash
docker compose -f docker-compose.deploy.yml --profile chatmock-login run --rm chatmock-login
```

Caddy 보호 영역은 사용자명과 비밀번호 해시를 필수 Secret으로 받습니다. 평문 비밀번호는
저장하지 말고 아래처럼 bcrypt 해시를 만든 뒤 주입하세요. 해시에 포함된 `$`가 Compose에
의해 보간되지 않도록 `.env`에서는 값을 작은따옴표로 감싸야 합니다.

```bash
docker run --rm caddy:2-alpine caddy hash-password --plaintext '긴-운영-비밀번호'
# .env (실제 출력 전체를 작은따옴표 안에 복사하고 커밋하지 않음)
CADDY_BASIC_AUTH_USER=operator
CADDY_BASIC_AUTH_HASH='<caddy hash-password 출력값>'

docker compose -f docker-compose.deploy.yml up --build -d
```

운영 백엔드 healthcheck는 `/ready`를 사용하며 ChatMock, Redis, Supabase, Next.js를 실제 호출합니다.
필수 의존성 중 하나라도 응답하지 않으면 `503`으로 실패 폐쇄됩니다. `/health`는 프로세스 생존만
확인하는 liveness(프로세스 생존 검사)로 유지됩니다.

### Railway

1. Railway의 `insight-engine` 서비스 Source를 Docker Image로 한 번 설정하고,
   초기 이미지 이름에 `<DOCKER_USERNAME>/insight-engine:<git-sha>`를 입력합니다.
   이후 CI는 Railway CLI의 `service source connect --image`로 이 참조를 매
   릴리스의 고유 SHA 태그로 갱신합니다. 비공개 Docker Hub 저장소라면 Source의
   Registry Credentials에는 배포 전용 read-only 토큰을 설정하세요.
2. Variables 탭에서 `FLASK_ENV=production`, 외부 ChatMock의 `CHATMOCK_BASE_URL`,
   Redis·Supabase·CORS·보안·백업 관련 필수 환경변수를 설정합니다.
   `RAILWAY_RUN_UID=0`을 필수로 설정하고 서비스에 **하나의 영속 볼륨만**
   `/app/persist`에 마운트하세요. Railway 볼륨은 root 소유로 마운트되므로 시작
   supervisor가 하위 디렉터리를 초기화·`chown`한 뒤 `appuser` UID/GID로 영구
   강등합니다. Flask·Next.js·nginx·선택적 백업 데몬은 root로 실행되지
   않습니다. 제약과 권한 설정은 Railway의 [Volumes](https://docs.railway.com/volumes)와
   [Volume Reference](https://docs.railway.com/volumes/reference)를 기준으로 합니다.
3. Docker Image Source는 저장소의 `railway.json`을 읽지 않으므로 서비스
   **Settings → Deploy**에서 Healthcheck Path를 `/ready`, Healthcheck Timeout을
   `120`, Required Mount Path를 `/app/persist`로 직접 설정하세요. Draining Time은
   최소 `630`초로 설정하고 Variables에도
   `RAILWAY_DEPLOYMENT_DRAINING_SECONDS=630`을 명시하세요. 기본 종료 유예는
   0초이므로 이 설정이 없으면 nginx와 Gunicorn의 정상 종료가 즉시 잘립니다.
4. 운영 복구의 기준은 Railway의 해당 볼륨에 대한 manual/automated backup으로
   설정하고 `PLATFORM_VOLUME_BACKUPS_ENABLED=true`로 운영 설정에 명시하세요.
   위의 ZIP 백업은 다른 플랫폼으로 이전할 때를 위한 보조 기능이며 Railway
   볼륨 백업을 대체하지 않습니다. 같은 볼륨의 ZIP만으로는 운영 준비 검사를
   통과하지 않습니다.
5. 기본 브랜치 `master`에 push하면 CI가 로컬 런타임 스모크를 통과한 동일
   이미지를 커밋 SHA 태그와 편의용 mutable `production` 태그로 게시합니다.
   배포에는 mutable 태그를 사용하지 않고 Railway CLI `5.45.2`로 서비스 Source를
   `<DOCKER_USERNAME>/insight-engine:<git-sha>`에 직접 갱신합니다. CI는 새
   deployment ID가 생성된 뒤 Railway 상태가 최종 `SUCCESS`가 될 때까지 기다리며,
   실패나 시간 초과를 production 배포 실패로 처리합니다. 이때 Railway의 live
   environment config도 읽어 Source 이미지, `/ready` healthcheck, 120초 timeout,
   `/app/persist` 단일 볼륨과 required mount, 630초 draining을 다시 검증합니다.
   성공 상태 뒤에는 `PUBLIC_ORIGIN/ready`가 실제로 `200`을 반환해야 CI가 끝납니다.
   따라서 실제 Railway 배포와 CI에서 검증한 이미지가 같은 릴리스 태그로 고정되고
   설정 drift를 차단하며 커밋 단위 롤백이 가능합니다. 변수 전체 JSON은 로그에
   출력하지 않고 `PUBLIC_ORIGIN`과 draining 계약만 파이프로 검사합니다.

이 Source 설정이 중요합니다. Railway가 GitHub 소스를 별도로 다시 빌드하게 두거나
mutable `production` 태그만 재배포하면 CI에서 검증·게시한 이미지와 실제 실행 산출물이
달라질 수 있습니다. `main` push는 테스트와
Docker 빌드 검증만 수행하며 프로덕션 이미지를 게시하거나 배포하지 않습니다.
`railway.json`은 GitHub-source 배포를 위한 별도 안전망으로 Dockerfile builder,
`/ready`, `/app/persist` 필수 mount, 630초 draining을 선언합니다. Docker Image
Source에서는 위 Settings 값이 실제 계약입니다. `/ready`는 ChatMock·Redis·Supabase
스키마뿐 아니라 동일 컨테이너의 Next.js 응답도 확인하므로 모두 준비된 뒤에만 새
배포가 트래픽을 받습니다.

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

**Backend:** Python 3.11+ · Flask 3.1+ · LiteLLM · APScheduler · ChromaDB · faster-whisper · Supabase

**Frontend:** Next.js 16 · React 19 · TypeScript · Tailwind CSS v4 · Zustand · TanStack Query · shadcn/ui · Radix UI

**Testing:** pytest · Playwright E2E · Vitest · MSW

---

## License

MIT License
