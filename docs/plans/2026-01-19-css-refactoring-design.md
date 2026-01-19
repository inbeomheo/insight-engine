# CSS 리팩토링 설계

**날짜:** 2026-01-19
**목표:** 유지보수성 향상 - 인라인 CSS를 외부 파일로 분리

## 현재 상태

- `templates/index.html`: 6,274줄
- 인라인 CSS: ~4,900줄 (116줄 ~ 5025줄)
- Tailwind CDN 사용 중
- `static/css/` 폴더 존재하나 미사용

## 최종 파일 구조

```
static/css/
├── base/
│   ├── variables.css      # CSS 변수 (--primary, --background-dark 등)
│   └── typography.css     # 폰트, 텍스트 스타일
├── layout/
│   ├── sidebar.css        # 사이드바 네비게이션
│   ├── header.css         # 상단 헤더 바
│   └── panels.css         # input-panel, result-panel
├── components/
│   ├── buttons.css        # 버튼 스타일
│   ├── cards.css          # 스타일 카드, URL 카드
│   ├── forms.css          # 입력 필드, 라디오, 체크박스
│   └── modals.css         # 모달, 토스트 알림
├── features/
│   ├── url-section.css    # URL 입력 섹션
│   ├── style-section.css  # 스타일 선택 섹션
│   └── result-section.css # 결과 표시 영역
├── themes/
│   └── dark.css           # [data-theme="dark"] 오버라이드
├── animations.css         # 키프레임, 트랜지션
├── tailwind.css           # Tailwind 지시문 (기존)
├── main.css               # 모든 파일 @import (엔트리포인트)
└── dist/
    └── main.css           # 빌드 결과물
```

## 빌드 설정

### postcss.config.js

```javascript
module.exports = {
  plugins: {
    'postcss-import': {},
    tailwindcss: {},
    autoprefixer: {},
    cssnano: { preset: 'default' }
  },
}
```

### package.json 스크립트

```json
{
  "scripts": {
    "build:css": "postcss static/css/main.css -o static/css/dist/main.css",
    "build:css:prod": "NODE_ENV=production postcss static/css/main.css -o static/css/dist/main.css",
    "watch:css": "postcss static/css/main.css -o static/css/dist/main.css --watch"
  }
}
```

### main.css (엔트리포인트)

```css
/* Base */
@import "./base/variables.css";
@import "./base/typography.css";

/* Tailwind */
@import "tailwindcss/base";
@import "tailwindcss/components";
@import "tailwindcss/utilities";

/* Layout */
@import "./layout/sidebar.css";
@import "./layout/header.css";
@import "./layout/panels.css";

/* Components */
@import "./components/buttons.css";
@import "./components/cards.css";
@import "./components/forms.css";
@import "./components/modals.css";

/* Features */
@import "./features/url-section.css";
@import "./features/style-section.css";
@import "./features/result-section.css";

/* Animations */
@import "./animations.css";

/* Themes */
@import "./themes/dark.css";
```

### 추가 설치

```bash
npm install -D postcss-import cssnano postcss-cli
```

## 마이그레이션 계획

### 1단계: 준비 (빌드 환경)

- `npm install -D postcss-import cssnano postcss-cli`
- `postcss.config.js` 수정
- `package.json` 스크립트 수정
- `static/css/dist/` 폴더 생성
- `.gitignore`에 `static/css/dist/` 추가

### 2단계: CSS 추출 및 분류

- `index.html`의 `<style>` 블록(4,900줄)을 분석
- 기능별로 분류하여 각 파일에 배치:
  - CSS 변수 → `base/variables.css`
  - 레이아웃 → `layout/*.css`
  - 컴포넌트 → `components/*.css`
  - 다크 모드 → `themes/dark.css`
- `main.css`에 import 순서 정리

### 3단계: HTML 수정

- 인라인 `<style>` 블록 제거
- Tailwind CDN `<script>` 제거
- `<link rel="stylesheet" href="/static/css/dist/main.css">` 추가

### 4단계: 검증

- 로컬에서 `npm run watch:css` 실행
- 라이트/다크 모드 테스트
- 모든 섹션 UI 확인
- 기존 E2E 테스트 실행

## 위험 요소 및 대응

| 위험 | 대응 |
|------|------|
| CSS 순서 변경으로 스타일 깨짐 | import 순서 주의, 단계별 테스트 |
| Tailwind 클래스 누락 | tailwind.config.js content 경로 확인 |
| 다크 모드 동작 안 함 | `[data-theme="dark"]` 선택자 유지 확인 |
| Railway 배포 실패 | 빌드 스크립트를 배포 전 실행 필요 |

## 롤백 계획

- 작업 전 별도 브랜치에서 진행 (`refactor/css-separation`)
- 문제 발생 시 `git checkout master`로 즉시 복구
- 인라인 CSS 원본은 커밋 히스토리에 보존됨

## Railway 배포 설정

```json
{
  "build": {
    "builder": "NIXPACKS",
    "buildCommand": "npm install && npm run build:css:prod"
  }
}
```
