/**
 * UrlManager - URL 관리 모듈
 * 다중 URL 추가, 삭제, 드래그 앤 드롭 관리
 */
export class UrlManager {
    constructor(uiManager) {
        this.ui = uiManager;
        this.maxUrls = 10;
        this.urlList = [];
        this.draggedUrlIndex = null;
    }

    // ==================== URL Operations ====================

    addUrl(url) {
        url = url.trim();
        if (!url) return false;
        if (!this.ui.isYouTubeUrl(url)) return false;
        if (this.urlList.length >= this.maxUrls) return false;
        if (this.urlList.includes(url)) return false;

        this.urlList.push(url);
        this.render();
        this.updateCount();
        return true;
    }

    removeUrl(index) {
        if (index >= 0 && index < this.urlList.length) {
            this.urlList.splice(index, 1);
            this.render();
            this.updateCount();
        }
    }

    getUrls() {
        return [...this.urlList];
    }

    clear() {
        this.urlList = [];
        this.render();
        this.updateCount();
    }

    parseAndAddUrls(text) {
        const lines = text.split(/[\r\n,\s]+/).filter(Boolean);
        let addedCount = 0;

        for (const line of lines) {
            if (this.urlList.length >= this.maxUrls) break;
            if (this.addUrl(line)) {
                addedCount++;
            }
        }

        return addedCount;
    }

    // ==================== UI Updates ====================

    updateCount() {
        const countEl = document.getElementById('url-count');
        if (countEl) {
            countEl.textContent = this.urlList.length || '0';
        }
    }

    render() {
        const container = document.getElementById('url-list-container');
        if (!container) return;

        container.innerHTML = this.urlList.map((url, index) => `
            <div class="url-card flex items-center bg-surface-dark border border-card-border p-2 group hover:border-primary/50 transition-colors"
                 data-index="${index}" draggable="true">
                <div class="url-drag-handle pl-2 pr-1 text-text-subtle cursor-grab hover:text-primary" title="드래그하여 순서 변경">
                    <span class="material-symbols-outlined text-lg">drag_indicator</span>
                </div>
                <div class="pl-2 pr-3 text-text-subtle">
                    <span class="material-symbols-outlined text-xl">link</span>
                </div>
                <div class="flex-1 truncate text-text-light font-mono text-sm">
                    ${this.ui.escapeHtml(url)}
                </div>
                <button class="url-remove-btn p-2 text-text-subtle hover:text-red-400 transition-colors" data-index="${index}" title="삭제">
                    <span class="material-symbols-outlined text-lg">close</span>
                </button>
            </div>
        `).join('');

        this.setupRemoveButtons(container);
        this.setupDragEvents(container);
    }

    setupRemoveButtons(container) {
        container.querySelectorAll('.url-remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                this.removeUrl(index);
            });
        });
    }

    setupDragEvents(container) {
        container.querySelectorAll('.url-card').forEach(card => {
            card.addEventListener('dragstart', (e) => {
                this.draggedUrlIndex = parseInt(e.currentTarget.dataset.index);
                e.currentTarget.classList.add('opacity-50');
            });

            card.addEventListener('dragend', (e) => {
                e.currentTarget.classList.remove('opacity-50');
                this.draggedUrlIndex = null;
            });

            card.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.currentTarget.classList.add('border-primary');
            });

            card.addEventListener('dragleave', (e) => {
                e.currentTarget.classList.remove('border-primary');
            });

            card.addEventListener('drop', (e) => {
                e.preventDefault();
                e.currentTarget.classList.remove('border-primary');
                const targetIndex = parseInt(e.currentTarget.dataset.index);

                if (this.draggedUrlIndex !== null && this.draggedUrlIndex !== targetIndex) {
                    const [movedUrl] = this.urlList.splice(this.draggedUrlIndex, 1);
                    this.urlList.splice(targetIndex, 0, movedUrl);
                    this.render();
                }
            });
        });
    }
}
