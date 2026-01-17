# History/Usage 탭 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 아이콘 바의 History, Usage 탭 기능을 구현하여 결과 패널이 각 뷰로 전환되도록 한다.

**Architecture:** result-panel 내에 3개의 뷰(dashboard-view, history-view, usage-view)를 생성하고, 아이콘 바 클릭 시 해당 뷰만 표시. CSS-only 차트 사용.

**Tech Stack:** HTML, CSS, Vanilla JavaScript (ES6 모듈)

---

## Task 1: HTML 구조 변경 - 뷰 컨테이너 추가

**Files:**
- Modify: `templates/index.html:1652-1673`

**Step 1: result-panel 내부를 3개 뷰로 분리**

기존 구조:
```html
<div id="result-panel" class="...">
    <!-- 헤더 -->
    <div class="p-4 border-b...">...</div>
    <!-- 리포트 스트림 -->
    <div id="report-stream">...</div>
    <!-- Empty State -->
    <div id="empty-state">...</div>
</div>
```

변경 구조:
```html
<div id="result-panel" class="...">
    <!-- Dashboard View (기존) -->
    <div id="dashboard-view" class="panel-view">
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
        <div id="report-stream" class="flex-1 p-4 space-y-2 overflow-y-auto"></div>
        <!-- Empty State -->
        <div id="empty-state" class="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <span class="material-symbols-outlined text-6xl text-text-muted mb-4">article</span>
            <p class="text-text-muted text-lg mb-2">생성된 콘텐츠가 없습니다</p>
            <p class="text-text-muted text-sm">왼쪽에서 URL을 입력하고 콘텐츠를 생성하세요</p>
        </div>
    </div>

    <!-- History View (신규) -->
    <div id="history-view" class="panel-view hidden">
        <!-- 헤더 -->
        <div class="p-4 border-b border-border-dark flex-shrink-0">
            <div class="flex items-center justify-between">
                <h2 class="text-lg font-semibold text-white flex items-center gap-2">
                    <span class="material-symbols-outlined">history</span>
                    히스토리
                </h2>
                <button id="clear-all-history-btn" class="text-xs text-text-muted hover:text-red-400 transition-colors flex items-center gap-1">
                    <span class="material-symbols-outlined text-sm">delete</span>
                    전체 삭제
                </button>
            </div>
        </div>
        <!-- 히스토리 목록 -->
        <div id="history-list" class="flex-1 p-4 space-y-3 overflow-y-auto"></div>
        <!-- Empty State -->
        <div id="history-empty-state" class="flex-1 flex flex-col items-center justify-center p-8 text-center">
            <span class="material-symbols-outlined text-6xl text-text-muted mb-4">history</span>
            <p class="text-text-muted text-lg mb-2">히스토리가 없습니다</p>
            <p class="text-text-muted text-sm">콘텐츠를 생성하면 여기에 기록됩니다</p>
        </div>
        <!-- 푸터 -->
        <div id="history-footer" class="p-3 border-t border-border-dark text-xs text-text-muted text-center hidden">
            총 <span id="history-count">0</span>개 항목 • 최대 50개 저장
        </div>
    </div>

    <!-- Usage View (신규) -->
    <div id="usage-view" class="panel-view hidden">
        <!-- 헤더 -->
        <div class="p-4 border-b border-border-dark flex-shrink-0">
            <h2 class="text-lg font-semibold text-white flex items-center gap-2">
                <span class="material-symbols-outlined">bar_chart</span>
                사용량
            </h2>
        </div>
        <!-- 사용량 대시보드 -->
        <div class="flex-1 p-4 space-y-6 overflow-y-auto">
            <!-- 오늘 사용량 카드 -->
            <div class="bg-card-dark border border-card-border rounded-xl p-4">
                <h3 class="text-sm font-medium text-text-muted mb-3">오늘 사용량</h3>
                <div class="space-y-2">
                    <div class="flex justify-between text-sm">
                        <span id="usage-current" class="text-white font-semibold">0</span>
                        <span id="usage-limit" class="text-text-muted">/ 5</span>
                    </div>
                    <div class="h-2 bg-background-dark rounded-full overflow-hidden">
                        <div id="usage-progress-bar" class="h-full bg-primary rounded-full transition-all" style="width: 0%"></div>
                    </div>
                    <p id="usage-remaining" class="text-xs text-text-muted">남은 횟수: 5회</p>
                </div>
            </div>

            <!-- 최근 7일 그래프 -->
            <div class="bg-card-dark border border-card-border rounded-xl p-4">
                <h3 class="text-sm font-medium text-text-muted mb-4">최근 7일</h3>
                <div id="weekly-chart" class="flex items-end justify-between h-32 gap-2">
                    <!-- 바 차트 (JS로 생성) -->
                </div>
            </div>

            <!-- 스타일별 통계 -->
            <div class="bg-card-dark border border-card-border rounded-xl p-4">
                <h3 class="text-sm font-medium text-text-muted mb-4">스타일별 사용</h3>
                <div id="style-stats" class="space-y-3">
                    <!-- 스타일 바 (JS로 생성) -->
                </div>
                <p id="style-stats-empty" class="text-center text-text-muted text-sm py-4 hidden">통계 데이터가 없습니다</p>
            </div>
        </div>
    </div>
</div>
```

