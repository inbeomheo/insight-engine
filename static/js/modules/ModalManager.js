/**
 * ModalManager - 모달 관리 모듈
 * Settings, Onboarding, Custom Style 모달 관리
 * API 키는 서버 환경변수에서 관리됩니다.
 */
export class ModalManager {
    constructor(storage, providerManager, uiManager) {
        this.storage = storage;
        this.providerManager = providerManager;
        this.ui = uiManager;
        this.onCustomStylesChange = null;

        // ESC 키로 모달 닫기 설정
        this.setupEscapeKeyHandler();
    }

    // ==================== ESC Key Handler ====================

    /**
     * ESC 키를 눌렀을 때 열린 모달을 닫는 전역 이벤트 핸들러
     */
    setupEscapeKeyHandler() {
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.closeActiveModal();
            }
        });
    }

    /**
     * 현재 열려있는 모달을 닫습니다
     * 우선순위: prompt > custom-style > auth > settings > onboarding
     * 참고: mindmap-modal은 MindmapManager에서 자체 ESC 핸들러로 처리
     */
    closeActiveModal() {
        // 모달 우선순위 순서대로 체크 (가장 위에 떠있을 가능성 높은 순)
        const modalPriority = [
            { id: 'prompt-modal', hide: () => this.hidePromptModal() },
            { id: 'custom-style-modal', hide: () => this.hideCustomStyleModal() },
            { id: 'auth-modal', hide: () => this.hideAuthModal() },
            { id: 'settings-modal', hide: () => this.hideSettingsModal() },
            { id: 'onboarding-modal', hide: () => this.closeOnboarding() }
        ];

        for (const modal of modalPriority) {
            const element = document.getElementById(modal.id);
            if (element && element.classList.contains('active')) {
                modal.hide();
                return; // 하나만 닫고 종료
            }
        }
    }

    // ==================== Additional Modal Helpers ====================

    hidePromptModal() {
        const modal = document.getElementById('prompt-modal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    hideAuthModal() {
        const modal = document.getElementById('auth-modal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    // ==================== Settings Modal ====================

    setupSettingsModal() {
        const settingsBtn = document.getElementById('settings-btn');
        const settingsModal = document.getElementById('settings-modal');
        const modalClose = document.getElementById('modal-close');
        const modalCancel = document.getElementById('modal-cancel');

        if (settingsBtn) {
            settingsBtn.addEventListener('click', () => this.showSettingsModal());
        }

        if (modalClose) {
            modalClose.addEventListener('click', () => this.hideSettingsModal());
        }

        if (modalCancel) {
            modalCancel.addEventListener('click', () => this.hideSettingsModal());
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

        const providers = this.providerManager.getProviders();
        const providerCount = Object.keys(providers).length;

        // 서버에서 설정된 프로바이더 목록 표시
        if (providerCount > 0) {
            providerList.innerHTML = `
                <div class="text-center py-4 mb-4">
                    <span class="material-symbols-outlined text-3xl text-green-500 mb-2">check_circle</span>
                    <p class="text-sm text-gray-text">
                        <strong class="text-white">${providerCount}개</strong>의 AI 서비스가 사용 가능합니다
                    </p>
                </div>
                <div class="space-y-2">
                    ${Object.entries(providers).map(([id, provider]) => `
                        <div class="flex items-center gap-2 p-2 bg-surface-lighter/50 rounded-lg">
                            <span class="material-symbols-outlined text-sm text-green-500">check</span>
                            <span class="text-sm">${provider.name}</span>
                        </div>
                    `).join('')}
                </div>
                <p class="text-xs text-gray-text mt-4 text-center">
                    API 키는 서버 환경변수에서 관리됩니다.
                </p>
            `;
        } else {
            providerList.innerHTML = `
                <div class="text-center py-6">
                    <span class="material-symbols-outlined text-3xl text-yellow-500 mb-2">warning</span>
                    <p class="text-sm text-gray-text">
                        사용 가능한 AI 서비스가 없습니다.
                    </p>
                    <p class="text-xs text-gray-text mt-2">
                        서버 관리자에게 API 키 설정을 요청하세요.
                    </p>
                </div>
            `;
        }

        this.setupSettingsModalEvents();
        modal.classList.add('active');
    }

    setupSettingsModalEvents() {
        // 캐시 삭제 버튼
        const clearCacheBtn = document.getElementById('clear-cache-btn');
        if (clearCacheBtn) {
            // 기존 이벤트 리스너 제거 후 추가
            const newBtn = clearCacheBtn.cloneNode(true);
            clearCacheBtn.parentNode.replaceChild(newBtn, clearCacheBtn);

            newBtn.addEventListener('click', async () => {
                if (!confirm('모든 캐시를 삭제하시겠습니까?\n(저장된 자막/댓글 데이터가 삭제됩니다)')) {
                    return;
                }

                try {
                    newBtn.disabled = true;
                    newBtn.innerHTML = `
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
                    newBtn.disabled = false;
                    newBtn.innerHTML = `
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

    // ==================== Onboarding Modal ====================

    showOnboardingModal() {
        const modal = document.getElementById('onboarding-modal');
        const providerContainer = document.getElementById('onboarding-providers');

        if (!modal || !providerContainer) return;

        const providers = this.providerManager.getProviders();
        const providerCount = Object.keys(providers).length;

        // 사용 가능한 AI 서비스 안내
        if (providerCount > 0) {
            providerContainer.innerHTML = `
                <div class="text-center mb-4">
                    <span class="material-symbols-outlined text-4xl text-green-500 mb-2">rocket_launch</span>
                    <h3 class="text-lg font-bold mb-1">준비 완료!</h3>
                    <p class="text-sm text-gray-text">
                        ${providerCount}개의 AI 서비스가 사용 가능합니다
                    </p>
                </div>
                <div class="space-y-2 mb-4">
                    ${Object.entries(providers).map(([id, provider]) => `
                        <div class="flex items-center gap-2 p-3 bg-surface-lighter/50 rounded-lg">
                            <span class="material-symbols-outlined text-base text-green-500">smart_toy</span>
                            <span class="font-medium">${provider.name}</span>
                            <span class="text-xs text-gray-text ml-auto">${provider.models?.length || 0}개 모델</span>
                        </div>
                    `).join('')}
                </div>
            `;
        } else {
            providerContainer.innerHTML = `
                <div class="text-center py-6">
                    <span class="material-symbols-outlined text-4xl text-yellow-500 mb-2">warning</span>
                    <h3 class="text-lg font-bold mb-1">설정 필요</h3>
                    <p class="text-sm text-gray-text">
                        사용 가능한 AI 서비스가 없습니다.<br>
                        서버 관리자에게 문의하세요.
                    </p>
                </div>
            `;
        }

        const startBtn = document.getElementById('onboarding-save');
        if (startBtn) {
            startBtn.textContent = '시작하기';
            // 기존 이벤트 리스너 제거 후 추가
            const newBtn = startBtn.cloneNode(true);
            startBtn.parentNode.replaceChild(newBtn, startBtn);
            newBtn.addEventListener('click', () => this.closeOnboarding());
        }

        const skipBtn = document.getElementById('onboarding-skip');
        if (skipBtn) {
            skipBtn.style.display = 'none';
        }

        modal.classList.add('active');
    }

    closeOnboarding() {
        const modal = document.getElementById('onboarding-modal');
        if (modal) {
            modal.classList.remove('active');
        }
        localStorage.setItem('onboarding_completed', 'true');
        this.ui.showAlert('YouTube URL을 입력하여 시작해보세요!', 'success');
    }

    skipOnboarding() {
        this.closeOnboarding();
    }

    checkFirstTimeUser() {
        const completed = localStorage.getItem('onboarding_completed');
        const skipped = localStorage.getItem('onboarding_skipped');
        const providers = this.providerManager.getProviders();

        // 처음 방문이고 사용 가능한 프로바이더가 있으면 온보딩 표시
        if (!completed && !skipped && Object.keys(providers).length > 0) {
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
