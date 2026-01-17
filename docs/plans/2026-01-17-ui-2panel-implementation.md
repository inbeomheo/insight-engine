# UI 2-Panel 레이아웃 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 사이드바를 아이콘 바로 축소하고 입력/결과를 나란히 배치하는 2-Panel 레이아웃 구현

**Architecture:** 기존 세로 스크롤 레이아웃을 좌우 분할로 변경. 왼쪽(40%)에 입력 폼, 오른쪽(60%)에 결과 표시. 사이드바는 48px 아이콘 바로 축소.

**Tech Stack:** HTML, Tailwind CSS, Vanilla JS (ES6 Modules)

---

## Phase 1: 아이콘 바 구현

### Task 1.1: 사이드바를 아이콘 바로 축소

**Files:**
- Modify: `templates/index.html:873-920` (사이드바 영역)

**Step 1: 사이드바 너비 및 구조 변경**

기존:
```html
<aside id="sidebar" class="w-20 lg:w-72 flex flex-col border-r border-border-dark bg-background-dark...">
```

변경:
```html
<aside id="sidebar" class="w-12 flex flex-col border-r border-border-dark bg-background-dark flex-shrink-0 h-full z-50">
```

**Step 2: 로고 영역 아이콘만 표시**

기존 로고+텍스트 → 아이콘만:
```html
<!-- Logo Area -->
<div class="h-14 flex items-center justify-center border-b border-border-dark">
    <div class="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
        <span class="material-symbols-outlined text-white text-lg">auto_awesome_motion</span>
    </div>
</div>
```

**Step 3: 네비게이션 아이콘화**

```html
<nav class="flex-1 flex flex-col items-center gap-1 py-4">
    <button class="nav-icon-btn active" data-section="dashboard" title="Dashboard">
        <span class="material-symbols-outlined">dashboard</span>
    </button>
    <button class="nav-icon-btn" data-section="history" title="History">
        <span class="material-symbols-outlined">history</span>
    </button>
    <button class="nav-icon-btn" data-section="usage" title="Usage">
        <span class="material-symbols-outlined">pie_chart</span>
    </button>
    <button id="sidebar-settings-btn" class="nav-icon-btn" title="Settings">
        <span class="material-symbols-outlined">settings</span>
    </button>
</nav>
```

**Step 4: 프로필 아이콘화**

```html
<div class="py-4 border-t border-border-dark flex justify-center">
    <button id="sidebar-auth-container" class="nav-icon-btn" title="로그인">
        <span class="material-symbols-outlined">person</span>
    </button>
</div>
```

**Step 5: 아이콘 버튼 스타일 추가 (CSS)**

`<style>` 섹션에 추가:
```css
.nav-icon-btn {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    color: #9ca3af;
    transition: all 0.2s;
    cursor: pointer;
    border: none;
    background: transparent;
}
.nav-icon-btn:hover {
    background: #202428;
    color: #0f758a;
}
.nav-icon-btn.active {
    background: rgba(15, 117, 138, 0.15);
    color: #0f758a;
}
.nav-icon-btn .material-symbols-outlined {
    font-size: 20px;
}
```

**Step 6: 브라우저에서 확인**

Run: 브라우저에서 `http://localhost:5001` 열고 사이드바가 아이콘 바로 변경되었는지 확인

**Step 7: Commit**

```bash
git add templates/index.html
git commit -m "refactor(ui): 사이드바를 48px 아이콘 바로 축소"
```

---

## Phase 2: 2-Panel 레이아웃 구조

### Task 2.1: 메인 영역 2-Panel 분할

**Files:**
- Modify: `templates/index.html:925-1680` (메인 콘텐츠 영역)

**Step 1: 메인 컨테이너 구조 변경**

기존 `<main>` 태그 내부를 2-Panel로 분할:

```html
<main id="main-content" class="flex-1 overflow-hidden">
    <div class="h-full flex">
        <!-- 입력 패널 (40%) -->
        <div id="input-panel" class="w-2/5 h-full overflow-y-auto border-r border-border-dark p-6 flex flex-col">
            <!-- 입력 폼들이 여기로 이동 -->
        </div>

        <!-- 결과 패널 (60%) -->
        <div id="result-panel" class="w-3/5 h-full overflow-y-auto p-6">
            <!-- 리포트 스트림이 여기로 이동 -->
        </div>
    </div>
</main>
```

