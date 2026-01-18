# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 작업 규칙

- 모든 커뮤니케이션은 한국어로 한다
- 전문 용어 사용 시 괄호 안에 한 줄 설명 추가
- 에러 발생 시 "왜 났는지 / 어떻게 고치는지 / 다음에 피하려면" 3단계로 설명
- Key/Secret 하드코딩 금지
- 데이터 삭제/교체/마이그레이션은 "경고 + 사용자 확인" 없이 금지

## Project Overview

**Insight Engine** - YouTube 영상 URL로 다양한 AI 모델(OpenAI, Claude, Gemini, GLM-4, DeepSeek)을 활용해 고품질 한국어 블로그 포스트를 자동 생성하는 Flask 웹 앱. LiteLLM을 통해 다중 AI 프로바이더를 통합 지원.

## Commands

```bash
# 의존성 설치
pip install -r requirements.txt

# 앱 실행 (개발 모드) → http://localhost:5001
python app.py

# 단위 테스트
pytest tests/ -v
pytest tests/ -v --ignore=tests/test_ui_comprehensive.py  # UI 테스트 제외
pytest tests/test_routes_smoke.py::TestRoutesSmoke::test_generate_web_smoke -v  # 단일 함수

# E2E 테스트 (Playwright)
cd tests/e2e && npm install
npx playwright test                    # 병렬 실행
npx playwright test --workers=1        # 순차 실행 (안정적)
npx playwright test --ui               # UI 모드
npx playwright test main-page/         # 특정 폴더만

# 커버리지
pytest tests/ --cov=. --cov-report=html
```

## Architecture

### Core Request Flow

```
[사용자] → POST /generate
    ↓
[@require_usage] 사용량 체크/차감 (services/usage/)
    ↓
[content_service] YouTube 자막 추출 (3단계 폴백: Supadata → youtube-transcript-api → watch 페이지 파싱)
    ↓
[content_service] 댓글 수집 (YOUTUBE_API_KEY 필요)
    ↓
[ai_service] LiteLLM completion() 호출 (프로바이더 자동 라우팅)
    ↓
JSON 응답 {title, content, html, usage}
```

### Backend Layers

| 레이어 | 파일 | 역할 |
|-------|------|-----|
| 라우트 | `routes/blog_routes.py` | 콘텐츠 생성 API, `@require_usage` 데코레이터 |
| 라우트 | `routes/auth_routes.py` | 인증, API 키, 히스토리, 사용량 관리 |
| 서비스 | `services/ai_service.py` | LiteLLM 래퍼, 다중 프로바이더 통합 |
| 서비스 | `services/content_service.py` | YouTube 자막/댓글 추출, 폴백 로직 |
| 서비스 | `services/supabase_service.py` | Supabase 인증, CRUD |
| 설정 | `config.py` | 토큰 제한, 지원 프로바이더/모델 정의 |
| 프롬프트 | `prompts/__init__.py` | `STYLE_PROMPTS` 매핑 (16개 스타일) |

### Frontend Module Communication (EventBus)

모듈 간 통신은 `static/js/core/EventBus.js`의 Pub/Sub 패턴 사용:

```javascript
// 이벤트 발행 (modules/ContentGenerator.js)
EventBus.emit(EVENTS.GENERATION_COMPLETE, { title, content });

// 이벤트 구독 (modules/ReportManager.js)
EventBus.on(EVENTS.GENERATION_COMPLETE, (data) => this.displayReport(data));
```

주요 이벤트: `EVENTS.GENERATION_COMPLETE`, `EVENTS.STYLE_CHANGED`, `EVENTS.URL_ADDED`, `EVENTS.AUTH_STATE_CHANGED`

### Frontend Key Modules (`static/js/modules/`)

| 모듈 | 역할 |
|-----|-----|
| `UrlManager.js` | URL 입력/삭제/드래그 정렬, `#url-list-container .url-card` |
| `ProviderManager.js` | AI 프로바이더/모델 선택, `#provider`, `#model` |
| `StyleManager.js` | 스타일 카드 선택 |
| `ContentGenerator.js` | `/generate` API 호출, `#run-analysis-btn` |
| `HistoryPanelManager.js` | 히스토리 뷰, `button[data-section="history"]` |
| `UsagePanelManager.js` | 사용량 뷰, `button[data-section="usage"]` |
| `ModalManager.js` | 온보딩 모달 (`#onboarding-modal`, `#onboarding-save`) |

### Usage Decorators

```python
# 사용량 체크 + 성공 시 자동 차감 (단일 요청)
@require_usage
def generate():
    ...

# 사용량 체크만 (배치용 - 개별 차감 필요)
@check_usage
def generate_batch():
    ...
```

## Key Patterns

### API 응답 형식
- 성공: `{"title": "...", "content": "...", "html": "...", "usage": {...}}`
- 실패: `{"error": "메시지"}`

### 새 스타일 추가 방법
1. `prompts/` 디렉토리에 새 파일 생성 또는 기존 파일에 추가
2. `prompts/__init__.py`의 `STYLE_PROMPTS` 딕셔너리에 매핑 추가
3. `config.py`의 `STYLE_CONFIG`에 메타데이터 추가

### 모디파이어 (`config.py`)
- `length`: short/medium/long
- `tone`: professional/friendly/humorous
- `language`: ko/en/ja
- `emoji`: use/none

## Testing

### 단위 테스트 - Supabase 인증 우회 (필수 패턴)

인증이 필요한 엔드포인트 테스트 시 반드시 mock:

```python
@patch('services.supabase_service.is_supabase_enabled', return_value=False)
def test_example(self, mock_enabled):
    # 테스트 코드
```

### E2E 테스트 (`tests/e2e/`)

Playwright 기반, 79개 테스트 케이스. `playwright.config.ts`에서 webServer가 Flask 앱 자동 실행 (Supabase 비활성화 상태).

**테스트 그룹:**
- `no-auth-chromium`: 메인 페이지, URL 입력, 접근성, 반응형
- `content-generation`: 콘텐츠 생성
- `batch-generation`: 배치 처리
- `authenticated-tests`: 히스토리, 설정, 사용량 (인증 필요 시 스킵)
- `error-handling`: 에러 케이스
- `performance`: 로드 시간

**Fixtures (`fixtures/test-fixtures.ts`):**
- `mainPage.goto()`: 페이지 이동 + 온보딩 모달 자동 닫기
- `urlInput.addUrl(url)`: URL 입력 후 Enter
- `urlInput.removeUrl(index)`: JavaScript evaluate로 삭제 버튼 클릭
- `contentGenerator.clickGenerate()`: `#run-analysis-btn` 클릭

## Configuration

`.env.example` → `.env` 복사. 상세 환경변수 설명은 `README.md` 참조.

**필수**: AI Provider API 키 최소 하나 (API 키가 설정된 프로바이더만 UI에 표시)

**선택**: `SUPADATA_API_KEY` (자막 백업), `YOUTUBE_API_KEY` (댓글), `SUPABASE_*` (클라우드 저장), `YT_*_PROXY` (차단 우회)
