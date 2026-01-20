# Insight Engine 코드 리뷰 문서

> 리뷰 일자: 2026-01-20
> 대상: `templates/index.html` + `static/js/modules/` 전체

---

## 목차
1. [templates/index.html](#1-templatesindexhtml)
2. [main.js (진입점)](#2-mainjs-진입점)
3. [AuthManager.js](#3-authmanagerjs)
4. [ContentGenerator.js](#4-contentgeneratorjs)
5. [UIManager.js](#5-uimanagerjs)
6. [UrlManager.js](#6-urlmanagerjs)
7. [ProviderManager.js](#7-providermanagerjs)
8. [StyleManager.js](#8-stylemanagerjs)
9. [ReportManager.js](#9-reportmanagerjs)
10. [ModalManager.js](#10-modalmanagerjs)
11. [StorageManager.js](#11-storagemanagerjs)
12. [HistoryPanelManager.js](#12-historypanelmanagerjs)
13. [UsagePanelManager.js](#13-usagepanelmanagerjs)
14. [ThemeManager.js](#14-thememanagerjs)
15. [MindmapManager.js](#15-mindmapmanagerjs)
16. [PanelResizeManager.js](#16-panelresizemanagerjs)
17. [KeyboardNavigationManager.js](#17-keyboardnavigationmanagerjs)
18. [종합 평가](#18-종합-평가)

---

## 1. templates/index.html

### 현재 상태 분석
- **규모**: 약 2,500줄 이상의 대형 단일 파일
- **구조**: HTML + 인라인 Tailwind 설정 + 1,000줄 이상의 `<style>` 블록
- **기능**: FOUC 방지 스크립트, WCAG AA 색상 대비, 다크/라이트 테마, Creative Studio 디자인 시스템

**장점:**
- WCAG AA 접근성 기준 충족 (색상 대비 4.5:1 이상)
- CSS 변수를 활용한 체계적인 테마 시스템
- 타이포그래피 스케일 일관성 (최소 14px 보장)
- 스켈레톤 로딩, 애니메이션 등 UX 고려

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **높음** | CSS가 HTML에 인라인으로 포함됨 | 유지보수 어려움, 캐싱 불가 |
| **높음** | 파일 크기가 너무 큼 (64K+ 토큰) | 초기 로딩 지연 |
| **중간** | Tailwind CDN 사용 | 프로덕션에서 성능 이슈, 버전 관리 어려움 |
| **중간** | 반복되는 CSS 패턴 | 코드 중복 |
| **낮음** | 일부 하드코딩된 색상값 | 테마 일관성 저하 가능 |

### 개선안
1. **CSS 분리**: `<style>` 블록을 `static/css/main.css`로 추출
   ```
   /static/css/
   ├── base.css          # 변수, 리셋
   ├── components.css    # 카드, 버튼, 모달 등
   ├── layouts.css       # 그리드, 패널
   └── animations.css    # 애니메이션
   ```

2. **Tailwind 빌드 도입**: CDN 대신 PostCSS 빌드 파이프라인 구성
   ```bash
   npx tailwindcss -i ./src/input.css -o ./static/css/output.css --minify
   ```

3. **컴포넌트 템플릿화**: Jinja2 매크로 또는 include로 반복 요소 분리

---

## 2. main.js (진입점)

### 현재 상태 분석
- **역할**: 오케스트레이터 - 모든 모듈 초기화 및 연결
- **구조**: `ContentAnalysis` 클래스 + 간단한 EventBus 패턴
- **라인 수**: ~540줄

**장점:**
- 명확한 모듈 의존성 주입 패턴
- 초기화 순서가 잘 정리됨
- EventBus를 통한 느슨한 결합

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **중간** | EventBus가 main.js 내부에 인라인 정의 | 재사용 어려움 |
| **중간** | `handleAiAnalyze`, `handleGenerateStyle`이 main에 있음 | 관심사 분리 부족 |
| **낮음** | DOM 조작 코드가 일부 포함 | 모듈 경계 모호 |

### 개선안
1. **EventBus 분리**: `static/js/core/EventBus.js`가 이미 존재하므로 이것을 사용
2. **기능 이동**: AI 분석/스타일 생성 로직을 `ContentGenerator`로 이동
3. **설정 객체 도입**: 모듈 설정을 별도 config 객체로 관리

---

## 3. AuthManager.js

### 현재 상태 분석
- **역할**: Supabase 인증, OAuth PKCE 플로우
- **라인 수**: ~540줄
- **패턴**: SDK 기반 인증 + 서버 API 하이브리드

**장점:**
- PKCE OAuth 자동 처리
- 세션 자동 갱신
- 깔끔한 UI 상태 관리
- 하위 호환성 메서드 유지

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **높음** | `_fetchJson`에서 에러 객체 구조 불일치 | 디버깅 어려움 |
| **중간** | 모달 이벤트 중복 등록 방지 플래그(`_modalEventsSetup`)가 불안정 | 잠재적 메모리 누수 |
| **낮음** | 일부 하드코딩된 문자열 | 국제화 어려움 |

### 개선안
```javascript
// 개선: 에러 처리 일관성
async _fetchJson(url, options = {}) {
    try {
        const response = await fetch(url, { ... });
        const data = await response.json();
        return {
            ok: response.ok,
            status: response.status,
            data
        };
    } catch (error) {
        return {
            ok: false,
            status: 0,
            data: { error: error.message },
            networkError: true
        };
    }
}
```

---

## 4. ContentGenerator.js

### 현재 상태 분석
- **역할**: API 호출, 단일/배치 URL 처리
- **라인 수**: ~210줄
- **구조**: 단순하고 명확한 책임

**장점:**
- 백그라운드 처리로 UX 개선
- 인증 헤더 자동 첨부
- 에러 상태별 적절한 처리

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **중간** | `processSingleUrl`과 `processUrlInBackground` 중복 로직 | 유지보수성 저하 |
| **중간** | 재시도 로직 없음 | 일시적 네트워크 오류에 취약 |
| **낮음** | 배치 처리 시 동시 요청 제한 없음 | 서버 과부하 가능 |

### 개선안
1. **공통 로직 추출**: 요청 생성 부분을 private 메서드로 분리
2. **재시도 로직 추가**: 지수 백오프로 최대 3회 재시도
3. **동시성 제한**: `Promise.all`에 동시 요청 수 제한 추가

---

## 5. UIManager.js

### 현재 상태 분석
- **역할**: 알림, 로딩 상태, 유틸리티 함수
- **라인 수**: ~250줄

**장점:**
- XSS 방지 (`escapeHtml`, `sanitizeUrl`, `sanitizeHtml`)
- 알림 자동 제거
- 일관된 로딩 상태 관리

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **낮음** | `sanitizeHtml`이 기본적인 패턴만 처리 | 복잡한 XSS 우회 가능 |
| **낮음** | 알림 컨테이너가 없으면 무시 | 조용한 실패 |

### 개선안
```javascript
// 더 강력한 sanitize를 위해 DOMPurify 사용 권장
import DOMPurify from 'dompurify';

sanitizeHtml(html) {
    return DOMPurify.sanitize(html, {
        ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
        ALLOWED_ATTR: ['href', 'target', 'rel']
    });
}
```

---

## 6. UrlManager.js

### 현재 상태 분석
- **역할**: URL 추가/삭제, 드래그앤드롭
- **라인 수**: ~140줄

**장점:**
- 최대 URL 수 제한 (10개)
- 중복 URL 방지
- 드래그앤드롭으로 순서 변경

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **낮음** | URL 유효성 검사가 정규식만 의존 | 비정상 URL 허용 가능 |
| **낮음** | 드래그 상태가 인스턴스 변수로 관리 | 다중 드래그 시 문제 가능 |

### 개선안
```javascript
// URL 유효성 추가 검증
addUrl(url) {
    url = url.trim();
    try {
        const urlObj = new URL(url);
        if (!['http:', 'https:'].includes(urlObj.protocol)) return false;
    } catch {
        return false;
    }
    // ... 기존 로직
}
```

---

## 7. ProviderManager.js

### 현재 상태 분석
- **역할**: AI 프로바이더/모델 선택 관리
- **라인 수**: ~190줄

**장점:**
- 서버에서 사용 가능한 프로바이더만 로드
- 설정 자동 복원
- 깔끔한 select 동기화

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **낮음** | 프로바이더 로드 실패 시 재시도 없음 | 초기화 실패 가능 |
| **낮음** | 기본 프로바이더가 하드코딩 ('gemini') | 설정 의존성 |

### 개선안
- 프로바이더 목록을 config에서 관리
- 로드 실패 시 재시도 + 오프라인 캐시

---

## 8. StyleManager.js

### 현재 상태 분석
- **역할**: 스타일 선택, 커스텀 스타일, 모디파이어
- **라인 수**: ~250줄

**장점:**
- 키보드 네비게이션 지원
- 터치 이벤트 지원
- 언어 칩과 select 동기화

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **중간** | `styleLabels`가 영어로 하드코딩 | UI 일관성 저하 |
| **낮음** | 커스텀 스타일 편집 버튼이 hover에만 표시 | 모바일에서 접근 어려움 |

### 개선안
```javascript
// 스타일 라벨을 서버/config에서 관리
async loadStyleLabels() {
    const response = await fetch('/api/style-labels');
    this.styleLabels = await response.json();
}
```

---

## 9. ReportManager.js

### 현재 상태 분석
- **역할**: 리포트 카드 생성, 표시, 히스토리
- **라인 수**: ~630줄 (가장 큰 모듈)

**장점:**
- 새로운 Result Card 시스템 (제목/본문/메타 분리)
- 스켈레톤 로딩 UI
- 복사 버튼 피드백

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **높음** | HTML 템플릿이 문자열로 하드코딩 | 유지보수 매우 어려움 |
| **중간** | 파일이 너무 큼 (600줄+) | 가독성 저하 |
| **중간** | `_build*Html` 메서드들이 길고 복잡 | 테스트 어려움 |

### 개선안
1. **템플릿 분리**: HTML 템플릿을 별도 파일로 분리
   ```
   /templates/components/
   ├── pending-card.html
   ├── result-card.html
   └── error-card.html
   ```

2. **클래스 분리**:
   ```javascript
   // ReportCardBuilder.js - 카드 HTML 생성
   // ReportCardEvents.js - 이벤트 핸들링
   // ReportManager.js - 오케스트레이션
   ```

---

## 10. ModalManager.js

### 현재 상태 분석
- **역할**: Settings, Onboarding, Custom Style 모달 관리
- **라인 수**: ~450줄

**장점:**
- ESC 키로 모달 닫기
- 모달 우선순위 관리
- 이벤트 리스너 중복 등록 방지 (cloneNode 패턴)

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **중간** | 각 모달별 메서드가 유사한 패턴 반복 | 코드 중복 |
| **낮음** | 프롬프트 길이 제한이 클라이언트에서만 검증 | 서버 검증 필요 |

### 개선안
```javascript
// 제네릭 모달 핸들러
class GenericModal {
    constructor(id, options = {}) {
        this.modal = document.getElementById(id);
        this.closeBtn = this.modal.querySelector('[data-close]');
        // ...
    }
    show() { ... }
    hide() { ... }
}
```

---

## 11. StorageManager.js

### 현재 상태 분석
- **역할**: localStorage 관리
- **라인 수**: ~170줄

**장점:**
- 버전 관리 키 사용 (`cad_*_v1`)
- 최대 항목 수 제한
- 에러 처리 포함

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **중간** | localStorage 용량 초과 처리 없음 | 데이터 손실 가능 |
| **낮음** | 히스토리 항목이 커지면 성능 저하 | 느린 로드/저장 |

### 개선안
```javascript
saveHistory(history) {
    try {
        const json = JSON.stringify(history);
        if (json.length > 4 * 1024 * 1024) { // 4MB 제한
            // 오래된 항목부터 삭제
            history = history.slice(0, Math.floor(history.length / 2));
        }
        localStorage.setItem(this.keys.history, JSON.stringify(history));
    } catch (e) {
        if (e.name === 'QuotaExceededError') {
            this.clearOldHistory();
        }
    }
}
```

---

## 12. HistoryPanelManager.js

### 현재 상태 분석
- **역할**: 히스토리 패널 UI
- **라인 수**: ~170줄

**장점:**
- 이벤트 위임 패턴 사용
- 시간 포맷팅 (n분 전, n시간 전)
- XSS 방지 escapeHtml

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **낮음** | 큰 히스토리에서 전체 재렌더링 | 성능 저하 |
| **낮음** | 가상 스크롤 미적용 | 많은 항목 시 느림 |

### 개선안
- 가상 스크롤 라이브러리 도입 (예: virtual-scroll)
- 또는 페이지네이션 적용

---

## 13. UsagePanelManager.js

### 현재 상태 분석
- **역할**: 사용량 패널 UI, 주간 차트
- **라인 수**: ~150줄

**장점:**
- 주간 사용량 시각화
- 스타일별 통계

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **낮음** | 차트가 HTML 문자열로 생성 | 복잡한 차트 확장 어려움 |
| **낮음** | API 실패 시 기본값만 표시 | 사용자 혼란 |

### 개선안
- 경량 차트 라이브러리 고려 (Chart.js 또는 ApexCharts)

---

## 14. ThemeManager.js

### 현재 상태 분석
- **역할**: 다크/라이트/시스템 테마 관리
- **라인 수**: ~230줄

**장점:**
- 시스템 설정 감지 (`prefers-color-scheme`)
- 부드러운 전환 애니메이션
- 3단계 토글 (light → dark → system)

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **낮음** | `destroy()` 메서드에서 `toggleTheme` 언바인딩 오류 | 메모리 누수 가능 |

### 개선안
```javascript
// 바인딩된 함수 저장
constructor() {
    this._boundToggleTheme = this.toggleTheme.bind(this);
}

destroy() {
    this.mediaQuery.removeEventListener('change', this.handleSystemChange);
    const btn = document.getElementById('theme-toggle-btn');
    if (btn) {
        btn.removeEventListener('click', this._boundToggleTheme);
    }
}
```

---

## 15. MindmapManager.js

### 현재 상태 분석
- **역할**: 마인드맵 생성 및 시각화
- **라인 수**: ~175줄
- **의존성**: Markmap 라이브러리

**장점:**
- 캐시된 마인드맵 재사용
- 폴백 렌더링 (Markmap 실패 시)
- 줌 컨트롤

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **높음** | `getApiKey()` 메서드 호출 - StorageManager에 없음 | 런타임 에러 |
| **중간** | 에러 시 모달이 닫히면서 에러 메시지가 안 보일 수 있음 | UX 저하 |

### 개선안
```javascript
// API 키 방식 수정 - 서버 인증 사용
async generateMindmap(content, title) {
    const response = await fetch('/api/mindmap', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...this._getAuthHeaders() // AuthManager에서 가져오기
        },
        body: JSON.stringify({ content, model })
    });
}
```

---

## 16. PanelResizeManager.js

### 현재 상태 분석
- **역할**: 패널 리사이즈 기능
- **라인 수**: ~330줄

**장점:**
- 키보드 접근성 지원 (화살표 키, Home/End)
- 터치 이벤트 지원
- 크기 자동 저장/복원
- 반응형 (xl 이상에서만 활성화)

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **낮음** | ResizeObserver 무한 루프 가능성 | 성능 이슈 |

### 개선안
```javascript
setupResizeObserver() {
    // 디바운스 추가
    let timeout;
    const observer = new ResizeObserver(() => {
        clearTimeout(timeout);
        timeout = setTimeout(() => this.handleWindowResize(), 100);
    });
}
```

---

## 17. KeyboardNavigationManager.js

### 현재 상태 분석
- **역할**: 키보드 접근성 (US-013)
- **라인 수**: ~530줄

**장점:**
- 포커스 모드 감지 (keyboard vs mouse)
- 모달 포커스 트랩
- Skip Link
- 그리드/칩/사이드바 화살표 네비게이션

### 문제점
| 우선순위 | 문제 | 영향 |
|---------|------|------|
| **낮음** | `init()`이 constructor에서 자동 호출 | 테스트 어려움 |
| **낮음** | 동적으로 추가되는 요소는 접근성 속성 미적용 | 일부 요소 접근성 저하 |

### 개선안
- MutationObserver로 동적 요소 감지
- 접근성 속성 자동 적용

---

## 18. 종합 평가

### 아키텍처 평가

| 항목 | 점수 | 평가 |
|------|------|------|
| **모듈화** | ★★★★☆ | 잘 분리되어 있으나 일부 책임이 겹침 |
| **확장성** | ★★★☆☆ | 새 기능 추가는 쉬우나 기존 코드 수정 필요 |
| **유지보수성** | ★★★☆☆ | HTML 템플릿 하드코딩이 주요 문제 |
| **접근성** | ★★★★☆ | WCAG AA 준수, 키보드 네비게이션 우수 |
| **보안** | ★★★★☆ | XSS 방지, API 키 서버 관리 |
| **성능** | ★★★☆☆ | 대형 파일, CDN 의존성 개선 필요 |

### 우선순위별 개선 로드맵

#### Phase 1: 긴급 (1-2주)
- [ ] MindmapManager의 `getApiKey()` 버그 수정
- [ ] index.html CSS 분리 시작

#### Phase 2: 중요 (2-4주)
- [ ] ReportManager 리팩토링 (템플릿 분리)
- [ ] Tailwind 빌드 파이프라인 도입
- [ ] EventBus 통합

#### Phase 3: 개선 (1-2개월)
- [ ] DOMPurify 도입
- [ ] 가상 스크롤 적용
- [ ] API 요청 재시도 로직
- [ ] 다국어 지원 준비

### 코드 품질 지표

```
총 파일 수: 18개 (HTML 1 + JS 17)
총 라인 수: 약 5,500줄 (CSS 제외)
평균 파일 크기: ~300줄

가장 큰 파일:
1. ReportManager.js - 634줄 ⚠️ 분리 권장
2. KeyboardNavigationManager.js - 529줄
3. main.js - 543줄
4. AuthManager.js - 541줄
```

---

*이 리뷰 문서는 코드 품질 향상을 위한 참고용입니다.*