**Step 2: 헤더 단순화**

기존 헤더의 네비게이션 요소들은 아이콘 바로 이동했으므로 헤더 단순화:

```html
<header class="h-14 flex items-center justify-between px-6 border-b border-border-dark bg-background-dark flex-shrink-0">
    <div class="flex items-center gap-3">
        <span class="text-sm font-semibold text-white">Insight Engine</span>
        <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-surface-dark text-primary">Beta v2.5</span>
    </div>
    <div class="flex items-center gap-3">
        <div id="usage-display-header" class="flex items-center gap-2 px-3 py-1.5 bg-surface-dark rounded-lg text-xs">
            <span class="material-symbols-outlined text-primary text-sm">bolt</span>
            <span class="text-text-secondary"><span id="header-usage-count">-</span> / <span id="header-usage-limit">-</span></span>
        </div>
        <div id="provider-badge-header" class="flex items-center gap-2 px-3 py-1.5 bg-surface-dark rounded-lg cursor-pointer hover:bg-bg-elevated transition-colors">
            <span class="text-primary text-[10px] font-bold">AI</span>
            <span class="text-xs text-text-secondary" id="current-provider-label">미설정</span>
        </div>
    </div>
</header>
```

**Step 3: Commit**

```bash
git add templates/index.html
git commit -m "refactor(ui): 메인 영역 2-Panel 구조로 분할 (40:60)"
```

---

### Task 2.2: 입력 폼을 왼쪽 패널로 이동

**Files:**
- Modify: `templates/index.html` (입력 패널 내부)

**Step 1: URL 입력 섹션**

```html
<div id="input-panel" class="w-2/5 h-full overflow-y-auto border-r border-border-dark flex flex-col">
    <!-- URL 입력 -->
    <div class="p-4 border-b border-border-dark">
        <div class="flex items-center gap-2 mb-3">
            <span class="material-symbols-outlined text-primary text-sm">link</span>
            <span class="text-sm font-medium text-white">URL 입력</span>
        </div>
        <div class="flex gap-2">
            <input type="text" id="url-input"
                   class="flex-1 bg-surface-dark border border-border-dark rounded-lg px-3 py-2 text-sm text-white placeholder-text-secondary focus:border-primary focus:outline-none"
                   placeholder="https://www.youtube.com/watch?v=...">
            <button id="add-url-btn" class="px-3 py-2 bg-surface-dark border border-border-dark rounded-lg text-text-secondary hover:text-primary hover:border-primary transition-colors">
                <span class="material-symbols-outlined text-lg">add</span>
            </button>
        </div>
        <div id="url-list" class="mt-2 space-y-1"></div>
        <div class="flex items-center justify-between mt-2 text-xs text-text-secondary">
            <span><span id="url-count">0</span>/10 URLs</span>
        </div>
    </div>

    <!-- AI 모델 -->
    <div class="p-4 border-b border-border-dark">
        <div class="flex items-center gap-2 mb-3">
            <span class="material-symbols-outlined text-primary text-sm">psychology</span>
            <span class="text-sm font-medium text-white">AI 모델</span>
        </div>
        <div class="space-y-2">
            <select id="provider-select" class="w-full bg-surface-dark border border-border-dark rounded-lg px-3 py-2 text-sm text-white">
                <option>서비스 선택</option>
            </select>
            <select id="model-select" class="w-full bg-surface-dark border border-border-dark rounded-lg px-3 py-2 text-sm text-white">
                <option>모델 선택</option>
            </select>
        </div>
    </div>

    <!-- 스타일 -->
    <div class="p-4 border-b border-border-dark flex-1 overflow-y-auto">
        <div class="flex items-center gap-2 mb-3">
            <span class="material-symbols-outlined text-primary text-sm">style</span>
            <span class="text-sm font-medium text-white">스타일</span>
        </div>
        <div id="style-options" class="space-y-3">
            <!-- 스타일 버튼들 -->
        </div>
    </div>

    <!-- 고급 옵션 (접힘) -->
    <div class="border-b border-border-dark">
        <button id="advanced-toggle" class="w-full p-4 flex items-center justify-between text-text-secondary hover:text-white transition-colors">
            <div class="flex items-center gap-2">
                <span class="material-symbols-outlined text-sm">tune</span>
                <span class="text-sm">고급 옵션</span>
            </div>
            <span class="material-symbols-outlined text-sm transition-transform" id="advanced-icon">expand_more</span>
        </button>
        <div id="advanced-options" class="hidden p-4 pt-0">
            <!-- 고급 옵션 내용 -->
        </div>
    </div>

    <!-- 생성 버튼 (하단 고정) -->
    <div class="p-4 border-t border-border-dark mt-auto">
        <button id="run-analysis-btn" class="w-full bg-primary hover:bg-primary-hover text-white font-semibold py-3 px-4 rounded-lg transition-colors flex items-center justify-center gap-2">
            <span class="material-symbols-outlined">auto_awesome</span>
            <span>콘텐츠 생성</span>
        </button>
    </div>
</div>
```

