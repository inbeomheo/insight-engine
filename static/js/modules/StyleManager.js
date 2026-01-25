/**
 * StyleManager - 스타일 관리 모듈 v3.0
 * 5개 핵심 스타일, 2개 모디파이어 지원
 */
export class StyleManager {
    constructor(storage, uiManager, modalManager) {
        this.storage = storage;
        this.ui = uiManager;
        this.modalManager = modalManager;

        // 5개 핵심 스타일 라벨
        this.styleLabels = {
            'blog_seo': 'Blog+SEO',
            'summary': '요약',
            'tutorial': '튜토리얼',
            'qna': 'Q&A',
            'app_ideas': '앱 아이디어'
        };

        // 문체 라벨
        this.writingStyleLabels = {
            'conversational': '대화체',
            'explanatory': '설명체',
            'casual': '캐주얼',
            'expert': '전문가'
        };
    }

    // ==================== Style Selection ====================

    getSelectedStyle() {
        const checked = document.querySelector('input[name="style"]:checked');
        return checked ? checked.value : 'blog_seo';
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

        // 길이
        const lengthChecked = document.querySelector('input[name="length"]:checked');
        if (lengthChecked) {
            modifiers.length = lengthChecked.value;
        }

        // 문체
        const writingStyleChecked = document.querySelector('input[name="writing_style"]:checked');
        if (writingStyleChecked) {
            modifiers.writing_style = writingStyleChecked.value;
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
                <div class="style-card peer-checked:border-primary peer-checked:bg-primary/10">
                    <span class="material-symbols-outlined text-2xl mb-2">${this.ui.escapeHtml(style.icon || 'edit_note')}</span>
                    <span class="text-xs font-bold uppercase tracking-wider">${this.ui.escapeHtml(style.name)}</span>
                    <button type="button" class="custom-style-edit-btn absolute top-2 right-2 text-text-subtle hover:text-primary p-1" data-edit-style="${style.id}">
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
                const isExpanded = toggleBtn.getAttribute('aria-expanded') === 'true';
                if (isExpanded) {
                    panel.classList.add('hidden');
                    toggleBtn.setAttribute('aria-expanded', 'false');
                    if (arrow) arrow.textContent = 'expand_more';
                } else {
                    panel.classList.remove('hidden');
                    toggleBtn.setAttribute('aria-expanded', 'true');
                    if (arrow) arrow.textContent = 'expand_less';
                }
            });
        }

        // 모디파이어 변경 시 요약 뱃지 업데이트
        this.setupModifierSummary();
    }

    setupModifierSummary() {
        const lengthRadios = document.querySelectorAll('input[name="length"]');
        const writingStyleRadios = document.querySelectorAll('input[name="writing_style"]');
        const summaryText = document.getElementById('modifier-summary-text');

        const updateSummary = () => {
            if (!summaryText) return;

            const lengthLabels = { short: '짧게', medium: '보통', long: '길게' };

            const selectedLength = document.querySelector('input[name="length"]:checked');
            const selectedWritingStyle = document.querySelector('input[name="writing_style"]:checked');

            const lengthText = selectedLength ? lengthLabels[selectedLength.value] || selectedLength.value : '보통';
            const writingStyleText = selectedWritingStyle ? this.writingStyleLabels[selectedWritingStyle.value] || selectedWritingStyle.value : '대화체';

            summaryText.textContent = `${lengthText} · ${writingStyleText}`;
        };

        lengthRadios.forEach(radio => radio.addEventListener('change', updateSummary));
        writingStyleRadios.forEach(radio => radio.addEventListener('change', updateSummary));

        // 초기값 설정
        updateSummary();
    }

    // ==================== Style Selection Setup (모바일 터치 지원) ====================

    setupStyleSelection() {
        // 스타일 컨테이너 찾기
        const styleContainer = document.getElementById('style-options');

        if (styleContainer) {
            // 모든 스타일 라벨에 클릭 이벤트 추가
            styleContainer.querySelectorAll('label').forEach(label => {
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

        // 키보드 네비게이션 설정
        this.setupKeyboardNavigation();
    }

    // ==================== Keyboard Navigation ====================

    setupKeyboardNavigation() {
        // 모든 스타일 라디오 버튼 수집
        const allRadios = document.querySelectorAll('input[name="style"]');
        if (allRadios.length === 0) return;

        allRadios.forEach((radio, index) => {
            const label = radio.closest('label');
            if (!label) return;

            // 라벨에 tabindex 추가하여 포커스 가능하게 함
            label.setAttribute('tabindex', '0');

            label.addEventListener('keydown', (e) => {
                let targetIndex = index;

                switch (e.key) {
                    case 'ArrowRight':
                    case 'ArrowDown':
                        e.preventDefault();
                        targetIndex = (index + 1) % allRadios.length;
                        break;
                    case 'ArrowLeft':
                    case 'ArrowUp':
                        e.preventDefault();
                        targetIndex = (index - 1 + allRadios.length) % allRadios.length;
                        break;
                    case 'Enter':
                    case ' ':
                        e.preventDefault();
                        radio.checked = true;
                        radio.dispatchEvent(new Event('change', { bubbles: true }));
                        return;
                    default:
                        return;
                }

                // 타겟 라디오로 이동
                const targetRadio = allRadios[targetIndex];
                const targetLabel = targetRadio.closest('label');
                if (targetLabel) {
                    targetLabel.focus();
                    targetRadio.checked = true;
                    targetRadio.dispatchEvent(new Event('change', { bubbles: true }));
                }
            });
        });
    }
}
