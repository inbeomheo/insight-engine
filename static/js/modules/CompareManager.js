/**
 * CompareManager - 모델 비교 뷰 모듈
 * 동일 URL을 여러 모델로 병렬 생성하여 나란히 비교
 */
import { getEventBus, EVENTS } from '../core/EventBus.js';

export class CompareManager {
    constructor(providerManager, styleManager, urlManager, reportManager, ui, authManager) {
        this.providerManager = providerManager;
        this.styleManager = styleManager;
        this.urlManager = urlManager;
        this.reportManager = reportManager;
        this.ui = ui;
        this.authManager = authManager;
        this.isCompareMode = false;

        this._setupUI();
    }

    _setupUI() {
        // 비교 모드 토글 버튼
        this.compareToggle = document.getElementById('compare-mode-toggle');
        this.compareModelSection = document.getElementById('compare-model-section');

        if (this.compareToggle) {
            this.compareToggle.addEventListener('click', () => this.toggleCompareMode());
        }
    }

    toggleCompareMode() {
        this.isCompareMode = !this.isCompareMode;
        this.compareToggle?.classList.toggle('active', this.isCompareMode);

        if (this.compareModelSection) {
            this.compareModelSection.classList.toggle('hidden', !this.isCompareMode);
        }

        // 비교 모드일 때 모델 체크박스 렌더링
        if (this.isCompareMode) {
            this._renderModelCheckboxes();
        }

        const icon = this.compareToggle?.querySelector('.material-symbols-outlined');
        if (icon) icon.textContent = this.isCompareMode ? 'compare' : 'compare_arrows';
    }

    _renderModelCheckboxes() {
        const container = document.getElementById('compare-model-list');
        if (!container) return;

        const providers = this.providerManager.getProviders();
        container.innerHTML = '';

        Object.entries(providers).forEach(([providerId, provider]) => {
            (provider.models || []).forEach(model => {
                const modelId = `${providerId}/${model.id}`;
                const label = document.createElement('label');
                label.className = 'compare-model-checkbox';
                label.innerHTML = `
                    <input type="checkbox" value="${modelId}" name="compare-model">
                    <span class="compare-model-name">${provider.name} - ${model.name}</span>
                `;
                container.appendChild(label);
            });
        });
    }

    getSelectedModels() {
        const checkboxes = document.querySelectorAll('input[name="compare-model"]:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    }

    /**
     * 비교 생성 실행
     */
    async handleCompare() {
        const urls = this.urlManager.getUrls();
        const url = urls[0]; // 비교는 단일 URL만

        if (!url) {
            this.ui.showAlert('비교할 YouTube URL을 입력해주세요.', 'error');
            return;
        }

        const models = this.getSelectedModels();
        if (models.length < 2) {
            this.ui.showAlert('비교할 모델을 2개 이상 선택해주세요.', 'error');
            return;
        }

        if (models.length > 3) {
            this.ui.showAlert('최대 3개 모델까지 비교할 수 있습니다.', 'error');
            return;
        }

        const style = this.styleManager.getSelectedStyle();
        const modifiers = this.styleManager.getModifiers();
        const customPrompt = this.styleManager.getCustomPrompt();

        getEventBus().emit(EVENTS.COMPARE_START, { url, models });

        // 비교 결과 컨테이너 생성
        const compareCard = this._createCompareContainer(url, models);
        const reportStream = document.getElementById('report-stream');
        reportStream?.insertBefore(compareCard, reportStream.firstChild);

        try {
            const token = this.authManager?.getAccessToken?.() || '';
            const res = await fetch('/api/compare', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { 'Authorization': `Bearer ${token}` } : {})
                },
                body: JSON.stringify({ url, models, style, modifiers, customPrompt })
            });

            const data = await res.json();

            if (!res.ok) {
                throw new Error(data.error || '비교 생성 실패');
            }

            // 결과 렌더링
            this._renderCompareResults(compareCard, data, style);
            getEventBus().emit(EVENTS.COMPARE_COMPLETE, data);

            this.urlManager.clear();

        } catch (e) {
            compareCard.innerHTML = `
                <div class="compare-error">
                    <span class="material-symbols-outlined">error</span>
                    <span>${e.message}</span>
                </div>
            `;
        }
    }

    _createCompareContainer(url, models) {
        const card = document.createElement('div');
        card.className = 'compare-container';
        card.innerHTML = `
            <div class="compare-header">
                <div class="compare-header-info">
                    <span class="material-symbols-outlined">compare_arrows</span>
                    <span>모델 비교</span>
                    <span class="compare-model-count">${models.length}개 모델</span>
                </div>
                <button class="compare-close-btn" title="닫기">
                    <span class="material-symbols-outlined">close</span>
                </button>
            </div>
            <div class="compare-grid" style="grid-template-columns: repeat(${models.length}, 1fr);">
                ${models.map(m => `
                    <div class="compare-column" data-model="${m}">
                        <div class="compare-column-header">${m.split('/').pop()}</div>
                        <div class="compare-column-body">
                            <div class="flex items-center justify-center gap-2 py-8 text-gray-400">
                                <span class="material-symbols-outlined loading-spinner">progress_activity</span>
                                <span class="text-sm">생성 중...</span>
                            </div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;

        card.querySelector('.compare-close-btn')?.addEventListener('click', () => card.remove());

        return card;
    }

    _renderCompareResults(container, data, style) {
        const results = data.results || {};
        const styleLabel = this.styleManager.getStyleLabel(style);

        Object.entries(results).forEach(([modelId, result]) => {
            const col = container.querySelector(`[data-model="${modelId}"]`);
            if (!col) return;

            const body = col.querySelector('.compare-column-body');
            if (!body) return;

            if (result.error) {
                body.innerHTML = `
                    <div class="compare-error-item">
                        <span class="material-symbols-outlined">warning</span>
                        <span>${result.error}</span>
                    </div>
                `;
                return;
            }

            const tokens = result.usage?.total_tokens?.toLocaleString() || '-';
            body.innerHTML = `
                <div class="compare-result">
                    <h4 class="compare-result-title">${this.ui.escapeHtml(result.title)}</h4>
                    <div class="compare-result-meta">${tokens} tokens</div>
                    <div class="compare-result-content report-content">${this.ui.sanitizeHtml(result.html)}</div>
                    <div class="compare-result-actions">
                        <button class="compare-select-btn" data-model="${modelId}">
                            <span class="material-symbols-outlined">check_circle</span>
                            <span>이거 선택</span>
                        </button>
                    </div>
                </div>
            `;

            // "이거 선택" 버튼 이벤트
            body.querySelector('.compare-select-btn')?.addEventListener('click', () => {
                this._selectCompareResult(container, data, modelId, result, style);
            });
        });

        // 헤더에 소요 시간 표시
        const header = container.querySelector('.compare-header-info');
        if (header && data.elapsed_time) {
            header.innerHTML += `<span class="compare-elapsed">${data.elapsed_time}초</span>`;
        }
    }

    _selectCompareResult(container, compareData, modelId, result, style) {
        // 비교 컨테이너를 일반 카드로 변환
        const cardData = {
            url: container.querySelector('.compare-header-info')?.textContent?.match(/https?:\/\/\S+/)?.[0] || '',
            title: result.title,
            style,
            html: result.html,
            content: result.content,
            keywords: result.keywords || [],
            usage: result.usage,
            elapsed_time: compareData.elapsed_time,
            transcript_source: compareData.transcript_source,
        };

        this.reportManager.displayReportCard(cardData);
        container.remove();

        this.ui.showAlert(`${modelId.split('/').pop()} 결과가 선택되었습니다.`, 'success');
    }
}
