/**
 * PanelResizeManager - 패널 리사이즈 관리 모듈
 * 입력 패널과 결과 패널 사이의 리사이즈 기능 담당
 */
export class PanelResizeManager {
    constructor() {
        this.storageKey = 'cad_panel_sizes_v1';
        this.isResizing = false;
        this.currentHandle = null;
        this.startX = 0;
        this.startWidth = 0;

        // 패널 제한 설정 (픽셀)
        this.limits = {
            inputPanel: {
                min: 280,
                max: 500,
                default: 350
            },
            sidebar: {
                min: 160,
                max: 280,
                default: 200
            }
        };

        // 미디어 쿼리 브레이크포인트
        this.breakpoints = {
            xl: 1280,
            lg: 1024,
            md: 768
        };
    }

    init() {
        // xl 이상에서만 리사이즈 기능 활성화
        if (window.innerWidth < this.breakpoints.xl) {
            return;
        }

        this.createResizeHandles();
        this.loadSavedSizes();
        this.setupEventListeners();
        this.setupResizeObserver();
    }

    /**
     * 리사이즈 핸들 생성
     */
    createResizeHandles() {
        // 입력 패널과 결과 패널 사이의 리사이즈 핸들
        const inputPanel = document.getElementById('input-panel');
        if (inputPanel) {
            const handle = this.createHandle('input-resize-handle');
            inputPanel.appendChild(handle);
        }
    }

    /**
     * 개별 리사이즈 핸들 요소 생성
     */
    createHandle(id) {
        const handle = document.createElement('div');
        handle.id = id;
        handle.className = 'resize-handle';
        handle.setAttribute('role', 'separator');
        handle.setAttribute('aria-orientation', 'vertical');
        handle.setAttribute('aria-label', '패널 크기 조절');
        handle.setAttribute('tabindex', '0');

        // 핸들 내부에 그립 라인 추가
        const grip = document.createElement('div');
        grip.className = 'resize-handle-grip';
        handle.appendChild(grip);

        return handle;
    }

    /**
     * 저장된 패널 크기 불러오기
     */
    loadSavedSizes() {
        try {
            const saved = localStorage.getItem(this.storageKey);
            if (saved) {
                const sizes = JSON.parse(saved);
                this.applySizes(sizes);
            }
        } catch (e) {
            console.warn('패널 크기 로드 실패:', e);
        }
    }

    /**
     * 패널 크기 적용
     */
    applySizes(sizes) {
        if (window.innerWidth < this.breakpoints.xl) return;

        const inputPanel = document.getElementById('input-panel');

        if (inputPanel && sizes.inputPanel) {
            const width = Math.max(
                this.limits.inputPanel.min,
                Math.min(this.limits.inputPanel.max, sizes.inputPanel)
            );
            inputPanel.style.width = `${width}px`;
            inputPanel.style.minWidth = `${width}px`;
            inputPanel.style.maxWidth = `${width}px`;
        }
    }

    /**
     * 현재 패널 크기 저장
     */
    saveSizes() {
        try {
            const inputPanel = document.getElementById('input-panel');
            const sizes = {
                inputPanel: inputPanel ? parseInt(inputPanel.style.width) || this.limits.inputPanel.default : this.limits.inputPanel.default
            };
            localStorage.setItem(this.storageKey, JSON.stringify(sizes));
        } catch (e) {
            console.warn('패널 크기 저장 실패:', e);
        }
    }

    /**
     * 이벤트 리스너 설정
     */
    setupEventListeners() {
        const handle = document.getElementById('input-resize-handle');

        if (handle) {
            // 마우스 이벤트
            handle.addEventListener('mousedown', (e) => this.startResize(e, 'input'));

            // 터치 이벤트 (모바일/태블릿)
            handle.addEventListener('touchstart', (e) => this.startResize(e, 'input'), { passive: false });

            // 키보드 접근성
            handle.addEventListener('keydown', (e) => this.handleKeyboard(e, 'input'));
        }

        // 전역 마우스/터치 이벤트
        document.addEventListener('mousemove', (e) => this.onResize(e));
        document.addEventListener('mouseup', () => this.stopResize());
        document.addEventListener('touchmove', (e) => this.onResize(e), { passive: false });
        document.addEventListener('touchend', () => this.stopResize());

        // 윈도우 리사이즈 시 핸들 표시/숨김
        window.addEventListener('resize', () => this.handleWindowResize());
    }

