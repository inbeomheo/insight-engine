# Insight Engine - AI 콘텐츠 분석 도구

YouTube 영상 URL을 입력하면 다양한 AI 모델(Gemini, DeepSeek, Zhipu GLM, Ollama)을 활용하여 고품질 콘텐츠를 자동으로 생성하는 Flask + Next.js 웹 애플리케이션입니다.

## 주요 기능

- **다중 AI 프로바이더**: Gemini, DeepSeek, Zhipu GLM + **Ollama (로컬 LLM)**
- **13가지 출력 스타일**: 블로그+SEO, 요약, 튜토리얼, Q&A, SNS, 뉴스레터, **GEO (AI검색 최적화)**, **Shorts 클립** 등
- **다국어 출력**: 한국어, 영어, 일본어 선택
- **배치 / 합치기 / 퓨전 분석**: 최대 10개 URL 동시 처리
- **Whisper 자막 폴백**: YouTube 자막 API 실패 시 로컬 음성인식
- **파이프라인 자동화**: 자막 추출 → 콘텐츠 생성 → SEO 최적화 자동 진행
- **MCP 플러그인**: Naver Blog, WordPress 자동 발행
- **예약 캘린더**: 콘텐츠 예약 발행 + 월간 캘린더 UI
- **팀 협업**: 워크스페이스 기반 멤버 관리 (Owner/Editor/Viewer)
- **RAG 지식 참조**: txt/md/pdf 업로드 → 콘텐츠 생성 시 자동 참조
- **웹훅 알림**: 생성 완료 시 외부 서비스 알림
- **마인드맵 / 실시간 스트리밍 / 커스텀 스타일**

---

## 빠른 시작

### 1. 필수 요구사항
- Python 3.8 이상
- AI Provider API 키 (최소 하나 필수)

### 2. 설치

```bash
# 저장소 클론
git clone <repository-url>
cd insight-engine

# 가상환경 생성 (권장)
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

# 백엔드 의존성
pip install -r requirements.txt

# 프론트엔드 의존성
cd frontend && npm install && cd ..
```

### 3. 환경변수 설정

`.env.example` 파일을 `.env`로 복사하고 API 키를 설정합니다:

```bash
cp .env.example .env
```

`.env` 파일 예시:
```env
# AI Provider API Keys (최소 하나 필수)
GEMINI_API_KEY=AIza...
DEEPSEEK_API_KEY=sk-...
ZHIPUAI_API_KEY=...

# Ollama 로컬 LLM (선택)
OLLAMA_BASE_URL=http://localhost:11434

# 선택 사항
SUPADATA_API_KEY=            # 자막 백업 서비스
YOUTUBE_API_KEY=             # 댓글 수집용
WEBHOOK_URL=                 # 생성 완료 알림 웹훅
```

> **중요**: API 키가 설정된 프로바이더만 UI에 표시됩니다. Ollama는 OLLAMA_BASE_URL 설정 시 활성화됩니다.

### 4. 실행

```bash
# 백엔드 (Flask) — http://localhost:5001
python app.py

# 프론트엔드 (Next.js) — http://localhost:3000
cd frontend && npm run dev
```

브라우저에서 http://localhost:3000 접속

---

## 환경변수 상세 설명

### AI Provider API Keys (최소 하나 필수)