**Step 2: Commit**

```bash
git add templates/index.html
git commit -m "refactor(ui): 입력 폼을 왼쪽 패널로 재구성"
```

---

### Task 2.3: 결과 패널 구성

**Files:**
- Modify: `templates/index.html` (결과 패널)

**Step 1: 결과 패널 HTML**

```html
<div id="result-panel" class="w-3/5 h-full overflow-y-auto flex flex-col">
    <!-- 헤더 -->
    <div class="p-4 border-b border-border-dark flex-shrink-0">
        <div class="flex items-center justify-between">
            <h2 class="text-lg font-semibold text-white">결과</h2>
            <div id="live-indicator" class="hidden flex items-center gap-2 text-xs text-primary">
                <span class="w-2 h-2 bg-primary rounded-full animate-pulse"></span>
                <span>LIVE</span>
            </div>
        </div>
    </div>

    <!-- 리포트 스트림 -->
    <div id="report-stream" class="flex-1 p-4 space-y-2 overflow-y-auto">
        <!-- 리포트 카드들 -->
    </div>

    <!-- Empty State -->
    <div id="empty-state" class="flex-1 flex flex-col items-center justify-center p-8 text-center">
        <div class="w-16 h-16 mb-4 bg-surface-dark rounded-xl flex items-center justify-center border border-border-dark">
            <span class="material-symbols-outlined text-primary text-3xl">auto_awesome</span>
        </div>
        <h3 class="text-lg font-medium text-white mb-2">인사이트를 발견하세요</h3>
        <p class="text-sm text-text-secondary max-w-xs">YouTube 영상 URL을 입력하고 AI 분석을 시작하세요</p>
    </div>
</div>
```

**Step 2: Commit**

```bash
git add templates/index.html
git commit -m "refactor(ui): 결과 패널 구성"
```

---

## Phase 3: 리포트 카드 아코디언 개선

### Task 3.1: 카드 HTML 구조 변경

**Files:**
- Modify: `static/js/modules/ReportManager.js:233-274`

**Step 1: 접힌 상태 카드 HTML 수정**

`_buildReportCardHtml` 메서드 수정:

