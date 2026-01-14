# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 작업 규칙

- 모든 커뮤니케이션은 한국어로 한다
- 전문 용어 사용 시 괄호 안에 한 줄 설명 추가
- 에러 발생 시 "왜 났는지 / 어떻게 고치는지 / 다음에 피하려면" 3단계로 설명

### 안전/보안

- Key/Secret 하드코딩 금지
- 데이터 삭제/교체/마이그레이션은 "경고 + 사용자 확인" 없이 금지

---

## Project Overview

**Insight Engine** - YouTube 영상 URL로 다양한 AI 모델(OpenAI, Claude, Gemini, GLM-4, DeepSeek)을 활용해 고품질 한국어 블로그 포스트를 자동 생성하는 Flask 웹 앱. LiteLLM을 통해 다중 AI 프로바이더를 통합 지원.

## Commands

```bash
# 의존성 설치
pip install -r requirements.txt

# 앱 실행 (개발 모드) → http://localhost:5001
python app.py

# 테스트 실행
pytest tests/ -v

# UI 테스트 제외 (Playwright 필요)
pytest tests/ -v --ignore=tests/test_ui_comprehensive.py

# 단일 테스트 파일 실행
pytest tests/test_routes_smoke.py -v

# 특정 테스트 함수 실행
pytest tests/test_routes_smoke.py::TestRoutesSmoke::test_generate_web_smoke -v

# 커버리지 리포트
pytest tests/ --cov=. --cov-report=html
```

## Architecture

### Backend Structure

```
app.py                      # Flask 앱 팩토리, 블루프린트 등록 (port 5001)
config.py                   # 토큰 제한, 지원 프로바이더/모델 정의
prompts/                    # 스타일별 프롬프트 패키지
├── __init__.py             # STYLE_PROMPTS 매핑
├── blog.py                 # blog, detailed
├── summary.py              # summary, easy
├── professional.py         # seo, news
├── creative.py             # script, sns
├── analytical.py           # needs, compare, infographic
└── structured.py           # qna, mindmap

routes/
├── blog_routes.py          # 콘텐츠 생성 API (@require_usage 데코레이터)
└── auth_routes.py          # 인증, API 키, 히스토리, 사용량 관리

services/
├── ai_service.py           # LiteLLM completion() 호출
├── content_service.py      # YouTube 자막/댓글 추출
├── supabase_service.py     # Supabase 클라이언트, 인증, CRUD
├── logging_config.py       # 통합 로거 (ServiceLogger)
├── exceptions/             # 커스텀 예외 클래스
│   └── __init__.py         # InsightEngineError, ValidationError 등
└── usage/                  # 사용량 관리
    ├── __init__.py
    ├── usage_service.py    # UsageService 클래스
    └── usage_decorator.py  # @require_usage, @check_usage
```

### Frontend Structure (ES6 모듈)

```
static/js/
├── main.js                 # 모듈 오케스트레이터
├── core/                   # 핵심 인프라
│   ├── EventBus.js         # Pub/Sub 패턴 (EVENTS 상수)
│   └── DOMCache.js         # DOM 쿼리 캐싱
├── constants/
│   └── messages.js         # 에러/알림 메시지 상수
├── services/               # 비즈니스 로직 분리
│   ├── CustomStyleService.js   # 커스텀 스타일 CRUD
│   └── GenerationContext.js    # 생성 파라미터 수집
└── modules/                # UI 모듈
    ├── StorageManager.js   # LocalStorage
    ├── ProviderManager.js  # AI 서비스/모델 선택
    ├── StyleManager.js     # 스타일 선택, 모디파이어
    ├── UrlManager.js       # URL 입력/파싱
    ├── ContentGenerator.js # API 호출
    ├── ReportManager.js    # 리포트 카드
    ├── ModalManager.js     # 모달 관리
    ├── UIManager.js        # Toast, 로딩 상태
    ├── MindmapManager.js   # 마인드맵 생성
    └── AuthManager.js      # 인증 상태
```

### API Endpoints

