/**
 * MindmapManager - 마인드맵 생성 및 시각화 모듈
 * Markmap 라이브러리를 사용하여 마크다운을 마인드맵으로 변환
 */
export class MindmapManager {
    constructor(storage, providerManager, uiManager) {
        this.storage = storage;
        this.providerManager = providerManager;
        this.ui = uiManager;
        this.markmapInstance = null;

        // DOM 요소 캐싱
        this.elements = {
            modal: document.getElementById('mindmap-modal'),
            loading: document.getElementById('mindmap-loading'),
            svg: document.getElementById('mindmap-svg'),
            title: document.getElementById('mindmap-title'),
            stats: document.getElementById('mindmap-stats')
        };

        this.setupEventListeners();
    }

    setupEventListeners() {
        const { modal } = this.elements;

        // 모달 닫기
        document.getElementById('mindmap-close')?.addEventListener('click', () => this.closeModal());
        modal?.addEventListener('click', (e) => {
            if (e.target === modal) this.closeModal();
        });

        // 줌 컨트롤
        document.getElementById('mindmap-zoom-in')?.addEventListener('click', () => this.zoomIn());
        document.getElementById('mindmap-zoom-out')?.addEventListener('click', () => this.zoomOut());
        document.getElementById('mindmap-fit')?.addEventListener('click', () => this.fit());

        // ESC 키로 닫기
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal?.classList.contains('active')) {
                this.closeModal();
            }
        });
    }

    _setModalState(isLoading, title = '마인드맵', stats = '') {
        const { modal, loading, svg, title: titleEl, stats: statsEl } = this.elements;

        modal.classList.add('active');
        loading.style.display = isLoading ? 'flex' : 'none';
        svg.innerHTML = '';
        titleEl.textContent = title;
        statsEl.textContent = stats;
    }

    showCachedMindmap(markdown, title) {
        this._setModalState(false, title || '마인드맵', '캐시됨');
        this.renderMindmap(markdown);
    }

    async generateMindmap(content, title) {
        this._setModalState(true, title || '마인드맵');

        try {
            const provider = this.providerManager.getSelectedProvider();
            const model = this.providerManager.getSelectedModel();
            const apiKey = this.storage.getApiKey(provider);

            if (!apiKey) {
                throw new Error('API 키가 설정되지 않았습니다.');
            }

            const response = await fetch('/api/mindmap', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content, model, apiKey })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || '마인드맵 생성 실패');
            }

            this.renderMindmap(data.markdown);

            if (data.usage) {
                const tokens = data.usage.total_tokens?.toLocaleString() || '-';
                this.elements.stats.textContent = `토큰: ${tokens} | 시간: ${data.elapsed_time || '-'}초`;
            }

            return data.markdown;

        } catch (error) {
            console.error('Mindmap generation error:', error);
            this.ui.showAlert(error.message || '마인드맵 생성 중 오류가 발생했습니다.', 'error');
            this.closeModal();
            return null;
        } finally {
            this.elements.loading.style.display = 'none';
        }
    }

    static DEPTH_COLORS = ['#D4A574', '#E8C49A', '#B88B5A', '#C9A77C', '#A67B5B'];

    renderMindmap(markdown) {
        const { svg } = this.elements;

        if (!svg) {
            console.error('SVG element not found');
            return;
        }

        try {
            const { Transformer, Markmap } = window.markmap;

            if (!Transformer || !Markmap) {
                throw new Error('Markmap 라이브러리가 로드되지 않았습니다.');
            }

            const { root } = new Transformer().transform(markdown);

            if (this.markmapInstance) {
                svg.innerHTML = '';
            }

            this.markmapInstance = Markmap.create(svg, {
                color: (node) => MindmapManager.DEPTH_COLORS[node.state?.depth % MindmapManager.DEPTH_COLORS.length] || MindmapManager.DEPTH_COLORS[0],
                paddingX: 16,
                autoFit: true,
                duration: 500,
                maxWidth: 300,
                initialExpandLevel: 3
            }, root);

            setTimeout(() => this.fit(), 100);

        } catch (error) {
            console.error('Mindmap render error:', error);
            this._renderFallbackMarkdown(svg, markdown);
        }
    }

    _renderFallbackMarkdown(svg, markdown) {
        svg.innerHTML = `
            <foreignObject width="100%" height="100%">
                <div xmlns="http://www.w3.org/1999/xhtml" style="padding: 20px; color: #D4A574; font-family: monospace; white-space: pre-wrap; overflow: auto; height: 100%;">
                    ${this._escapeHtml(markdown)}
                </div>
            </foreignObject>
        `;
    }

    zoomIn() {
        this.markmapInstance?.rescale(1.25);
    }

    zoomOut() {
        this.markmapInstance?.rescale(0.8);
    }

    fit() {
        this.markmapInstance?.fit();
    }

    closeModal() {
        this.elements.modal?.classList.remove('active');
    }

    _escapeHtml(text) {
        const escapeMap = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
        return String(text).replace(/[&<>"']/g, (char) => escapeMap[char]);
    }
}