| 환경변수 | 설명 | 발급처 |
|---------|------|-------|
| `OPENAI_API_KEY` | OpenAI API 키 (GPT-4o, GPT-4 Turbo 등) | [platform.openai.com](https://platform.openai.com/api-keys) |
| `ANTHROPIC_API_KEY` | Anthropic API 키 (Claude Sonnet, Haiku 등) | [console.anthropic.com](https://console.anthropic.com/settings/keys) |
| `GEMINI_API_KEY` | Google Gemini API 키 | [aistudio.google.com](https://aistudio.google.com/apikey) |
| `ZHIPU_API_KEY` | Zhipu AI API 키 (GLM-4 등) | [open.bigmodel.cn](https://open.bigmodel.cn/usercenter/apikeys) |
| `DEEPSEEK_API_KEY` | DeepSeek API 키 | [platform.deepseek.com](https://platform.deepseek.com/api_keys) |

### 선택 환경변수

| 환경변수 | 설명 | 발급처 |
|---------|------|-------|
| `OLLAMA_BASE_URL` | Ollama 로컬 LLM URL | `http://localhost:11434` |
| `SUPADATA_API_KEY` | YouTube 자막 백업 서비스 | [supadata.ai](https://supadata.ai/) |
| `YOUTUBE_API_KEY` | YouTube 댓글 수집용 | [Google Cloud Console](https://console.cloud.google.com/apis/credentials) |
| `WEBHOOK_URL` | 콘텐츠 생성 완료 웹훅 | 사용자 설정 |
| `WHISPER_ENABLED` | Whisper 자막 폴백 활성화 | `true` / `false` (기본 비활성) |
| `RAG_ENABLED` | RAG 지식 참조 활성화 | `true` / `false` (기본 비활성) |
| `SUPABASE_URL` | Supabase 프로젝트 URL | [Supabase Dashboard](https://supabase.com/) |
| `SUPABASE_ANON_KEY` | Supabase Anonymous Key | Supabase Dashboard > Settings > API |

### 프록시 설정 (선택)

YouTube 자막 수집이 차단되는 환경에서 사용:

```env
YT_HTTP_PROXY=http://your-proxy:port
YT_HTTPS_PROXY=http://your-proxy:port
```

---

## 프로젝트 구조

```
insight-engine/
├── app.py                      # Flask 앱 진입점 (포트 5001)
├── config.py                   # 프로바이더/스타일/모디파이어 설정
├── requirements.txt            # Python 의존성
├── .env.example                # 환경변수 템플릿
│
├── routes/
│   ├── blog_routes.py          # 콘텐츠 생성/파이프라인/MCP/예약/지식 API
│   └── auth_routes.py          # 인증/워크스페이스 API
│
├── services/
│   ├── ai_service.py           # LiteLLM 기반 AI 호출 (다국어, RAG 주입)
│   ├── content_service.py      # YouTube 자막/댓글 추출 (4단계 폴백)
│   ├── whisper_service.py      # faster-whisper 로컬 음성인식
│   ├── pipeline_service.py     # 파이프라인 자동화 (SSE 스트리밍)
│   ├── webhook_service.py      # 웹훅 알림 (fire-and-forget)
│   ├── schedule_service.py     # 예약 발행 관리
│   ├── scheduler_worker.py     # APScheduler 백그라운드 워커
│   ├── workspace_service.py    # 팀 협업/워크스페이스 관리
│   ├── mcp/                    # MCP 플러그인 시스템
│   │   ├── plugin_interface.py # 추상 플러그인 인터페이스
│   │   ├── registry.py         # 플러그인 레지스트리
│   │   └── plugins/            # Naver Blog, WordPress
│   └── rag/                    # RAG 지식 참조
│       ├── vector_store.py     # ChromaDB 벡터 스토어
│       ├── chunker.py          # 텍스트 청킹/파일 추출
│       └── context_builder.py  # RAG 컨텍스트 빌더
│
├── prompts/
│   ├── base.py                 # 기본 프롬프트
│   └── styles/                 # 13개 스타일 프롬프트
│
├── frontend/                   # Next.js 16 + Tailwind v4 + shadcn
│   ├── app/page.tsx            # 메인 페이지
│   ├── components/             # UI 컴포넌트
│   ├── hooks/                  # 커스텀 훅
│   ├── stores/                 # Zustand 상태 관리
│   └── lib/                    # API, 타입, 유틸
│
└── supabase/schema.sql         # Supabase 스키마 (인증, 예약, 워크스페이스)
```

---

## API 엔드포인트

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/generate` | POST | 단일 URL 콘텐츠 생성 |
| `/generate-batch` | POST | 다중 URL 배치 처리 (최대 10개) |
| `/regenerate` | POST | 기존 콘텐츠 재생성 |
| `/api/providers` | GET | 사용 가능한 AI 서비스 목록 |
| `/api/mindmap` | POST | 마인드맵 마크다운 생성 |
| `/api/generate-multi` | POST | 1 URL × N 스타일 동시 생성 |
| `/api/pipeline` | POST | 파이프라인 자동화 (SSE) |
| `/api/mcp/plugins` | GET | MCP 플러그인 목록 |
| `/api/mcp/publish` | POST | MCP 플러그인으로 발행 |
| `/api/schedule` | POST/GET/DELETE | 예약 발행 관리 |
| `/api/knowledge/upload` | POST | RAG 지식 문서 업로드 |
| `/api/knowledge/list` | GET | 업로드된 문서 목록 |
| `/api/knowledge/<id>` | DELETE | 문서 삭제 |
| `/api/ollama/health` | GET | Ollama 연결 상태 확인 |
| `/api/workspaces` | GET/POST | 워크스페이스 관리 |

---

## 지원 AI 모델

| 프로바이더 | 모델 | 비고 |
|-----------|------|------|
| **Gemini** (기본) | gemini-3-flash-preview, gemini-2.5-flash-lite | reasoning_effort 지원 |
| **DeepSeek** | deepseek-chat (V3), deepseek-reasoner (R1) | |
| **Zhipu AI** | GLM-4.7, GLM-4.5-Air | OpenAI 호환 API |
| **Ollama** (로컬) | llama3.2, mistral, gemma2 | API 키 불필요, URL만 설정 |

---

## 배포

### Railway

1. GitHub 저장소 연결
2. Variables 탭에서 환경변수 설정
3. 자동 배포

### 수동 배포

```bash
# 프로덕션 모드
export FLASK_ENV=production
export FLASK_DEBUG=0
python app.py
```

---

## 테스트

```bash
# 전체 단위 테스트
python -m pytest tests/ -v

# E2E 테스트 (Playwright)
cd tests/e2e && npx playwright test --workers=1

# 개별 기능 테스트
python -m pytest tests/test_rag_service.py -v         # RAG
python -m pytest tests/test_ollama_provider.py -v     # Ollama
python -m pytest tests/test_webhook_service.py -v     # 웹훅
python -m pytest tests/test_pipeline_service.py -v    # 파이프라인
python -m pytest tests/test_mcp_plugins.py -v         # MCP
python -m pytest tests/test_schedule_service.py -v    # 예약 발행
python -m pytest tests/test_workspace_service.py -v   # 워크스페이스
```

---

## 문제 해결

### AI 서비스가 표시되지 않음
- `.env` 파일에 해당 프로바이더의 API 키가 설정되어 있는지 확인
- API 키가 유효한지 확인

### YouTube 자막 수집 실패
- `SUPADATA_API_KEY`를 설정하여 백업 서비스 사용
- 프록시 설정 (`YT_HTTP_PROXY`, `YT_HTTPS_PROXY`)

### 댓글이 수집되지 않음
- `YOUTUBE_API_KEY`가 설정되어 있는지 확인
- YouTube Data API v3가 활성화되어 있는지 확인

---

## 보안 주의사항

- **API 키는 절대 공개 저장소에 커밋하지 마세요**
- `.env` 파일은 `.gitignore`에 포함되어 있습니다
- 프로덕션 환경에서는 환경변수로 직접 설정하세요

---

## 라이선스

MIT License
