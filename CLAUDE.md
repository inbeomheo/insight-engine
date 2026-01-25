# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 작업 규칙

- 모든 커뮤니케이션은 한국어로 한다
- 전문 용어 사용 시 괄호 안에 한 줄 설명 추가
- 에러 발생 시 "왜 났는지 / 어떻게 고치는지 / 다음에 피하려면" 3단계로 설명
- Key/Secret 하드코딩 금지
- 데이터 삭제/교체/마이그레이션은 "경고 + 사용자 확인" 없이 금지

## Project Overview

**Insight Engine** - YouTube 영상 URL로 다양한 AI 모델(Gemini, DeepSeek)을 활용해 고품질 한국어 블로그 포스트를 자동 생성하는 Flask 웹 앱. LiteLLM을 통해 다중 AI 프로바이더를 통합 지원. Gemini가 기본 프로바이더.

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
[content_service] YouTube 자막 추출 (3단계 폴백: youtube-transcript-api → watch 페이지 파싱 → Supadata API)
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
| 라우트 | `routes/auth_routes.py` | 인증, API 키, 사용량, 관리자 API |
| 서비스 | `services/ai_service.py` | LiteLLM 래퍼, 다중 프로바이더 통합 |
| 서비스 | `services/content_service.py` | YouTube 자막/댓글 추출, 폴백 로직 |
| 서비스 | `services/supabase_service.py` | Supabase 인증, CRUD, 관리자 조회 |
| 설정 | `config.py` | 토큰 제한, 지원 프로바이더/모델/가격 정의 |
| 프롬프트 | `prompts/__init__.py` | `STYLE_PROMPTS` 매핑 (5개 스타일) |

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
| `ThemeManager.js` | 테마 전환 (Dark/Light/Minimal), localStorage 저장 |
| `ContentGenerator.js` | `/generate` API 호출, 재시도 로직 (지수 백오프) |
| `UsagePanelManager.js` | 사용량 프로그레스 바 UI (`#usage-bar-*`) |
| `AdminDashboard.js` | 관리자 대시보드 모달 (`#admin-modal`) - 사용자/콘텐츠 관리 |
| `ModalManager.js` | 온보딩 모달 (`#onboarding-modal`, `#onboarding-save`) |
| `AuthManager.js` | 인증 상태 관리, 사이드바/헤더 UI 업데이트 |
| `report/` | ReportManager 분할 모듈 (CardHtmlBuilder, CardEventHandler, ReportFormatter) |

### CSS 모듈 구조 (`static/css/`)

```
static/css/
├── main.css              # 엔트리포인트 (@import)
├── tailwind.css          # Tailwind 입력 파일
├── tailwind.output.css   # 빌드 결과물
├── base/                 # 토큰(_tokens.css), 테마(_theme.css), 타이포그래피
├── components/           # 버튼, 카드, 모달, 알림 등
├── layouts/              # 앱 레이아웃, 사이드바, 패널
├── utilities/            # 애니메이션, 스크롤바, 접근성, 가독성(_readability.css)
└── responsive/           # 미디어 쿼리 브레이크포인트
```

**CSS 수정 워크플로우:**
1. CSS 파일 수정
2. `npm run build:css:prod` 실행 (필수)
3. 브라우저 새로고침 (캐시 무시: Ctrl+Shift+R)

### 테마 시스템 (3가지 테마 지원)

**지원 테마:**

| 테마 | `data-theme` | 배경 | 텍스트 | 특징 |
|------|-------------|------|--------|------|
| Dark (기본) | `dark` | #1A1612 | #FDFCFB | Warm Cream 다크 |
| Light | `light` | #F9FAFB | #1F2937 | 밝은 크림/화이트 |
| Minimal | `minimal` | #FFFFFF | #171717 | 흑백 미니멀 |

**CSS 변수 정의 위치:**
- `base/_tokens.css`: CSS 변수 정의 (`:root`, `[data-theme="light"]`, `[data-theme="minimal"]`)
- `base/_theme.css`: 테마별 추가 스타일, `::selection` 색상
- `tailwind.css`: CSS 변수 정의 **없음** (Tailwind 지시문만)

