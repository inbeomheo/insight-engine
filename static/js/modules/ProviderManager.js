/**
 * ProviderManager - AI 프로바이더 관리 모듈
 * 프로바이더 로딩, 모델 선택, 옵션 업데이트 담당
 * API 키는 서버 환경변수에서 관리되므로 클라이언트에서 검증하지 않습니다.
 */
export class ProviderManager {
    constructor(storage, uiManager) {
        this.storage = storage;
        this.ui = uiManager;
        this.providers = {};
        this.styles = [];
        this.supadataConfigured = false;
    }

    // ==================== Provider Loading ====================

    async loadProviders() {
        try {
            const response = await fetch('/api/providers');
            const data = await response.json();
            // 서버에서 이미 API 키가 설정된 프로바이더만 반환합니다
            this.providers = data.providers || {};
            this.styles = data.styles || [];
            this.supadataConfigured = data.supadataConfigured || false;
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

    isSupadataConfigured() {
        return this.supadataConfigured;
    }

    // ==================== Provider Options ====================

    updateProviderOptions() {
        const providerSelect = document.getElementById('provider');
        if (!providerSelect) return;

        providerSelect.innerHTML = '';

        const providerIds = Object.keys(this.providers);

        if (providerIds.length === 0) {
            providerSelect.innerHTML = '<option value="">사용 가능한 AI 서비스가 없습니다</option>';
            this.updateProviderLabel();
            return;
        }

        providerIds.forEach(providerId => {
            const provider = this.providers[providerId];
            if (provider) {
                const option = document.createElement('option');
                option.value = providerId;
                option.textContent = provider.name;
                providerSelect.appendChild(option);
            }
        });

        // 저장된 프로바이더 선택 복원 (기본값: gemini)
        const savedProvider = this.storage.getSelectedProvider();
        if (savedProvider && providerIds.includes(savedProvider)) {
            providerSelect.value = savedProvider;
        } else if (providerIds.includes('gemini')) {
            providerSelect.value = 'gemini';
        } else if (providerIds.length > 0) {
            providerSelect.value = providerIds[0];
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
            this.updateSelectedModelInfo();
            return;
        }

        provider.models.forEach(model => {
            const option = document.createElement('option');
            option.value = model.id;
            option.textContent = model.name;
            modelSelect.appendChild(option);
        });

        // 저장된 모델 선택 복원
        const savedModel = this.storage.getSelectedModel();
        const modelIds = provider.models.map(m => m.id);
        if (savedModel && modelIds.includes(savedModel)) {
            modelSelect.value = savedModel;
        } else if (provider.models.length > 0) {
            modelSelect.value = provider.models[0].id;
        }

        this.updateSelectedModelInfo();
    }

    updateSelectedModelInfo() {
        const infoContainer = document.getElementById('selected-model-info');
        const infoText = document.getElementById('selected-model-text');
        if (!infoContainer || !infoText) return;

        const providerSelect = document.getElementById('provider');
        const modelSelect = document.getElementById('model');

        const providerId = providerSelect?.value;
        const modelId = modelSelect?.value;
        const provider = this.providers[providerId];

        if (provider && modelId) {
            const model = provider.models?.find(m => m.id === modelId);
            if (model) {
                infoText.textContent = `${provider.name} - ${model.name}`;
                infoContainer.classList.remove('hidden');
                return;
            }
        }

        infoContainer.classList.add('hidden');
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
        const modelSelect = document.getElementById('model');

        if (providerSelect) {
            providerSelect.addEventListener('change', () => {
                this.updateModelOptions();
                this.updateProviderLabel();
                this.storage.saveSelectedProvider(providerSelect.value);
            });
        }

        if (modelSelect) {
            modelSelect.addEventListener('change', () => {
                this.storage.saveSelectedModel(modelSelect.value);
                this.updateSelectedModelInfo();
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
