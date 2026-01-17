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
