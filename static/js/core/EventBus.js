/**
 * EventBus - Pub/Sub 패턴 이벤트 시스템
 * 모듈 간 느슨한 결합을 위한 이벤트 버스
 */
export class EventBus {
    constructor() {
        this.listeners = new Map();
        this.onceListeners = new Map();
    }

    /**
     * 이벤트 구독
     * @param {string} event - 이벤트 이름
     * @param {Function} callback - 콜백 함수
     * @returns {Function} 구독 해제 함수
     */
    on(event, callback) {
        if (!this.listeners.has(event)) {
            this.listeners.set(event, new Set());
        }
        this.listeners.get(event).add(callback);

        // 구독 해제 함수 반환
        return () => this.off(event, callback);
    }

    /**
     * 일회성 이벤트 구독
     * @param {string} event - 이벤트 이름
     * @param {Function} callback - 콜백 함수
     */
    once(event, callback) {
        if (!this.onceListeners.has(event)) {
            this.onceListeners.set(event, new Set());
        }
        this.onceListeners.get(event).add(callback);
    }

    /**
     * 이벤트 구독 해제
     * @param {string} event - 이벤트 이름
     * @param {Function} callback - 콜백 함수
     */
    off(event, callback) {
        if (this.listeners.has(event)) {
            this.listeners.get(event).delete(callback);
        }
        if (this.onceListeners.has(event)) {
            this.onceListeners.get(event).delete(callback);
        }
    }

    /**
     * 이벤트 발행
     * @param {string} event - 이벤트 이름
     * @param {*} data - 전달할 데이터
     */
    emit(event, data) {
        // 일반 리스너 호출
        if (this.listeners.has(event)) {
            this.listeners.get(event).forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[EventBus] Error in listener for "${event}":`, error);
                }
            });
        }

        // 일회성 리스너 호출 후 제거
        if (this.onceListeners.has(event)) {
            const onceCallbacks = this.onceListeners.get(event);
            this.onceListeners.delete(event);
            onceCallbacks.forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error(`[EventBus] Error in once listener for "${event}":`, error);
                }
            });
        }
    }

    /**
     * 특정 이벤트의 모든 리스너 제거
     * @param {string} event - 이벤트 이름
     */
    clear(event) {
        this.listeners.delete(event);
        this.onceListeners.delete(event);
    }

    /**
     * 모든 이벤트 리스너 제거
     */
    clearAll() {
        this.listeners.clear();
        this.onceListeners.clear();
    }

    /**
     * 이벤트 리스너 수 조회
     * @param {string} event - 이벤트 이름
     * @returns {number}
     */
    listenerCount(event) {
        const regular = this.listeners.has(event) ? this.listeners.get(event).size : 0;
        const once = this.onceListeners.has(event) ? this.onceListeners.get(event).size : 0;
        return regular + once;
    }
}

// 사전 정의된 이벤트 이름 상수
export const EVENTS = {
    // 인증 관련
    AUTH_LOGIN: 'auth:login',
    AUTH_LOGOUT: 'auth:logout',
    AUTH_CHANGE: 'auth:change',

    // 사용량 관련
    USAGE_UPDATE: 'usage:update',
    USAGE_EXHAUSTED: 'usage:exhausted',

    // 스타일 관련
    STYLE_CHANGE: 'style:change',
    STYLE_CUSTOM_ADD: 'style:custom:add',
    STYLE_CUSTOM_UPDATE: 'style:custom:update',
    STYLE_CUSTOM_DELETE: 'style:custom:delete',

    // 콘텐츠 생성 관련
    GENERATE_START: 'generate:start',
    GENERATE_PROGRESS: 'generate:progress',
    GENERATE_COMPLETE: 'generate:complete',
    GENERATE_ERROR: 'generate:error',

    // 모달 관련
    MODAL_OPEN: 'modal:open',
    MODAL_CLOSE: 'modal:close',

    // URL 관련
    URL_ADD: 'url:add',
    URL_REMOVE: 'url:remove',
    URL_CLEAR: 'url:clear',
    URL_REORDER: 'url:reorder',

    // 상태 변경
    STATE_CHANGE: 'state:change',
};

// 싱글톤 인스턴스
let eventBusInstance = null;

/**
 * EventBus 싱글톤 인스턴스 조회
 * @returns {EventBus}
 */
export function getEventBus() {
    if (!eventBusInstance) {
        eventBusInstance = new EventBus();
    }
    return eventBusInstance;
}

export default EventBus;
