# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 작업 규칙

- 모든 커뮤니케이션은 한국어로 한다
- 전문 용어 사용 시 괄호 안에 한 줄 설명 추가
- 에러 발생 시 "왜 났는지 / 어떻게 고치는지 / 다음에 피하려면" 3단계로 설명
- Key/Secret 하드코딩 금지
- 데이터 삭제/교체/마이그레이션은 "경고 + 사용자 확인" 없이 금지

## Project Overview

**Insight Engine** - YouTube 영상 URL로 다양한 AI 모델(Gemini, DeepSeek, Zhipu GLM)을 활용해 고품질 한국어 블로그 포스트를 자동 생성하는 Flask 웹 앱. LiteLLM을 통해 다중 AI 프로바이더를 통합 지원. Gemini가 기본 프로바이더.

## Commands

```bash
# 의존성 설치
pip install -r requirements.txt
npm install  # Tailwind CSS 빌드용

# 앱 실행 (개발 모드) → http://localhost:5001
python app.py

# Tailwind CSS 빌드
npm run build:css              # 개발용
npm run build:css:prod         # 프로덕션 (minify)
npm run watch:css              # 파일 변경 감지

# 단위 테스트
pytest tests/ -v
pytest tests/ -v --ignore=tests/test_ui_comprehensive.py  # UI 테스트 제외
pytest tests/test_routes_smoke.py::TestRoutesSmoke::test_generate_web_smoke -v  # 단일 함수

# E2E 테스트 (Playwright)
cd tests/e2e && npm install
npx playwright test --workers=1        # 순차 실행 (안정적, 권장)
npx playwright test --ui               # UI 모드
npx playwright test main-page/         # 특정 폴더만

# 커버리지
pytest tests/ --cov=. --cov-report=html
```

## Architecture

### Core Request Flow (단일 생성)