**테마 전환:**
```javascript
// ThemeManager.js
themeManager.applyTheme('light');  // 테마 적용
themeManager.cycleTheme();         // 순환: dark → light → minimal → dark
// localStorage 키: 'insight-engine-theme'
```

**주요 색상 변수 (Dark 테마 기준):**
```css
--primary: #D4A87A;           /* 테라코타 골드 */
--background-dark: #1A1612;   /* 따뜻한 다크 브라운 */
--surface-dark: #231E19;
--text-primary: #FDFCFB;
--text-muted: #D8CFC5;
--selection-bg: rgba(212, 168, 122, 0.5);  /* 텍스트 선택 색상 */
```

**Tailwind와 CSS 변수 동기화 (중요):**
```javascript
// tailwind.config.js - _tokens.css 변수 직접 참조
colors: {
  'bg-primary': 'var(--background-dark)',
  'primary': 'var(--primary)',
  'text-primary': 'var(--text-primary)',
}
```

**하드코딩 금지 패턴:**
```css
/* ❌ 하드코딩 */
background: #ffffff;
color: white;

/* ✅ CSS 변수 사용 */
background: var(--background-dark);
color: var(--text-primary);
```

**테마 색상 문제 디버깅:**
1. `tailwind.config.js`의 색상이 `_tokens.css` 변수를 참조하는지 확인
2. `tailwind.css`에 `:root` 색상 정의가 **없는지** 확인 (충돌 방지)
3. 빌드 후 확인: `npm run build:css:prod`
4. `<html data-theme="...">` 속성이 올바른지 확인

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

### 5개 핵심 스타일 (v3.0)

| 스타일 ID | 이름 | 설명 |
|-----------|------|------|
| `blog_seo` | 블로그+SEO | SEO 최적화된 블로그 포스트 |
| `summary` | 요약 | 핵심 내용을 빠르게 파악 |
| `tutorial` | 튜토리얼 | 단계별 학습 가이드 |
| `qna` | Q&A | 질문-답변 형식 정리 |
| `app_ideas` | 앱 아이디어 | 영상에서 개발 아이디어 추출 |

### 새 스타일 추가 방법
1. `prompts/styles/` 디렉토리에 새 파일 생성 (예: `new_style.py`)
2. `prompts/styles/__init__.py`에서 import 및 `STYLE_PROMPTS`에 추가
3. `config.py`의 `STYLE_OPTIONS`에 메타데이터 추가
4. `templates/index.html`의 스타일 그리드에 UI 추가
5. `static/js/modules/StyleManager.js`의 `styleLabels`에 라벨 추가

### 지원 모델 (LiteLLM 형식)

| 프로바이더 | 모델 ID | 가격 ($/1M tokens) |
|-----------|---------|-------------------|
| Gemini | `gemini/gemini-3-flash-preview` | $0.50 / $3.00 |
| Gemini | `gemini/gemini-2.5-flash-lite-preview-09-2025` | $0.10 / $0.40 |
| DeepSeek | `deepseek/deepseek-chat` | $0.27 / $1.10 |
| DeepSeek | `deepseek/deepseek-reasoner` | $0.55 / $2.19 |

- Gemini 모델은 `reasoning_effort="minimal"` 옵션 사용 (단, Flash Lite 모델은 미지원으로 제외)
- 모델 추가 시 `config.py`의 `SUPPORTED_PROVIDERS`에 `price_input`, `price_output` 필수

### 스타일 프롬프트 규칙 (`prompts/styles/`)

모든 스타일 프롬프트에 공통 적용:
- **금지 표현**: 놀라운, 혁신적, 획기적, 최고의, 게임체인저, 압도적, 경이로운, 드디어, 탁월한, 인상적, 뛰어난, 강력한
- **댓글 활용**: `[댓글]` 섹션이 입력에 없으면 시청자 반응 절대 언급 금지, 댓글은 본문에 자연스럽게 녹임
- **원칙**: 자막에 있는 정보만 사용 (창작/추측 절대 금지)

### 사용량 제한