```javascript
_buildReportCardHtml(data, styleLabel, shortUrl, statsHtml, isExpanded) {
    const toggleIcon = isExpanded ? 'expand_less' : 'expand_more';
    const contentDisplay = isExpanded ? 'block' : 'none';

    // 미리보기 텍스트 (처음 100자)
    const previewText = data.content ?
        data.content.replace(/[#*`]/g, '').substring(0, 100) + '...' : '';

    return `
        <div class="card-header p-4 cursor-pointer hover:bg-surface-dark/50 transition-colors" data-toggle="card">
            <div class="flex items-start justify-between gap-3">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="material-symbols-outlined text-sm text-text-secondary">${toggleIcon}</span>
                        <span class="text-xs font-medium text-primary">${styleLabel}</span>
                        <span class="text-xs text-text-secondary">${data.time}</span>
                    </div>
                    <h3 class="text-sm font-medium text-white truncate">${this.ui.escapeHtml(data.title)}</h3>
                    <p class="text-xs text-text-secondary mt-1 line-clamp-2 card-preview" style="display: ${isExpanded ? 'none' : 'block'}">${this.ui.escapeHtml(previewText)}</p>
                </div>
                <div class="flex items-center gap-1 flex-shrink-0">
                    <button class="copy-btn p-1.5 text-text-secondary hover:text-primary hover:bg-primary/10 rounded transition-colors" title="복사">
                        <span class="material-symbols-outlined text-sm">content_copy</span>
                    </button>
                    <button class="delete-btn p-1.5 text-text-secondary hover:text-red-400 hover:bg-red-500/10 rounded transition-colors" title="삭제">
                        <span class="material-symbols-outlined text-sm">delete</span>
                    </button>
                </div>
            </div>
        </div>
        <div class="report-content border-t border-border-dark" style="display: ${contentDisplay}">
            <div class="p-4">
                ${data.html}
            </div>
            <div class="card-footer border-t border-border-dark px-4 py-2 flex items-center justify-between bg-surface-dark/30">
                <div class="flex items-center gap-3 text-xs text-text-secondary">
                    <span>${styleLabel}</span>
                    ${statsHtml}
                </div>
                <div class="flex items-center gap-1">
                    <button class="prompt-btn px-2 py-1 text-xs text-text-secondary hover:text-primary transition-colors">프롬프트</button>
                    <button class="mindmap-btn px-2 py-1 text-xs text-text-secondary hover:text-purple-400 transition-colors">마인드맵</button>
                    <button class="download-btn px-2 py-1 text-xs text-text-secondary hover:text-primary transition-colors">저장</button>
                </div>
            </div>
        </div>
    `;
}
```

**Step 2: 카드 클래스 단순화**

`createReportCard` 메서드 수정:

```javascript
createReportCard(data, styleLabel, shortUrl, isExpanded = false) {  // 기본값 false로 변경
    const card = this._createCardElement(
        'report-card bg-surface-dark border border-border-dark rounded-lg overflow-hidden',
        this._buildReportCardHtml(data, styleLabel, shortUrl, this._buildStatsBadges(data), isExpanded)
    );
    card.dataset.reportId = data.id;
    this.setupToggleButton(card);
    return card;
}
```

**Step 3: 토글 이벤트 수정**

`setupToggleButton` 메서드 수정:

```javascript
setupToggleButton(card) {
    const header = card.querySelector('[data-toggle="card"]');
    const content = card.querySelector('.report-content');
    const preview = card.querySelector('.card-preview');
    const icon = header?.querySelector('.material-symbols-outlined');

    if (!header || !content || !icon) return;

    header.addEventListener('click', (e) => {
        // 버튼 클릭은 무시
        if (e.target.closest('button')) return;

        const isExpanded = content.style.display !== 'none';
        this._animateToggle(content, preview, icon, isExpanded);
    });
}

_animateToggle(content, preview, icon, isCollapsing) {
    if (isCollapsing) {
        content.style.display = 'none';
        if (preview) preview.style.display = 'block';
        icon.textContent = 'expand_more';
    } else {
        content.style.display = 'block';
        if (preview) preview.style.display = 'none';
        icon.textContent = 'expand_less';
    }
}
```

**Step 4: 브라우저에서 확인**

리포트 카드가 아코디언 형태로 동작하는지 확인

**Step 5: Commit**

```bash
git add static/js/modules/ReportManager.js
git commit -m "refactor(ui): 리포트 카드 아코디언 방식으로 변경"
```

---

### Task 3.2: 새 결과 생성 시 기존 카드 접기

**Files:**
- Modify: `static/js/modules/ReportManager.js:178-204`

**Step 1: displayReportCard 메서드 수정**

```javascript
displayReportCard(data) {
    const { reportStream } = this.elements;
    this._setEmptyStateVisibility(false);

    // 기존 카드들 모두 접기
    this._collapseAllCards();

    const styleLabel = this.styleManager.getStyleLabel(data.style);
    // ... 기존 코드 ...

    // 새 카드는 펼쳐진 상태로 생성
    const card = this.createReportCard(historyData, styleLabel, this._formatShortUrl(data.url), true);
    // ... 나머지 코드 ...
}

