/**
 * HistorySidebar - 사이드바 히스토리 관리
 * 날짜별 그룹핑, 클릭 → 결과 로드, 삭제, 검색 필터
 */
import { getEventBus, EVENTS } from '../core/EventBus.js';

export class HistorySidebar {
    constructor(authManager, reportManager) {
        this.authManager = authManager;
        this.reportManager = reportManager;
        this.eventBus = getEventBus();

        this.historyList = document.getElementById('history-list');
        this.searchInput = document.getElementById('sidebar-search-input');
        this.newAnalysisBtn = document.getElementById('new-analysis-btn');

        this._items = [];
    }

    init() {
        this._setupSearch();
        this._setupNewAnalysisButton();
        this._subscribeEvents();
    }

    /**
     * 히스토리 로드 (클라우드 또는 로컬)
     */
    async loadHistory() {
        if (!this.historyList) return;

        this._items = [];

        if (this.authManager?.isLoggedIn?.()) {
            await this._loadCloudHistory();
        } else {
            this._loadLocalHistory();
        }

        this._renderList();
    }

    async _loadCloudHistory() {
        try {
            const headers = this.authManager.getAuthHeaders?.() || {};
            const response = await fetch('/api/user/history?page=1&per_page=50', { headers });
            if (!response.ok) return;

            const data = await response.json();
            const histories = data.histories || [];

            this._items = histories
                .filter(h => h && h.id)
                .map(h => ({
                    id: h.id,
                    title: h.title || '제목 없음',
                    url: h.url || '',
                    style: h.style || 'blog_seo',
                    html: h.html || '',
                    content: h.content || '',
                    prompt: h.prompt ?? null,
                    usage: h.usage ?? null,
                    elapsed_time: h.elapsed_time ?? null,
                    is_favorite: h.is_favorite ?? false,
                    keywords: h.keywords ?? [],
                    createdAt: h.createdAt || h.timestamp || Date.now(),
                    timestamp: h.timestamp ?? h.createdAt ?? Date.now()
                }));
        } catch (e) {
            console.error('[HistorySidebar] 클라우드 히스토리 로드 오류:', e);
        }
    }

    _loadLocalHistory() {
        try {
            const stored = localStorage.getItem('insight_engine_history');
            if (!stored) return;
            const history = JSON.parse(stored);
            if (!Array.isArray(history)) return;

            this._items = history.map(h => ({
                id: h.id,
                title: h.title || '제목 없음',
                url: h.url || '',
                style: h.style || 'blog_seo',
                html: h.html || '',
                content: h.content || '',
                prompt: h.prompt ?? null,
                usage: h.usage ?? null,
                elapsed_time: h.elapsed_time ?? null,
                createdAt: h.timestamp || Date.now(),
                timestamp: h.timestamp || Date.now()
            }));
        } catch (e) {
            console.error('[HistorySidebar] 로컬 히스토리 로드 오류:', e);
        }
    }

    _renderList(filterQuery = '') {
        if (!this.historyList) return;

        const query = filterQuery.toLowerCase().trim();
        const filtered = query
            ? this._items.filter(item => item.title.toLowerCase().includes(query))
            : this._items;

        if (filtered.length === 0) {
            this.historyList.innerHTML = `
                <div class="sidebar-empty-state">
                    <p>${query ? '검색 결과가 없습니다' : '분석 히스토리가 없습니다'}</p>
                </div>
            `;
            return;
        }

        let html = '';

        // 즐겨찾기 섹션 (날짜 그룹 상단)
        const favorites = filtered.filter(item => item.is_favorite);
        const nonFavorites = filtered.filter(item => !item.is_favorite);

        if (favorites.length > 0) {
            html += `<div class="history-group history-group--favorites" role="group" aria-label="즐겨찾기">`;
            html += `<div class="history-group-title"><span class="material-symbols-outlined" style="font-size: 14px; vertical-align: -2px;">star</span> 즐겨찾기</div>`;
            for (const item of favorites) {
                html += this._buildHistoryItemHtml(item);
            }
            html += '</div>';
        }

        // 날짜별 그룹핑 (즐겨찾기 제외)
        const groups = this._groupByDate(nonFavorites);

        for (const [label, items] of groups) {
            html += `<div class="history-group" role="group" aria-label="${label}">`;
            html += `<div class="history-group-title">${label}</div>`;
            for (const item of items) {
                html += this._buildHistoryItemHtml(item);
            }
            html += '</div>';
        }

        this.historyList.innerHTML = html;
        this._setupItemEvents();
    }

