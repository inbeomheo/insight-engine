/**
 * ReportManager - 리포트 카드 관리 모듈
 * 리포트 카드 생성, 표시, 히스토리 로딩 담당
 */
export class ReportManager {
    constructor(storage, styleManager, uiManager) {
        this.storage = storage;
        this.styleManager = styleManager;
        this.ui = uiManager;
        this.mindmapManager = null;

        // DOM 요소 캐싱
        this.elements = {
            reportStream: document.getElementById('report-stream'),
            emptyState: document.getElementById('empty-state'),
            liveIndicator: document.getElementById('live-indicator')
        };
    }

    setMindmapManager(mindmapManager) {
        this.mindmapManager = mindmapManager;
    }

    // ==================== 헬퍼 메서드 ====================

    _formatShortUrl(url, maxLength = 40) {
        const stripped = url.replace(/^https?:\/\//, '');
        return stripped.length > maxLength ? `${stripped.substring(0, maxLength)}...` : stripped;
    }

    _getCurrentTimeStr() {
        return new Date().toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
    }

    _generatePendingId() {
        return `pending_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    }

    _setEmptyStateVisibility(visible) {
        const { emptyState, liveIndicator } = this.elements;
        if (emptyState) emptyState.style.display = visible ? 'flex' : 'none';
        if (liveIndicator) liveIndicator.style.display = visible ? 'none' : 'flex';
    }

    _createCardElement(className, html) {
        const card = document.createElement('article');
        card.className = className;
        card.innerHTML = html;
        return card;
    }

    // ==================== Pending Card (처리 중 카드) ====================

    _buildPendingCardHtml(styleLabel, timeStr, url, shortUrl) {
        return `
            <div class="absolute -left-[1px] top-0 bottom-0 w-1.5 bg-gradient-to-b from-primary/50 via-primary/30 to-transparent rounded-full animate-pulse"></div>
            <div class="card-header p-6 md:p-8 border-b border-border-dark/30">
                <div class="space-y-3">
                    <div class="flex items-center gap-3 flex-wrap">
                        <span class="bg-gradient-to-r from-primary/60 to-primary-glow/60 text-background-dark text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 rounded-md">${styleLabel}</span>
                        <span class="text-text-subtle/50 text-[10px] font-mono tracking-wide">${timeStr}</span>
                        <span class="inline-flex items-center gap-1.5 px-3 py-1 bg-primary/10 border border-primary/20 rounded-full text-primary text-[10px] font-medium animate-pulse">
                            <span class="material-symbols-outlined text-xs loading-spinner">progress_activity</span>
                            <span>분석 중</span>
                        </span>
                    </div>
                    <!-- Skeleton Title -->
                    <div class="space-y-2">
                        <div class="skeleton skeleton-title"></div>
                        <div class="skeleton skeleton-text" style="width: 50%;"></div>
                    </div>
                    <a class="inline-flex items-center gap-1.5 text-text-subtle/40 text-xs font-mono hover:text-text-subtle/60 transition-colors" href="${url}" target="_blank">
                        <span class="material-symbols-outlined text-sm">play_circle</span>
                        <span class="truncate max-w-[200px]">${this.ui.escapeHtml(shortUrl)}</span>
                    </a>
                </div>
            </div>
            <!-- Skeleton Content Area -->
            <div class="p-6 md:p-8">
                <div class="space-y-4">
                    <!-- Skeleton paragraph lines -->
                    <div class="skeleton skeleton-text" style="width: 100%;"></div>
                    <div class="skeleton skeleton-text" style="width: 95%;"></div>
                    <div class="skeleton skeleton-text" style="width: 88%;"></div>
                    <div class="skeleton skeleton-text" style="width: 92%;"></div>
                    <div class="skeleton skeleton-text" style="width: 75%;"></div>
                </div>
                <!-- Loading indicator -->
                <div class="flex items-center justify-center gap-3 mt-8 pt-6 border-t border-border-dark/20">
                    <div class="flex items-center gap-1.5">
                        <span class="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
                        <span class="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
                        <span class="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
                    </div>
                    <span class="text-[11px] text-text-subtle/50 font-medium">AI가 영상을 분석하고 있습니다</span>
                </div>
            </div>
        `;
    }

    createPendingCard(url, style) {
        const { reportStream } = this.elements;
        this._setEmptyStateVisibility(false);

        const pendingId = this._generatePendingId();
        const styleLabel = this.styleManager.getStyleLabel(style);
        const shortUrl = this._formatShortUrl(url);
        const timeStr = this._getCurrentTimeStr();

        const card = this._createCardElement(
            'report-card bg-surface-dark border border-border-dark/50 relative rounded-xl overflow-hidden',
            this._buildPendingCardHtml(styleLabel, timeStr, url, shortUrl)
        );
        card.dataset.pendingId = pendingId;

        reportStream.insertBefore(card, reportStream.firstChild);
        return pendingId;
    }

    updatePendingCard(pendingId, data, isError = false) {
        const card = document.querySelector(`[data-pending-id="${pendingId}"]`);
        if (!card) return;

        if (!isError) {
            card.remove();
            this.displayReportCard(data);
            return;
        }

        // 에러 카드로 변환
        const shortUrl = this._formatShortUrl(data.url);
        card.className = 'report-card bg-surface-dark border border-red-500/30 relative opacity-80 rounded-xl overflow-hidden';
        card.removeAttribute('data-pending-id');
        card.innerHTML = this._createErrorCardHtml(data.url, shortUrl, data.error);

        this._setupDeleteButton(card);
    }

    _createErrorCardHtml(url, shortUrl, error) {
        return `
            <div class="absolute -left-[1px] top-0 bottom-0 w-1.5 bg-red-500 rounded-full"></div>
            <div class="p-6 md:p-8 border-b border-border-dark flex flex-col gap-3">
                <div class="flex items-center gap-3">
                    <span class="bg-red-500/20 text-red-400 text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded">Error</span>
                </div>
                <h3 class="text-xl font-bold text-red-400 leading-tight">분석 실패</h3>
                <a class="inline-flex items-center gap-2 text-gray-500 hover:text-white transition-colors text-sm font-mono" href="${url}" target="_blank">
                    <span class="material-symbols-outlined text-sm">open_in_new</span> ${this.ui.escapeHtml(shortUrl)}
                </a>
            </div>
            <div class="p-6 md:p-8 text-gray-400 font-body">
                <div class="flex items-center gap-2 text-red-400">
                    <span class="material-symbols-outlined">warning</span>
                    <span>${this.ui.escapeHtml(error)}</span>
                </div>
            </div>
            <div class="card-footer bg-background-dark/60 border-t border-border-dark/30 px-4 py-3 flex justify-end">
                <button class="delete-btn inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-red-400/70 hover:text-red-400 px-3 py-2 hover:bg-red-500/10 transition-all duration-200 rounded-lg">
                    <span class="material-symbols-outlined text-sm">delete</span>
                    <span>삭제</span>
                </button>
            </div>
        `;
    }

    _setupDeleteButton(card) {
        const deleteBtn = card.querySelector('.delete-btn');
        deleteBtn?.addEventListener('click', () => {
            card.remove();
            if (this.elements.reportStream.children.length === 0) {
                this._setEmptyStateVisibility(true);
            }
        });
    }

    // ==================== Report Card Display ====================

    displayReportCard(data) {
        const { reportStream } = this.elements;
        this._setEmptyStateVisibility(false);

        // 기존 카드들 모두 접기
        this._collapseAllCards();

        const styleLabel = this.styleManager.getStyleLabel(data.style);
        const historyData = {
            id: this.ui.generateReportId(),
            url: data.url,
            title: `[${styleLabel}] ${data.title}`,
            style: data.style,
            html: data.html,
            content: data.content,
            prompt: data.prompt || null,
            time: this._getCurrentTimeStr(),
            timestamp: Date.now(),
            usage: data.usage || null,
            elapsed_time: data.elapsed_time || null
        };

        this.storage.addToHistory(historyData);

        // 새로 생성된 카드는 펼쳐진 상태로 표시
        const card = this.createReportCard(historyData, styleLabel, this._formatShortUrl(data.url), true);
        this.setupCardEvents(card, historyData);

        reportStream.insertBefore(card, reportStream.firstChild);
        setTimeout(() => card.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    }

    _buildStatsBadge(icon, value) {
        return `<span class="stats-badge inline-flex items-center gap-1.5 text-primary/80"><span class="material-symbols-outlined text-xs">${icon}</span>${value}</span>`;
    }

    _buildStatsBadges(data) {
        const badges = [];
        if (data.usage?.total_tokens) {
            badges.push(this._buildStatsBadge('token', data.usage.total_tokens.toLocaleString()));
        }
        if (data.elapsed_time) {
            badges.push(this._buildStatsBadge('schedule', `${data.elapsed_time}s`));
        }
        return badges.length ? `<div class="flex items-center gap-2 mt-1">${badges.join('')}</div>` : '';
    }

    _buildFooterButton(className, icon, label, hoverColor = 'primary') {
        const colorClasses = hoverColor === 'purple'
            ? 'hover:text-purple-400 hover:bg-purple-500/10'
            : hoverColor === 'red'
                ? 'hover:text-red-400 hover:bg-red-500/10'
                : 'hover:text-primary hover:bg-primary/10';
        return `<button class="${className} inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-text-subtle/60 ${colorClasses} px-3 py-2 transition-all duration-200 rounded-lg">
            <span class="material-symbols-outlined text-sm">${icon}</span>
            <span>${label}</span>
        </button>`;
    }

    _buildReportCardHtml(data, styleLabel, shortUrl, statsHtml, isExpanded = false) {
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

    createReportCard(data, styleLabel, shortUrl, isExpanded = false) {
        const card = this._createCardElement(
            'report-card bg-surface-dark border border-border-dark rounded-lg overflow-hidden',
            this._buildReportCardHtml(data, styleLabel, shortUrl, this._buildStatsBadges(data), isExpanded)
        );
        card.dataset.reportId = data.id;
        this.setupToggleButton(card);
        return card;
    }

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
            if (icon) icon.textContent = 'expand_more';
        } else {
            content.style.display = 'block';
            if (preview) preview.style.display = 'none';
            if (icon) icon.textContent = 'expand_less';
        }
    }

    _collapseAllCards() {
        const cards = this.elements.reportStream.querySelectorAll('.report-card');
        cards.forEach(card => {
            const content = card.querySelector('.report-content');
            const preview = card.querySelector('.card-preview');
            const icon = card.querySelector('[data-toggle="card"] .material-symbols-outlined');

            if (content && content.style.display !== 'none') {
                this._animateToggle(content, preview, icon, true);
            }
        });
    }

    _buildErrorCardHtml(reportId, timeStr, url, shortUrl, error) {
        return `
            <div class="absolute -left-[1px] top-0 bottom-0 w-1 bg-red-500"></div>
            <div class="p-6 md:p-8 border-b border-border-dark flex flex-col md:flex-row md:items-start justify-between gap-6">
                <div class="space-y-3">
                    <div class="flex items-center gap-3">
                        <span class="bg-red-500/20 text-red-400 text-[10px] font-bold uppercase tracking-widest px-2 py-1">Error</span>
                        <span class="text-text-subtle text-xs font-mono">ID: ${reportId} • ${timeStr}</span>
                    </div>
                    <h3 class="text-xl font-bold text-red-400 leading-tight">분석 실패</h3>
                    <a class="inline-flex items-center gap-2 text-gray-500 hover:text-white transition-colors text-sm font-mono uppercase tracking-wide" href="${url}" target="_blank">
                        <span class="material-symbols-outlined text-sm">open_in_new</span> ${this.ui.escapeHtml(shortUrl)}
                    </a>
                </div>
            </div>
            <div class="p-6 md:p-8 text-gray-400 font-body">
                <div class="flex items-center gap-2 text-red-400">
                    <span class="material-symbols-outlined">warning</span>
                    <span>${this.ui.escapeHtml(error)}</span>
                </div>
            </div>
            <div class="bg-surface-dark/50 border-t border-border-dark p-4 flex justify-end gap-3">
                <button class="delete-btn text-xs font-bold uppercase tracking-widest text-red-500 hover:text-red-400 px-4 py-2 hover:bg-red-500/10 transition-colors">Delete</button>
            </div>
        `;
    }

    displayErrorCard(data) {
        const { reportStream } = this.elements;
        this._setEmptyStateVisibility(false);

        const card = this._createCardElement(
            'report-card bg-surface-dark border border-red-500/30 relative opacity-80',
            this._buildErrorCardHtml(
                this.ui.generateReportId(),
                this._getCurrentTimeStr(),
                data.url,
                this._formatShortUrl(data.url),
                data.error
            )
        );

        this._setupDeleteButton(card);
        reportStream.insertBefore(card, reportStream.firstChild);
    }

    // ==================== Card Events ====================

    setupCardEvents(card, data) {
        const promptBtn = card.querySelector('.prompt-btn');
        const mindmapBtn = card.querySelector('.mindmap-btn');
        const copyBtn = card.querySelector('.copy-btn');
        const downloadBtn = card.querySelector('.download-btn');
        const deleteBtn = card.querySelector('.delete-btn');

        // 프롬프트 보기 버튼 이벤트
        if (promptBtn) {
            if (data.prompt) {
                promptBtn.addEventListener('click', () => this._handlePromptClick(data));
            } else {
                // 프롬프트가 없으면 버튼 비활성화
                promptBtn.classList.add('opacity-30', 'cursor-not-allowed');
                promptBtn.disabled = true;
                promptBtn.title = '프롬프트 데이터 없음';
            }
        }

        // 마인드맵 버튼 이벤트
        if (mindmapBtn && this.mindmapManager) {
            mindmapBtn.addEventListener('click', () => this._handleMindmapClick(mindmapBtn, data));
        }

        copyBtn?.addEventListener('click', () => this._handleCopyClick(copyBtn, data.content));
        downloadBtn?.addEventListener('click', () => this._handleDownloadClick(data));
        deleteBtn?.addEventListener('click', () => this._handleDeleteClick(card, data.id));
    }

    _handlePromptClick(data) {
        const modal = document.getElementById('prompt-modal');
        const content = document.getElementById('prompt-content');
        const stats = document.getElementById('prompt-stats');
        const copyBtn = document.getElementById('prompt-copy-btn');
        const closeBtn = document.getElementById('prompt-close');

        if (!modal || !content) return;

        // 프롬프트 내용 표시
        content.textContent = data.prompt;

        // 통계 표시
        const charCount = data.prompt.length;
        const wordCount = data.prompt.split(/\s+/).filter(w => w).length;
        stats.textContent = `${charCount.toLocaleString()}자 • 약 ${wordCount.toLocaleString()}단어`;

        // 모달 열기
        modal.classList.add('active');

        // 복사 버튼 이벤트 (한 번만 등록)
        const newCopyBtn = copyBtn.cloneNode(true);
        copyBtn.parentNode.replaceChild(newCopyBtn, copyBtn);
        newCopyBtn.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(data.prompt);
                const icon = newCopyBtn.querySelector('.material-symbols-outlined');
                const label = newCopyBtn.querySelector('span:last-child');
                icon.textContent = 'check';
                label.textContent = '완료!';
                newCopyBtn.classList.add('text-green-400');
                setTimeout(() => {
                    icon.textContent = 'content_copy';
                    label.textContent = '복사';
                    newCopyBtn.classList.remove('text-green-400');
                }, 2000);
            } catch {
                this.ui.showAlert('복사 실패', 'error');
            }
        });

        // 닫기 이벤트
        const closeHandler = () => modal.classList.remove('active');
        closeBtn.onclick = closeHandler;
        modal.onclick = (e) => { if (e.target === modal) closeHandler(); };
    }

    async _handleMindmapClick(btn, data) {
        if (data.mindmapMarkdown) {
            this.mindmapManager.showCachedMindmap(data.mindmapMarkdown, data.title);
            return;
        }

        const btnIcon = btn.querySelector('.material-symbols-outlined');
        const originalIcon = btnIcon.textContent;

        btnIcon.textContent = 'progress_activity';
        btnIcon.classList.add('loading-spinner');
        btn.disabled = true;

        try {
            const markdown = await this.mindmapManager.generateMindmap(data.content, data.title);
            if (markdown) {
                data.mindmapMarkdown = markdown;
                this.storage.updateHistoryItem(data.id, { mindmapMarkdown: markdown });
            }
        } finally {
            btnIcon.textContent = originalIcon;
            btnIcon.classList.remove('loading-spinner');
            btn.disabled = false;
        }
    }

    async _handleCopyClick(btn, content) {
        try {
            await navigator.clipboard.writeText(content);
            const originalHtml = btn.innerHTML;
            btn.innerHTML = '<span class="material-symbols-outlined text-sm">check</span><span>완료!</span>';
            btn.classList.add('text-green-400');

            setTimeout(() => {
                btn.innerHTML = originalHtml;
                btn.classList.remove('text-green-400');
            }, 2000);
        } catch {
            this.ui.showAlert('복사 실패', 'error');
        }
    }

    _handleDownloadClick(data) {
        const blob = new Blob([data.content], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${data.title.substring(0, 30)}.md`;
        a.click();
        URL.revokeObjectURL(url);
    }

    _handleDeleteClick(card, reportId) {
        this.storage.removeFromHistory(reportId);
        card.style.animation = 'slideOut 0.3s ease forwards';

        setTimeout(() => {
            card.remove();
            if (this.elements.reportStream.children.length === 0) {
                this._setEmptyStateVisibility(true);
            }
        }, 300);
    }

    // ==================== History Loading ====================

    loadHistory() {
        const history = this.storage.getHistory();
        if (history.length === 0) return;

        this._setEmptyStateVisibility(false);
        history.forEach(data => this._displayHistoryCard(data));
    }

    _displayHistoryCard(data) {
        const styleLabel = this.styleManager.getStyleLabel(data.style);
        const shortUrl = this._formatShortUrl(data.url);

        const card = this.createReportCard(data, styleLabel, shortUrl, false);
        this.setupCardEvents(card, data);
        this.elements.reportStream.appendChild(card);
    }

    // ==================== History Panel Support ====================

    /**
     * 히스토리 패널에서 아이템 클릭 시 호출
     * 해당 콘텐츠를 Dashboard에 표시
     */
    displayHistoryItem(item) {
        const { reportStream } = this.elements;

        // 기존 카드가 있는지 확인
        const existingCard = reportStream.querySelector(`[data-report-id="${item.id}"]`);
        if (existingCard) {
            // 기존 카드가 있으면 펼치고 스크롤
            const content = existingCard.querySelector('.report-content');
            const preview = existingCard.querySelector('.card-preview');
            const icon = existingCard.querySelector('[data-toggle="card"] .material-symbols-outlined');

            if (content && content.style.display === 'none') {
                this._collapseAllCards();
                this._animateToggle(content, preview, icon, false);
            }
            existingCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            return;
        }

        // 카드가 없으면 새로 생성 (펼쳐진 상태)
        this._setEmptyStateVisibility(false);
        this._collapseAllCards();

        const styleLabel = this.styleManager.getStyleLabel(item.style);
        const shortUrl = this._formatShortUrl(item.url);

        // 시간 포맷 변환 (timestamp가 있으면 사용)
        const historyData = {
            ...item,
            time: item.time || new Date(item.createdAt || item.timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
        };

        const card = this.createReportCard(historyData, styleLabel, shortUrl, true);
        this.setupCardEvents(card, historyData);

        reportStream.insertBefore(card, reportStream.firstChild);
        setTimeout(() => card.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    }
}