    /**
     * 리사이즈 시작
     */
    startResize(e, type) {
        if (window.innerWidth < this.breakpoints.xl) return;

        e.preventDefault();
        this.isResizing = true;
        this.currentHandle = type;

        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        this.startX = clientX;

        const panel = document.getElementById('input-panel');
        this.startWidth = panel ? panel.offsetWidth : this.limits.inputPanel.default;

        // 리사이즈 중 커서 스타일 설정
        document.body.classList.add('resizing');
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';

        // 핸들 활성 상태
        const handle = document.getElementById('input-resize-handle');
        if (handle) {
            handle.classList.add('active');
        }
    }

    /**
     * 리사이즈 진행
     */
    onResize(e) {
        if (!this.isResizing) return;

        e.preventDefault();

        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const delta = clientX - this.startX;

        const panel = document.getElementById('input-panel');
        if (!panel) return;

        let newWidth = this.startWidth + delta;

        // 제한 적용
        newWidth = Math.max(this.limits.inputPanel.min, Math.min(this.limits.inputPanel.max, newWidth));

        // 패널 크기 적용
        panel.style.width = `${newWidth}px`;
        panel.style.minWidth = `${newWidth}px`;
        panel.style.maxWidth = `${newWidth}px`;
    }

    /**
     * 리사이즈 종료
     */
    stopResize() {
        if (!this.isResizing) return;

        this.isResizing = false;
        this.currentHandle = null;

        // 커서 스타일 복원
        document.body.classList.remove('resizing');
        document.body.style.cursor = '';
        document.body.style.userSelect = '';

        // 핸들 활성 상태 해제
        const handle = document.getElementById('input-resize-handle');
        if (handle) {
            handle.classList.remove('active');
        }

        // 크기 저장
        this.saveSizes();
    }

    /**
     * 키보드 접근성 처리
     */
    handleKeyboard(e, type) {
        if (window.innerWidth < this.breakpoints.xl) return;

        const step = e.shiftKey ? 50 : 10; // Shift 키로 큰 단위 이동
        const panel = document.getElementById('input-panel');
        if (!panel) return;

        let currentWidth = panel.offsetWidth;
        let newWidth = currentWidth;

        switch (e.key) {
            case 'ArrowLeft':
                newWidth = currentWidth - step;
                e.preventDefault();
                break;
            case 'ArrowRight':
                newWidth = currentWidth + step;
                e.preventDefault();
                break;
            case 'Home':
                newWidth = this.limits.inputPanel.min;
                e.preventDefault();
                break;
            case 'End':
                newWidth = this.limits.inputPanel.max;
                e.preventDefault();
                break;
            default:
                return;
        }

        // 제한 적용
        newWidth = Math.max(this.limits.inputPanel.min, Math.min(this.limits.inputPanel.max, newWidth));

        panel.style.width = `${newWidth}px`;
        panel.style.minWidth = `${newWidth}px`;
        panel.style.maxWidth = `${newWidth}px`;

        this.saveSizes();
    }

    /**
     * 윈도우 리사이즈 핸들러
     */
    handleWindowResize() {
        const handle = document.getElementById('input-resize-handle');

        if (window.innerWidth < this.breakpoints.xl) {
            // 작은 화면에서는 핸들 숨기고 기본 스타일로 복원
            if (handle) {
                handle.style.display = 'none';
            }
            this.resetToDefault();
        } else {
            // 큰 화면에서는 핸들 표시
            if (handle) {
                handle.style.display = '';
            }
            this.loadSavedSizes();
        }
    }

    /**
     * 기본값으로 리셋
     */
    resetToDefault() {
        const inputPanel = document.getElementById('input-panel');
        if (inputPanel) {
            inputPanel.style.width = '';
            inputPanel.style.minWidth = '';
            inputPanel.style.maxWidth = '';
        }
    }

    /**
     * ResizeObserver 설정 (레이아웃 변경 감지)
     */
    setupResizeObserver() {
        if (!window.ResizeObserver) return;

        const mainContent = document.getElementById('main-content');
        if (!mainContent) return;

        const observer = new ResizeObserver(() => {
            // 레이아웃이 변경되면 핸들 위치 재조정 필요시 처리
            this.handleWindowResize();
        });

        observer.observe(mainContent);
    }

    /**
     * 패널 크기 초기화 (기본값으로)
     */
    reset() {
        localStorage.removeItem(this.storageKey);
        this.resetToDefault();
    }
}