- 일일 사용량: 20회 (`services/supabase_service.py`의 `MAX_USAGE_COUNT`)
- 관리자는 무제한 (999회)
- Race Condition 방지: `decrement_usage_safe` RPC 함수로 원자적 차감

### 관리자 API (`@require_auth` + `is_admin` 체크)

| 엔드포인트 | 메서드 | 설명 |
|-----------|--------|------|
| `/api/admin/users` | GET | 전체 사용자 사용량 조회 |
| `/api/admin/users/<user_id>/reset` | POST | 특정 사용자 사용량 리셋 |
| `/api/admin/stats` | GET | 사용량 통계 (전체/오늘/소진) |
| `/api/admin/contents` | GET | 모든 생성 콘텐츠 조회 (페이지네이션) |
| `/api/admin/contents/<report_id>` | GET | 특정 콘텐츠 상세 조회 |

### 모디파이어 (v3.0 - 2개만 지원)

| 모디파이어 | 값 | 설명 |
|-----------|-----|------|
| `length` | short/medium/long | 글 길이 (500-800 / 1000-1500 / 2000-3000자) |
| `writing_style` | conversational/explanatory/casual/expert | 문체 (대화체/설명체/캐주얼/전문가) |

- 기본값: `length: medium`, `writing_style: conversational`
- 언어는 한국어 고정 (다국어 지원 제거됨)

## Testing

### 단위 테스트 - Supabase 인증 우회 (필수 패턴)

인증이 필요한 엔드포인트 테스트 시 반드시 mock:

```python
@patch('services.supabase_service.is_supabase_enabled', return_value=False)
def test_example(self, mock_enabled):
    # 테스트 코드
```

### E2E 테스트 (`tests/e2e/`)

Playwright 기반. `playwright.config.ts`에서 webServer가 Flask 앱 자동 실행 (Supabase 비활성화 상태).

**테스트 그룹:**
- `no-auth-chromium`: 메인 페이지, URL 입력, 접근성, 반응형, 모달
- `content-generation`: 콘텐츠 생성
- `batch-generation`: 배치 처리
- `authenticated-tests`: 설정, 사용량, 관리자 기능 (인증 필요 시 스킵)
- `error-handling`: 에러 케이스
- `performance`: 로드 시간

**Fixtures (`fixtures/test-fixtures.ts`):**
- `mainPage.goto()`: 페이지 이동 + 온보딩 모달 자동 닫기
- `urlInput.addUrl(url)`: URL 입력 후 Enter
- `urlInput.removeUrl(index)`: JavaScript evaluate로 삭제 버튼 클릭
- `contentGenerator.clickGenerate()`: `#run-analysis-btn` 클릭

**E2E 테스트 실행 시 주의사항:**
```bash
# 병렬 실행 시 Flask 서버 타임아웃 발생 가능 → workers=1 권장
npx playwright test --workers=1

# 특정 폴더만 실행
npx playwright test settings-modals/ main-page/
```

**자주 발생하는 테스트 오류:**
- `strict mode violation`: 여러 요소 매칭 시 더 구체적인 선택자 사용
- 서버 타임아웃: `--workers=1`로 실행
- localStorage 키 불일치: 여러 키 시도 또는 UI에서 직접 확인

## Configuration

`.env.example` → `.env` 복사. 상세 환경변수 설명은 `README.md` 참조.

**필수**: AI Provider API 키 최소 하나 (API 키가 설정된 프로바이더만 UI에 표시)

**선택**: `SUPADATA_API_KEY` (자막 마지막 폴백 - 유료), `YOUTUBE_API_KEY` (댓글), `SUPABASE_*` (클라우드 저장), `YT_*_PROXY` (차단 우회)

## Supabase 설정

### 테이블 (ie_ 접두사)

| 테이블 | 용도 |
|--------|------|
| `ie_usage` | 일일 사용량 (usage_count, last_reset_date) |
| `ie_histories` | 분석 히스토리 (콘텐츠, HTML, 자막 미리보기) |
| `ie_api_keys` | 사용자별 암호화된 API 키 |
| `ie_custom_styles` | 커스텀 스타일 프롬프트 |
| `ie_admins` | 관리자 목록 |