**Step 2: 검증**

브라우저에서 페이지 로드 후 개발자 도구에서:
- `#dashboard-view` 존재 확인
- `#history-view` 존재 확인 (hidden)
- `#usage-view` 존재 확인 (hidden)

---

## Task 2: CSS 스타일 추가

**Files:**
- Modify: `templates/index.html` (style 태그 내)

**Step 1: 패널 뷰 스타일 추가**

`.nav-icon-btn` 스타일 블록 근처에 추가:

```css
/* 패널 뷰 전환 */
.panel-view {
    display: flex;
    flex-direction: column;
    height: 100%;
}
.panel-view.hidden {
    display: none;
}

/* 히스토리 아이템 */
.history-item {
    background: var(--card-dark);
    border: 1px solid var(--card-border);
    border-radius: 0.75rem;
    padding: 1rem;
    cursor: pointer;
    transition: all 0.2s;
}
.history-item:hover {
    border-color: var(--primary);
    transform: translateY(-1px);
}
.history-item-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.5rem;
}
.history-item-meta {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
    color: var(--text-muted);
}
.history-item-title {
    font-size: 0.9375rem;
    font-weight: 600;
    color: white;
    margin-bottom: 0.25rem;
    line-height: 1.4;
}
.history-item-url {
    font-size: 0.75rem;
    color: var(--text-muted);
    margin-bottom: 0.5rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.history-item-preview {
    font-size: 0.8125rem;
    color: #9ca3af;
    line-height: 1.5;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.history-delete-btn {
    padding: 0.25rem;
    color: var(--text-muted);
    transition: color 0.2s;
}
.history-delete-btn:hover {
    color: #ef4444;
}

/* Usage 차트 */
.weekly-bar {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.5rem;
}
.weekly-bar-fill {
    width: 100%;
    max-width: 2rem;
    background: var(--primary);
    border-radius: 0.25rem 0.25rem 0 0;
    transition: height 0.3s;
}
.weekly-bar-label {
    font-size: 0.625rem;
    color: var(--text-muted);
}
.weekly-bar-value {
    font-size: 0.75rem;
    color: white;
    font-weight: 500;
}

.style-stat-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
}
.style-stat-label {
    width: 4.5rem;
    font-size: 0.75rem;
    color: white;
    flex-shrink: 0;
}
.style-stat-bar-bg {
    flex: 1;
    height: 0.5rem;
    background: var(--background-dark);
    border-radius: 0.25rem;
    overflow: hidden;
}
.style-stat-bar-fill {
    height: 100%;
    background: var(--primary);
    border-radius: 0.25rem;
    transition: width 0.3s;
}
.style-stat-value {
    width: 4rem;
    font-size: 0.75rem;
    color: var(--text-muted);
    text-align: right;
    flex-shrink: 0;
}
```

