/**
 * CardEventHandler - 카드 이벤트 핸들링
 * 복사, 프롬프트, 마인드맵, 다운로드, 삭제 이벤트 담당
 */
import { ReportFormatter } from './ReportFormatter.js';

export class CardEventHandler {
    /**
     * @param {Object} storage - StorageManager
     * @param {Object} uiManager - UIManager (showAlert 등)
     * @param {Object} mindmapManager - MindmapManager (optional)
     * @param {Function} onCardDelete - 카드 삭제 시 콜백 (empty state 체크용)
     */
    constructor(storage, uiManager, mindmapManager, onCardDelete) {
        this.storage = storage;
        this.ui = uiManager;
        this.mindmapManager = mindmapManager;
        this.onCardDelete = onCardDelete;
    }

    /**
     * MindmapManager 설정 (지연 주입용)
     */
    setMindmapManager(mindmapManager) {
        this.mindmapManager = mindmapManager;
    }

    /**
     * 카드에 이벤트 바인딩
     * @param {HTMLElement} card - 카드 요소
     * @param {Object} data - 리포트 데이터
     */
    setupCardEvents(card, data) {
        const promptBtn = card.querySelector('.prompt-btn');
        const mindmapBtn = card.querySelector('.mindmap-btn');
        const downloadBtn = card.querySelector('.download-btn');
        const deleteBtn = card.querySelector('.delete-btn');

        // 개별 카드 복사 버튼들
        const copyTitleBtn = card.querySelector('.copy-title-btn');
        const copyContentBtn = card.querySelector('.copy-content-btn');
        const copyMetaBtn = card.querySelector('.copy-meta-btn');

        // 제목 복사 버튼
        copyTitleBtn?.addEventListener('click', () => {
            this._handleCardCopyClick(copyTitleBtn, data.title);
        });

        // 본문 복사 버튼
        copyContentBtn?.addEventListener('click', () => {
            this._handleCardCopyClick(copyContentBtn, data.content);
        });

        // 메타정보 복사 버튼
        copyMetaBtn?.addEventListener('click', () => {
            const metaText = ReportFormatter.buildMetaText(data);
            this._handleCardCopyClick(copyMetaBtn, metaText);
        });

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

        downloadBtn?.addEventListener('click', () => this._handleDownloadClick(data));
        deleteBtn?.addEventListener('click', () => this._handleDeleteClick(card, data.id));
    }

    /**
     * 삭제 버튼만 설정 (에러 카드용)
     */
    setupDeleteButton(card) {
        const deleteBtn = card.querySelector('.delete-btn');
        deleteBtn?.addEventListener('click', () => {
            card.remove();
            this.onCardDelete?.();
        });
    }

    /**
     * 복사 버튼 클릭 핸들러
     */
    async _handleCardCopyClick(btn, content) {
        try {
            await navigator.clipboard.writeText(content);
            const icon = btn.querySelector('.material-symbols-outlined');
            const label = btn.querySelector('span:last-child');
            const originalIcon = icon.textContent;
            const originalLabel = label.textContent;

            icon.textContent = 'check';
            label.textContent = '완료!';
            btn.classList.add('copied');

            setTimeout(() => {
                icon.textContent = originalIcon;
                label.textContent = originalLabel;
                btn.classList.remove('copied');
            }, 2000);
        } catch {
            this.ui.showAlert('복사 실패', 'error');
        }
    }

    /**
     * 프롬프트 모달 표시
     */
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

    /**
     * 마인드맵 생성 핸들러
     */
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

    /**
     * 마크다운 다운로드 핸들러
     */
    _handleDownloadClick(data) {
        const blob = new Blob([data.content], { type: 'text/markdown;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${data.title.substring(0, 30)}.md`;
        a.click();
        URL.revokeObjectURL(url);
    }

    /**
     * 카드 삭제 핸들러
     */
    _handleDeleteClick(card, reportId) {
        this.storage.removeFromHistory(reportId);
        card.style.animation = 'slideOut 0.3s ease forwards';

        setTimeout(() => {
            card.remove();
            this.onCardDelete?.();
        }, 300);
    }
}