    _buildHistoryItemHtml(item) {
        const safeTitle = this._escapeHtml(item.title);
        const favIcon = item.is_favorite ? '<span class="material-symbols-outlined" style="font-size: 12px; color: var(--primary); flex-shrink: 0;">star</span>' : '';
        return `
            <div class="history-item${item.is_favorite ? ' history-item--favorite' : ''}" data-id="${item.id}" role="listitem" tabindex="0" title="${safeTitle}">
                <div style="display: flex; align-items: start; justify-content: space-between; gap: 4px;">
                    <div class="history-item-title" style="display: flex; align-items: center; gap: 4px;">${favIcon}${safeTitle}</div>
                    <button class="history-delete-btn" data-id="${item.id}" title="삭제" aria-label="히스토리 삭제">
                        <span class="material-symbols-outlined" style="font-size: 14px;">close</span>
                    </button>
                </div>
                <div class="history-item-meta">
                    <span>${this._formatTime(item.createdAt)}</span>
                    <span>·</span>
                    <span>${this._getStyleLabel(item.style)}</span>
                </div>
            </div>
        `;
    }

    _groupByDate(items) {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today.getTime() - 86400000);
        const weekAgo = new Date(today.getTime() - 7 * 86400000);

        const groups = new Map();
        groups.set('오늘', []);
        groups.set('어제', []);
        groups.set('이번 주', []);
        groups.set('이전', []);

        for (const item of items) {
            const date = new Date(item.createdAt);
            if (date >= today) {
                groups.get('오늘').push(item);
            } else if (date >= yesterday) {
                groups.get('어제').push(item);
            } else if (date >= weekAgo) {
                groups.get('이번 주').push(item);
            } else {
                groups.get('이전').push(item);
            }
        }

        // 빈 그룹 제거
        for (const [key, value] of groups) {
            if (value.length === 0) groups.delete(key);
        }

        return groups;
    }

    _setupItemEvents() {
        if (!this.historyList) return;

        // 클릭 → 결과 로드
        this.historyList.querySelectorAll('.history-item').forEach(el => {
            el.addEventListener('click', (e) => {
                if (e.target.closest('.history-delete-btn')) return;
                const id = el.dataset.id;
                const item = this._items.find(i => String(i.id) === String(id));
                if (item) {
                    this._setActive(el);
                    this.reportManager.displayHistoryItem(item);
                }
            });

            // Enter 키 지원
            el.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') el.click();
            });
        });

        // 삭제 버튼
        this.historyList.querySelectorAll('.history-delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = btn.dataset.id;
                await this._deleteItem(id);
            });
        });
    }

    _setActive(el) {
        this.historyList?.querySelectorAll('.history-item').forEach(item => {
            item.classList.remove('active');
        });
        el.classList.add('active');
    }

    async _deleteItem(id) {
        // 클라우드 삭제 시도
        if (this.authManager?.isLoggedIn?.()) {
            try {
                const headers = this.authManager.getAuthHeaders?.() || {};
                headers['Content-Type'] = 'application/json';
                await fetch(`/api/user/history/${id}`, {
                    method: 'DELETE',
                    headers
                });
            } catch (e) {
                console.error('[HistorySidebar] 삭제 오류:', e);
            }
        }

        // 로컬 목록에서 제거
        this._items = this._items.filter(item => String(item.id) !== String(id));
        const query = this.searchInput?.value || '';
        this._renderList(query);
    }

    _setupSearch() {
        if (!this.searchInput) return;

        let debounceTimer = null;
        this.searchInput.addEventListener('input', () => {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => {
                this._renderList(this.searchInput.value);
            }, 200);
        });
    }

    _setupNewAnalysisButton() {
        if (!this.newAnalysisBtn) return;

        this.newAnalysisBtn.addEventListener('click', () => {
            // URL 입력 필드로 포커스
            const urlInput = document.getElementById('url-input');
            if (urlInput) {
                urlInput.value = '';
                urlInput.focus();
            }

            // 활성 히스토리 항목 해제
            this.historyList?.querySelectorAll('.history-item').forEach(item => {
                item.classList.remove('active');
            });
        });
    }

    _subscribeEvents() {
        // 콘텐츠 생성 완료 시 사이드바 목록 갱신
        if (this.eventBus) {
            this.eventBus.on(EVENTS.GENERATE_COMPLETE, () => {
                setTimeout(() => this.loadHistory(), 500);
            });

            // 즐겨찾기 토글 시 사이드바 갱신
            this.eventBus.on(EVENTS.FAVORITE_TOGGLE, ({ id, is_favorite }) => {
                const item = this._items.find(i => String(i.id) === String(id));
                if (item) {
                    item.is_favorite = is_favorite;
                    const query = this.searchInput?.value || '';
                    this._renderList(query);
                }
            });
        }
    }

    _formatTime(timestamp) {
        try {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now - date;

            if (diff < 60000) return '방금';
            if (diff < 3600000) return `${Math.floor(diff / 60000)}분 전`;
            if (diff < 86400000) return `${Math.floor(diff / 3600000)}시간 전`;
            return date.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' });
        } catch {
            return '';
        }
    }

    _getStyleLabel(style) {
        const labels = {
            blog_seo: 'Blog+SEO',
            summary: '요약',
            tutorial: '튜토리얼',
            qna: 'Q&A',
            app_ideas: '앱 아이디어',
            yozm_it: '요즘IT',
            brunch_essay: '브런치',
            naver_popular: '네이버'
        };
        return labels[style] || style || '';
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }
}