**Step 2: 검증**

개발자 도구에서 `.panel-view`, `.history-item` 등의 스타일이 적용되었는지 확인.

---

## Task 3: 탭 전환 로직 구현

**Files:**
- Modify: `templates/index.html` (script 태그 내)

**Step 1: 탭 전환 함수 추가**

`sidebar-settings-btn` 이벤트 리스너 근처에 추가:

```javascript
// 탭(패널 뷰) 전환
function switchPanelView(viewName) {
    // 모든 패널 뷰 숨기기
    document.querySelectorAll('.panel-view').forEach(view => {
        view.classList.add('hidden');
    });

    // 선택한 뷰만 표시
    const targetView = document.getElementById(`${viewName}-view`);
    if (targetView) {
        targetView.classList.remove('hidden');
    }

    // 아이콘 버튼 활성화 상태 업데이트
    document.querySelectorAll('.nav-icon-btn[data-section]').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.section === viewName);
    });

    // 뷰별 초기화
    if (viewName === 'history') {
        window.dispatchEvent(new CustomEvent('panel:history-opened'));
    } else if (viewName === 'usage') {
        window.dispatchEvent(new CustomEvent('panel:usage-opened'));
    }
}

// 아이콘 바 버튼 클릭 이벤트
document.querySelectorAll('.nav-icon-btn[data-section]').forEach(btn => {
    btn.addEventListener('click', () => {
        const section = btn.dataset.section;
        if (section && section !== 'settings') {
            switchPanelView(section);
            if (window.innerWidth < 1024) toggleSidebar();
        }
    });
});

// 전역으로 노출 (다른 모듈에서 사용)
window.switchPanelView = switchPanelView;
```

**Step 2: 검증**

- Dashboard 아이콘 클릭 → dashboard-view 표시
- History 아이콘 클릭 → history-view 표시
- Usage 아이콘 클릭 → usage-view 표시

---

## Task 4: HistoryPanelManager 모듈 생성

**Files:**
- Create: `static/js/modules/HistoryPanelManager.js`

**Step 1: 모듈 구현**