### 뷰 (관리자용)

- `ie_usage_with_email`: 사용량 + 이메일 조인
- `ie_histories_with_email`: 히스토리 + 이메일 조인

### RPC 함수

```sql
-- 원자적 사용량 차감 (Race Condition 방지)
SELECT decrement_usage_safe('user-uuid');
-- 반환: {"success": true, "new_count": 19} 또는 {"success": false, "reason": "no_usage_left"}
```

### 스키마 적용

```bash
# Supabase SQL Editor에서 실행
# 파일: supabase/schema.sql
```

## Security

- XSS 방지: `UIManager.sanitizeHtml()`에서 DOMPurify 사용
- HTML 콘텐츠 렌더링 시 반드시 `sanitizeHtml()` 호출
- 마크다운 테이블 폴백: `UIManager.convertMarkdownTables()` - 백엔드 변환 실패 시 프론트엔드에서 `|` 테이블을 HTML `<table>`로 변환

## Result Card Structure

결과 카드는 통합 컴팩트 디자인 (`result-card--unified`):
```
┌─────────────────────────────────────┐
│ [스타일뱃지] 12:34  [복사][복사][↑] │  ← unified-header (collapse-btn)
│ 제목                                │
│ ▶ youtu.be/xxx                      │
├─────────────────────────────────────┤
│ 본문 내용 (report-content)          │  ← unified-body
├─────────────────────────────────────┤
│ [토큰] [시간]  저장 [⋯] 삭제        │  ← unified-footer
└─────────────────────────────────────┘
        └─ 더보기 메뉴 (프롬프트/마인드맵)
```

- `CardHtmlBuilder.buildReportCardHtml()` - HTML 템플릿 생성
- `_cards.css` - 통합 카드 스타일, 더보기 메뉴 (`.more-actions-btn`)
- `_report-content.css` - 본문 타이포그래피

### 카드 접기/펼치기 기능

**개별 카드 접기:**
- 각 카드 헤더의 `collapse-btn` 클릭
- `.collapsed` 클래스 토글 → unified-body, unified-footer 숨김
- 접힌 상태: 패딩 축소, 제목 작게, 소스 링크 숨김

**모두 접기/펼치기:**
- 결과 패널 헤더의 `#collapse-all-btn` 버튼
- `ReportManager.toggleCollapseAll()` - 모든 카드 토글
- 버튼 상태 자동 동기화: 개별 카드 변경 시 `syncCollapseAllButtonState()` 호출

```javascript
// 모두 접기 토글
reportManager.toggleCollapseAll();

// 버튼 텍스트/아이콘 상태
// 펼쳐진 카드 있음 → "모두 접기" (unfold_less)
// 모두 접힘 → "모두 펼치기" (unfold_more)
```

## 히스토리 로딩 최적화

### 중복 로드 방지 (`main.js`)

```javascript
// 플래그로 중복 로드 방지
this._historyLoaded = false;
this._currentUserId = null;

// 계정 변경 시에만 다시 로드
this.authManager.onAuthChange = async (isLoggedIn, user) => {
    const newUserId = user?.id || null;
    if (this._currentUserId !== newUserId) {
        this._currentUserId = newUserId;
        this._historyLoaded = false;
        this._clearReportStream();
        await this.reportManager.loadHistory();
        this._historyLoaded = true;
    }
};
```

### 중복 카드 방지 (`ReportManager.js`)

```javascript
_displayHistoryCard(data) {
    // 이미 같은 ID의 카드가 있으면 스킵
    if (this.elements.reportStream.querySelector(`[data-report-id="${data.id}"]`)) {
        return;
    }
    // ...
}
```

### 초기화 순서 (중요)

1. `onAuthChange` 콜백 설정 (init 전에!)
2. `authManager.init()` - `INITIAL_SESSION` 이벤트 발생
3. 로그인 상태면 클라우드 히스토리 로드, `_historyLoaded = true`
4. 마지막 `loadHistory()` 호출 시 `_historyLoaded` 체크로 스킵
