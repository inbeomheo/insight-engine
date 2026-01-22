/**
 * UsagePanelManager - 사용량 바 UI 관리
 * 입력 패널 상단의 사용량 프로그레스 바를 관리
 */
export class UsagePanelManager {
    constructor(storageManager, eventBus) {
        this.storageManager = storageManager;
        this.eventBus = eventBus;
        this.elements = {};
    }

    init() {
        this.cacheElements();
        this.bindEvents();
        this.render();
    }

    cacheElements() {
        this.elements = {
            barText: document.getElementById('usage-bar-text'),
            barProgress: document.getElementById('usage-bar-progress'),
            adminBtn: document.getElementById('admin-dashboard-btn')
        };
    }

    bindEvents() {
        // 사용량 업데이트 이벤트 수신
        this.eventBus?.on('usage:updated', () => this.render());

        // 인증 상태 변경 시 업데이트
        window.addEventListener('auth:state-changed', () => this.render());
    }

    async render() {
        await this.updateUsageBar();
    }

    async updateUsageBar() {
        try {
            const response = await fetch('/api/user/usage');
            if (!response.ok) {
                this.showLocalMode();
                return;
            }

            const data = await response.json();

            // 관리자 여부 확인
            const isAdmin = data.is_admin || false;

            // 관리자 버튼 표시/숨기기
            if (this.elements.adminBtn) {
                this.elements.adminBtn.classList.toggle('hidden', !isAdmin);
            }

            // 관리자는 무제한
            if (isAdmin) {
                this.showAdminMode();
                return;
            }

            const used = data.used || 0;
            const limit = data.limit || 20;
            const percent = Math.min(100, (used / limit) * 100);

            // 텍스트 업데이트
            if (this.elements.barText) {
                this.elements.barText.textContent = `${used}/${limit}`;
            }

            // 프로그레스 바 업데이트
            if (this.elements.barProgress) {
                this.elements.barProgress.style.width = `${percent}%`;
                this.elements.barProgress.style.backgroundColor = this.getColorByPercent(percent);
            }

        } catch (e) {
            console.warn('사용량 조회 실패:', e);
            this.showLocalMode();
        }
    }

    /**
     * 퍼센트에 따른 색상 반환
     * 0-50%: primary (테라코타)
     * 51-80%: amber (경고)
     * 81-100%: red (위험)
     */
    getColorByPercent(percent) {
        if (percent <= 50) {
            return 'var(--primary)';
        } else if (percent <= 80) {
            return '#F59E0B'; // amber
        } else {
            return '#EF4444'; // red
        }
    }

    showAdminMode() {
        if (this.elements.barText) {
            this.elements.barText.textContent = '∞ 무제한';
            this.elements.barText.classList.add('text-primary');
        }
        if (this.elements.barProgress) {
            this.elements.barProgress.style.width = '100%';
            this.elements.barProgress.style.backgroundColor = 'var(--primary)';
            this.elements.barProgress.style.opacity = '0.5';
        }
    }

    showLocalMode() {
        // 로컬 모드 (Supabase 비활성화)
        if (this.elements.barText) {
            this.elements.barText.textContent = '로컬 모드';
        }
        if (this.elements.barProgress) {
            this.elements.barProgress.style.width = '0%';
        }
        if (this.elements.adminBtn) {
            this.elements.adminBtn.classList.add('hidden');
        }
    }
}
