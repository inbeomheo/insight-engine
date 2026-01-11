/**
 * StorageManager - LocalStorage 관리 모듈
 * 설정, 히스토리, 커스텀 스타일 등의 저장/로드 담당
 */
export class StorageManager {
    constructor() {
        this.keys = {
            settings: 'cad_settings_v1',
            supadata: 'cad_supadata_key_v1',
            history: 'cad_history_v1',
            customStyles: 'cad_custom_styles_v1'
        };
        this.maxHistoryItems = 50;
        this.maxCustomStyles = 5;
    }

    // ==================== Settings ====================

    getSettings() {
        try {
            const raw = localStorage.getItem(this.keys.settings);
            return raw ? JSON.parse(raw) : { providers: {}, selectedProvider: '' };
        } catch {
            return { providers: {}, selectedProvider: '' };
        }
    }

    saveSettings(settings) {
        try {
            localStorage.setItem(this.keys.settings, JSON.stringify(settings));
        } catch {
            // ignore
        }
    }

    getApiKey(providerId) {
        const settings = this.getSettings();
        return settings.providers[providerId]?.apiKey || '';
    }

    hasAnyApiKey() {
        const settings = this.getSettings();
        return Object.values(settings.providers).some(p => p.apiKey && p.apiKey.trim());
    }

    getConfiguredProviders() {
        const settings = this.getSettings();
        return Object.entries(settings.providers)
            .filter(([_, config]) => config.apiKey && config.apiKey.trim())
            .map(([id]) => id);
    }

    // ==================== Supadata API Key ====================

    getSupadataApiKey() {
        try {
            return localStorage.getItem(this.keys.supadata) || '';
        } catch {
            return '';
        }
    }

    saveSupadataApiKey(key) {
        try {
            if (key) {
                localStorage.setItem(this.keys.supadata, key);
            } else {
                localStorage.removeItem(this.keys.supadata);
            }
        } catch {
            // ignore
        }
    }

    // ==================== History ====================

    getHistory() {
        try {
            const raw = localStorage.getItem(this.keys.history);
            return raw ? JSON.parse(raw) : [];
        } catch {
            return [];
        }
    }

    saveHistory(history) {
        try {
            localStorage.setItem(this.keys.history, JSON.stringify(history));
        } catch (e) {
            console.warn('히스토리 저장 실패:', e);
        }
    }

    addToHistory(reportData) {
        try {
            const history = this.getHistory();
            const existingIndex = history.findIndex(item => item.id === reportData.id);
            if (existingIndex >= 0) {
                history[existingIndex] = reportData;
            } else {
                history.unshift(reportData);
            }
            if (history.length > this.maxHistoryItems) {
                history.splice(this.maxHistoryItems);
            }
            this.saveHistory(history);
        } catch (e) {
            console.warn('히스토리 추가 실패:', e);
        }
    }

    removeFromHistory(reportId) {
        try {
            const history = this.getHistory();
            const filtered = history.filter(item => item.id !== reportId);
            this.saveHistory(filtered);
        } catch (e) {
            console.warn('히스토리 삭제 실패:', e);
        }
    }

    updateHistoryItem(reportId, updates) {
        try {
            const history = this.getHistory();
            const index = history.findIndex(item => item.id === reportId);
            if (index >= 0) {
                history[index] = { ...history[index], ...updates };
                this.saveHistory(history);
                return true;
            }
            return false;
        } catch (e) {
            console.warn('히스토리 업데이트 실패:', e);
            return false;
        }
    }

    // ==================== Custom Styles ====================

    getCustomStyles() {
        try {
            const raw = localStorage.getItem(this.keys.customStyles);
            return raw ? JSON.parse(raw) : [];
        } catch {
            return [];
        }
    }

    saveCustomStyles(styles) {
        try {
            localStorage.setItem(this.keys.customStyles, JSON.stringify(styles));
        } catch (e) {
            console.warn('커스텀 스타일 저장 실패:', e);
        }
    }

    addCustomStyle(styleData) {
        const styles = this.getCustomStyles();
        if (styles.length >= this.maxCustomStyles) {
            return { success: false, message: `커스텀 스타일은 최대 ${this.maxCustomStyles}개까지 저장할 수 있습니다.` };
        }
        styleData.id = 'custom_' + Date.now();
        styles.push(styleData);
        this.saveCustomStyles(styles);
        return { success: true, id: styleData.id };
    }

    updateCustomStyle(styleId, styleData) {
        const styles = this.getCustomStyles();
        const index = styles.findIndex(s => s.id === styleId);
        if (index >= 0) {
            styles[index] = { ...styles[index], ...styleData };
            this.saveCustomStyles(styles);
            return true;
        }
        return false;
    }

    deleteCustomStyle(styleId) {
        const styles = this.getCustomStyles();
        const filtered = styles.filter(s => s.id !== styleId);
        this.saveCustomStyles(filtered);
    }
}
