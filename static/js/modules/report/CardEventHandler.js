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
     * @param {Function} onCollapseChange - 카드 접기/펼치기 시 콜백 (버튼 상태 동기화용)
     * @param {Object} authManager - AuthManager (optional, 클라우드 삭제 동기화용)
     * @param {Function} onRegenerate - 재생성 콜백 (url을 받아 생성 트리거)
     */
    constructor(storage, uiManager, mindmapManager, onCardDelete, onCollapseChange = null, authManager = null, onRegenerate = null) {
        this.storage = storage;
        this.ui = uiManager;
        this.mindmapManager = mindmapManager;
        this.onCardDelete = onCardDelete;
        this.onCollapseChange = onCollapseChange;
        this.authManager = authManager;
        this.onRegenerate = onRegenerate;
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
        const collapseBtn = card.querySelector('.collapse-btn');
        const htmlExportBtn = card.querySelector('.html-export-btn');
        const copyRichBtn = card.querySelector('.copy-rich-btn');
        const regenerateBtn = card.querySelector('.regenerate-btn');
        const shareBtn = card.querySelector('.share-btn');

        // 개별 카드 복사 버튼들
        const copyTitleBtn = card.querySelector('.copy-title-btn');
        const copyContentBtn = card.querySelector('.copy-content-btn');
        const copyMetaBtn = card.querySelector('.copy-meta-btn');

        // 접기/펼치기 버튼 이벤트
        collapseBtn?.addEventListener('click', () => this._handleCollapseClick(card));

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

        // 더보기 메뉴 aria-expanded 토글
        const moreActionsBtn = card.querySelector('.more-actions-btn');
        if (moreActionsBtn) {
            const triggerBtn = moreActionsBtn.querySelector('button[aria-haspopup]');
            if (triggerBtn) {
                moreActionsBtn.addEventListener('mouseenter', () => triggerBtn.setAttribute('aria-expanded', 'true'));
                moreActionsBtn.addEventListener('mouseleave', () => triggerBtn.setAttribute('aria-expanded', 'false'));
            }
        }

        downloadBtn?.addEventListener('click', () => this._handleDownloadClick(data));
        htmlExportBtn?.addEventListener('click', () => this._handleHtmlExportClick(data));
        copyRichBtn?.addEventListener('click', () => this._handleRichCopyClick(copyRichBtn, data));
        regenerateBtn?.addEventListener('click', () => this._handleRegenerateClick(data));
        shareBtn?.addEventListener('click', () => this._handleShareClick(shareBtn, data));
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
     * HTML 내보내기 핸들러
     */
    _handleHtmlExportClick(data) {
        const htmlContent = `<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>${(data.title || 'AI 생성 결과').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</title>
<style>
body { font-family: 'Pretendard', -apple-system, sans-serif; max-width: 800px; margin: 2rem auto; padding: 0 1.5rem; line-height: 1.8; color: #1f2937; }
h1 { font-size: 1.75rem; font-weight: 700; margin: 1.5rem 0 0.75rem; border-bottom: 2px solid #e5e7eb; padding-bottom: 0.5rem; }
h2 { font-size: 1.375rem; font-weight: 600; color: #0d7377; margin: 1.25rem 0 0.5rem; }
h3 { font-size: 1.125rem; font-weight: 600; margin: 1rem 0 0.375rem; }
p { margin: 0.625rem 0; }
ul, ol { padding-left: 1.5rem; margin: 0.625rem 0; }
li { margin: 0.375rem 0; }
blockquote { margin: 1rem 0; padding: 1rem 1.25rem; background: #f3f4f6; border-left: 3px solid #0d7377; border-radius: 0 8px 8px 0; }
table { width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.875rem; }
th, td { padding: 0.75rem 1rem; border-bottom: 1px solid #e5e7eb; text-align: left; }
th { font-weight: 600; background: #f9fafb; }
code { background: #f3f4f6; padding: 0.2rem 0.4rem; border-radius: 3px; font-size: 0.85em; }
pre { background: #f3f4f6; padding: 1rem; border-radius: 8px; overflow-x: auto; }
pre code { background: transparent; padding: 0; }
strong { font-weight: 600; }
a { color: #0d7377; }
</style>
</head>
<body>
${data.html || ''}
</body>
</html>`;
        const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${(data.title || 'content').substring(0, 30)}.html`;
        a.click();
        URL.revokeObjectURL(url);
    }

    /**
     * 서식 있는 복사 (Rich Copy) 핸들러
     */
    async _handleRichCopyClick(btn, data) {
        try {
            const htmlBlob = new Blob([data.html || ''], { type: 'text/html' });
            const textBlob = new Blob([data.content || ''], { type: 'text/plain' });
            const item = new ClipboardItem({
                'text/html': htmlBlob,
                'text/plain': textBlob
            });
            await navigator.clipboard.write([item]);

            const icon = btn.querySelector('.material-symbols-outlined');
            const originalIcon = icon.textContent;
            icon.textContent = 'check';
            btn.title = '복사 완료!';
            setTimeout(() => {
                icon.textContent = originalIcon;
                btn.title = '서식 복사';
            }, 2000);
        } catch {
            // ClipboardItem 미지원 시 텍스트 복사로 폴백
            try {
                await navigator.clipboard.writeText(data.content || '');
                this.ui.showAlert('서식 복사가 지원되지 않아 텍스트만 복사되었습니다.', 'warning');
            } catch {
                this.ui.showAlert('복사 실패', 'error');
            }
        }
    }

    /**
     * 재생성 핸들러 - URL을 입력 필드에 채우고 생성 트리거
     */
    _handleRegenerateClick(data) {
        if (!data.url) {
            this.ui.showAlert('재생성할 URL 정보가 없습니다.', 'warning');
            return;
        }
        if (this.onRegenerate) {
            this.onRegenerate(data.url);
        } else {
            // 폴백: URL 입력 필드에 직접 채우기
            const urlInput = document.getElementById('url-input');
            if (urlInput) {
                urlInput.value = data.url;
                urlInput.dispatchEvent(new Event('input', { bubbles: true }));
                this.ui.showAlert('URL이 입력되었습니다. 생성 버튼을 클릭해주세요.', 'success');
            }
        }
    }

    /**
     * 공유 핸들러 - 요약 텍스트를 클립보드에 복사
     */
    async _handleShareClick(btn, data) {
        const title = data.title || 'AI 생성 결과';
        const preview = (data.content || '').substring(0, 200);
        const shareText = `${title}\n\n${preview}${(data.content || '').length > 200 ? '...' : ''}\n\n${data.url || ''}`;

        try {
            await navigator.clipboard.writeText(shareText);
            const icon = btn.querySelector('.material-symbols-outlined');
            const label = btn.querySelector('span:last-child');
            if (icon) icon.textContent = 'check';
            if (label) label.textContent = '복사됨';
            setTimeout(() => {
                if (icon) icon.textContent = 'share';
                if (label) label.textContent = '공유';
            }, 2000);
        } catch {
            this.ui.showAlert('복사 실패', 'error');
        }
    }

    /**
     * 카드 삭제 핸들러
     * 로컬 스토리지 삭제 + 로그인 상태면 클라우드도 삭제
     */
    _handleDeleteClick(card, reportId) {
        this.storage.removeFromHistory(reportId);
        this._deleteFromCloud(reportId);

        card.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => {
            card.remove();
            this.onCardDelete?.();
        }, 300);
    }

    /**
     * 클라우드 히스토리 삭제 (로그인 상태일 때만)
     * 실패해도 로컬 삭제는 유지 (UX 우선)
     */
    async _deleteFromCloud(reportId) {
        if (!this.authManager?.isLoggedIn?.()) return;

        try {
            const token = this.authManager.getAccessToken?.();
            if (!token) return;

            const res = await fetch(`/api/user/history/${reportId}`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (!res.ok) {
                console.warn(`클라우드 히스토리 삭제 실패: ${res.status}`);
            }
        } catch (e) {
            console.warn('클라우드 히스토리 삭제 중 오류:', e);
        }
    }

    /**
     * 카드 접기/펼치기 핸들러
     */
    _handleCollapseClick(card) {
        const resultCard = card.querySelector('.result-card--unified') || card.closest('.result-card--unified') || card;
        resultCard.classList.toggle('collapsed');

        // 버튼 title 업데이트
        const collapseBtn = card.querySelector('.collapse-btn');
        if (collapseBtn) {
            const isCollapsed = resultCard.classList.contains('collapsed');
            collapseBtn.title = isCollapsed ? '펼치기' : '접기';
        }

        // 모두 접기 버튼 상태 동기화
        this.onCollapseChange?.();
    }
}
