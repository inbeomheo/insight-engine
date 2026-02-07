/**
 * ReportManager - 리포트 카드 관리 모듈
 * 리포트 카드 생성, 표시, 히스토리 로딩 담당
 *
 * 리팩토링: HTML 빌더와 이벤트 핸들러를 별도 모듈로 분리
 */
import { CardHtmlBuilder, CardEventHandler, ReportFormatter } from './report/index.js';

export class ReportManager {
    constructor(storage, styleManager, uiManager, authManager = null) {
        this.storage = storage;
        this.styleManager = styleManager;
        this.ui = uiManager;
        this.authManager = authManager;

        // DOM 요소 캐싱
        this.elements = {
            reportStream: document.getElementById('report-stream'),
            emptyState: document.getElementById('empty-state'),
            liveIndicator: document.getElementById('live-indicator'),
            collapseAllBtn: document.getElementById('collapse-all-btn'),
            loadMoreBtn: document.getElementById('load-more-btn')
        };

        // 페이지네이션 상태
        this.pagination = {
            currentPage: 1,
            perPage: 20,
            totalPages: 0,
            hasMore: false,
            isLoading: false
        };

        // 모두 접기 버튼 이벤트 바인딩
        this._setupCollapseAllButton();

        // 더보기 버튼 이벤트 바인딩
        this._setupLoadMoreButton();

        // 모듈 초기화
        this.htmlBuilder = new CardHtmlBuilder(uiManager);
        this.eventHandler = new CardEventHandler(
            storage,
            uiManager,
            null, // mindmapManager는 나중에 설정
            () => this._checkEmptyState(),
            () => this.syncCollapseAllButtonState(), // 개별 카드 접기 시 버튼 상태 동기화
            authManager // 클라우드 히스토리 삭제 동기화용
        );
    }

    /**
     * AuthManager 설정 (초기화 순서 문제 해결용)
     */
    setAuthManager(authManager) {
        this.authManager = authManager;
    }

    setMindmapManager(mindmapManager) {
        this.eventHandler.setMindmapManager(mindmapManager);
    }

    // ==================== 내부 헬퍼 ====================

    _setEmptyStateVisibility(visible) {
        const { emptyState, liveIndicator, collapseAllBtn } = this.elements;
        if (emptyState) emptyState.style.display = visible ? 'flex' : 'none';
        if (liveIndicator) liveIndicator.style.display = visible ? 'none' : 'flex';
        // 카드가 없으면 모두 접기 버튼 숨김
        if (collapseAllBtn) collapseAllBtn.classList.toggle('hidden', visible);
    }

    // ==================== 모두 접기/펼치기 ====================

    _setupCollapseAllButton() {
        const { collapseAllBtn } = this.elements;
        if (!collapseAllBtn) return;

        collapseAllBtn.addEventListener('click', () => this.toggleCollapseAll());
    }

    _setupLoadMoreButton() {
        const { loadMoreBtn } = this.elements;
        if (!loadMoreBtn) return;

        loadMoreBtn.addEventListener('click', () => this._loadMoreHistory());
    }

    /**
     * 더보기 버튼 표시/숨김
     */
    _updateLoadMoreButton() {
        const { loadMoreBtn } = this.elements;
        if (!loadMoreBtn) return;

        if (this.pagination.hasMore && !this.pagination.isLoading) {
            loadMoreBtn.classList.remove('hidden');
            loadMoreBtn.disabled = false;
            loadMoreBtn.innerHTML = `
                <span class="material-symbols-outlined text-sm">expand_more</span>
                더보기 (${this.pagination.currentPage}/${this.pagination.totalPages})
            `;
        } else if (this.pagination.isLoading) {
            loadMoreBtn.classList.remove('hidden');
            loadMoreBtn.disabled = true;
            loadMoreBtn.innerHTML = `
                <span class="material-symbols-outlined text-sm animate-spin">progress_activity</span>
                로딩 중...
            `;
        } else {
            loadMoreBtn.classList.add('hidden');
        }
    }

    /**
     * 다음 페이지 로드
     */
    async _loadMoreHistory() {
        if (this.pagination.isLoading || !this.pagination.hasMore) return;
        if (!this.authManager?.isLoggedIn?.()) return;

        this.pagination.isLoading = true;
        this._updateLoadMoreButton();

        try {
            const headers = this.authManager.getAuthHeaders?.() || {};
            const nextPage = this.pagination.currentPage + 1;
            const response = await fetch(
                `/api/user/history?page=${nextPage}&per_page=${this.pagination.perPage}`,
                { headers }
            );

            if (!response.ok) {
                throw new Error('히스토리 로드 실패');
            }

            const data = await response.json();
            const histories = data.histories || [];

            // 페이지네이션 상태 업데이트
            this.pagination.currentPage = data.page;
            this.pagination.totalPages = data.total_pages;
            this.pagination.hasMore = data.has_more;

            // 히스토리 카드 추가 (하단에)
            histories
                .map(h => this._formatCloudHistory(h))
                .filter(Boolean)
                .forEach(h => this._displayHistoryCard(h));

            console.log(`[ReportManager] 페이지 ${nextPage} 로드 완료 (${histories.length}개)`);

        } catch (e) {
            console.error('[ReportManager] 더보기 로드 오류:', e);
        } finally {
            this.pagination.isLoading = false;
            this._updateLoadMoreButton();
        }
    }