```javascript
/**
 * HistoryPanelManager - 히스토리 패널 UI 관리
 */
export class HistoryPanelManager {
    constructor(storageManager, eventBus) {
        this.storageManager = storageManager;
        this.eventBus = eventBus;
        this.elements = {};
    }

    init() {
        this.cacheElements();
        this.bindEvents();
        this.render();
    }

    cacheElements() {
        this.elements = {
            list: document.getElementById('history-list'),
            emptyState: document.getElementById('history-empty-state'),
            footer: document.getElementById('history-footer'),
            count: document.getElementById('history-count'),
            clearAllBtn: document.getElementById('clear-all-history-btn')
        };
    }

    bindEvents() {
        // 히스토리 패널 열림 이벤트
        window.addEventListener('panel:history-opened', () => this.render());

        // 전체 삭제 버튼
        this.elements.clearAllBtn?.addEventListener('click', () => this.confirmClearAll());

        // 히스토리 변경 이벤트 (새 콘텐츠 생성 시)
        this.eventBus?.on('history:updated', () => this.render());
    }

    render() {
        const history = this.storageManager.getHistory();
        const list = this.elements.list;
        const emptyState = this.elements.emptyState;
        const footer = this.elements.footer;

        if (!list) return;

        if (history.length === 0) {
            list.innerHTML = '';
            emptyState?.classList.remove('hidden');
            footer?.classList.add('hidden');
            return;
        }

        emptyState?.classList.add('hidden');
        footer?.classList.remove('hidden');
        if (this.elements.count) {
            this.elements.count.textContent = history.length;
        }

        list.innerHTML = history.map(item => this.createHistoryItemHTML(item)).join('');

        // 이벤트 위임으로 클릭 처리
        list.onclick = (e) => {
            const deleteBtn = e.target.closest('.history-delete-btn');
            const historyItem = e.target.closest('.history-item');

            if (deleteBtn) {
                e.stopPropagation();
                const id = deleteBtn.dataset.id;
                this.deleteItem(id);
            } else if (historyItem) {
                const id = historyItem.dataset.id;
                this.viewItem(id);
            }
        };
    }

    createHistoryItemHTML(item) {
        const timeAgo = this.formatTimeAgo(item.createdAt || item.timestamp);
        const preview = this.getPreview(item.content || item.html, 100);
        const truncatedUrl = this.truncateUrl(item.url, 40);
        const styleLabel = item.style || 'Blog';
        const modelLabel = item.model || 'AI';

        return `
            <div class="history-item" data-id="${item.id}">
                <div class="history-item-header">
                    <div class="history-item-meta">
                        <span class="px-2 py-0.5 bg-primary/20 text-primary rounded text-xs">${styleLabel}</span>
                        <span>•</span>
                        <span>${modelLabel}</span>
                        <span>•</span>
                        <span>${timeAgo}</span>
                    </div>
                    <button class="history-delete-btn" data-id="${item.id}" title="삭제">
                        <span class="material-symbols-outlined text-lg">delete</span>
                    </button>
                </div>
                <div class="history-item-title">${this.escapeHtml(item.title || '제목 없음')}</div>
                <div class="history-item-url">${this.escapeHtml(truncatedUrl)}</div>
                <div class="history-item-preview">${this.escapeHtml(preview)}</div>
            </div>
        `;
    }

    formatTimeAgo(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return '방금 전';
        if (diffMins < 60) return `${diffMins}분 전`;
        if (diffHours < 24) return `${diffHours}시간 전`;
        if (diffDays < 7) return `${diffDays}일 전`;
        return date.toLocaleDateString('ko-KR');
    }

    getPreview(content, maxLength) {
        if (!content) return '';
        // HTML 태그 제거
        const text = content.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
        return text.length > maxLength ? text.slice(0, maxLength) + '...' : text;
    }

    truncateUrl(url, maxLength) {
        if (!url) return '';
        try {
            const urlObj = new URL(url);
            const display = urlObj.hostname + urlObj.pathname;
            return display.length > maxLength ? display.slice(0, maxLength) + '...' : display;
        } catch {
            return url.length > maxLength ? url.slice(0, maxLength) + '...' : url;
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    deleteItem(id) {
        if (!confirm('이 항목을 삭제하시겠습니까?')) return;
        this.storageManager.removeFromHistory(id);
        this.render();
        this.eventBus?.emit('history:updated');
    }

    confirmClearAll() {
        if (!confirm('모든 히스토리를 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.')) return;
        this.storageManager.saveHistory([]);
        this.render();
        this.eventBus?.emit('history:updated');
    }

    viewItem(id) {
        const history = this.storageManager.getHistory();
        const item = history.find(h => h.id === id);
        if (!item) return;

        // Dashboard로 전환
        window.switchPanelView('dashboard');

        // 해당 콘텐츠 표시 이벤트 발행
        this.eventBus?.emit('history:view-item', item);
    }
}
```

**Step 2: 검증**

- 모듈 파일 존재 확인
- 문법 오류 없음 확인

---

## Task 5: UsagePanelManager 모듈 생성

**Files:**
- Create: `static/js/modules/UsagePanelManager.js`

**Step 1: 모듈 구현**

