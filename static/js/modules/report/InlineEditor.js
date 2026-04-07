/**
 * InlineEditor - 카드 콘텐츠 인라인 편집
 * 마크다운 편집 → 미리보기 → 저장/취소
 */
export class InlineEditor {
    /**
     * @param {Object} storage - StorageManager
     * @param {Object} ui - UIManager
     * @param {Object} authManager - AuthManager
     */
    constructor(storage, ui, authManager) {
        this.storage = storage;
        this.ui = ui;
        this.authManager = authManager;
    }

    /**
     * 카드를 편집 모드로 전환
     */
    enterEditMode(card, data) {
        const body = card.querySelector('.unified-body');
        if (!body || card.dataset.editing === 'true') return;

        card.dataset.editing = 'true';
        const originalHtml = body.innerHTML;
        const originalContent = data.content || '';

        // 본문 영역을 textarea로 교체
        body.innerHTML = `
            <div class="inline-edit-container">
                <div class="inline-edit-toolbar">
                    <button class="inline-edit-btn preview-toggle-btn" title="미리보기">
                        <span class="material-symbols-outlined" style="font-size: 16px;">visibility</span>
                        <span>미리보기</span>
                    </button>
                    <div style="flex: 1;"></div>
                    <button class="inline-edit-btn save-edit-btn">
                        <span class="material-symbols-outlined" style="font-size: 16px;">check</span>
                        <span>저장</span>
                    </button>
                    <button class="inline-edit-btn cancel-edit-btn">
                        <span class="material-symbols-outlined" style="font-size: 16px;">close</span>
                        <span>취소</span>
                    </button>
                </div>
                <textarea class="inline-edit-textarea" spellcheck="false">${this.ui.escapeHtml(originalContent)}</textarea>
                <div class="inline-edit-preview hidden report-content"></div>
            </div>
        `;

        const textarea = body.querySelector('.inline-edit-textarea');
        const preview = body.querySelector('.inline-edit-preview');
        const previewBtn = body.querySelector('.preview-toggle-btn');
        const saveBtn = body.querySelector('.save-edit-btn');
        const cancelBtn = body.querySelector('.cancel-edit-btn');

        // Auto-resize textarea
        this._autoResize(textarea);
        textarea.addEventListener('input', () => this._autoResize(textarea));

        // 미리보기 토글
        let isPreview = false;
        previewBtn.addEventListener('click', async () => {
            isPreview = !isPreview;
            if (isPreview) {
                const html = await this._renderMarkdown(textarea.value);
                preview.innerHTML = this.ui.sanitizeHtml(html);
                textarea.classList.add('hidden');
                preview.classList.remove('hidden');
                previewBtn.querySelector('span:last-child').textContent = '편집';
            } else {
                textarea.classList.remove('hidden');
                preview.classList.add('hidden');
                previewBtn.querySelector('span:last-child').textContent = '미리보기';
            }
        });

        // 저장
        saveBtn.addEventListener('click', async () => {
            const newContent = textarea.value;
            const newHtml = await this._renderMarkdown(newContent);

            // 로컬 데이터 업데이트
            data.content = newContent;
            data.html = newHtml;
            this.storage.updateHistoryItem(data.id, { content: newContent, html: newHtml });

            // 클라우드 동기화
            this._syncToCloud(data.id, newContent, newHtml);

            // DOM 복원
            body.innerHTML = '';
            body.classList.add('report-content');
            body.innerHTML = this.ui.sanitizeHtml(newHtml);
            card.dataset.editing = 'false';

            this.ui.showAlert('저장 완료', 'success');
        });

        // 취소 (리스너 누수 방지: cloneNode로 이벤트 리스너 없는 깨끗한 DOM 복원)
        cancelBtn.addEventListener('click', () => {
            const cleanBody = body.cloneNode(false);
            cleanBody.classList.add('report-content');
            cleanBody.innerHTML = originalHtml;
            body.parentNode.replaceChild(cleanBody, body);
            card.dataset.editing = 'false';
        });

        // 접기/삭제 버튼 비활성화
        const collapseBtn = card.querySelector('.collapse-btn');
        const deleteBtn = card.querySelector('.delete-btn');
        if (collapseBtn) collapseBtn.disabled = true;
        if (deleteBtn) deleteBtn.disabled = true;
    }

    async _renderMarkdown(content) {
        // 서버에 마크다운→HTML 변환 요청
        try {
            const res = await fetch('/api/render-markdown', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
            if (res.ok) {
                const data = await res.json();
                return data.html;
            }
        } catch { /* fallback */ }
        // 폴백: 간단한 변환
        return `<pre>${this.ui.escapeHtml(content)}</pre>`;
    }

    async _syncToCloud(reportId, content, html) {
        if (!this.authManager?.isLoggedIn?.()) return;
        try {
            const token = this.authManager.getAccessToken?.();
            if (!token) return;
            await fetch(`/api/user/history/${reportId}`, {
                method: 'PUT',
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content, html })
            });
        } catch {
            console.warn('편집 내용 클라우드 동기화 실패');
        }
    }

    _autoResize(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = Math.max(200, textarea.scrollHeight) + 'px';
    }

}
