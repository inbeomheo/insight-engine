/**
 * KeyboardNavigationManager - 키보드 네비게이션 관리 모듈
 * US-013: 키보드만으로 모든 기능을 사용할 수 있도록 지원
 *
 * 주요 기능:
 * - Tab 순서 관리
 * - Enter/Space로 버튼 활성화
 * - 화살표 키로 드롭다운/메뉴 탐색
 * - focus-visible 스타일 관리
 */
export class KeyboardNavigationManager {
    constructor() {
        // 현재 포커스 모드 (keyboard/mouse)
        this.focusMode = 'mouse';

        // 드롭다운/메뉴 상태
        this.activeDropdown = null;

        // 네비게이션 가능한 요소들의 선택자
        this.focusableSelector = [
            'a[href]:not([disabled])',
            'button:not([disabled])',
            'input:not([disabled])',
            'select:not([disabled])',
            'textarea:not([disabled])',
            '[tabindex]:not([tabindex="-1"])',
            '[role="button"]:not([disabled])',
            '[role="menuitem"]',
            '[role="option"]',
            'label.cursor-pointer'
        ].join(', ');

        this.init();
    }

    /**
     * 초기화
     */
    init() {
        this.setupFocusModeDetection();
        this.setupKeyboardHandlers();
        this.setupCustomElementHandlers();
        this.setupModalFocusTrap();
        this.setupSkipLink();
        this.setupArrowNavigation();
    }