_collapseAllCards() {
    const cards = this.elements.reportStream.querySelectorAll('.report-card');
    cards.forEach(card => {
        const content = card.querySelector('.report-content');
        const preview = card.querySelector('.card-preview');
        const icon = card.querySelector('[data-toggle="card"] .material-symbols-outlined');

        if (content && content.style.display !== 'none') {
            content.style.display = 'none';
            if (preview) preview.style.display = 'block';
            if (icon) icon.textContent = 'expand_more';
        }
    });
}
```

**Step 2: Commit**

```bash
git add static/js/modules/ReportManager.js
git commit -m "feat(ui): 새 결과 생성 시 기존 카드 자동 접기"
```

---

## Phase 4: 반응형 처리

### Task 4.1: 모바일 탭 전환 구현

**Files:**
- Modify: `templates/index.html` (CSS 미디어 쿼리)

**Step 1: 모바일 CSS 추가**

```css
@media (max-width: 768px) {
    /* 아이콘 바 숨김 */
    #sidebar {
        display: none;
    }

    /* 2-Panel을 탭 방식으로 */
    #input-panel,
    #result-panel {
        width: 100%;
        display: none;
    }

    #input-panel.active,
    #result-panel.active {
        display: flex;
    }

    /* 모바일 탭 바 */
    .mobile-tab-bar {
        display: flex;
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: #16191d;
        border-top: 1px solid #2a2e33;
        z-index: 50;
    }

    .mobile-tab-bar button {
        flex: 1;
        padding: 12px;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        color: #9ca3af;
        font-size: 10px;
    }

    .mobile-tab-bar button.active {
        color: #0f758a;
    }
}

@media (min-width: 769px) {
    .mobile-tab-bar {
        display: none;
    }
}
```

**Step 2: 모바일 탭 바 HTML**

`</body>` 직전에 추가:

```html
<div class="mobile-tab-bar">
    <button class="mobile-tab active" data-panel="input">
        <span class="material-symbols-outlined">edit</span>
        <span>입력</span>
    </button>
    <button class="mobile-tab" data-panel="result">
        <span class="material-symbols-outlined">article</span>
        <span>결과</span>
    </button>
    <button class="mobile-tab" data-panel="settings" onclick="document.getElementById('settings-modal')?.classList.add('active')">
        <span class="material-symbols-outlined">settings</span>
        <span>설정</span>
    </button>
</div>
```

**Step 3: 탭 전환 JS**

```javascript
// 모바일 탭 전환
document.querySelectorAll('.mobile-tab[data-panel]').forEach(tab => {
    tab.addEventListener('click', () => {
        const panel = tab.dataset.panel;
        if (panel === 'settings') return;

        document.querySelectorAll('.mobile-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');

        document.getElementById('input-panel')?.classList.toggle('active', panel === 'input');
        document.getElementById('result-panel')?.classList.toggle('active', panel === 'result');
    });
});

// 초기 상태
if (window.innerWidth <= 768) {
    document.getElementById('input-panel')?.classList.add('active');
}
```

**Step 4: Commit**

```bash
git add templates/index.html
git commit -m "feat(ui): 모바일 반응형 탭 전환 구현"
```

---

## Phase 5: 최종 정리 및 테스트

### Task 5.1: 불필요한 코드 정리

**Files:**
- Modify: `templates/index.html`
- Modify: `static/js/modules/ReportManager.js`

**Step 1: 사용하지 않는 클래스/스타일 제거**

- 기존 사이드바 관련 스타일
- 이전 리포트 카드 스타일
- 사용하지 않는 애니메이션

**Step 2: Commit**

```bash
git add -A
git commit -m "chore: 불필요한 코드 정리"
```

### Task 5.2: 전체 테스트

**Step 1: 데스크톱 테스트**

- [ ] 아이콘 바 hover 시 툴팁
- [ ] 입력 패널 스크롤
- [ ] 결과 패널 독립 스크롤
- [ ] 리포트 카드 접기/펼치기
- [ ] 새 결과 시 기존 카드 접힘
- [ ] 복사/삭제 버튼 동작

**Step 2: 모바일 테스트**

- [ ] 탭 전환 동작
- [ ] 입력 탭 UI
- [ ] 결과 탭 UI
- [ ] 하단 네비게이션

**Step 3: 최종 Commit**

```bash
git add -A
git commit -m "feat(ui): 2-Panel 레이아웃 리디자인 완료

- 사이드바를 48px 아이콘 바로 축소
- 40:60 비율의 입력/결과 2-Panel 구조
- 리포트 카드 아코디언 방식 적용
- 모바일 반응형 탭 전환 지원"
```
