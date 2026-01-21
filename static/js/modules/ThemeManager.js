/**
 * ThemeManager - Multi-Theme Support
 * 3가지 테마 지원: Dark, Light, Minimal
 */
export class ThemeManager {
    static THEMES = ['dark', 'light', 'minimal'];
    static THEME_LABELS = {
        dark: 'Dark',
        light: 'Light',
        minimal: 'Minimal'
    };
    static THEME_ICONS = {
        dark: 'dark_mode',
        light: 'light_mode',
        minimal: 'contrast'
    };
    static STORAGE_KEY = 'insight-engine-theme';

    constructor() {
        this.currentTheme = 'dark';
        this.dropdownVisible = false;
    }

    /**
     * 초기화 - 저장된 테마 복원 또는 기본 다크 모드 적용
     */
    init() {
        // localStorage에서 테마 복원
        const savedTheme = localStorage.getItem(ThemeManager.STORAGE_KEY);
        if (savedTheme && ThemeManager.THEMES.includes(savedTheme)) {
            this.currentTheme = savedTheme;
        } else {
            this.currentTheme = 'dark';
        }

        this.applyTheme(this.currentTheme);
        this.setupEventListeners();
        this.updateButtonUI();
    }

    /**
     * 테마 적용
     * @param {string} theme - 적용할 테마 ('dark', 'light', 'minimal')
     */
    applyTheme(theme) {
        if (!ThemeManager.THEMES.includes(theme)) {
            console.warn(`Unknown theme: ${theme}, falling back to dark`);
            theme = 'dark';
        }

        const html = document.documentElement;

        // 이전 테마 클래스 제거
        ThemeManager.THEMES.forEach(t => {
            html.classList.remove(t);
        });

        // 새 테마 적용
        html.setAttribute('data-theme', theme);
        html.classList.add(theme);

        // dark 클래스는 Tailwind 호환성을 위해 dark 테마일 때만 추가
        if (theme === 'dark') {
            html.classList.add('dark');
        } else {
            html.classList.remove('dark');
        }

        this.currentTheme = theme;
        localStorage.setItem(ThemeManager.STORAGE_KEY, theme);

        this.updateButtonUI();
        this.hideDropdown();

        // 테마 변경 이벤트 발행
        window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme } }));
    }

    /**
     * 테마 순환 (버튼 클릭 시)
     */
    cycleTheme() {
        const currentIndex = ThemeManager.THEMES.indexOf(this.currentTheme);
        const nextIndex = (currentIndex + 1) % ThemeManager.THEMES.length;
        this.applyTheme(ThemeManager.THEMES[nextIndex]);
    }

    /**
     * 현재 테마 반환
     */
    getCurrentTheme() {
        return this.currentTheme;
    }

    /**
     * 현재 적용된 테마 반환
     */
    getAppliedTheme() {
        return document.documentElement.getAttribute('data-theme') || 'dark';
    }

    /**
     * 이벤트 리스너 설정
     */
    setupEventListeners() {
        const themeBtn = document.getElementById('theme-toggle-btn');
        if (!themeBtn) return;

        // 버튼 클릭 시 드롭다운 토글
        themeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.toggleDropdown();
        });

        // 외부 클릭 시 드롭다운 닫기
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#theme-dropdown') && !e.target.closest('#theme-toggle-btn')) {
                this.hideDropdown();
            }
        });

        // ESC 키로 드롭다운 닫기
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.dropdownVisible) {
                this.hideDropdown();
            }
        });
    }

    /**
     * 드롭다운 토글
     */
    toggleDropdown() {
        if (this.dropdownVisible) {
            this.hideDropdown();
        } else {
            this.showDropdown();
        }
    }

    /**
     * 드롭다운 표시
     */
    showDropdown() {
        let dropdown = document.getElementById('theme-dropdown');

        if (!dropdown) {
            dropdown = this.createDropdown();
        }

        dropdown.classList.remove('hidden');
        dropdown.classList.add('theme-dropdown-enter');
        this.dropdownVisible = true;

        // 위치 조정
        const btn = document.getElementById('theme-toggle-btn');
        if (btn) {
            const rect = btn.getBoundingClientRect();
            dropdown.style.top = `${rect.bottom + 8}px`;
            dropdown.style.right = `${window.innerWidth - rect.right}px`;
        }

        // 애니메이션 후 클래스 제거
        setTimeout(() => {
            dropdown.classList.remove('theme-dropdown-enter');
        }, 200);
    }

    /**
     * 드롭다운 숨기기
     */
    hideDropdown() {
        const dropdown = document.getElementById('theme-dropdown');
        if (dropdown) {
            dropdown.classList.add('hidden');
        }
        this.dropdownVisible = false;
    }

    /**
     * 드롭다운 생성
     */
    createDropdown() {
        const dropdown = document.createElement('div');
        dropdown.id = 'theme-dropdown';
        dropdown.className = 'theme-dropdown hidden';
        dropdown.setAttribute('role', 'menu');
        dropdown.setAttribute('aria-label', '테마 선택');

        ThemeManager.THEMES.forEach(theme => {
            const item = document.createElement('button');
            item.className = 'theme-dropdown-item';
            item.setAttribute('role', 'menuitem');
            item.setAttribute('data-theme', theme);

            const isActive = theme === this.currentTheme;
            if (isActive) {
                item.classList.add('active');
            }

            item.innerHTML = `
                <span class="material-symbols-outlined">${ThemeManager.THEME_ICONS[theme]}</span>
                <span class="theme-label">${ThemeManager.THEME_LABELS[theme]}</span>
                ${isActive ? '<span class="material-symbols-outlined check-icon">check</span>' : ''}
            `;

            item.addEventListener('click', (e) => {
                e.stopPropagation();
                this.applyTheme(theme);
                this.updateDropdownItems();
            });

            dropdown.appendChild(item);
        });

        document.body.appendChild(dropdown);
        return dropdown;
    }

    /**
     * 드롭다운 아이템 업데이트
     */
    updateDropdownItems() {
        const items = document.querySelectorAll('.theme-dropdown-item');
        items.forEach(item => {
            const theme = item.getAttribute('data-theme');
            const isActive = theme === this.currentTheme;

            item.classList.toggle('active', isActive);

            // 체크 아이콘 업데이트
            const existingCheck = item.querySelector('.check-icon');
            if (isActive && !existingCheck) {
                const check = document.createElement('span');
                check.className = 'material-symbols-outlined check-icon';
                check.textContent = 'check';
                item.appendChild(check);
            } else if (!isActive && existingCheck) {
                existingCheck.remove();
            }
        });
    }

    /**
     * 버튼 UI 업데이트
     */
    updateButtonUI() {
        const btn = document.getElementById('theme-toggle-btn');
        if (!btn) return;

        const icon = btn.querySelector('.material-symbols-outlined');
        const tooltip = btn.querySelector('.theme-tooltip');

        if (icon) {
            icon.textContent = ThemeManager.THEME_ICONS[this.currentTheme];
        }

        if (tooltip) {
            tooltip.textContent = ThemeManager.THEME_LABELS[this.currentTheme];
        }

        btn.setAttribute('aria-label', `현재 테마: ${ThemeManager.THEME_LABELS[this.currentTheme]}`);
    }

    /**
     * 정리
     */
    destroy() {
        const dropdown = document.getElementById('theme-dropdown');
        if (dropdown) {
            dropdown.remove();
        }
    }
}

export default ThemeManager;
