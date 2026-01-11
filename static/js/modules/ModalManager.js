/**
 * ModalManager - 모달 관리 모듈
 * Settings, Onboarding, Custom Style 모달 관리
 */
export class ModalManager {
    constructor(storage, providerManager, uiManager) {
        this.storage = storage;
        this.providerManager = providerManager;
        this.ui = uiManager;
        this.onCustomStylesChange = null;
    }

    // ==================== Settings Modal ====================

    setupSettingsModal() {
        const settingsBtn = document.getElementById('settings-btn');
        const settingsModal = document.getElementById('settings-modal');
        const modalClose = document.getElementById('modal-close');
        const modalCancel = document.getElementById('modal-cancel');
        const modalSave = document.getElementById('modal-save');

        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.showSettingsModal());
        }

        if (modalClose) {
            modalClose.addEventListener('click', () => this.hideSettingsModal());
        }

        if (modalCancel) {
            modalCancel.addEventListener('click', () => this.hideSettingsModal());
        }

        if (modalSave) {
            modalSave.addEventListener('click', () => this.saveSettingsFromModal());
        }

        if (settingsModal) {
            settingsModal.addEventListener('click', (e) => {
                if (e.target === settingsModal) {
                    this.hideSettingsModal();
                }
            });
        }
    }

    showSettingsModal() {
        const modal = document.getElementById('settings-modal');
        const providerList = document.getElementById('provider-list');

        if (!modal || !providerList) return;

        const settings = this.storage.getSettings();
        const providers = this.providerManager.getProviders();

        const supadataInput = document.getElementById('supadata-api-key');
        if (supadataInput) {
            supadataInput.value = this.storage.getSupadataApiKey();
        }

        providerList.innerHTML = Object.entries(providers).map(([id, provider]) => {
            const savedKey = settings.providers[id]?.apiKey || '';
            const isConfigured = savedKey.trim() !== '';

            return `
                <div class="provider-card ${isConfigured ? 'configured' : ''}" data-provider="${id}">
                    <div class="flex items-center gap-3">
                        <label class="provider-checkbox">
                            <input type="checkbox" ${isConfigured ? 'checked' : ''} data-provider-check="${id}">
                        </label>
                        <div class="flex-1">
                            <span class="font-bold text-sm">${provider.name}</span>
                            <span class="text-xs text-gray-text ml-2">${isConfigured ? '설정됨' : '미설정'}</span>
                        </div>
                    </div>
                    <div class="provider-body ${isConfigured ? 'expanded' : ''}">
                        <div class="api-key-input-wrapper">
                            <input type="password" data-provider-key="${id}"
                                value="${savedKey}" placeholder="${provider.key_placeholder || 'API 키 입력'}">
                            <button type="button" data-toggle-key="${id}">
                                <span class="material-symbols-outlined text-sm">visibility</span>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        this.setupSettingsModalEvents();
        modal.classList.add('active');
    }

    setupSettingsModalEvents() {
        document.querySelectorAll('[data-provider-check]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const card = e.target.closest('.provider-card');
                const body = card.querySelector('.provider-body');

                if (e.target.checked) {
                    card.classList.add('configured');
                    body.classList.add('expanded');
                    body.querySelector('input').focus();
                } else {
                    card.classList.remove('configured');
                    body.classList.remove('expanded');
                }
            });
        });

        document.querySelectorAll('[data-toggle-key]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const providerId = e.currentTarget.dataset.toggleKey;
                const input = document.querySelector(`[data-provider-key="${providerId}"]`);
                const icon = e.currentTarget.querySelector('.material-symbols-outlined');

                if (input.type === 'password') {
                    input.type = 'text';
                    icon.textContent = 'visibility_off';
                } else {
                    input.type = 'password';
                    icon.textContent = 'visibility';
                }
            });
        });

        const supadataToggle = document.getElementById('toggle-supadata-key');
        if (supadataToggle) {
            supadataToggle.addEventListener('click', () => {
                const input = document.getElementById('supadata-api-key');
                const icon = supadataToggle.querySelector('.material-symbols-outlined');

                if (input.type === 'password') {
                    input.type = 'text';
                    icon.textContent = 'visibility_off';
                } else {
                    input.type = 'password';
                    icon.textContent = 'visibility';
                }
            });
        }

        // 캐시 삭제 버튼
        const clearCacheBtn = document.getElementById('clear-cache-btn');
        if (clearCacheBtn) {
            clearCacheBtn.addEventListener('click', async () => {
                if (!confirm('모든 캐시를 삭제하시겠습니까?\n(저장된 자막/댓글 데이터가 삭제됩니다)')) {
                    return;
                }

                try {
                    clearCacheBtn.disabled = true;
                    clearCacheBtn.innerHTML = `
                        <span class="material-symbols-outlined text-base animate-spin">sync</span>
                        <span>삭제 중...</span>
                    `;

                    const response = await fetch('/api/cache', {
                        method: 'DELETE',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({})
                    });

                    const result = await response.json();

                    if (result.success) {
                        this.ui.showAlert(`캐시가 삭제되었습니다. (${result.deleted}개 파일)`, 'success');
                    } else {
                        this.ui.showAlert('캐시 삭제에 실패했습니다.', 'error');
                    }
                } catch (error) {
                    console.error('Cache clear error:', error);
                    this.ui.showAlert('캐시 삭제 중 오류가 발생했습니다.', 'error');
                } finally {
                    clearCacheBtn.disabled = false;
                    clearCacheBtn.innerHTML = `
                        <span class="material-symbols-outlined text-base">delete</span>
                        <span>전체 캐시 삭제</span>
                    `;
                }
            });
        }
    }

    hideSettingsModal() {
        const modal = document.getElementById('settings-modal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    saveSettingsFromModal() {
        const settings = { providers: {}, selectedProvider: '' };

        document.querySelectorAll('[data-provider-key]').forEach(input => {
            const providerId = input.dataset.providerKey;
            const apiKey = input.value.trim();

            if (apiKey) {
                settings.providers[providerId] = { apiKey };
            }
        });

        const supadataInput = document.getElementById('supadata-api-key');
        if (supadataInput) {
            this.storage.saveSupadataApiKey(supadataInput.value.trim());
        }

        const configuredProviders = Object.keys(settings.providers);
        if (configuredProviders.length > 0) {
            const currentProvider = document.getElementById('provider')?.value;
            settings.selectedProvider = configuredProviders.includes(currentProvider)
                ? currentProvider
                : configuredProviders[0];
        }

        this.storage.saveSettings(settings);
        this.providerManager.updateProviderOptions();
        this.hideSettingsModal();
        this.ui.showAlert('설정이 저장되었습니다.', 'success');
    }

    // ==================== Onboarding Modal ====================

    showOnboardingModal() {
        const modal = document.getElementById('onboarding-modal');
        const providerContainer = document.getElementById('onboarding-providers');

        if (!modal || !providerContainer) return;

        const providers = this.providerManager.getProviders();

        providerContainer.innerHTML = Object.entries(providers).map(([id, provider]) => {
            return `
                <div class="provider-card" data-provider="${id}">
                    <div class="flex items-center gap-3">
                        <label class="provider-checkbox">
                            <input type="checkbox" data-onboard-check="${id}">
                        </label>
                        <span class="font-bold text-sm">${provider.name}</span>
                    </div>
                    <div class="provider-body" data-onboard-body="${id}">
                        <div class="api-key-input-wrapper">
                            <input type="password" data-onboard-key="${id}" placeholder="${provider.key_placeholder || 'API 키 입력'}">
                            <button type="button" data-onboard-toggle="${id}">
                                <span class="material-symbols-outlined text-sm">visibility</span>
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        this.setupOnboardingEvents();

        const saveBtn = document.getElementById('onboarding-save');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveOnboardingSettings());
        }

        modal.classList.add('active');
    }

    setupOnboardingEvents() {
        document.querySelectorAll('[data-onboard-check]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const providerId = e.target.dataset.onboardCheck;
                const body = document.querySelector(`[data-onboard-body="${providerId}"]`);
                const card = e.target.closest('.provider-card');

                if (e.target.checked) {
                    body.classList.add('expanded');
                    card.classList.add('configured');
                    body.querySelector('input').focus();
                } else {
                    body.classList.remove('expanded');
                    card.classList.remove('configured');
                }
            });
        });

        document.querySelectorAll('[data-onboard-toggle]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const providerId = e.currentTarget.dataset.onboardToggle;
                const input = document.querySelector(`[data-onboard-key="${providerId}"]`);
                const icon = e.currentTarget.querySelector('.material-symbols-outlined');

                if (input.type === 'password') {
                    input.type = 'text';
                    icon.textContent = 'visibility_off';
                } else {
                    input.type = 'password';
                    icon.textContent = 'visibility';
                }
            });
        });
    }

    saveOnboardingSettings() {
        const settings = { providers: {}, selectedProvider: '' };

        document.querySelectorAll('[data-onboard-key]').forEach(input => {
            const providerId = input.dataset.onboardKey;
            const apiKey = input.value.trim();

            if (apiKey) {
                settings.providers[providerId] = { apiKey };
            }
        });

        const configuredProviders = Object.keys(settings.providers);

        if (configuredProviders.length === 0) {
            this.ui.showAlert('최소 하나의 AI 서비스를 설정해주세요.', 'warning');
            return;
        }

        settings.selectedProvider = configuredProviders[0];

        this.storage.saveSettings(settings);
        this.providerManager.updateProviderOptions();

        const modal = document.getElementById('onboarding-modal');
        if (modal) {
            modal.classList.remove('active');
        }

        this.ui.showAlert('설정이 완료되었습니다! YouTube URL을 입력해보세요.', 'success');
    }

    checkFirstTimeUser() {
        if (!this.storage.hasAnyApiKey()) {
            this.showOnboardingModal();
        }
    }

    // ==================== Custom Style Modal ====================

    setupCustomStyleModal() {
        const addBtn = document.getElementById('add-custom-style-btn');
        const modal = document.getElementById('custom-style-modal');
        const closeBtn = document.getElementById('custom-style-modal-close');
        const cancelBtn = document.getElementById('custom-style-cancel');
        const saveBtn = document.getElementById('custom-style-save');
        const deleteBtn = document.getElementById('custom-style-delete');
        const promptTextarea = document.getElementById('custom-style-prompt');
        const charCount = document.getElementById('prompt-char-count');

        if (addBtn) {
            addBtn.addEventListener('click', () => this.openCustomStyleModal());
        }

        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.hideCustomStyleModal());
        }
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.hideCustomStyleModal());
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveCustomStyleFromModal());
        }

        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => this.deleteCustomStyleFromModal());
        }

        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.hideCustomStyleModal();
                }
            });
        }

        if (promptTextarea && charCount) {
            promptTextarea.addEventListener('input', () => {
                const len = promptTextarea.value.length;
                charCount.textContent = len;
                if (len > 2000) {
                    promptTextarea.value = promptTextarea.value.substring(0, 2000);
                    charCount.textContent = '2000';
                }
            });
        }
    }

    openCustomStyleModal(styleId = null) {
        const modal = document.getElementById('custom-style-modal');
        const titleEl = document.getElementById('custom-style-modal-title');
        const nameInput = document.getElementById('custom-style-name');
        const promptTextarea = document.getElementById('custom-style-prompt');
        const charCount = document.getElementById('prompt-char-count');
        const deleteBtn = document.getElementById('custom-style-delete');

        if (!modal) return;

        modal.dataset.editingId = styleId || '';

        if (styleId) {
            const styles = this.storage.getCustomStyles();
            const style = styles.find(s => s.id === styleId);
            if (style) {
                if (titleEl) titleEl.textContent = '스타일 편집';
                if (nameInput) nameInput.value = style.name;
                if (promptTextarea) {
                    promptTextarea.value = style.prompt;
                    if (charCount) charCount.textContent = style.prompt.length;
                }
                const iconRadio = document.querySelector(`input[name="custom-icon"][value="${style.icon}"]`);
                if (iconRadio) iconRadio.checked = true;
                if (deleteBtn) deleteBtn.style.display = 'inline-flex';
            }
        } else {
            if (titleEl) titleEl.textContent = '새 스타일 만들기';
            if (nameInput) nameInput.value = '';
            if (promptTextarea) {
                promptTextarea.value = '';
                if (charCount) charCount.textContent = '0';
            }
            const defaultIcon = document.querySelector('input[name="custom-icon"][value="edit_note"]');
            if (defaultIcon) defaultIcon.checked = true;
            if (deleteBtn) deleteBtn.style.display = 'none';
        }

        modal.classList.add('active');
    }

    hideCustomStyleModal() {
        const modal = document.getElementById('custom-style-modal');
        if (modal) {
            modal.classList.remove('active');
            modal.dataset.editingId = '';
        }
    }

    saveCustomStyleFromModal() {
        const modal = document.getElementById('custom-style-modal');
        const nameInput = document.getElementById('custom-style-name');
        const promptTextarea = document.getElementById('custom-style-prompt');
        const iconRadio = document.querySelector('input[name="custom-icon"]:checked');

        const name = nameInput?.value.trim();
        const prompt = promptTextarea?.value.trim();
        const icon = iconRadio?.value || 'edit_note';

        if (!name) {
            this.ui.showAlert('스타일 이름을 입력해주세요.', 'warning');
            return;
        }

        if (!prompt) {
            this.ui.showAlert('프롬프트를 입력해주세요.', 'warning');
            return;
        }

        const editingId = modal?.dataset.editingId;

        if (editingId) {
            this.storage.updateCustomStyle(editingId, { name, prompt, icon });
            this.ui.showAlert('스타일이 수정되었습니다.', 'success');
        } else {
            const result = this.storage.addCustomStyle({ name, prompt, icon });
            if (result.success) {
                this.ui.showAlert('새 스타일이 추가되었습니다.', 'success');
            } else {
                this.ui.showAlert(result.message, 'warning');
                return;
            }
        }

        if (this.onCustomStylesChange) {
            this.onCustomStylesChange();
        }
        this.hideCustomStyleModal();
    }

    deleteCustomStyleFromModal() {
        const modal = document.getElementById('custom-style-modal');
        const editingId = modal?.dataset.editingId;

        if (editingId) {
            if (confirm('이 스타일을 삭제하시겠습니까?')) {
                this.storage.deleteCustomStyle(editingId);
                this.ui.showAlert('스타일이 삭제되었습니다.', 'success');

                const currentSelected = document.querySelector('input[name="style"]:checked');
                if (currentSelected && currentSelected.value === editingId) {
                    const defaultStyle = document.querySelector('input[name="style"][value="summary"]');
                    if (defaultStyle) {
                        defaultStyle.checked = true;
                    }
                }

                if (this.onCustomStylesChange) {
                    this.onCustomStylesChange();
                }
                this.hideCustomStyleModal();
            }
        }
    }
}
