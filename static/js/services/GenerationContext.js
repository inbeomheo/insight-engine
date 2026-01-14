/**
 * GenerationContext - 콘텐츠 생성 컨텍스트
 * ContentGenerator의 의존성을 축소 (7개 → 이 클래스 1개 + 필수 3개)
 * 생성에 필요한 파라미터를 중앙에서 수집
 */
export class GenerationContext {
    /**
     * @param {Object} providerManager - ProviderManager 인스턴스
     * @param {Object} styleManager - StyleManager 인스턴스
     * @param {Object} urlManager - UrlManager 인스턴스
     */
    constructor(providerManager, styleManager, urlManager) {
        this.providerManager = providerManager;
        this.styleManager = styleManager;
        this.urlManager = urlManager;
    }

    /**
     * 콘텐츠 생성에 필요한 모든 파라미터 수집
     * @returns {Object}
     */
    getGenerationParams() {
        return {
            urls: this.urlManager.getUrls(),
            provider: this.providerManager.getSelectedProvider(),
            model: this.providerManager.getSelectedModel(),
            style: this.styleManager.getSelectedStyle(),
            modifiers: this.styleManager.getModifiers(),
            customPrompt: this.styleManager.getCustomPrompt()
        };
    }

    /**
     * 단일 URL 생성 파라미터
     * @param {string} url - 명시적 URL (없으면 첫 번째 URL 사용)
     * @returns {Object}
     */
    getSingleGenerationParams(url = null) {
        const params = this.getGenerationParams();
        return {
            ...params,
            url: url || (params.urls.length > 0 ? params.urls[0] : null)
        };
    }

    /**
     * 배치 생성 파라미터
     * @returns {Object}
     */
    getBatchGenerationParams() {
        return this.getGenerationParams();
    }

    /**
     * 생성 가능 여부 확인
     * @returns {Object} { valid: boolean, error?: string }
     */
    validate() {
        const params = this.getGenerationParams();

        if (params.urls.length === 0) {
            return { valid: false, error: 'YouTube URL을 입력해주세요.' };
        }

        if (!params.provider) {
            return { valid: false, error: '사용 가능한 AI 서비스가 없습니다.' };
        }

        if (!params.model) {
            return { valid: false, error: '모델을 선택해주세요.' };
        }

        return { valid: true };
    }

    /**
     * 현재 선택된 프로바이더 정보
     * @returns {Object|null}
     */
    getProviderInfo() {
        return this.providerManager.getCurrentProviderInfo?.() || null;
    }

    /**
     * 현재 선택된 스타일 정보
     * @returns {Object}
     */
    getStyleInfo() {
        return {
            style: this.styleManager.getSelectedStyle(),
            isCustom: this.styleManager.isCustomStyle?.(this.styleManager.getSelectedStyle()) || false
        };
    }

    /**
     * URL 개수
     * @returns {number}
     */
    getUrlCount() {
        return this.urlManager.getUrls().length;
    }

    /**
     * 배치 모드인지 확인 (URL 2개 이상)
     * @returns {boolean}
     */
    isBatchMode() {
        return this.getUrlCount() > 1;
    }
}

export default GenerationContext;
