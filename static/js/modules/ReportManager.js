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
            <div class="absolute -left-[1px] top-0 bottom-0 w-1.5 bg-gradient-to-b from-primary-accent/50 via-primary-accent/30 to-transparent rounded-full animate-pulse"></div>
            <div class="card-header p-6 md:p-8 border-b border-border-dark/30">
                <div class="space-y-3">
                    <div class="flex items-center gap-3 flex-wrap">
                        <span class="bg-gradient-to-r from-primary-accent/60 to-primary-glow/60 text-background-dark text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 rounded-md">${styleLabel}</span>
                        <span class="text-gray-text/50 text-[10px] font-mono tracking-wide">${timeStr}</span>
                        <span class="stats-badge inline-flex items-center gap-1.5 text-primary-accent/80 animate-pulse">
                            <span class="material-symbols-outlined text-xs loading-spinner">progress_activity</span>
                            <span>분석 중...</span>
                        </span>
                    </div>
                    <h3 class="text-xl md:text-2xl font-display font-semibold text-warm-white/60 leading-snug tracking-tight">
                        <span class="inline-flex items-center gap-2">
                            <span class="material-symbols-outlined loading-spinner">hourglass_empty</span>
                            분석 진행 중...
                        </span>
                    </h3>
                    <a class="inline-flex items-center gap-1.5 text-gray-text/40 text-xs font-mono" href="${url}" target="_blank">
                        <span class="material-symbols-outlined text-sm">play_circle</span>
                        <span class="truncate max-w-[200px]">${this.ui.escapeHtml(shortUrl)}</span>
                    </a>
                </div>
            </div>
            <div class="p-6 md:p-8 flex items-center justify-center min-h-[120px]">
                <div class="flex flex-col items-center gap-3 text-gray-text/40">
                    <div class="flex items-center gap-2">
                        <span class="w-2 h-2 bg-primary-accent/60 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
                        <span class="w-2 h-2 bg-primary-accent/60 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
                        <span class="w-2 h-2 bg-primary-accent/60 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
                    </div>
                    <span class="text-xs">AI가 영상을 분석하고 있습니다</span>
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
        card.className = 'report-card bg-black border border-red-500/30 relative opacity-80 rounded-xl overflow-hidden';
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

        const styleLabel = this.styleManager.getStyleLabel(data.style);
        const historyData = {
            id: this.ui.generateReportId(),
            url: data.url,
            title: `[${styleLabel}] ${data.title}`,
            style: data.style,
            html: data.html,
            content: data.content,
            transcript: data.transcript || null,
            time: this._getCurrentTimeStr(),
            timestamp: Date.now(),
            usage: data.usage || null,
            elapsed_time: data.elapsed_time || null
        };

        this.storage.addToHistory(historyData);

        const card = this.createReportCard(historyData, styleLabel, this._formatShortUrl(data.url));
        this.setupCardEvents(card, historyData);

        reportStream.insertBefore(card, reportStream.firstChild);
        setTimeout(() => card.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    }

    _buildStatsBadge(icon, value) {
        return `<span class="stats-badge inline-flex items-center gap-1.5 text-primary-accent/80"><span class="material-symbols-outlined text-xs">${icon}</span>${value}</span>`;
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

    _buildFooterButton(className, icon, label, hoverColor = 'primary-accent') {
        const colorClasses = hoverColor === 'purple'
            ? 'hover:text-purple-400 hover:bg-purple-500/10'
            : hoverColor === 'red'
                ? 'hover:text-red-400 hover:bg-red-500/10'
                : 'hover:text-primary-accent hover:bg-primary-accent/10';
        return `<button class="${className} inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider text-gray-text/60 ${colorClasses} px-3 py-2 transition-all duration-200 rounded-lg">
            <span class="material-symbols-outlined text-sm">${icon}</span>
            <span>${label}</span>
        </button>`;
    }

    _buildReportCardHtml(data, styleLabel, shortUrl, statsHtml, isExpanded) {
        const toggleIcon = isExpanded ? 'expand_less' : 'expand_more';
        const toggleTitle = isExpanded ? '접기' : '펼치기';
        const contentDisplay = isExpanded ? 'block' : 'none';

        return `
            <div class="absolute -left-[1px] top-0 bottom-0 w-1.5 bg-gradient-to-b from-primary-accent via-primary-accent/60 to-transparent rounded-full"></div>
            <div class="card-header p-6 md:p-8 border-b border-border-dark/30 flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div class="space-y-3 flex-1 min-w-0">
                    <div class="flex items-center gap-3 flex-wrap">
                        <span class="bg-gradient-to-r from-primary-accent to-primary-glow text-background-dark text-[10px] font-bold uppercase tracking-wider px-3 py-1.5 rounded-md shadow-lg shadow-primary-accent/20">${styleLabel}</span>
                        <span class="text-gray-text/50 text-[10px] font-mono tracking-wide">#${data.id} • ${data.time}</span>
                    </div>
                    <h3 class="text-xl md:text-2xl font-display font-semibold text-warm-white leading-snug tracking-tight line-clamp-2">${this.ui.escapeHtml(data.title)}</h3>
                    <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
                        <a class="inline-flex items-center gap-1.5 text-gray-text/60 hover:text-primary-accent transition-colors text-xs font-mono group" href="${data.url}" target="_blank">
                            <span class="material-symbols-outlined text-sm group-hover:scale-110 transition-transform">play_circle</span>
                            <span class="truncate max-w-[200px]">${this.ui.escapeHtml(shortUrl)}</span>
                            <span class="material-symbols-outlined text-xs opacity-0 group-hover:opacity-100 transition-opacity">open_in_new</span>
                        </a>
                        ${statsHtml}
                    </div>
                </div>
                <button class="toggle-btn flex items-center justify-center size-9 text-gray-text/50 hover:text-primary-accent hover:bg-primary-accent/10 transition-all duration-300 rounded-lg border border-transparent hover:border-primary-accent/20" title="${toggleTitle}">
                    <span class="material-symbols-outlined text-xl transition-transform duration-300">${toggleIcon}</span>
                </button>
            </div>
            <div class="report-content p-6 md:p-8" style="display: ${contentDisplay}">
                ${data.html}
            </div>
            <div class="card-footer bg-background-dark/60 border-t border-border-dark/30 px-4 py-3 flex items-center justify-between">
                <span class="text-[10px] text-gray-text/40 font-mono">Insight Engine</span>
                <div class="flex items-center gap-1">
                    ${this._buildFooterButton('transcript-btn', 'subtitles', '자막 원문', 'primary-accent')}
                    ${this._buildFooterButton('mindmap-btn', 'account_tree', '마인드맵', 'purple')}
                    ${this._buildFooterButton('copy-btn', 'content_copy', '복사')}
                    ${this._buildFooterButton('download-btn', 'download', '저장')}
                    ${this._buildFooterButton('delete-btn', 'delete', '삭제', 'red')}
                </div>
            </div>
        `;
    }

    createReportCard(data, styleLabel, shortUrl, isExpanded = true) {
        const card = this._createCardElement(
            'report-card bg-surface-dark border border-border-dark/50 relative rounded-xl overflow-hidden',
            this._buildReportCardHtml(data, styleLabel, shortUrl, this._buildStatsBadges(data), isExpanded)
        );
        card.dataset.reportId = data.id;
        this.setupToggleButton(card);
        return card;
    }

    setupToggleButton(card) {
        const toggleBtn = card.querySelector('.toggle-btn');
        const content = card.querySelector('.report-content');
        const icon = toggleBtn?.querySelector('.material-symbols-outlined');

        if (!toggleBtn || !content || !icon) return;

        toggleBtn.addEventListener('click', () => {
            const isExpanded = content.style.display !== 'none';
            this._animateToggle(content, icon, toggleBtn, isExpanded);
        });
    }

    _animateToggle(content, icon, toggleBtn, isCollapsing) {
        const ANIMATION_DURATION = 300;

        if (isCollapsing) {
            content.style.maxHeight = `${content.scrollHeight}px`;
            requestAnimationFrame(() => {
                content.style.maxHeight = '0';
                content.style.overflow = 'hidden';
            });
            setTimeout(() => {
                content.style.display = 'none';
                content.style.maxHeight = '';
                content.style.overflow = '';
            }, ANIMATION_DURATION);
            icon.textContent = 'expand_more';
            toggleBtn.title = '펼치기';
        } else {
            content.style.display = 'block';
            content.style.overflow = 'hidden';
            content.style.maxHeight = '0';
            requestAnimationFrame(() => {
                content.style.maxHeight = `${content.scrollHeight}px`;
            });
            setTimeout(() => {
                content.style.maxHeight = '';
                content.style.overflow = '';
            }, ANIMATION_DURATION);
            icon.textContent = 'expand_less';
            toggleBtn.title = '접기';
        }
    }

    _buildErrorCardHtml(reportId, timeStr, url, shortUrl, error) {
        return `
            <div class="absolute -left-[1px] top-0 bottom-0 w-1 bg-red-500"></div>
            <div class="p-6 md:p-8 border-b border-border-dark flex flex-col md:flex-row md:items-start justify-between gap-6">
                <div class="space-y-3">
                    <div class="flex items-center gap-3">
                        <span class="bg-red-500/20 text-red-400 text-[10px] font-bold uppercase tracking-widest px-2 py-1">Error</span>
                        <span class="text-gray-text text-xs font-mono">ID: ${reportId} • ${timeStr}</span>
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
            'report-card bg-black border border-red-500/30 relative opacity-80',
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
        const transcriptBtn = card.querySelector('.transcript-btn');
        const mindmapBtn = card.querySelector('.mindmap-btn');
        const copyBtn = card.querySelector('.copy-btn');
        const downloadBtn = card.querySelector('.download-btn');
        const deleteBtn = card.querySelector('.delete-btn');

        // 자막 원문 버튼 이벤트
        if (transcriptBtn) {
            if (data.transcript) {
                transcriptBtn.addEventListener('click', () => this._handleTranscriptClick(data));
            } else {
                // 자막이 없으면 버튼 비활성화
                transcriptBtn.classList.add('opacity-30', 'cursor-not-allowed');
                transcriptBtn.disabled = true;
                transcriptBtn.title = '자막 데이터 없음';
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

    _handleTranscriptClick(data) {
        const modal = document.getElementById('transcript-modal');
        const content = document.getElementById('transcript-content');
        const stats = document.getElementById('transcript-stats');
        const copyBtn = document.getElementById('transcript-copy-btn');
        const closeBtn = document.getElementById('transcript-close');

        if (!modal || !content) return;

        // 자막 내용 표시
        content.textContent = data.transcript;

        // 통계 표시
        const charCount = data.transcript.length;
        const wordCount = data.transcript.split(/\s+/).filter(w => w).length;
        stats.textContent = `${charCount.toLocaleString()}자 • 약 ${wordCount.toLocaleString()}단어`;

        // 모달 열기
        modal.classList.add('active');

        // 복사 버튼 이벤트 (한 번만 등록)
        const newCopyBtn = copyBtn.cloneNode(true);
        copyBtn.parentNode.replaceChild(newCopyBtn, copyBtn);
        newCopyBtn.addEventListener('click', async () => {
            try {
                await navigator.clipboard.writeText(data.transcript);
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
}
