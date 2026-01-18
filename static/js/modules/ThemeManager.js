/**
 * ThemeManager - 다크/라이트 테마 관리 모듈
 * US-003: 시스템 설정 감지, localStorage 저장, 부드러운 전환
 */
export class ThemeManager {
    constructor() {
        this.storageKey = 'cad_theme_v1';
        this.themes = {
            LIGHT: 'light',
            DARK: 'dark',
            SYSTEM: 'system'
        };
        this.transitionDuration = 150; // ms
        this.currentTheme = this.themes.SYSTEM;
        this.mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

        // 시스템 테마 변경 리스너
        this.handleSystemChange = this.handleSystemChange.bind(this);
    }

    /**
     * 초기화 - 저장된 테마 또는 시스템 설정 적용
     */
    init() {
        // 저장된 테마 불러오기
        const savedTheme = this.getSavedTheme();
        this.currentTheme = savedTheme;

        // 시스템 테마 변경 감지 리스너 등록
        this.mediaQuery.addEventListener('change', this.handleSystemChange);

        // 초기 테마 적용 (트랜지션 없이)
        this.applyTheme(this.getEffectiveTheme(), false);

        // 토글 버튼 이벤트 설정
        this.setupToggleButton();

        // 아이콘 업데이트
        this.updateToggleIcon();
    }

    /**
     * localStorage에서 저장된 테마 가져오기
     * @returns {string} 저장된 테마 또는 'system'
     */
    getSavedTheme() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved && Object.values(this.themes).includes(saved)) {
                return saved;
            }
        } catch {
            // localStorage 접근 실패
        }
        return this.themes.SYSTEM;
    }

    /**
     * 테마를 localStorage에 저장
     * @param {string} theme - 저장할 테마
     */
    saveTheme(theme) {
        try {
            localStorage.setItem(this.storageKey, theme);
        } catch {
            // localStorage 접근 실패
        }
    }

    /**
     * 실제 적용될 테마 계산 (system이면 시스템 설정 반영)
     * @returns {string} 'light' 또는 'dark'
     */
    getEffectiveTheme() {
        if (this.currentTheme === this.themes.SYSTEM) {
            return this.mediaQuery.matches ? this.themes.DARK : this.themes.LIGHT;
        }
        return this.currentTheme;
    }

    /**
     * 시스템 테마 변경 핸들러
     * @param {MediaQueryListEvent} event
     */
    handleSystemChange(event) {
        if (this.currentTheme === this.themes.SYSTEM) {
            this.applyTheme(event.matches ? this.themes.DARK : this.themes.LIGHT, true);
            this.updateToggleIcon();
        }
    }

    /**
     * 테마를 DOM에 적용
     * @param {string} theme - 적용할 테마 ('light' 또는 'dark')
     * @param {boolean} animate - 트랜지션 적용 여부
     */
    applyTheme(theme, animate = true) {
        const html = document.documentElement;
        const body = document.body;

        if (animate) {
            // 트랜지션 클래스 추가
            html.classList.add('theme-transition');
            body.classList.add('theme-transition');
        }

        // data-theme 속성 설정 (CSS 변수용)
        html.setAttribute('data-theme', theme);

        // Tailwind dark 클래스 설정
        if (theme === this.themes.DARK) {
            html.classList.add('dark');
        } else {
            html.classList.remove('dark');
        }

        if (animate) {
            // 트랜지션 완료 후 클래스 제거
            setTimeout(() => {
                html.classList.remove('theme-transition');
                body.classList.remove('theme-transition');
            }, this.transitionDuration);
        }
    }

    /**
     * 테마 전환 (light -> dark -> system -> light 순환)
     */
    toggleTheme() {
        const themes = [this.themes.LIGHT, this.themes.DARK, this.themes.SYSTEM];
        const currentIndex = themes.indexOf(this.currentTheme);
        const nextIndex = (currentIndex + 1) % themes.length;

        this.setTheme(themes[nextIndex]);
    }

    /**
     * 테마를 직접 설정
     * @param {string} theme - 설정할 테마
     */
    setTheme(theme) {
        if (!Object.values(this.themes).includes(theme)) {
            return;
        }

        this.currentTheme = theme;
        this.saveTheme(theme);
        this.applyTheme(this.getEffectiveTheme(), true);
        this.updateToggleIcon();
    }

    /**
     * 토글 버튼 아이콘 업데이트
     */
    updateToggleIcon() {
        const btn = document.getElementById('theme-toggle-btn');
        if (!btn) return;

        const icon = btn.querySelector('.material-symbols-outlined');
        const tooltip = btn.querySelector('.theme-tooltip');

        if (!icon) return;

        let iconName, tooltipText;

        switch (this.currentTheme) {
            case this.themes.LIGHT:
                iconName = 'light_mode';
                tooltipText = '라이트 모드';
                break;
            case this.themes.DARK:
                iconName = 'dark_mode';
                tooltipText = '다크 모드';
                break;
            case this.themes.SYSTEM:
            default:
                iconName = 'contrast';
                tooltipText = '시스템 설정';
                break;
        }

        icon.textContent = iconName;

        if (tooltip) {
            tooltip.textContent = tooltipText;
        }

        btn.setAttribute('aria-label', `테마 전환 (현재: ${tooltipText})`);
    }

    /**
     * 토글 버튼 이벤트 설정
     */
    setupToggleButton() {
        const btn = document.getElementById('theme-toggle-btn');
        if (btn) {
            btn.addEventListener('click', () => this.toggleTheme());
        }
    }

    /**
     * 현재 테마 반환
     * @returns {string}
     */
    getCurrentTheme() {
        return this.currentTheme;
    }

    /**
     * 현재 적용된 테마 반환 (system인 경우 실제 적용값)
     * @returns {string}
     */
    getAppliedTheme() {
        return this.getEffectiveTheme();
    }

    /**
     * 정리 - 이벤트 리스너 제거
     */
    destroy() {
        this.mediaQuery.removeEventListener('change', this.handleSystemChange);

        const btn = document.getElementById('theme-toggle-btn');
        if (btn) {
            btn.removeEventListener('click', this.toggleTheme);
        }
    }
}

export default ThemeManager;
