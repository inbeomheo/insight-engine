/**
 * ThemeManager - Light 테마 고정 (no-op stub)
 * 기존 멀티 테마 시스템에서 Light 단일 테마로 전환됨.
 * 외부 참조 호환성을 위해 export만 유지.
 */
export class ThemeManager {
    constructor() {
        this.currentTheme = 'light';
    }

    init() {}

    getCurrentTheme() {
        return 'light';
    }

    getAppliedTheme() {
        return 'light';
    }

    destroy() {}
}

export default ThemeManager;
