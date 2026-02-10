/**
 * CardHtmlBuilder - 카드 HTML 템플릿 생성
 * 각종 카드 타입의 HTML 마크업 생성 담당
 */
import { SeoAnalyzer } from '../../services/SeoAnalyzer.js';

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
            <div class="card-header p-5 md:p-6 border-b" style="border-color: var(--border-dark);">
                <div class="space-y-3">
                    <div class="flex items-center gap-2 text-xs text-gray-500">
                        <span class="font-medium text-indigo-600">${styleLabel}</span>
                        <span>&middot;</span>
                        <span>${timeStr}</span>
                        <span>&middot;</span>
                        <span class="inline-flex items-center gap-1 text-indigo-600 animate-pulse">
                            <span class="material-symbols-outlined text-xs loading-spinner">progress_activity</span>
                            분석 중
                        </span>
                    </div>
                    <div class="space-y-2">
                        <div class="skeleton skeleton-title"></div>
                        <div class="skeleton skeleton-text" style="width: 50%;"></div>
                    </div>
                    <a class="inline-flex items-center gap-1.5 text-gray-400 text-xs hover:text-gray-600 transition-colors" href="${this.ui.sanitizeUrl(url)}" target="_blank" rel="noopener noreferrer">
                        <span class="material-symbols-outlined text-sm">play_circle</span>
                        <span class="truncate max-w-[200px]">${this.ui.escapeHtml(shortUrl)}</span>
                    </a>
                </div>
            </div>
            <div class="p-5 md:p-6">
                <div class="space-y-4">
                    <div class="skeleton skeleton-text" style="width: 100%;"></div>
                    <div class="skeleton skeleton-text" style="width: 95%;"></div>
                    <div class="skeleton skeleton-text" style="width: 88%;"></div>
                    <div class="skeleton skeleton-text" style="width: 92%;"></div>
                    <div class="skeleton skeleton-text" style="width: 75%;"></div>
                </div>
                <div class="flex items-center justify-center gap-3 mt-6 pt-4 border-t" style="border-color: var(--border-dark);">
                    <div class="flex items-center gap-1.5">
                        <span class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 0ms"></span>
                        <span class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 150ms"></span>
                        <span class="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-bounce" style="animation-delay: 300ms"></span>
                    </div>
                    <span class="text-xs text-gray-400">AI가 영상을 분석하고 있습니다</span>
                </div>
            </div>
        `;
    }

    /**
     * 에러 카드 HTML 생성 (간단 버전)
     */
    buildSimpleErrorCardHtml(url, shortUrl, error) {
        return `
            <div class="p-5 md:p-6 border-b flex flex-col gap-3" style="border-color: var(--border-dark);">
                <div class="flex items-center gap-2 text-xs">
                    <span class="text-red-600 font-semibold">Error</span>
                </div>
                <h3 class="text-lg font-semibold text-red-600 leading-tight">분석 실패</h3>
                <a class="inline-flex items-center gap-1.5 text-gray-400 hover:text-gray-600 transition-colors text-xs" href="${this.ui.sanitizeUrl(url)}" target="_blank" rel="noopener noreferrer">
                    <span class="material-symbols-outlined text-sm">open_in_new</span> ${this.ui.escapeHtml(shortUrl)}
                </a>
            </div>
            <div class="p-5 md:p-6 text-gray-600 text-sm">
                <div class="flex items-center gap-2 text-red-600">
                    <span class="material-symbols-outlined text-base">warning</span>
                    <span>${this.ui.escapeHtml(error)}</span>
                </div>
            </div>
            <div class="border-t px-4 py-3 flex justify-end" style="border-color: var(--border-dark);">
                <button class="delete-btn inline-flex items-center gap-1.5 text-xs text-red-500 hover:text-red-600 px-3 py-2 hover:bg-red-50 transition-colors rounded-lg">
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
            <div class="p-5 md:p-6 border-b flex flex-col gap-3" style="border-color: var(--border-dark);">
                <div class="flex items-center gap-2 text-xs text-gray-500">
                    <span class="text-red-600 font-semibold">Error</span>
                    <span>&middot;</span>
                    <span>ID: ${reportId}</span>
                    <span>&middot;</span>
                    <span>${timeStr}</span>
                </div>
                <h3 class="text-lg font-semibold text-red-600 leading-tight">분석 실패</h3>
                <a class="inline-flex items-center gap-1.5 text-gray-400 hover:text-gray-600 transition-colors text-xs" href="${this.ui.sanitizeUrl(url)}" target="_blank" rel="noopener noreferrer">
                    <span class="material-symbols-outlined text-sm">open_in_new</span> ${this.ui.escapeHtml(shortUrl)}
                </a>
            </div>
            <div class="p-5 md:p-6 text-gray-600 text-sm">
                <div class="flex items-center gap-2 text-red-600">
                    <span class="material-symbols-outlined text-base">warning</span>
                    <span>${this.ui.escapeHtml(error)}</span>
                </div>
            </div>
            <div class="border-t p-4 flex justify-end gap-3" style="border-color: var(--border-dark);">
                <button class="delete-btn text-xs text-red-500 hover:text-red-600 px-4 py-2 hover:bg-red-50 transition-colors rounded-lg">삭제</button>
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
        // 글자수/단어수
        const charCount = (data.content || '').length;
        if (charCount > 0) {
            badges.push(this.buildStatsBadge('edit_note', `${charCount.toLocaleString()}자`));
        }
        const wordCount = (data.content || '').split(/\s+/).filter(w => w).length;
        if (wordCount > 0) {
            badges.push(this.buildStatsBadge('description', `${wordCount.toLocaleString()}단어`));
        }
        return badges.length ? `<div class="flex items-center gap-2 mt-1">${badges.join('')}</div>` : '';
    }

    /**
     * 자막 소스 뱃지 생성
     */
    _buildSourceBadge(source) {
        const sourceLabels = {
            'api': { label: 'API', icon: 'api', color: 'text-green-600' },
            'watch': { label: 'Watch', icon: 'web', color: 'text-blue-600' },
            'supadata': { label: 'Supadata', icon: 'cloud', color: 'text-purple-600' },
            'cache': { label: 'Cache', icon: 'cached', color: 'text-yellow-600' }
        };
        const info = sourceLabels[source] || { label: source || '?', icon: 'help', color: 'text-gray-500' };
        return `<span class="source-badge ${info.color}" title="자막 소스: ${info.label}"><span class="material-symbols-outlined">${info.icon}</span></span>`;
    }

    /**
     * 키워드 태그 칩 HTML 생성
     */
    _buildKeywordChips(keywords) {
        if (!keywords || !Array.isArray(keywords) || keywords.length === 0) return '';
        const chips = keywords.map(kw =>
            `<span class="keyword-chip" title="클릭하여 복사">${this.ui.escapeHtml(kw)}</span>`
        ).join('');
        return `<div class="keyword-chips">${chips}</div>`;
    }

    /**
     * 리포트 카드 HTML 생성 (통합 미니멀 디자인)
     */
    buildReportCardHtml(data, styleLabel, shortUrl) {
        // 메타 정보 빌드 (한 줄 텍스트, · 구분)
        const metaParts = [];
        if (data.usage?.total_tokens) {
            metaParts.push(`${data.usage.total_tokens.toLocaleString()} tokens`);
        }
        if (data.elapsed_time) {
            metaParts.push(`${data.elapsed_time}초`);
        }
        const charCount = (data.content || '').length;
        if (charCount > 0) {
            metaParts.push(`${charCount.toLocaleString()}자`);
        }
        const wordCount = (data.content || '').split(/\s+/).filter(w => w).length;
        if (wordCount > 0) {
            metaParts.push(`${wordCount.toLocaleString()}단어`);
        }
        if (data.comment_summary_included === false) {
            metaParts.push('댓글 미포함');
        }
        const metaText = metaParts.join(' · ');

        // 자막 소스 뱃지
        const sourceBadge = data.transcript_source ? this._buildSourceBadge(data.transcript_source) : '';

        // SEO 뱃지 (blog_seo 스타일만)
        const seoBadgeHtml = this._buildSeoBadge(data);

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
                            <button class="icon-btn favorite-btn${data.is_favorite ? ' active' : ''}" title="즐겨찾기" data-report-id="${data.id}">
                                <span class="material-symbols-outlined">${data.is_favorite ? 'star' : 'star_border'}</span>
                            </button>
                            <button class="icon-btn copy-title-btn" title="제목 복사" data-copy-type="title">
                                <span class="material-symbols-outlined">content_copy</span>
                            </button>
                            <button class="icon-btn copy-content-btn" title="전체 복사" data-copy-type="content">
                                <span class="material-symbols-outlined">file_copy</span>
                            </button>
                            <button class="icon-btn copy-rich-btn" title="서식 복사">
                                <span class="material-symbols-outlined">content_paste</span>
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

                <!-- 키워드 태그 -->
                ${this._buildKeywordChips(data.keywords)}

                <!-- 본문 -->
                <div class="unified-body report-content">
                    ${this.ui.sanitizeHtml(data.html)}
                </div>

                <!-- 푸터: 메타 텍스트 + 아이콘 액션 -->
                <div class="unified-footer">
                    <div class="meta-text">${metaText} ${seoBadgeHtml}</div>
                    <div class="footer-actions">
                        <button class="action-btn download-btn" title="저장">
                            <span class="material-symbols-outlined">download</span>
                        </button>
                        <div class="more-actions-btn">
                            <button class="action-btn" title="더보기" aria-haspopup="menu" aria-expanded="false" aria-label="더보기 메뉴">
                                <span class="material-symbols-outlined">more_horiz</span>
                            </button>
                            <div class="more-actions-menu" role="menu" aria-label="추가 작업">
                                <button class="action-btn prompt-btn" role="menuitem">
                                    <span class="material-symbols-outlined">code</span>
                                    <span>프롬프트</span>
                                </button>
                                <button class="action-btn mindmap-btn" role="menuitem">
                                    <span class="material-symbols-outlined">account_tree</span>
                                    <span>마인드맵</span>
                                </button>
                                <button class="action-btn html-export-btn" role="menuitem">
                                    <span class="material-symbols-outlined">html</span>
                                    <span>HTML</span>
                                </button>
                                <button class="action-btn docx-export-btn" role="menuitem">
                                    <span class="material-symbols-outlined">description</span>
                                    <span>Word</span>
                                </button>
                                <button class="action-btn edit-content-btn" role="menuitem">
                                    <span class="material-symbols-outlined">edit</span>
                                    <span>편집</span>
                                </button>
                                <button class="action-btn regenerate-btn" role="menuitem">
                                    <span class="material-symbols-outlined">refresh</span>
                                    <span>다시 생성</span>
                                </button>
                                <button class="action-btn share-btn" role="menuitem">
                                    <span class="material-symbols-outlined">share</span>
                                    <span>공유</span>
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

    /**
     * SEO 뱃지 HTML 생성 (blog_seo 스타일만)
     */
    _buildSeoBadge(data) {
        // blog_seo 스타일 + 제목에 [Blog SEO] 접두사가 있는 경우 포함
        const isSeoStyle = (data.style === 'blog_seo') ||
            (data.title && data.title.startsWith('[Blog SEO]'));
        if (!isSeoStyle || !data.html) return '';

        try {
            const result = SeoAnalyzer.analyze(data.html, data.title, data.keywords);
            const grade = SeoAnalyzer.getGrade(result.score);
            return `<span class="seo-badge" style="background: ${grade.color}15; color: ${grade.color}; border-color: ${grade.color}30;" title="SEO 점수 상세 보기" data-seo-score="${result.score}" data-seo-items='${JSON.stringify(result.items)}'>
                <span class="material-symbols-outlined" style="font-size: 12px;">query_stats</span>
                SEO <span class="seo-grade">${grade.label}</span> ${result.score}점
            </span>`;
        } catch {
            return '';
        }
    }
}