    /**
     * 모든 카드 접기/펼치기 토글
     */
    toggleCollapseAll() {
        const cards = this.elements.reportStream.querySelectorAll('.result-card--unified');
        if (cards.length === 0) return;

        // 현재 상태 확인: 하나라도 펼쳐져 있으면 모두 접기, 전부 접혀있으면 모두 펼치기
        const hasExpanded = Array.from(cards).some(card => !card.classList.contains('collapsed'));

        cards.forEach(card => {
            if (hasExpanded) {
                card.classList.add('collapsed');
            } else {
                card.classList.remove('collapsed');
            }
        });

        this._updateCollapseAllButton(!hasExpanded);
    }

    /**
     * 모두 접기 버튼 상태 업데이트
     * @param {boolean} allCollapsed - 모든 카드가 접힌 상태인지
     */
    _updateCollapseAllButton(allCollapsed) {
        const { collapseAllBtn } = this.elements;
        if (!collapseAllBtn) return;

        const icon = collapseAllBtn.querySelector('.material-symbols-outlined');
        const label = collapseAllBtn.querySelector('.collapse-all-label');

        if (allCollapsed) {
            icon.textContent = 'unfold_more';
            label.textContent = '모두 펼치기';
            collapseAllBtn.title = '모두 펼치기';
        } else {
            icon.textContent = 'unfold_less';
            label.textContent = '모두 접기';
            collapseAllBtn.title = '모두 접기';
        }
    }

    /**
     * 개별 카드 접기/펼치기 시 버튼 상태 동기화
     */
    syncCollapseAllButtonState() {
        const cards = this.elements.reportStream.querySelectorAll('.result-card--unified');
        if (cards.length === 0) return;

        const allCollapsed = Array.from(cards).every(card => card.classList.contains('collapsed'));
        this._updateCollapseAllButton(allCollapsed);
    }

    _checkEmptyState() {
        if (this.elements.reportStream.children.length === 0) {
            this._setEmptyStateVisibility(true);
        }
    }

    _createCardElement(className, html) {
        const card = document.createElement('article');
        card.className = className;
        card.innerHTML = html;
        return card;
    }

    // ==================== Pending Card (처리 중 카드) ====================

