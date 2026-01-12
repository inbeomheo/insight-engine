/**
 * StyleManager - 스타일 관리 모듈
 * 스타일 선택, 커스텀 스타일 렌더링, 모디파이어 관리
 */
export class StyleManager {
    constructor(storage, uiManager, modalManager) {
        this.storage = storage;
        this.ui = uiManager;
        this.modalManager = modalManager;

        this.styleLabels = {
            'summary': 'Summary',
            'easy': 'Thread',
            'detailed': 'Blog Post',
            'needs': 'Takeaways',
            'news': 'Sentiment',
            'script': 'Script',
            'qna': 'Q&A',
            'infographic': 'Infographic',
            'compare': 'Compare',
            'sns': 'SNS'
        };
    }

    // ==================== Style Selection ====================

    getSelectedStyle() {
        const checked = document.querySelector('input[name="style"]:checked');
        return checked ? checked.value : 'summary';
    }

    getStyleLabel(style) {
        const customStyles = this.storage.getCustomStyles();
        const customStyle = customStyles.find(s => s.id === style);
        if (customStyle) {
            return customStyle.name;
        }
        return this.styleLabels[style] || style;
    }

    // ==================== Modifiers ====================

    getModifiers() {
        const modifiers = {};

        const lengthChecked = document.querySelector('input[name="length"]:checked');
        if (lengthChecked) {
            modifiers.length = lengthChecked.value;
        }

        const toneChecked = document.querySelector('input[name="tone"]:checked');
        if (toneChecked) {
            modifiers.tone = toneChecked.value;
        }

        const languageSelect = document.getElementById('language-select');
        if (languageSelect) {
            modifiers.language = languageSelect.value;
        }

        const emojiCheckbox = document.getElementById('emoji-checkbox');
        if (emojiCheckbox) {
            modifiers.emoji = emojiCheckbox.checked ? 'use' : 'none';
        }

        return modifiers;
    }

    getCustomPrompt() {
        const selectedStyle = this.getSelectedStyle();
        if (selectedStyle.startsWith('custom_')) {
            const styles = this.storage.getCustomStyles();
            const style = styles.find(s => s.id === selectedStyle);
            return style?.prompt || '';
        }
        return '';
    }

    // ==================== Custom Styles Rendering ====================

    renderCustomStyles() {
        const container = document.getElementById('custom-styles-grid');
        const section = document.getElementById('custom-styles-section');
        if (!container) return;

        const styles = this.storage.getCustomStyles();

        if (section) {
            section.style.display = styles.length > 0 ? 'block' : 'none';
        }

        container.innerHTML = styles.map(style => `
            <label class="style-option custom-style-card" data-custom-id="${style.id}">
                <input type="radio" name="style" value="${style.id}" class="hidden peer">
                <div class="style-card peer-checked:border-primary-accent peer-checked:bg-primary-accent/10">
                    <span class="material-symbols-outlined text-2xl mb-2">${this.ui.escapeHtml(style.icon || 'edit_note')}</span>
                    <span class="text-xs font-bold uppercase tracking-wider">${this.ui.escapeHtml(style.name)}</span>
                    <button type="button" class="custom-style-edit-btn absolute top-2 right-2 text-gray-text hover:text-primary-accent p-1" data-edit-style="${style.id}">
                        <span class="material-symbols-outlined text-sm">edit</span>
                    </button>
                </div>
            </label>
        `).join('');

        this.setupEditButtons(container);
    }

    setupEditButtons(container) {
        container.querySelectorAll('[data-edit-style]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const styleId = btn.dataset.editStyle;
                this.modalManager.openCustomStyleModal(styleId);
            });
        });
    }

    // ==================== Advanced Options ====================

    setupAdvancedOptions() {
        const toggleBtn = document.getElementById('advanced-options-toggle');
        const panel = document.getElementById('advanced-options-panel');
        const arrow = document.getElementById('advanced-options-arrow');

        if (toggleBtn && panel) {
            toggleBtn.addEventListener('click', () => {
                const isHidden = panel.classList.contains('hidden');
                if (isHidden) {
                    panel.classList.remove('hidden');
                    if (arrow) arrow.textContent = 'expand_less';
                } else {
                    panel.classList.add('hidden');
                    if (arrow) arrow.textContent = 'expand_more';
                }
            });
        }
    }

    // ==================== Style Selection Setup (모바일 터치 지원) ====================

    setupStyleSelection() {
        const styleOptions = document.getElementById('style-options');
        if (!styleOptions) return;

        // 모든 스타일 라벨에 클릭 이벤트 추가
        styleOptions.querySelectorAll('label').forEach(label => {
            label.addEventListener('click', (e) => {
                const radio = label.querySelector('input[type="radio"]');
                if (radio) {
                    // 명시적으로 라디오 버튼 선택
                    radio.checked = true;
                    // 시각적 업데이트를 위해 change 이벤트 발생
                    radio.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });

            // 터치 이벤트도 지원
            label.addEventListener('touchend', (e) => {
                const radio = label.querySelector('input[type="radio"]');
                if (radio) {
                    radio.checked = true;
                    radio.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
        });
    }
}
