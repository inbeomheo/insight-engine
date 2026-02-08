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

        if (this.urlList.length === 0) {
            container.innerHTML = '';
            return;
        }

        container.innerHTML = this.urlList.map((url, index) => {
            const shortUrl = this._formatShortUrl(url);
            return `
                <span class="url-chip inline-flex items-center gap-1 px-3 py-1.5 bg-white border border-gray-200 rounded-full text-xs text-gray-700 group"
                      data-index="${index}" draggable="true" title="${this.ui.escapeHtml(url)}">
                    <span class="material-symbols-outlined" style="font-size: 14px; color: var(--primary);">play_circle</span>
                    <span class="truncate max-w-[180px]">${this.ui.escapeHtml(shortUrl)}</span>
                    <button class="url-remove-btn ml-1 text-gray-400 hover:text-red-500 transition-colors" data-index="${index}" title="삭제" aria-label="URL 삭제">
                        <span class="material-symbols-outlined" style="font-size: 14px;">close</span>
                    </button>
                </span>
            `;
        }).join('');

        this.setupRemoveButtons(container);
        this.setupDragEvents(container);
    }

    _formatShortUrl(url) {
        try {
            const u = new URL(url);
            const videoId = u.searchParams.get('v') || u.pathname.split('/').pop();
            return videoId ? `youtu.be/${videoId}` : url;
        } catch {
            return url.length > 30 ? url.substring(0, 30) + '...' : url;
        }
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
        container.querySelectorAll('.url-chip').forEach(card => {
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
