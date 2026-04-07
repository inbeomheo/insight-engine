/**
 * PresetManager - 콘텐츠 생성 프리셋 관리
 * 현재 설정(프로바이더, 모델, 스타일, 모디파이어)을 저장/로드
 */
export class PresetManager {
    /**
     * @param {Object} storage - StorageManager
     * @param {Object} providerManager - ProviderManager
     * @param {Object} styleManager - StyleManager
     * @param {Object} ui - UIManager
     */
    constructor(storage, providerManager, styleManager, ui) {
        this.storage = storage;
        this.providerManager = providerManager;
        this.styleManager = styleManager;
        this.ui = ui;

        this.presetList = document.getElementById('preset-list');
        this.savePresetBtn = document.getElementById('save-preset-btn');
    }

    init() {
        this._setupSaveButton();
        this.renderPresets();
    }

    _setupSaveButton() {
        if (!this.savePresetBtn) return;

        this.savePresetBtn.addEventListener('click', () => {
            const name = prompt('프리셋 이름 (최대 20자):', '');
            if (!name || !name.trim()) return;

            const trimmed = name.trim().substring(0, 20);
            const preset = this._captureCurrentSettings(trimmed);
            const result = this.storage.addPreset(preset);

            if (result.success) {
                this.renderPresets();
                this.ui.showAlert(`프리셋 "${trimmed}" 저장 완료`, 'success');
            } else {
                this.ui.showAlert(result.message, 'warning');
            }
        });
    }

    _captureCurrentSettings(name) {
        const provider = this.providerManager.getSelectedProvider();
        const model = this.providerManager.getSelectedModel();
        const style = document.querySelector('input[name="style"]:checked')?.value || 'blog_seo';
        const length = document.querySelector('input[name="length"]:checked')?.value || 'medium';
        const writingStyle = document.querySelector('input[name="writing_style"]:checked')?.value || 'conversational';

        return { name, provider, model, style, length, writing_style: writingStyle };
    }

    _applyPreset(preset) {
        // 프로바이더 선택
        const providerSelect = document.getElementById('provider');
        if (providerSelect && preset.provider) {
            providerSelect.value = preset.provider;
            providerSelect.dispatchEvent(new Event('change', { bubbles: true }));
        }

        // 모델 선택 (프로바이더 변경 후 약간의 딜레이)
        setTimeout(() => {
            const modelSelect = document.getElementById('model');
            if (modelSelect && preset.model) {
                modelSelect.value = preset.model;
                modelSelect.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }, 100);

        // 스타일 선택
        if (preset.style) {
            const styleRadio = document.querySelector(`input[name="style"][value="${preset.style}"]`);
            if (styleRadio) {
                styleRadio.checked = true;
                styleRadio.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }

        // 길이 모디파이어
        if (preset.length) {
            const lengthRadio = document.querySelector(`input[name="length"][value="${preset.length}"]`);
            if (lengthRadio) {
                lengthRadio.checked = true;
                lengthRadio.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }

        // 문체 모디파이어
        if (preset.writing_style) {
            const wsRadio = document.querySelector(`input[name="writing_style"][value="${preset.writing_style}"]`);
            if (wsRadio) {
                wsRadio.checked = true;
                wsRadio.dispatchEvent(new Event('change', { bubbles: true }));
            }
            const wsSelect = document.getElementById('writing-style-select');
            if (wsSelect) wsSelect.value = preset.writing_style;
        }

        this.ui.showAlert(`프리셋 "${preset.name}" 적용 완료`, 'success');
    }

    renderPresets() {
        if (!this.presetList) return;

        const presets = this.storage.getPresets();

        if (presets.length === 0) {
            this.presetList.innerHTML = '<div class="text-xs text-gray-400 py-2">저장된 프리셋이 없습니다</div>';
            return;
        }

        this.presetList.innerHTML = presets.map(p => `
            <div class="preset-item" data-id="${p.id}">
                <button class="preset-apply-btn" title="${p.name}">
                    <span class="material-symbols-outlined" style="font-size: 14px;">tune</span>
                    <span class="preset-name">${this.ui.escapeHtml(p.name)}</span>
                </button>
                <button class="preset-delete-btn" title="삭제">
                    <span class="material-symbols-outlined" style="font-size: 14px;">close</span>
                </button>
            </div>
        `).join('');

        // 이벤트 바인딩
        this.presetList.querySelectorAll('.preset-apply-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.closest('.preset-item').dataset.id;
                const preset = presets.find(p => p.id === id);
                if (preset) this._applyPreset(preset);
            });
        });

        this.presetList.querySelectorAll('.preset-delete-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.closest('.preset-item').dataset.id;
                this.storage.deletePreset(id);
                this.renderPresets();
            });
        });
    }

}
