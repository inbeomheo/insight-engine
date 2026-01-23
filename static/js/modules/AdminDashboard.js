/**
 * AdminDashboard - 관리자 대시보드 UI 관리
 */
export class AdminDashboard {
    constructor(uiManager, authManager) {
        this.ui = uiManager;
        this.authManager = authManager;
        this.currentPage = 1;
        this.perPage = 20;
        this.elements = {};
    }

    getHeaders() {
        return this.authManager?.getAuthHeaders?.() || {};
    }

    init() {
        this.cacheElements();
        this.bindEvents();
    }

    cacheElements() {
        this.elements = {
            modal: document.getElementById('admin-modal'),
            closeBtn: document.getElementById('admin-modal-close'),
            tabs: document.querySelectorAll('.admin-tab'),
            usersTab: document.getElementById('admin-users-tab'),
            contentsTab: document.getElementById('admin-contents-tab'),
            usersTbody: document.getElementById('admin-users-tbody'),
            contentsTbody: document.getElementById('admin-contents-tbody'),
            pagination: document.getElementById('admin-contents-pagination'),
            preview: document.getElementById('admin-content-preview'),
            previewTitle: document.getElementById('admin-preview-title'),
            previewContent: document.getElementById('admin-preview-content'),
            previewClose: document.getElementById('admin-preview-close'),
            statTotal: document.getElementById('admin-stat-total'),
            statActive: document.getElementById('admin-stat-active'),
            statExhausted: document.getElementById('admin-stat-exhausted')
        };
    }