```javascript
/**
 * UsagePanelManager - 사용량 패널 UI 관리
 */
export class UsagePanelManager {
    constructor(storageManager, eventBus) {
        this.storageManager = storageManager;
        this.eventBus = eventBus;
        this.elements = {};
    }

    init() {
        this.cacheElements();
        this.bindEvents();
    }

    cacheElements() {
        this.elements = {
            current: document.getElementById('usage-current'),
            limit: document.getElementById('usage-limit'),
            progressBar: document.getElementById('usage-progress-bar'),
            remaining: document.getElementById('usage-remaining'),
            weeklyChart: document.getElementById('weekly-chart'),
            styleStats: document.getElementById('style-stats'),
            styleStatsEmpty: document.getElementById('style-stats-empty')
        };
    }

    bindEvents() {
        window.addEventListener('panel:usage-opened', () => this.render());
    }

    async render() {
        await this.renderTodayUsage();
        this.renderWeeklyChart();
        this.renderStyleStats();
    }

    async renderTodayUsage() {
        try {
            const response = await fetch('/api/user/usage');
            if (response.ok) {
                const data = await response.json();
                const used = data.used || 0;
                const limit = data.limit || 5;
                const remaining = Math.max(0, limit - used);
                const percent = Math.min(100, (used / limit) * 100);

                if (this.elements.current) this.elements.current.textContent = used;
                if (this.elements.limit) this.elements.limit.textContent = `/ ${limit}`;
                if (this.elements.progressBar) this.elements.progressBar.style.width = `${percent}%`;
                if (this.elements.remaining) this.elements.remaining.textContent = `남은 횟수: ${remaining}회`;
            }
        } catch (e) {
            console.warn('사용량 조회 실패:', e);
            // 기본값 유지
        }
    }

    renderWeeklyChart() {
        const chart = this.elements.weeklyChart;
        if (!chart) return;

        const history = this.storageManager.getHistory();
        const weekData = this.calculateWeeklyData(history);
        const maxValue = Math.max(...weekData.map(d => d.count), 1);

        const days = ['일', '월', '화', '수', '목', '금', '토'];
        const today = new Date().getDay();

        // 오늘부터 7일 전까지의 요일 배열 생성
        const orderedDays = [];
        for (let i = 6; i >= 0; i--) {
            const dayIndex = (today - i + 7) % 7;
            orderedDays.push({
                label: days[dayIndex],
                count: weekData[6 - i].count
            });
        }

        chart.innerHTML = orderedDays.map(day => {
            const heightPercent = (day.count / maxValue) * 100;
            return `
                <div class="weekly-bar">
                    <span class="weekly-bar-value">${day.count}</span>
                    <div class="weekly-bar-fill" style="height: ${Math.max(4, heightPercent)}%"></div>
                    <span class="weekly-bar-label">${day.label}</span>
                </div>
            `;
        }).join('');
    }

    calculateWeeklyData(history) {
        const now = new Date();
        const weekData = Array(7).fill(null).map(() => ({ count: 0 }));

        history.forEach(item => {
            const itemDate = new Date(item.createdAt || item.timestamp);
            const diffDays = Math.floor((now - itemDate) / 86400000);
            if (diffDays >= 0 && diffDays < 7) {
                weekData[6 - diffDays].count++;
            }
        });

        return weekData;
    }

    renderStyleStats() {
        const container = this.elements.styleStats;
        const emptyState = this.elements.styleStatsEmpty;
        if (!container) return;

        const history = this.storageManager.getHistory();
        const styleData = this.calculateStyleStats(history);

        if (styleData.length === 0) {
            container.innerHTML = '';
            emptyState?.classList.remove('hidden');
            return;
        }

        emptyState?.classList.add('hidden');
        const total = styleData.reduce((sum, s) => sum + s.count, 0);

        container.innerHTML = styleData.slice(0, 5).map(style => {
            const percent = Math.round((style.count / total) * 100);
            return `
                <div class="style-stat-row">
                    <span class="style-stat-label">${style.name}</span>
                    <div class="style-stat-bar-bg">
                        <div class="style-stat-bar-fill" style="width: ${percent}%"></div>
                    </div>
                    <span class="style-stat-value">${percent}% (${style.count}회)</span>
                </div>
            `;
        }).join('');
    }

    calculateStyleStats(history) {
        const styleCounts = {};

        history.forEach(item => {
            const style = item.style || 'Blog';
            styleCounts[style] = (styleCounts[style] || 0) + 1;
        });

        return Object.entries(styleCounts)
            .map(([name, count]) => ({ name, count }))
            .sort((a, b) => b.count - a.count);
    }
}
```

