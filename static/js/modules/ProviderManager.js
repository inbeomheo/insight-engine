/**
 * ProviderManager - AI 프로바이더 관리 모듈
 * 프로바이더 로딩, 모델 선택, 옵션 업데이트 담당
 */
export class ProviderManager {
    constructor(storage, uiManager) {
        this.storage = storage;
        this.ui = uiManager;
        this.providers = {};
        this.styles = [];
    }

    // ==================== Provider Loading ====================

    async loadProviders() {
        try {
            const response = await fetch('/api/providers');
            const data = await response.json();
            this.providers = data.providers || {};
            this.styles = data.styles || [];
            this.updateProviderOptions();
        } catch (error) {
            console.error('Failed to load providers:', error);
            this.ui.showAlert('서비스 목록을 불러오는데 실패했습니다.', 'error');
        }
    }

    getProviders() {
        return this.providers;
    }

    getStyles() {
        return this.styles;
    }

    // ==================== Provider Options ====================

    updateProviderOptions() {
        const providerSelect = document.getElementById('provider');
        if (!providerSelect) return;

        const configuredProviders = this.storage.getConfiguredProviders();

        providerSelect.innerHTML = '';

        if (configuredProviders.length === 0) {
            providerSelect.innerHTML = '<option value="">설정에서 API 키를 입력하세요</option>';
            return;
        }

        configuredProviders.forEach(providerId => {
            const provider = this.providers[providerId];
            if (provider) {
                const option = document.createElement('option');
                option.value = providerId;
                option.textContent = provider.name;
                providerSelect.appendChild(option);
            }
        });

        const settings = this.storage.getSettings();
        if (settings.selectedProvider && configuredProviders.includes(settings.selectedProvider)) {
            providerSelect.value = settings.selectedProvider;
        } else if (configuredProviders.length > 0) {
            providerSelect.value = configuredProviders[0];
        }

        this.updateModelOptions();
        this.updateProviderLabel();
    }

    updateModelOptions() {
        const providerSelect = document.getElementById('provider');
        const modelSelect = document.getElementById('model');
        if (!providerSelect || !modelSelect) return;

        const providerId = providerSelect.value;
        const provider = this.providers[providerId];

        modelSelect.innerHTML = '';

        if (!provider || !provider.models) {
            modelSelect.innerHTML = '<option value="">서비스를 먼저 선택하세요</option>';
            return;
        }

        provider.models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = model.name;
            modelSelect.appendChild(option);
        });

        if (provider.models.length > 0) {
            modelSelect.value = provider.models[0].id;
        }
    }

    updateProviderLabel() {
        const label = document.getElementById('current-provider-label');
        if (!label) return;

        const providerSelect = document.getElementById('provider');
        const providerId = providerSelect?.value;
        const provider = this.providers[providerId];

        if (provider) {
            label.textContent = provider.name;
        } else {
            label.textContent = '미설정';
        }
    }

    // ==================== Provider Selection Events ====================

    setupProviderSelectEvents() {
        const providerSelect = document.getElementById('provider');
        if (providerSelect) {
            providerSelect.addEventListener('change', () => {
                this.updateModelOptions();
                this.updateProviderLabel();
                const settings = this.storage.getSettings();
                settings.selectedProvider = providerSelect.value;
                this.storage.saveSettings(settings);
            });
        }
    }

    // ==================== Getters ====================

    getSelectedProvider() {
        const providerSelect = document.getElementById('provider');
        return providerSelect?.value || '';
    }

    getSelectedModel() {
        const modelSelect = document.getElementById('model');
        return modelSelect?.value || '';
    }
}
