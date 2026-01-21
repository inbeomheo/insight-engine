/**
 * CardHtmlBuilder - 카드 HTML 템플릿 생성
 * 각종 카드 타입의 HTML 마크업 생성 담당
 */
export class CardHtmlBuilder {
    /**
     * @param {Object} uiManager - UI 매니저 (escapeHtml, sanitizeUrl 등)
     */
    constructor(uiManager) {
        this.ui = uiManager;
    }

    /**
     * Pending 카드 HTML 생성
     */
    buildPendingCardHtml(styleLabel, timeStr, url, shortUrl) {
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
                    <a class="inline-flex items-center gap-1.5 text-text-subtle/40 text-xs font-mono hover:text-text-subtle/60 transition-colors" href="${this.ui.sanitizeUrl(url)}" target="_blank" rel="noopener noreferrer">
                        <span class="material-symbols-outlined text-sm">play_circle</span>
                        <span class="truncate max-w-[200px]">${this.ui.escapeHtml(shortUrl)}</span>
                    </a>
                </div>
            </div>
            <!-- Skeleton Content Area -->
            <div class="p-6 md:p-8">
                <div class="space-y-4">
                    <div class="skeleton skeleton-text" style="width: 100%;"></div>
                    <div class="skeleton skeleton-text" style="width: 95%;"></div>
                    <div class="skeleton skeleton-text" style="width: 88%;"></div>
                    <div class="skeleton skeleton-text" style="width: 92%;"></div>
                    <div class="skeleton skeleton-text" style="width: 75%;"></div>
                </div>
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

    /**
     * 에러 카드 HTML 생성 (간단 버전)
     */
    buildSimpleErrorCardHtml(url, shortUrl, error) {
        return `
            <div class="absolute -left-[1px] top-0 bottom-0 w-1.5 bg-red-500 rounded-full"></div>
            <div class="p-6 md:p-8 border-b border-border-dark flex flex-col gap-3">
                <div class="flex items-center gap-3">
                    <span class="bg-red-500/20 text-red-400 text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded">Error</span>
                </div>
                <h3 class="text-xl font-bold text-red-400 leading-tight">분석 실패</h3>
                <a class="inline-flex items-center gap-2 text-gray-500 hover:text-white transition-colors text-sm font-mono" href="${this.ui.sanitizeUrl(url)}" target="_blank" rel="noopener noreferrer">
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

    /**
     * 에러 카드 HTML 생성 (상세 버전)
     */
    buildErrorCardHtml(reportId, timeStr, url, shortUrl, error) {
        return `
            <div class="absolute -left-[1px] top-0 bottom-0 w-1 bg-red-500"></div>
            <div class="p-6 md:p-8 border-b border-border-dark flex flex-col md:flex-row md:items-start justify-between gap-6">
                <div class="space-y-3">
                    <div class="flex items-center gap-3">
                        <span class="bg-red-500/20 text-red-400 text-[10px] font-bold uppercase tracking-widest px-2 py-1">Error</span>
                        <span class="text-text-subtle text-xs font-mono">ID: ${reportId} • ${timeStr}</span>
                    </div>
                    <h3 class="text-xl font-bold text-red-400 leading-tight">분석 실패</h3>
                    <a class="inline-flex items-center gap-2 text-gray-500 hover:text-white transition-colors text-sm font-mono uppercase tracking-wide" href="${this.ui.sanitizeUrl(url)}" target="_blank" rel="noopener noreferrer">
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

    /**
     * Stats 뱃지 HTML 생성
     */
    buildStatsBadge(icon, value) {
        return `<span class="stats-badge inline-flex items-center gap-1.5 text-primary/80"><span class="material-symbols-outlined text-xs">${icon}</span>${value}</span>`;
    }

    /**
     * Stats 뱃지들 묶음 HTML 생성
     */
    buildStatsBadges(data) {
        const badges = [];
        if (data.usage?.total_tokens) {
            badges.push(this.buildStatsBadge('token', data.usage.total_tokens.toLocaleString()));
        }
        if (data.elapsed_time) {
            badges.push(this.buildStatsBadge('schedule', `${data.elapsed_time}s`));
        }
        return badges.length ? `<div class="flex items-center gap-2 mt-1">${badges.join('')}</div>` : '';
    }

    /**
     * 자막 소스 뱃지 생성
     */
    _buildSourceBadge(source) {
        const sourceLabels = {
            'api': { label: 'API', icon: 'api', color: 'text-green-400' },
            'watch': { label: 'Watch', icon: 'web', color: 'text-blue-400' },
            'supadata': { label: 'Supadata', icon: 'cloud', color: 'text-purple-400' },
            'cache': { label: 'Cache', icon: 'cached', color: 'text-yellow-400' }
        };
        const info = sourceLabels[source] || { label: source || '?', icon: 'help', color: 'text-gray-400' };
        return `<span class="source-badge ${info.color}" title="자막 소스: ${info.label}"><span class="material-symbols-outlined">${info.icon}</span></span>`;
    }

    /**
     * 리포트 카드 HTML 생성 (통합 컴팩트 디자인)
     */
    buildReportCardHtml(data, styleLabel, shortUrl) {
        // 메타 정보 빌드 (인라인 형태)
        const metaChips = [];
        if (data.usage?.total_tokens) {
            metaChips.push(`<span class="meta-chip"><span class="material-symbols-outlined">token</span>${data.usage.total_tokens.toLocaleString()}</span>`);
        }
        if (data.elapsed_time) {
            metaChips.push(`<span class="meta-chip"><span class="material-symbols-outlined">schedule</span>${data.elapsed_time}초</span>`);
        }

        // 자막 소스 뱃지
        const sourceBadge = data.transcript_source ? this._buildSourceBadge(data.transcript_source) : '';

        return `
            <!-- 통합 결과 카드 -->
            <div class="result-card result-card--unified">
                <!-- 헤더: 제목 + 메타 + 복사버튼 -->
                <div class="unified-header">
                    <div class="unified-header-top">
                        <div class="header-badges">
                            <span class="style-badge">${styleLabel}</span>
                            <span class="time-badge">${data.time}</span>
                            ${sourceBadge}
                        </div>
                        <div class="header-actions">
                            <button class="icon-btn copy-title-btn" title="제목 복사" data-copy-type="title">
                                <span class="material-symbols-outlined">content_copy</span>
                            </button>
                            <button class="icon-btn copy-content-btn" title="전체 복사" data-copy-type="content">
                                <span class="material-symbols-outlined">file_copy</span>
                            </button>
                            <button class="icon-btn collapse-btn" title="접기/펼치기">
                                <span class="material-symbols-outlined">expand_less</span>
                            </button>
                        </div>
                    </div>
                    <h3 class="unified-title">${this.ui.escapeHtml(data.title)}</h3>
                    <a class="source-link" href="${this.ui.sanitizeUrl(data.url)}" target="_blank" rel="noopener noreferrer">
                        <span class="material-symbols-outlined">play_circle</span>
                        <span>${this.ui.escapeHtml(shortUrl)}</span>
                    </a>
                </div>

                <!-- 본문 -->
                <div class="unified-body report-content">
                    ${this.ui.sanitizeHtml(data.html)}
                </div>

                <!-- 푸터: 메타 + 액션 (간소화) -->
                <div class="unified-footer">
                    <div class="meta-chips">
                        ${metaChips.join('')}
                    </div>
                    <div class="footer-actions">
                        <button class="action-btn download-btn" title="저장">
                            <span class="material-symbols-outlined">download</span>
                        </button>
                        <div class="more-actions-btn">
                            <button class="action-btn" title="더보기">
                                <span class="material-symbols-outlined">more_horiz</span>
                            </button>
                            <div class="more-actions-menu">
                                <button class="action-btn prompt-btn">
                                    <span class="material-symbols-outlined">code</span>
                                    <span>프롬프트</span>
                                </button>
                                <button class="action-btn mindmap-btn">
                                    <span class="material-symbols-outlined">account_tree</span>
                                    <span>마인드맵</span>
                                </button>
                            </div>
                        </div>
                        <button class="action-btn delete-btn" title="삭제">
                            <span class="material-symbols-outlined">delete</span>
                        </button>
                    </div>
                </div>
            </div>
        `;
    }
}