**Step 2: 검증**

- 모듈 파일 존재 확인
- 문법 오류 없음 확인

---

## Task 6: main.js에 모듈 통합

**Files:**
- Modify: `static/js/main.js`

**Step 1: 모듈 import 추가**

기존 import 문 하단에 추가:
```javascript
import { HistoryPanelManager } from './modules/HistoryPanelManager.js';
import { UsagePanelManager } from './modules/UsagePanelManager.js';
```

**Step 2: 모듈 초기화 추가**

`initializeApp()` 함수 내에서 다른 모듈 초기화 후 추가:
```javascript
// 히스토리/사용량 패널 매니저
const historyPanelManager = new HistoryPanelManager(storageManager, eventBus);
historyPanelManager.init();

const usagePanelManager = new UsagePanelManager(storageManager, eventBus);
usagePanelManager.init();
```

**Step 3: history:view-item 이벤트 처리 추가**

ReportManager 또는 main.js에서 이벤트 리스너 추가:
```javascript
// 히스토리에서 아이템 보기
eventBus.on('history:view-item', (item) => {
    reportManager.displayHistoryItem(item);
});
```

**Step 4: 검증**

- 브라우저 콘솔에 에러 없음 확인
- History 탭 클릭 시 히스토리 목록 표시 확인
- Usage 탭 클릭 시 사용량 대시보드 표시 확인

---

## Task 7: ReportManager에 displayHistoryItem 메서드 추가

**Files:**
- Modify: `static/js/modules/ReportManager.js`

**Step 1: displayHistoryItem 메서드 추가**

클래스 내에 메서드 추가:
```javascript
displayHistoryItem(item) {
    // 기존 리포트 카드가 있으면 해당 ID의 카드를 찾아서 펼치기
    const existingCard = document.querySelector(`.report-card[data-id="${item.id}"]`);
    if (existingCard) {
        // 카드가 이미 있으면 펼치기
        existingCard.classList.add('expanded');
        existingCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
        return;
    }

    // 카드가 없으면 새로 생성
    this.createReportCard({
        id: item.id,
        title: item.title,
        content: item.content || item.html,
        url: item.url,
        style: item.style,
        model: item.model,
        createdAt: item.createdAt || item.timestamp,
        isFromHistory: true
    });
}
```

**Step 2: 검증**

- History 아이템 클릭 시 Dashboard로 전환 확인
- 해당 콘텐츠가 결과 패널에 표시되는지 확인

---

## Task 8: 통합 테스트

**Step 1: 전체 플로우 테스트**

1. 페이지 로드 → Dashboard 뷰가 기본 표시
2. History 아이콘 클릭 → History 뷰로 전환
3. Usage 아이콘 클릭 → Usage 뷰로 전환
4. Dashboard 아이콘 클릭 → Dashboard 뷰로 복귀
5. 콘텐츠 생성 → History에 기록됨
6. History 아이템 클릭 → Dashboard로 전환, 해당 콘텐츠 표시

**Step 2: 엣지 케이스 테스트**

1. 히스토리가 비어있을 때 empty state 표시
2. 전체 삭제 버튼 동작
3. 개별 삭제 버튼 동작
4. 사용량 API 실패 시 기본값 표시

---

## 구현 순서 요약

1. HTML 구조 변경 (뷰 컨테이너)
2. CSS 스타일 추가
3. 탭 전환 로직
4. HistoryPanelManager 모듈
5. UsagePanelManager 모듈
6. main.js 통합
7. ReportManager 확장
8. 통합 테스트