    /**
     * 포커스 모드 감지 (키보드 vs 마우스)
     * 키보드 사용 시에만 focus-visible 스타일 표시
     */
    setupFocusModeDetection() {
        // 키보드 사용 감지
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Tab') {
                this.focusMode = 'keyboard';
                document.body.classList.add('keyboard-navigation');
                document.body.classList.remove('mouse-navigation');
            }
        });

        // 마우스 사용 감지
        document.addEventListener('mousedown', () => {
            this.focusMode = 'mouse';
            document.body.classList.add('mouse-navigation');
            document.body.classList.remove('keyboard-navigation');
        });

        // 초기 상태 설정
        document.body.classList.add('mouse-navigation');
    }

    /**
     * 키보드 이벤트 핸들러 설정
     */
    setupKeyboardHandlers() {
        document.addEventListener('keydown', (e) => {
            const target = e.target;

            // Enter/Space로 버튼 활성화
            if (e.key === 'Enter' || e.key === ' ') {
                this.handleActivation(e, target);
            }

            // 화살표 키 네비게이션
            if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
                this.handleArrowNavigation(e, target);
            }

            // Home/End 키
            if (e.key === 'Home' || e.key === 'End') {
                this.handleHomeEnd(e, target);
            }
        });
    }

    /**
     * Enter/Space로 버튼 및 커스텀 요소 활성화
     */
    handleActivation(e, target) {
        // 라디오 버튼을 감싸는 label 처리
        if (target.matches('label.cursor-pointer')) {
            const input = target.querySelector('input[type="radio"], input[type="checkbox"]');
            if (input && e.key === ' ') {
                e.preventDefault();
                input.click();
                input.dispatchEvent(new Event('change', { bubbles: true }));
            }
        }

        // 스타일 카드 처리
        if (target.matches('.style-card') || target.closest('.style-card')) {
            const label = target.closest('label');
            if (label && e.key === ' ') {
                e.preventDefault();
                const input = label.querySelector('input');
                if (input) {
                    input.click();
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        }

        // 모디파이어 칩 처리
        if (target.matches('.modifier-chip') || target.closest('.modifier-chip')) {
            const label = target.closest('label');
            if (label && e.key === ' ') {
                e.preventDefault();
                const input = label.querySelector('input');
                if (input) {
                    input.click();
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }
        }

        // 커스텀 버튼 역할 요소
        if (target.matches('[role="button"]')) {
            if (e.key === ' ') {
                e.preventDefault();
            }
            target.click();
        }

        // 드롭다운 토글
        if (target.matches('select') && e.key === ' ') {
            // 브라우저 기본 동작 사용
            return;
        }
    }

    /**
     * 화살표 키 네비게이션
     */
    handleArrowNavigation(e, target) {
        // 스타일 그리드 네비게이션
        if (this.isInStyleGrid(target)) {
            this.navigateStyleGrid(e, target);
            return;
        }

        // 모디파이어 칩 네비게이션
        if (this.isInModifierGroup(target)) {
            this.navigateModifierChips(e, target);
            return;
        }

        // 사이드바 네비게이션
        if (this.isInSidebar(target)) {
            this.navigateSidebar(e, target);
            return;
        }

        // 라디오 그룹 네비게이션 (기본)
        if (target.matches('input[type="radio"]')) {
            this.navigateRadioGroup(e, target);
            return;
        }
    }

    /**
     * 스타일 그리드 내 네비게이션
     */
    isInStyleGrid(target) {
        return target.closest('#style-options, #style-options-analysis, #style-options-content, #custom-styles-grid');
    }

    navigateStyleGrid(e, target) {
        const grid = target.closest('.grid');
        if (!grid) return;

        const labels = Array.from(grid.querySelectorAll('label.cursor-pointer'));
        const currentIndex = labels.findIndex(label => label.contains(target) || label === target);

        if (currentIndex === -1) return;

        // 그리드 열 수 계산 (grid-cols-4)
        const cols = 4;
        let newIndex = currentIndex;

        switch (e.key) {
            case 'ArrowLeft':
                newIndex = currentIndex > 0 ? currentIndex - 1 : labels.length - 1;
                break;
            case 'ArrowRight':
                newIndex = currentIndex < labels.length - 1 ? currentIndex + 1 : 0;
                break;
            case 'ArrowUp':
                newIndex = currentIndex >= cols ? currentIndex - cols : currentIndex;
                break;
            case 'ArrowDown':
                newIndex = currentIndex + cols < labels.length ? currentIndex + cols : currentIndex;
                break;
        }

        if (newIndex !== currentIndex) {
            e.preventDefault();
            const newLabel = labels[newIndex];
            const input = newLabel.querySelector('input');
            if (input) {
                input.focus();
                // 포커스만 이동, 선택은 Enter/Space로
            }
        }
    }

    /**
     * 모디파이어 칩 그룹 내 네비게이션
     */
    isInModifierGroup(target) {
        return target.closest('.modifier-group');
    }

    navigateModifierChips(e, target) {
        const group = target.closest('.modifier-group');
        if (!group) return;

        const chips = Array.from(group.querySelectorAll('label.modifier-chip'));
        const currentLabel = target.closest('label.modifier-chip');
        const currentIndex = chips.indexOf(currentLabel);

        if (currentIndex === -1) return;

        let newIndex = currentIndex;

        if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
            newIndex = currentIndex > 0 ? currentIndex - 1 : chips.length - 1;
        } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
            newIndex = currentIndex < chips.length - 1 ? currentIndex + 1 : 0;
        }

        if (newIndex !== currentIndex) {
            e.preventDefault();
            const newLabel = chips[newIndex];
            const input = newLabel.querySelector('input');
            if (input) {
                input.focus();
            }
        }
    }

    /**
     * 사이드바 네비게이션
     */
    isInSidebar(target) {
        return target.closest('#sidebar');
    }

    navigateSidebar(e, target) {
        const sidebar = document.getElementById('sidebar');
        if (!sidebar) return;

        const buttons = Array.from(sidebar.querySelectorAll('.nav-icon-btn:not([style*="display: none"])'));
        const currentIndex = buttons.indexOf(target);

        if (currentIndex === -1) return;

        let newIndex = currentIndex;

        if (e.key === 'ArrowUp') {
            newIndex = currentIndex > 0 ? currentIndex - 1 : buttons.length - 1;
        } else if (e.key === 'ArrowDown') {
            newIndex = currentIndex < buttons.length - 1 ? currentIndex + 1 : 0;
        }

        if (newIndex !== currentIndex) {
            e.preventDefault();
            buttons[newIndex].focus();
        }
    }

    /**
     * 라디오 그룹 네비게이션
     */
    navigateRadioGroup(e, target) {
        const name = target.name;
        const radios = Array.from(document.querySelectorAll(`input[type="radio"][name="${name}"]`));
        const currentIndex = radios.indexOf(target);

        let newIndex = currentIndex;

        if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
            newIndex = currentIndex > 0 ? currentIndex - 1 : radios.length - 1;
            e.preventDefault();
        } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
            newIndex = currentIndex < radios.length - 1 ? currentIndex + 1 : 0;
            e.preventDefault();
        }

        if (newIndex !== currentIndex) {
            radios[newIndex].focus();
            radios[newIndex].checked = true;
            radios[newIndex].dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    /**
     * Home/End 키 처리
     */
    handleHomeEnd(e, target) {
        // 그리드 내에서 Home/End
        const grid = target.closest('.grid');
        if (grid) {
            const labels = Array.from(grid.querySelectorAll('label.cursor-pointer'));
            if (labels.length > 0) {
                e.preventDefault();
                const targetLabel = e.key === 'Home' ? labels[0] : labels[labels.length - 1];
                const input = targetLabel.querySelector('input');
                if (input) {
                    input.focus();
                }
            }
        }
    }

    /**
     * 커스텀 요소 핸들러 설정
     */
    setupCustomElementHandlers() {
        // 스타일 카드에 tabindex 추가
        document.querySelectorAll('label.style-grid-item input[type="radio"]').forEach(input => {
            // 라디오 버튼이 sr-only로 숨겨져 있지만 포커스 가능
            input.setAttribute('tabindex', '0');
        });

        // 모디파이어 칩에 tabindex 추가
        document.querySelectorAll('label.modifier-chip input').forEach(input => {
            input.setAttribute('tabindex', '0');
        });
    }

    /**
     * 모달 포커스 트랩 설정
     */
    setupModalFocusTrap() {
        // MutationObserver로 모달 활성화 감지
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                    const modal = mutation.target;
                    if (modal.classList.contains('modal-overlay')) {
                        if (modal.classList.contains('active')) {
                            this.trapFocusInModal(modal);
                        } else {
                            this.releaseFocusTrap(modal);
                        }
                    }
                }
            });
        });

        // 모든 모달 오버레이 관찰
        document.querySelectorAll('.modal-overlay').forEach(modal => {
            observer.observe(modal, { attributes: true });
        });
    }

    /**
     * 모달 내 포커스 트랩
     */
    trapFocusInModal(modal) {
        const focusableElements = modal.querySelectorAll(this.focusableSelector);
        const firstFocusable = focusableElements[0];
        const lastFocusable = focusableElements[focusableElements.length - 1];

        // 첫 번째 포커스 가능한 요소에 포커스
        if (firstFocusable) {
            setTimeout(() => firstFocusable.focus(), 50);
        }

        // 포커스 트랩 이벤트 리스너
        const trapHandler = (e) => {
            if (e.key !== 'Tab') return;

            if (e.shiftKey) {
                // Shift + Tab
                if (document.activeElement === firstFocusable) {
                    e.preventDefault();
                    lastFocusable.focus();
                }
            } else {
                // Tab
                if (document.activeElement === lastFocusable) {
                    e.preventDefault();
                    firstFocusable.focus();
                }
            }
        };

        modal._focusTrapHandler = trapHandler;
        modal.addEventListener('keydown', trapHandler);
    }

    /**
     * 포커스 트랩 해제
     */
    releaseFocusTrap(modal) {
        if (modal._focusTrapHandler) {
            modal.removeEventListener('keydown', modal._focusTrapHandler);
            delete modal._focusTrapHandler;
        }
    }

    /**
     * Skip Link 설정
     */
    setupSkipLink() {
        // Skip link가 없으면 생성
        let skipLink = document.querySelector('.skip-link');
        if (!skipLink) {
            skipLink = document.createElement('a');
            skipLink.href = '#main-content';
            skipLink.className = 'skip-link';
            skipLink.textContent = '메인 콘텐츠로 건너뛰기';
            document.body.insertBefore(skipLink, document.body.firstChild);
        }

        skipLink.addEventListener('click', (e) => {
            e.preventDefault();
            const mainContent = document.getElementById('main-content');
            if (mainContent) {
                mainContent.setAttribute('tabindex', '-1');
                mainContent.focus();
                mainContent.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }

    /**
     * 화살표 네비게이션을 위한 추가 설정
     */
    setupArrowNavigation() {
        // 드롭다운 select에 대한 키보드 지원 강화
        document.querySelectorAll('select').forEach(select => {
            select.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
                    // 기본 브라우저 동작 사용
                }
            });
        });

        // 사이드바 버튼 그룹에 role 추가
        const navSection = document.querySelector('#sidebar nav');
        if (navSection) {
            const buttonGroup = navSection.querySelector('.space-y-1\\.5');
            if (buttonGroup) {
                buttonGroup.setAttribute('role', 'group');
                buttonGroup.setAttribute('aria-label', '네비게이션 메뉴');
            }
        }
    }

    /**
     * 포커스 가능한 요소들 가져오기
     */
    getFocusableElements(container = document) {
        return Array.from(container.querySelectorAll(this.focusableSelector))
            .filter(el => {
                return el.offsetParent !== null && // visible
                    !el.hasAttribute('disabled') &&
                    el.getAttribute('tabindex') !== '-1';
            });
    }

    /**
     * 특정 요소로 포커스 이동
     */
    focusElement(element) {
        if (element) {
            element.focus();
            element.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    /**
     * 현재 포커스 모드 반환
     */
    getFocusMode() {
        return this.focusMode;
    }

    /**
     * 접근성 속성 자동 설정
     */
    setupAccessibilityAttributes() {
        // 아이콘 버튼에 aria-label 확인
        document.querySelectorAll('button').forEach(btn => {
            if (!btn.getAttribute('aria-label') && !btn.textContent.trim()) {
                const icon = btn.querySelector('.material-symbols-outlined');
                if (icon) {
                    // 아이콘 이름을 기반으로 aria-label 추정
                    const iconName = icon.textContent.trim();
                    btn.setAttribute('aria-label', iconName.replace(/_/g, ' '));
                }
            }
        });

        // 모달에 aria-modal 확인
        document.querySelectorAll('.modal-overlay').forEach(modal => {
            if (!modal.getAttribute('aria-modal')) {
                modal.setAttribute('aria-modal', 'true');
            }
            if (!modal.getAttribute('role')) {
                modal.setAttribute('role', 'dialog');
            }
        });
    }
}
