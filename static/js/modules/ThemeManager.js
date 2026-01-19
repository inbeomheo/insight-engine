/**
 * ThemeManager - Dark Mode Only
 * 다크 모드 전용 설정 (라이트 모드 제거됨)
 */
export class ThemeManager {
    constructor() {
        // Dark mode only
    }

    /**
     * 초기화 - 다크 모드 적용
     */
    init() {
        const html = document.documentElement;
        html.setAttribute('data-theme', 'dark');
        html.classList.add('dark');
    }

    /**
     * 현재 테마 반환 (항상 다크)
     */
    getCurrentTheme() {
        return 'dark';
    }

    /**
     * 현재 적용된 테마 반환 (항상 다크)
     */
    getAppliedTheme() {
        return 'dark';
    }

    /**
     * 정리 (no-op)
     */
    destroy() {}
}

export default ThemeManager;
