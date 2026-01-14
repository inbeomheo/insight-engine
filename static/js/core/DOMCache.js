/**
 * DOMCache - DOM 요소 캐싱 유틸리티
 * 반복되는 DOM 쿼리를 최적화
 */
export class DOMCache {
    constructor() {
        this.cache = new Map();
        this.hitCount = 0;
        this.missCount = 0;
    }

    /**
     * 단일 요소 조회 (캐싱)
     * @param {string} selector - CSS 선택자
     * @param {boolean} force - 캐시 무시 여부
     * @returns {Element|null}
     */
    get(selector, force = false) {
        if (!force && this.cache.has(selector)) {
            const cached = this.cache.get(selector);
            // 요소가 여전히 DOM에 존재하는지 확인
            if (document.contains(cached)) {
                this.hitCount++;
                return cached;
            }
            // DOM에서 제거된 경우 캐시에서도 제거
            this.cache.delete(selector);
        }

        const element = document.querySelector(selector);
        if (element) {
            this.cache.set(selector, element);
        }
        this.missCount++;
        return element;
    }

    /**
     * 다중 요소 조회 (캐싱하지 않음 - NodeList는 동적일 수 있음)
     * @param {string} selector - CSS 선택자
     * @returns {NodeList}
     */
    getAll(selector) {
        return document.querySelectorAll(selector);
    }

    /**
     * ID로 요소 조회 (최적화된 버전)
     * @param {string} id - 요소 ID
     * @param {boolean} force - 캐시 무시 여부
     * @returns {Element|null}
     */
    getById(id, force = false) {
        const cacheKey = `#${id}`;
        if (!force && this.cache.has(cacheKey)) {
            const cached = this.cache.get(cacheKey);
            if (document.contains(cached)) {
                this.hitCount++;
                return cached;
            }
            this.cache.delete(cacheKey);
        }

        const element = document.getElementById(id);
        if (element) {
            this.cache.set(cacheKey, element);
        }
        this.missCount++;
        return element;
    }

    /**
     * 특정 선택자의 캐시 무효화
     * @param {string} selector - CSS 선택자
     */
    invalidate(selector) {
        this.cache.delete(selector);
    }

    /**
     * 패턴에 맞는 캐시 무효화
     * @param {string} pattern - 선택자 패턴 (startsWith 매칭)
     */
    invalidatePattern(pattern) {
        for (const key of this.cache.keys()) {
            if (key.startsWith(pattern)) {
                this.cache.delete(key);
            }
        }
    }

    /**
     * 모든 캐시 무효화
     */
    invalidateAll() {
        this.cache.clear();
    }

    /**
     * 캐시 통계 조회
     * @returns {Object}
     */
    getStats() {
        const total = this.hitCount + this.missCount;
        return {
            size: this.cache.size,
            hits: this.hitCount,
            misses: this.missCount,
            hitRate: total > 0 ? (this.hitCount / total * 100).toFixed(2) + '%' : '0%'
        };
    }

    /**
     * 통계 초기화
     */
    resetStats() {
        this.hitCount = 0;
        this.missCount = 0;
    }

    /**
     * DOM 변경 감지 시 캐시 정리 (옵션)
     * @param {Element} root - 감시할 루트 요소
     */
    observeMutations(root = document.body) {
        const observer = new MutationObserver((mutations) => {
            // 요소가 제거되면 관련 캐시 정리
            mutations.forEach(mutation => {
                if (mutation.removedNodes.length > 0) {
                    this._cleanupRemovedNodes(mutation.removedNodes);
                }
            });
        });

        observer.observe(root, {
            childList: true,
            subtree: true
        });

        return observer;
    }

    /**
     * 제거된 노드와 관련된 캐시 정리
     * @private
     */
    _cleanupRemovedNodes(nodes) {
        nodes.forEach(node => {
            if (node.nodeType === Node.ELEMENT_NODE) {
                // 캐시에서 해당 요소 찾아서 제거
                for (const [selector, element] of this.cache.entries()) {
                    if (node === element || node.contains(element)) {
                        this.cache.delete(selector);
                    }
                }
            }
        });
    }
}

// 싱글톤 인스턴스
let domCacheInstance = null;

/**
 * DOMCache 싱글톤 인스턴스 조회
 * @returns {DOMCache}
 */
export function getDOMCache() {
    if (!domCacheInstance) {
        domCacheInstance = new DOMCache();
    }
    return domCacheInstance;
}

// 자주 사용되는 요소 ID 상수
export const DOM_IDS = {
    // 입력 요소
    URL_INPUT: 'url-input',
    URL_LIST_CONTAINER: 'url-list-container',

    // 버튼
    START_BTN: 'start-btn',
    RUN_BTN: 'run-btn',
    AI_ANALYZE_BTN: 'ai-analyze-btn',

    // 리포트
    REPORT_STREAM: 'report-stream',
    PENDING_STREAM: 'pending-stream',

    // 모달
    SETTINGS_MODAL: 'settings-modal',
    CUSTOM_STYLE_MODAL: 'custom-style-modal',
    AUTH_MODAL: 'auth-modal',
    ONBOARDING_MODAL: 'onboarding-modal',

    // 프로바이더
    PROVIDER_SELECT: 'provider-select',
    MODEL_SELECT: 'model-select',

    // 사용량
    USAGE_TEXT: 'usage-text',
    USAGE_BAR: 'usage-bar',
};

export default DOMCache;
