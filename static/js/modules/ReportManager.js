/**
 * ReportManager - 리포트 카드 관리 모듈
 * 리포트 카드 생성, 표시, 히스토리 로딩 담당
 *
 * 리팩토링: HTML 빌더와 이벤트 핸들러를 별도 모듈로 분리
 */
import { CardHtmlBuilder, CardEventHandler, ReportFormatter } from './report/index.js';

export class ReportManager {
    constructor(storage, styleManager, uiManager) {
        this.storage = storage;
        this.styleManager = styleManager;
        this.ui = uiManager;

        // DOM 요소 캐싱
        this.elements = {
            reportStream: document.getElementById('report-stream'),
            emptyState: document.getElementById('empty-state'),
            liveIndicator: document.getElementById('live-indicator')
        };

        // 모듈 초기화
        this.htmlBuilder = new CardHtmlBuilder(uiManager);
        this.eventHandler = new CardEventHandler(
            storage,
            uiManager,
            null, // mindmapManager는 나중에 설정
            () => this._checkEmptyState()
        );
    }

    setMindmapManager(mindmapManager) {
        this.eventHandler.setMindmapManager(mindmapManager);
    }

    // ==================== 내부 헬퍼 ====================

    _setEmptyStateVisibility(visible) {
        const { emptyState, liveIndicator } = this.elements;
        if (emptyState) emptyState.style.display = visible ? 'flex' : 'none';
        if (liveIndicator) liveIndicator.style.display = visible ? 'none' : 'flex';
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

    loadHistory() {
        const history = this.storage.getHistory();
        if (history.length === 0) return;

        this._setEmptyStateVisibility(false);
        history.forEach(data => this._displayHistoryCard(data));
    }

    _displayHistoryCard(data) {
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