| 엔드포인트 | 설명 | 데코레이터 |
|-----------|------|-----------|
| `POST /generate` | 단일 URL 콘텐츠 생성 | @require_usage |
| `POST /generate-batch` | 다중 URL 배치 처리 (최대 10개) | @check_usage |
| `POST /regenerate` | 기존 콘텐츠 재생성 | @require_usage |
| `POST /api/generate-mindmap` | 마인드맵 생성 | @require_usage |
| `GET /api/providers` | AI 서비스/모델 목록 | - |
| `POST /api/recommend-style` | 스타일 추천 | - |
| `POST /api/generate-style` | 맞춤 프롬프트 생성 | - |

### Request Flow

1. 사용자 URL + API 키 입력 → `/generate` 또는 `/generate-batch`
2. `@require_usage` 데코레이터가 사용량 체크/차감
3. `content_service`가 자막 추출 (Supadata → youtube-transcript-api → watch 페이지)
4. `content_service.get_top_comments()`로 댓글 수집
5. `ai_service.create_content()`가 LiteLLM으로 AI 호출
6. JSON 응답 (title, content, html, usage)

### YouTube Transcript Handling

`content_service.py` 우선순위 폴백:
1. Supadata API (`SUPADATA_API_KEY` 설정 시)
2. `youtube-transcript-api` 라이브러리 (지수 백오프 재시도 3회)
3. watch 페이지 직접 파싱 (`_get_transcript_from_watch_page`)

### Style System

**13가지 스타일** (`prompts/`):
`blog`, `detailed`, `summary`, `easy`, `news`, `script`, `seo`, `needs`, `qna`, `infographic`, `compare`, `sns`, `mindmap`

**모디파이어** (`config.py`):
- `length`: short/medium/long
- `tone`: professional/friendly/humorous
- `language`: ko/en/ja
- `emoji`: use/none

## API Configuration

`.env.example` → `.env` 복사. API 키가 설정된 프로바이더만 UI에 표시.

```bash
# AI Provider API Keys (최소 하나 필수)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
ZHIPU_API_KEY=...
DEEPSEEK_API_KEY=...

# 선택 사항
SUPADATA_API_KEY=           # YouTube 자막 백업 서비스
YOUTUBE_API_KEY=            # 댓글/제목 조회용
SUPABASE_URL=               # 클라우드 저장
SUPABASE_ANON_KEY=          # Supabase Anonymous Key
ENCRYPTION_SECRET=          # API 키 암호화 (Fernet, 필수 설정)

# 프록시 (YouTube 자막 차단 우회용)
YT_HTTP_PROXY=http://your-proxy:port
YT_HTTPS_PROXY=http://your-proxy:port
```

## Key Patterns

- 모든 API 라우트는 실패 시 JSON `{"error": "메시지"}` 반환
- 배치 처리: `ThreadPoolExecutor` max 5 workers, 최대 10 URL
- 사용량 제한: 일반 사용자 5회/일, 관리자 무제한
- `@require_usage`: 사용량 체크 + 성공 시 자동 차감
- `@check_usage`: 사용량 체크만 (배치용)
- 커스텀 예외: `InsightEngineError` 계층 (`services/exceptions/`)
- 로깅: `ServiceLogger` 사용 (`services/logging_config.py`)

## Testing

```
tests/
├── test_routes_smoke.py                    # API 라우트 스모크 테스트
├── test_ai_service.py                      # AI 서비스 단위 테스트
├── test_config.py                          # 설정 검증 테스트
├── test_usage_service.py                   # 사용량 서비스 테스트
├── test_content_service_transcript_fallback.py  # 자막 폴백 테스트
├── test_style_prompts.py                   # 스타일 프롬프트 테스트
├── test_app_lifecycle_smoke.py             # 앱 생명주기 테스트
├── test_url_drag_sort_contract.py          # URL 드래그 정렬 테스트
└── test_ui_comprehensive.py                # UI 테스트 (Playwright 필요)
```

**테스트 작성 시 주의**: 인증이 필요한 엔드포인트 테스트 시 `is_supabase_enabled`를 mock하여 우회:
```python
@patch('services.supabase_service.is_supabase_enabled', return_value=False)
def test_example(self, mock_enabled):
    # 테스트 코드
```