```
[사용자] → POST /generate
    ↓
[@require_auth] → [@require_usage] 인증 + 사용량 체크/차감
    ↓
[content_service] YouTube 자막 추출 (3단계 폴백: youtube-transcript-api → watch 페이지 파싱 → Supadata API)
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
| 라우트 | `routes/blog_routes.py` | 콘텐츠 생성 API (`/generate`, `/generate-batch`, `/regenerate`, `/api/mindmap`) |
| 라우트 | `routes/auth_routes.py` | 인증, API 키, 사용량, 관리자 API |
| 서비스 | `services/ai_service.py` | LiteLLM 래퍼, 다중 프로바이더 통합, GLM 재시도/락 |
| 서비스 | `services/content_service.py` | YouTube 자막/댓글 추출, 3단계 폴백 로직 |
| 서비스 | `services/supabase_service.py` | Supabase 인증, CRUD, 관리자 조회 |
| 서비스 | `services/usage/` | 사용량 관리 패키지 (`require_usage`, `check_usage`, `UsageService`) |
| 설정 | `config.py` | 토큰 제한, 지원 프로바이더/모델/가격, 스타일별 temperature/max_tokens 정의 |
| 프롬프트 | `prompts/` | 프롬프트 시스템 v3.1 (`build_full_prompt()`) |

### 프롬프트 구조

```
┌─────────────────────────────────────────┐
│ BASE_PROMPT (prompts/base.py)           │
│ ├─ 역할, 입력, 핵심 원칙                │
│ ├─ 작성 순서 (Chain-of-Thought)        │
│ ├─ 금지 표현, 댓글 활용 규칙            │
├─────────────────────────────────────────┤
│ STYLE_PROMPT (prompts/styles/*.py)      │
│ ├─ 스타일 목표, 작성 가이드, 출력 형식  │
│ └─ Few-shot 예시 + Output Priming       │
├─────────────────────────────────────────┤
│ MODIFIER_TEXT (선택적)                  │
├─────────────────────────────────────────┤
│ SELF_CHECK + FORBIDDEN_REMINDER         │
└─────────────────────────────────────────┘
```

- `build_full_prompt(style_id, modifiers)`: 최종 프롬프트 조합 함수
- `prompts/styles/comment_summary.py`: 병렬 댓글 요약 전용 프롬프트 (UI 비노출)

### Frontend Module Communication (EventBus)

모듈 간 통신은 `static/js/core/EventBus.js`의 Pub/Sub 패턴 사용:

```javascript
EventBus.emit(EVENTS.GENERATION_COMPLETE, { title, content });
EventBus.on(EVENTS.GENERATION_COMPLETE, (data) => this.displayReport(data));
```

주요 이벤트: `GENERATION_COMPLETE`, `STYLE_CHANGED`, `URL_ADDED`, `AUTH_STATE_CHANGED`

### Frontend Key Modules (`static/js/modules/`)

| 모듈 | 역할 |
|-----|-----|
| `ContentGenerator.js` | `/generate` API 호출, 재시도 로직 (지수 백오프) |
| `UrlManager.js` | URL 입력/삭제/드래그 정렬 |
| `ProviderManager.js` | AI 프로바이더/모델 선택 (`#provider`, `#model`) |
| `StyleManager.js` | 스타일 카드 선택 |
| `ThemeManager.js` | 테마 전환 (Dark/Light/Minimal), `localStorage: 'insight-engine-theme'` |
| `AuthManager.js` | 인증 상태 관리, 사이드바/헤더 UI 업데이트 |
| `report/` | ReportManager 분할 모듈 (CardHtmlBuilder, CardEventHandler, ReportFormatter) |

### 결과 카드 기능 (`report/`)

**카드 헤더 버튼**: 제목 복사, 전체 복사, 서식 복사 (Rich Copy: text/html + text/plain), 접기/펼치기

**카드 메타 칩**: 토큰 수, 처리 시간, 글자수, 단어수, 댓글 요약 포함/미포함

**더보기 메뉴 (⋯)**: 프롬프트 보기, 마인드맵, HTML 내보내기 (인라인 CSS 포함 독립 HTML), 다시 생성 (URL 재입력), 공유 (제목+미리보기+URL 클립보드 복사)

**필터 바** (`#card-filter-bar`): 검색 (300ms 디바운스, `<mark>` 하이라이트) + 스타일 드롭다운 필터 (AND 조건)

### 테마 시스템

3가지 테마: Dark (기본, `#1A1612`), Light (`#F9FAFB`), Minimal (`#FFFFFF`)

**핵심 규칙:**
- CSS 변수는 `base/_tokens.css`에서만 정의 (`:root`, `[data-theme="light"]`, `[data-theme="minimal"]`)
- `tailwind.css`에 `:root` 색상 정의 **없어야 함** (충돌 방지)
- `tailwind.config.js`는 `_tokens.css` 변수를 참조 (`'bg-primary': 'var(--background-dark)'`)
- 색상 하드코딩 금지 → 반드시 `var(--변수명)` 사용

**CSS 빌드 파이프라인:**
- 엔트리포인트: `static/css/main.css` → 18개 모듈 `@import`
- 출력: `static/css/dist/main.css` (PostCSS + minify)
- `dist/`는 `.gitignore`에 포함 → 커밋 불필요

**CSS 수정 워크플로우:**
1. CSS 파일 수정
2. `npm run build:css:prod` 실행 (필수)
3. 브라우저 새로고침 (캐시 무시: Ctrl+Shift+R)

> **주의**: 새 CSS 파일 추가 시 반드시 `static/css/main.css`에 `@import` 추가. 누락 시 빌드에 포함되지 않음 (과거 `features/result-section.css` 누락 버그 경험).

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

### 8개 스타일 + 댓글 요약 (v3.1)

UI에 표시되는 8개 스타일: `blog_seo`, `summary`, `tutorial`, `qna`, `app_ideas`, `yozm_it`, `brunch_essay`, `naver_popular`

내부 전용: `comment_summary` (병렬 댓글 요약용, `prompts/styles/comment_summary.py`)

> **주의**: `prompts/__init__.py`의 `get_available_styles()`는 초기 5개만 반환. 실제 전체 스타일은 `prompts/styles/__init__.py`의 `STYLE_PROMPTS` dict 참조.

### 새 스타일 추가 방법
1. `prompts/styles/` 디렉토리에 새 파일 생성 (예: `new_style.py`)
2. `prompts/styles/__init__.py`에서 import 및 `STYLE_PROMPTS`에 추가
3. `config.py`의 `STYLE_OPTIONS`에 메타데이터 추가
4. `templates/index.html`의 스타일 그리드에 UI 추가
5. `static/js/modules/StyleManager.js`의 `styleLabels`에 라벨 추가

### 지원 모델 (LiteLLM 형식)

| 프로바이더 | 모델 ID | 특이사항 |
|-----------|---------|---------|
| Gemini (기본) | `gemini/gemini-3-flash-preview` | `reasoning_effort="minimal"` |
| Gemini | `gemini/gemini-2.5-flash-lite-preview-09-2025` | reasoning_effort 미지원 |
| DeepSeek | `deepseek/deepseek-chat`, `deepseek/deepseek-reasoner` | |
| Zhipu AI | `zhipuai/GLM-4.7`, `zhipuai/GLM-4.5-Air` | OpenAI 호환 API 사용 |

- 모델 추가 시 `config.py`의 `SUPPORTED_PROVIDERS`에 `price_input`, `price_output` 필수

### 스타일 프롬프트 규칙 (`prompts/styles/`)

모든 스타일 프롬프트에 공통 적용:
- **금지 표현**: 놀라운, 혁신적, 획기적, 최고의, 게임체인저, 압도적, 경이로운, 드디어, 탁월한, 인상적, 뛰어난, 강력한
- **댓글 활용**: `[댓글]` 섹션이 입력에 없으면 시청자 반응 절대 언급 금지
- **원칙**: 자막에 있는 정보만 사용 (창작/추측 절대 금지)

### 모디파이어 (2개만 지원)

| 모디파이어 | 값 | 설명 |
|-----------|-----|------|
| `length` | short/medium/long | 글 길이 (500-800 / 1000-1500 / 2000-3000자) |
| `writing_style` | conversational/explanatory/casual/expert | 문체 |

기본값: `length: medium`, `writing_style: conversational`. 언어는 한국어 고정.

### AI 생성 파라미터 튜닝 (`config.py`)

**스타일별 temperature** (`STYLE_TEMPERATURE`):
- 정밀형 0.5: `summary`, `tutorial`, `qna`, `comment_summary`
- 균형형 0.7: `blog_seo`, `yozm_it`, `app_ideas`
- 창의형 0.85: `brunch_essay`, `naver_popular`

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

**선택**: `SUPADATA_API_KEY` (자막 마지막 폴백 - 유료), `YOUTUBE_API_KEY` (댓글), `SUPABASE_URL` + `SUPABASE_ANON_KEY` (클라우드 저장), `YT_HTTP_PROXY` / `YT_HTTPS_PROXY` (차단 우회)

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

- XSS 방지: `UIManager.sanitizeHtml()`에서 DOMPurify 사용 → HTML 콘텐츠 렌더링 시 반드시 호출
- 마크다운 테이블 폴백: `UIManager.convertMarkdownTables()` - 백엔드 변환 실패 시 프론트엔드에서 `|` 테이블을 HTML `<table>`로 변환
- 에러 응답 시 내부 정보(traceback, DB 연결 정보 등) 노출 차단: `_handle_error_response()`에서 필터링

## 히스토리 로딩

- `main.js`에서 `_historyLoaded` 플래그 + `_currentUserId` 비교로 중복 로드 방지
- `ReportManager._displayHistoryCard()`에서 `data-report-id`로 중복 카드 방지
- 초기화 순서: `onAuthChange` 콜백 설정 → `authManager.init()` → 히스토리 로드