    bindEvents() {
        // 모달 닫기
        this.elements.closeBtn?.addEventListener('click', () => this.close());
        this.elements.modal?.addEventListener('click', (e) => {
            if (e.target === this.elements.modal) this.close();
        });

        // ESC 키로 닫기
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.elements.modal?.classList.contains('active')) {
                this.close();
            }
        });

        // 탭 전환
        this.elements.tabs?.forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        // 미리보기 닫기
        this.elements.previewClose?.addEventListener('click', () => {
            this.elements.preview?.classList.add('hidden');
        });
    }

    async open() {
        this.elements.modal?.classList.add('active');
        await this.loadUsers();
        await this.loadStats();
    }

    close() {
        this.elements.modal?.classList.remove('active');
        this.elements.preview?.classList.add('hidden');
    }

    switchTab(tabName) {
        // 탭 버튼 활성화 상태 업데이트
        this.elements.tabs?.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        // 탭 콘텐츠 표시/숨기기
        this.elements.usersTab?.classList.toggle('hidden', tabName !== 'users');
        this.elements.contentsTab?.classList.toggle('hidden', tabName !== 'contents');

        // 콘텐츠 탭 선택 시 데이터 로드
        if (tabName === 'contents') {
            this.loadContents();
        }
    }

    async loadStats() {
        try {
            const response = await fetch('/api/admin/stats', { headers: this.getHeaders() });
            if (!response.ok) return;

            const data = await response.json();
            if (this.elements.statTotal) this.elements.statTotal.textContent = data.total_users || 0;
            if (this.elements.statActive) this.elements.statActive.textContent = data.active_today || 0;
            if (this.elements.statExhausted) this.elements.statExhausted.textContent = data.exhausted_users || 0;
        } catch (e) {
            console.error('통계 로드 실패:', e);
        }
    }

    async loadUsers() {
        const tbody = this.elements.usersTbody;
        if (!tbody) return;

        tbody.innerHTML = '<tr><td colspan="4" class="text-center p-4 text-text-muted">로딩 중...</td></tr>';

        try {
            const response = await fetch('/api/admin/users', { headers: this.getHeaders() });
            if (!response.ok) throw new Error('API 오류');

            const data = await response.json();
            const users = data.users || [];

            if (users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center p-4 text-text-muted">사용자가 없습니다.</td></tr>';
                return;
            }

            tbody.innerHTML = users.map(user => this.renderUserRow(user)).join('');

            // 리셋 버튼 이벤트
            tbody.querySelectorAll('.admin-reset-btn').forEach(btn => {
                btn.addEventListener('click', () => this.resetUser(btn.dataset.userId));
            });

        } catch (e) {
            console.error('사용자 로드 실패:', e);
            tbody.innerHTML = '<tr><td colspan="4" class="text-center p-4 text-red-400">로드 실패</td></tr>';
        }
    }

    renderUserRow(user) {
        const usageCount = user.usage_count ?? 0;
        const maxUsage = 20;
        const used = maxUsage - usageCount;
        const percent = (used / maxUsage) * 100;

        // 색상 결정
        let colorClass = 'text-text-primary';
        if (percent >= 80) colorClass = 'text-red-400';
        else if (percent >= 50) colorClass = 'text-amber-400';

        return `
            <tr class="border-b border-border-dark/50 hover:bg-background-dark/50">
                <td class="p-3 text-text-primary">${this.escapeHtml(user.user_id?.substring(0, 20) || '-')}...</td>
                <td class="p-3 text-center">
                    <span class="${colorClass} font-medium">${used}/${maxUsage}</span>
                </td>
                <td class="p-3 text-center text-text-muted text-xs">${user.last_reset_date || '-'}</td>
                <td class="p-3 text-center">
                    <button class="admin-reset-btn px-2 py-1 text-xs bg-primary/20 text-primary hover:bg-primary/30 rounded transition-colors" data-user-id="${user.user_id}">
                        리셋
                    </button>
                </td>
            </tr>
        `;
    }

    async resetUser(userId) {
        if (!confirm('이 사용자의 사용량을 리셋하시겠습니까?')) return;

        try {
            const response = await fetch(`/api/admin/users/${userId}/reset`, {
                method: 'POST',
                headers: this.getHeaders()
            });
            if (response.ok) {
                this.ui?.showAlert('사용량이 리셋되었습니다.', 'success');
                await this.loadUsers();
                await this.loadStats();
            } else {
                this.ui?.showAlert('리셋에 실패했습니다.', 'error');
            }
        } catch (e) {
            console.error('리셋 실패:', e);
            this.ui?.showAlert('리셋 중 오류가 발생했습니다.', 'error');
        }
    }

    async loadContents(page = 1) {
        this.currentPage = page;
        const tbody = this.elements.contentsTbody;
        if (!tbody) return;

        tbody.innerHTML = '<tr><td colspan="4" class="text-center p-4 text-text-muted">로딩 중...</td></tr>';

        try {
            const response = await fetch(`/api/admin/contents?page=${page}&per_page=${this.perPage}`, {
                headers: this.getHeaders()
            });
            if (!response.ok) throw new Error('API 오류');

            const data = await response.json();
            const contents = data.contents || [];

            if (contents.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-center p-4 text-text-muted">콘텐츠가 없습니다.</td></tr>';
                this.renderPagination(0, 0);
                return;
            }

            tbody.innerHTML = contents.map(content => this.renderContentRow(content)).join('');
            this.renderPagination(data.total_pages, data.page);

            // 행 클릭 이벤트 (미리보기)
            tbody.querySelectorAll('.admin-content-row').forEach(row => {
                row.addEventListener('click', () => this.showPreview(row.dataset.reportId));
            });

        } catch (e) {
            console.error('콘텐츠 로드 실패:', e);
            tbody.innerHTML = '<tr><td colspan="4" class="text-center p-4 text-red-400">로드 실패</td></tr>';
        }
    }

    renderContentRow(content) {
        const createdAt = new Date(content.created_at).toLocaleDateString('ko-KR');
        return `
            <tr class="admin-content-row border-b border-border-dark/50 hover:bg-background-dark/50 cursor-pointer" data-report-id="${content.id}">
                <td class="p-3 text-text-primary">${this.escapeHtml(content.title || '제목 없음')}</td>
                <td class="p-3 text-center">
                    <span class="px-2 py-0.5 bg-primary/20 text-primary rounded text-xs">${content.style || '-'}</span>
                </td>
                <td class="p-3 text-center text-text-muted text-xs">${content.user_id?.substring(0, 8) || '-'}...</td>
                <td class="p-3 text-center text-text-muted text-xs">${createdAt}</td>
            </tr>
        `;
    }

    renderPagination(totalPages, currentPage) {
        const container = this.elements.pagination;
        if (!container) return;

        if (totalPages <= 1) {
            container.innerHTML = '';
            return;
        }

        let html = '';

        // 이전 버튼
        html += `<button class="admin-page-btn px-3 py-1 text-sm rounded ${currentPage <= 1 ? 'text-text-muted cursor-not-allowed' : 'text-text-primary hover:bg-surface-dark'}" data-page="${currentPage - 1}" ${currentPage <= 1 ? 'disabled' : ''}>이전</button>`;

        // 페이지 번호
        for (let i = 1; i <= totalPages; i++) {
            if (i === currentPage) {
                html += `<span class="px-3 py-1 text-sm bg-primary text-white rounded">${i}</span>`;
            } else if (i <= 3 || i > totalPages - 2 || Math.abs(i - currentPage) <= 1) {
                html += `<button class="admin-page-btn px-3 py-1 text-sm text-text-primary hover:bg-surface-dark rounded" data-page="${i}">${i}</button>`;
            } else if (i === 4 || i === totalPages - 2) {
                html += `<span class="px-2 text-text-muted">...</span>`;
            }
        }

        // 다음 버튼
        html += `<button class="admin-page-btn px-3 py-1 text-sm rounded ${currentPage >= totalPages ? 'text-text-muted cursor-not-allowed' : 'text-text-primary hover:bg-surface-dark'}" data-page="${currentPage + 1}" ${currentPage >= totalPages ? 'disabled' : ''}>다음</button>`;

        container.innerHTML = html;

        // 페이지 버튼 이벤트
        container.querySelectorAll('.admin-page-btn:not([disabled])').forEach(btn => {
            btn.addEventListener('click', () => this.loadContents(parseInt(btn.dataset.page)));
        });
    }

    async showPreview(reportId) {
        try {
            const response = await fetch(`/api/admin/contents/${reportId}`, {
                headers: this.getHeaders()
            });
            if (!response.ok) throw new Error('API 오류');

            const content = await response.json();

            if (this.elements.previewTitle) {
                this.elements.previewTitle.textContent = content.title || '제목 없음';
            }

            if (this.elements.previewContent) {
                // HTML 콘텐츠가 있으면 표시, 없으면 텍스트 콘텐츠
                const displayContent = content.html || content.content || '내용 없음';
                this.elements.previewContent.innerHTML = this.ui?.sanitizeHtml?.(displayContent) || this.escapeHtml(displayContent);
            }

            this.elements.preview?.classList.remove('hidden');

        } catch (e) {
            console.error('미리보기 로드 실패:', e);
            this.ui?.showAlert('미리보기를 불러올 수 없습니다.', 'error');
        }
    }

    escapeHtml(str) {
        if (!str) return '';
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}
