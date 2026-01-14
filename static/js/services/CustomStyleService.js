/**
 * CustomStyleService - 커스텀 스타일 관리 서비스
 * StyleManager ↔ ModalManager 순환 의존 해결
 * EventBus를 통해 모듈 간 통신
 */
import { EVENTS } from '../core/EventBus.js';

export class CustomStyleService {
    /**
     * @param {Object} storage - StorageManager 인스턴스
     * @param {Object} eventBus - EventBus 인스턴스
     */
    constructor(storage, eventBus) {
        this.storage = storage;
        this.eventBus = eventBus;
        this.maxStyles = 5;
    }

    /**
     * 모든 커스텀 스타일 조회
     * @returns {Array}
     */
    getAll() {
        return this.storage.getCustomStyles() || [];
    }

    /**
     * ID로 커스텀 스타일 조회
     * @param {string} id - 스타일 ID
     * @returns {Object|null}
     */
    getById(id) {
        const styles = this.getAll();
        return styles.find(s => s.id === id) || null;
    }

    /**
     * 커스텀 스타일 추가
     * @param {Object} styleData - { name, icon, prompt }
     * @returns {Object|null} 생성된 스타일 또는 null (제한 초과)
     */
    add(styleData) {
        const styles = this.getAll();

        if (styles.length >= this.maxStyles) {
            return null;
        }

        const newStyle = {
            id: `custom_${Date.now()}`,
            name: styleData.name,
            icon: styleData.icon || 'edit_note',
            prompt: styleData.prompt
        };

        styles.push(newStyle);
        this.storage.setCustomStyles(styles);

        // 이벤트 발행
        this.eventBus.emit(EVENTS.STYLE_CUSTOM_ADD, newStyle);

        return newStyle;
    }

    /**
     * 커스텀 스타일 업데이트
     * @param {string} id - 스타일 ID
     * @param {Object} updates - { name?, icon?, prompt? }
     * @returns {Object|null} 업데이트된 스타일 또는 null
     */
    update(id, updates) {
        const styles = this.getAll();
        const index = styles.findIndex(s => s.id === id);

        if (index === -1) {
            return null;
        }

        const updatedStyle = {
            ...styles[index],
            ...updates
        };

        styles[index] = updatedStyle;
        this.storage.setCustomStyles(styles);

        // 이벤트 발행
        this.eventBus.emit(EVENTS.STYLE_CUSTOM_UPDATE, updatedStyle);

        return updatedStyle;
    }

    /**
     * 커스텀 스타일 삭제
     * @param {string} id - 스타일 ID
     * @returns {boolean} 성공 여부
     */
    delete(id) {
        const styles = this.getAll();
        const index = styles.findIndex(s => s.id === id);

        if (index === -1) {
            return false;
        }

        styles.splice(index, 1);
        this.storage.setCustomStyles(styles);

        // 이벤트 발행
        this.eventBus.emit(EVENTS.STYLE_CUSTOM_DELETE, { id });

        return true;
    }

    /**
     * 커스텀 스타일인지 확인
     * @param {string} id - 스타일 ID
     * @returns {boolean}
     */
    isCustomStyle(id) {
        return id && id.startsWith('custom_');
    }

    /**
     * 커스텀 스타일 개수 확인
     * @returns {number}
     */
    getCount() {
        return this.getAll().length;
    }

    /**
     * 추가 가능한 개수
     * @returns {number}
     */
    getRemainingSlots() {
        return Math.max(0, this.maxStyles - this.getCount());
    }

    /**
     * 최대 개수에 도달했는지 확인
     * @returns {boolean}
     */
    isMaxReached() {
        return this.getCount() >= this.maxStyles;
    }
}

export default CustomStyleService;
