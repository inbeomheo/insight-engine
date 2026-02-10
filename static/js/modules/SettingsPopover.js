/**
 * SettingsPopover - 설정 팝오버 관리
 * URL 입력 바의 ⚙ 버튼 클릭 시 팝오버 토글
 * writing-style select ↔ hidden radio 동기화
 */
export class SettingsPopover {
    constructor() {
        this.popover = document.getElementById('settings-popover');
        this.toggleBtn = document.getElementById('settings-popover-btn');
        this.writingStyleSelect = document.getElementById('writing-style-select');
        this.languageSelect = document.getElementById('language-select');
        this.isOpen = false;
    }

    init() {
        if (!this.popover || !this.toggleBtn) return;

        // 팝오버 토글
        this.toggleBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggle();
        });

        // 바깥 클릭 시 닫기
        document.addEventListener('click', (e) => {
            if (this.isOpen && !e.target.closest('#settings-popover') && !e.target.closest('#settings-popover-btn')) {
                this.close();
            }
        });

        // ESC 키로 닫기
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.close();
            }
        });

        // writing-style select ↔ hidden radio 동기화
        this._setupWritingStyleSync();

        // language select ↔ hidden radio 동기화
        this._setupLanguageSync();
    }

    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }

    open() {
        if (!this.popover) return;
        this.popover.classList.remove('hidden');
        this.toggleBtn?.setAttribute('aria-expanded', 'true');
        this.isOpen = true;
    }

    close() {
        if (!this.popover) return;
        this.popover.classList.add('hidden');
        this.toggleBtn?.setAttribute('aria-expanded', 'false');
        this.isOpen = false;
    }

    /**
     * writing-style <select> 변경 시 hidden radio와 동기화
     */
    _setupWritingStyleSync() {
        if (!this.writingStyleSelect) return;

        this.writingStyleSelect.addEventListener('change', () => {
            const value = this.writingStyleSelect.value;
            const radio = document.querySelector(`input[name="writing_style"][value="${value}"]`);
            if (radio) {
                radio.checked = true;
                radio.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    }

    _setupLanguageSync() {
        if (!this.languageSelect) return;

        this.languageSelect.addEventListener('change', () => {
            const value = this.languageSelect.value;
            const radio = document.querySelector(`input[name="language"][value="${value}"]`);
            if (radio) {
                radio.checked = true;
                radio.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    }
}