    createPendingCard(url, style) {
        const { reportStream } = this.elements;
        this._setEmptyStateVisibility(false);

        const pendingId = ReportFormatter.generatePendingId();
        const styleLabel = this.styleManager.getStyleLabel(style);
        const shortUrl = ReportFormatter.formatShortUrl(url);
        const timeStr = ReportFormatter.getCurrentTimeStr();

        const card = this._createCardElement(
            'report-card bg-surface-dark border border-border-dark/50 relative rounded-xl overflow-hidden',
            this.htmlBuilder.buildPendingCardHtml(styleLabel, timeStr, url, shortUrl)
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
        const shortUrl = ReportFormatter.formatShortUrl(data.url);
        card.className = 'report-card bg-surface-dark border border-red-500/30 relative opacity-80 rounded-xl overflow-hidden';
        card.removeAttribute('data-pending-id');
        card.innerHTML = this.htmlBuilder.buildSimpleErrorCardHtml(data.url, shortUrl, data.error);

        this.eventHandler.setupDeleteButton(card);
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
            prompt: data.prompt || null,
            time: ReportFormatter.getCurrentTimeStr(),
            timestamp: Date.now(),
            usage: data.usage || null,
            elapsed_time: data.elapsed_time || null
        };

        this.storage.addToHistory(historyData);

        // 새로운 카드 그룹 생성 (제목, 본문, 메타정보 카드)
        const card = this._createReportCard(historyData, styleLabel, ReportFormatter.formatShortUrl(data.url));
        this.eventHandler.setupCardEvents(card, historyData);

        reportStream.insertBefore(card, reportStream.firstChild);
        setTimeout(() => card.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    }

    _createReportCard(data, styleLabel, shortUrl) {
        const card = this._createCardElement(
            'result-card-group',
            this.htmlBuilder.buildReportCardHtml(data, styleLabel, shortUrl)
        );
        card.dataset.reportId = data.id;
        return card;
    }

    displayErrorCard(data) {
        const { reportStream } = this.elements;
        this._setEmptyStateVisibility(false);

        const card = this._createCardElement(
            'report-card bg-surface-dark border border-red-500/30 relative opacity-80',
            this.htmlBuilder.buildErrorCardHtml(
                this.ui.generateReportId(),
                ReportFormatter.getCurrentTimeStr(),
                data.url,
                ReportFormatter.formatShortUrl(data.url),
                data.error
            )
        );

        this.eventHandler.setupDeleteButton(card);
        reportStream.insertBefore(card, reportStream.firstChild);
    }

    // ==================== History Loading ====================

    /**
     * 히스토리 로드 (로컬 + 클라우드 통합)
     * - 로그인 상태: 클라우드에서 로드
     * - 비로그인: 로컬 스토리지에서 로드
     */
    async loadHistory() {
        // 클라우드 히스토리 로드 시도
        if (this.authManager?.isLoggedIn?.()) {
            await this._loadCloudHistory();
            return;
        }

        // 로컬 히스토리 로드 (비로그인 또는 Supabase 비활성화)
        this._loadLocalHistory();
    }

    /**
     * 클라우드 히스토리 로드 (Supabase, 페이지네이션 지원)
     */
    async _loadCloudHistory() {
        try {
            // 페이지네이션 초기화
            this.pagination.currentPage = 1;
            this.pagination.isLoading = true;
            this._updateLoadMoreButton();

            const headers = this.authManager.getAuthHeaders?.() || {};
            const response = await fetch(
                `/api/user/history?page=1&per_page=${this.pagination.perPage}`,
                { headers }
            );

            if (!response.ok) {
                console.warn('[ReportManager] 클라우드 히스토리 로드 실패, 로컬로 폴백');
                this._loadLocalHistory();
                return;
            }

            const data = await response.json();
            const histories = data.histories || [];

            // 페이지네이션 상태 업데이트
            this.pagination.currentPage = data.page || 1;
            this.pagination.totalPages = data.total_pages || 0;
            this.pagination.hasMore = data.has_more || false;

            if (histories.length === 0) {
                // 클라우드에 히스토리 없으면 로컬도 확인
                this._loadLocalHistory();
                return;
            }

            console.log(`[ReportManager] 클라우드 히스토리 ${histories.length}개 로드 (총 ${data.total}개, ${this.pagination.totalPages}페이지)`);
            this._setEmptyStateVisibility(false);

            // P2 버그 #9: null 필터링
            histories
                .map(h => this._formatCloudHistory(h))
                .filter(Boolean)
                .forEach(h => this._displayHistoryCard(h));

        } catch (e) {
            console.error('[ReportManager] 클라우드 히스토리 로드 오류:', e);
            this._loadLocalHistory();
        } finally {
            this.pagination.isLoading = false;
            this._updateLoadMoreButton();
        }
    }

    /**
     * 클라우드 히스토리를 프론트엔드 포맷으로 변환
     * P2 버그 #9: null 체크 추가
     */
    _formatCloudHistory(h) {
        // 유효성 검사
        if (!h || typeof h !== 'object' || !h.id) {
            console.warn('[ReportManager] 유효하지 않은 히스토리:', h);
            return null;
        }

        return {
            id: h.id,
            url: h.url || '',
            title: h.title || '제목 없음',
            style: h.style || 'blog_seo',
            html: h.html || '',
            content: h.content || '',
            prompt: h.prompt ?? null,
            usage: h.usage ?? null,
            elapsed_time: h.elapsed_time ?? null,
            time: this._formatHistoryTime(h.createdAt),
            timestamp: h.timestamp ?? h.createdAt ?? Date.now()
        };
    }

    /**
     * 히스토리 시간 포맷팅 헬퍼
     */
    _formatHistoryTime(createdAt) {
        if (!createdAt) return '';
        try {
            return new Date(createdAt).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' });
        } catch {
            return '';
        }
    }

    /**
     * 로컬 스토리지에서 히스토리 로드
     */
    _loadLocalHistory() {
        const history = this.storage.getHistory();
        if (history.length === 0) return;

        this._setEmptyStateVisibility(false);
        history.forEach(data => this._displayHistoryCard(data));
    }

    _displayHistoryCard(data) {
        // 중복 체크: 이미 같은 ID의 카드가 있으면 스킵
        if (this.elements.reportStream.querySelector(`[data-report-id="${data.id}"]`)) {
            return;
        }

        const styleLabel = this.styleManager.getStyleLabel(data.style);
        const shortUrl = ReportFormatter.formatShortUrl(data.url);

        const card = this._createReportCard(data, styleLabel, shortUrl);
        this.eventHandler.setupCardEvents(card, data);
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
            // 기존 카드가 있으면 스크롤
            existingCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
            return;
        }

        // 카드가 없으면 새로 생성
        this._setEmptyStateVisibility(false);

        const styleLabel = this.styleManager.getStyleLabel(item.style);
        const shortUrl = ReportFormatter.formatShortUrl(item.url);

        // 시간 포맷 변환 (timestamp가 있으면 사용)
        const historyData = {
            ...item,
            time: item.time || new Date(item.createdAt || item.timestamp).toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
        };

        const card = this._createReportCard(historyData, styleLabel, shortUrl);
        this.eventHandler.setupCardEvents(card, historyData);

        reportStream.insertBefore(card, reportStream.firstChild);
        setTimeout(() => card.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    }
}
