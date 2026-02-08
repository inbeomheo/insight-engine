/**
 * UIManager - UI 상태 관리 모듈
 * 알림, 로딩 상태, 유틸리티 함수 담당
 */
export class UIManager {
    constructor() {
        this.isGenerating = false;
        this.pendingCount = 0;  // 진행 중인 분석 개수
    }

    // ==================== Alerts ====================

    showAlert(message, type = 'info') {
        // 토스트 컨테이너 확보 (상단 중앙 고정)
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            container.style.cssText = 'position:fixed;top:16px;left:50%;transform:translateX(-50%);z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;';
            document.body.appendChild(container);
        }

        const colorMap = {
            success: '#22c55e',
            error: '#ef4444',
            warning: '#f59e0b',
            info: '#4F46E5'
        };
        const iconMap = {
            success: 'check_circle',
            error: 'error',
            warning: 'warning',
            info: 'info'
        };

        const toast = document.createElement('div');
        toast.style.cssText = `
            pointer-events:auto;display:flex;align-items:center;gap:8px;
            padding:10px 16px;background:#fff;border:1px solid #e5e7eb;
            border-left:3px solid ${colorMap[type] || colorMap.info};
            border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,0.08);
            font-size:13px;color:#374151;max-width:420px;
            opacity:0;transform:translateY(-8px);
            transition:opacity 0.2s,transform 0.2s;
        `;
        toast.innerHTML = `
            <span class="material-symbols-outlined" style="font-size:18px;color:${colorMap[type] || colorMap.info}">${iconMap[type] || iconMap.info}</span>
            <span style="flex:1">${this.escapeHtml(message)}</span>
            <button style="padding:2px;color:#9ca3af;cursor:pointer;background:none;border:none;" onclick="this.parentElement.remove()">
                <span class="material-symbols-outlined" style="font-size:16px">close</span>
            </button>
        `;

        container.appendChild(toast);

        // 등장 애니메이션
        requestAnimationFrame(() => {
            toast.style.opacity = '1';
            toast.style.transform = 'translateY(0)';
        });

        // 3초 후 자동 사라짐
        setTimeout(() => {
            if (toast.parentElement) {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(-8px)';
                setTimeout(() => toast.remove(), 200);
            }
        }, 3000);
    }

    // ==================== Loading States ====================

    setLoading(loading) {
        this.isGenerating = loading;

        const startBtn = document.getElementById('start-btn');
        const runBtn = document.getElementById('run-analysis-btn');
        const runIcon = document.getElementById('run-icon');
        const runText = document.getElementById('run-text');

        if (startBtn) {
            startBtn.disabled = loading;
            startBtn.textContent = loading ? 'Analyzing...' : 'Start';
        }

        if (runBtn) {
            runBtn.disabled = loading;
        }

        if (runIcon) {
            if (loading) {
                runIcon.textContent = 'progress_activity';
                runIcon.classList.add('loading-spinner');
            } else {
                runIcon.textContent = 'auto_awesome';
                runIcon.classList.remove('loading-spinner');
            }
        }

        if (runText) {
            runText.textContent = loading ? 'Analyzing...' : 'Run Analysis';
        }
    }

    // 백그라운드 처리용 - 버튼 비활성화 없이 카운터만 관리
    incrementPending() {
        this.pendingCount++;
        this.updatePendingUI();
    }

    decrementPending() {
        this.pendingCount = Math.max(0, this.pendingCount - 1);
        this.updatePendingUI();
    }

    updatePendingUI() {
        const runText = document.getElementById('run-text');
        const runIcon = document.getElementById('run-icon');
        const badge = document.getElementById('pending-badge');

        if (this.pendingCount > 0) {
            if (runIcon) {
                runIcon.textContent = 'progress_activity';
                runIcon.classList.add('loading-spinner');
            }
            if (runText) {
                runText.textContent = 'Run Analysis';
            }
            // 뱃지 표시
            if (badge) {
                badge.textContent = this.pendingCount;
                badge.classList.remove('hidden');
            }
        } else {
            if (runIcon) {
                runIcon.textContent = 'auto_awesome';
                runIcon.classList.remove('loading-spinner');
            }
            if (runText) {
                runText.textContent = 'Run Analysis';
            }
            // 뱃지 숨김
            if (badge) {
                badge.classList.add('hidden');
            }
        }
    }

    // ==================== Button Disabled Feedback ====================

    /**
     * 버튼 비활성화 시 이유를 표시하는 오버레이를 설정합니다.
     * @param {HTMLElement} button - 대상 버튼 요소
     * @param {string|null} reason - 비활성화 이유 (null이면 오버레이 제거)
     */
    setButtonDisabledReason(button, reason) {
        if (!button) return;

        // 기존 오버레이 제거
        const existingOverlay = button.querySelector('.disabled-reason-overlay');
        if (existingOverlay) {
            existingOverlay.remove();
        }

        // reason이 null이면 오버레이 없이 종료
        if (!reason) {
            button.classList.remove('has-disabled-reason');
            return;
        }

        // 버튼에 relative 클래스 추가 (이미 있으면 무시)
        if (!button.classList.contains('relative')) {
            button.classList.add('relative');
        }
        button.classList.add('has-disabled-reason');

        // 오버레이 생성
        const overlay = document.createElement('div');
        overlay.className = 'disabled-reason-overlay';
        overlay.innerHTML = `
            <span class="material-symbols-outlined text-xs mr-1">info</span>
            <span>${this.escapeHtml(reason)}</span>
        `;

        button.appendChild(overlay);
    }

    /**
     * 분석 버튼의 비활성화 상태와 이유를 업데이트합니다.
     * @param {boolean} disabled - 비활성화 여부
     * @param {string|null} reason - 비활성화 이유
     */
    updateAnalyzeButtonState(disabled, reason = null) {
        const runBtn = document.getElementById('run-analysis-btn');
        const startBtn = document.getElementById('start-btn');
        const aiAnalyzeBtn = document.getElementById('ai-analyze-btn');

        [runBtn, startBtn, aiAnalyzeBtn].forEach(btn => {
            if (btn) {
                btn.disabled = disabled;
                this.setButtonDisabledReason(btn, disabled ? reason : null);
            }
        });
    }

    // ==================== Utilities ====================

    escapeHtml(text) {
        return String(text)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    /**
     * URL을 안전하게 이스케이프합니다 (XSS 방지).
     * javascript: 프로토콜 등 위험한 URL을 차단합니다.
     * 프로토콜이 없는 URL에는 https://를 자동 추가합니다.
     */
    sanitizeUrl(url) {
        if (!url || typeof url !== 'string') return '#';
        let processedUrl = url.trim();
        const lowerUrl = processedUrl.toLowerCase();

        // 위험한 프로토콜 차단
        if (lowerUrl.startsWith('javascript:') ||
            lowerUrl.startsWith('data:') ||
            lowerUrl.startsWith('vbscript:')) {
            return '#';
        }

        // 프로토콜이 없으면 https:// 추가 (상대 경로 방지)
        if (!lowerUrl.startsWith('http://') && !lowerUrl.startsWith('https://')) {
            processedUrl = 'https://' + processedUrl;
        }

        // HTML 속성용 이스케이프
        return this.escapeHtml(processedUrl);
    }

    /**
     * 마크다운 테이블을 HTML 테이블로 변환 (폴백용)
     */
    convertMarkdownTables(html) {
        // 마크다운 테이블 패턴: | col | col | 로 시작하는 연속된 줄
        const lines = html.split('\n');
        const result = [];
        let tableLines = [];
        let inTable = false;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            const isTableLine = line.startsWith('|') && line.endsWith('|');
            const isSeparator = /^\|[-:\s|]+\|$/.test(line);

            if (isTableLine || isSeparator) {
                if (!inTable) {
                    inTable = true;
                }
                tableLines.push(line);
            } else {
                if (inTable && tableLines.length > 0) {
                    result.push(this._parseMarkdownTable(tableLines));
                    tableLines = [];
                    inTable = false;
                }
                result.push(lines[i]);
            }
        }

        // 마지막 테이블 처리
        if (tableLines.length > 0) {
            result.push(this._parseMarkdownTable(tableLines));
        }

        return result.join('\n');
    }

    /**
     * 마크다운 테이블 라인들을 HTML 테이블로 변환
     */
    _parseMarkdownTable(lines) {
        if (lines.length < 2) return lines.join('\n');

        const rows = [];
        let hasHeader = false;

        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            // 구분선 스킵 (|---|---|)
            if (/^\|[-:\s|]+\|$/.test(line)) {
                hasHeader = true;
                continue;
            }
            // 셀 파싱
            const cells = line.split('|')
                .filter((_, idx, arr) => idx > 0 && idx < arr.length - 1)
                .map(cell => cell.trim());
            rows.push(cells);
        }

        if (rows.length === 0) return lines.join('\n');

        // HTML 테이블 생성
        let tableHtml = '<table>';

        rows.forEach((cells, idx) => {
            if (idx === 0 && hasHeader) {
                tableHtml += '<thead><tr>';
                cells.forEach(cell => {
                    tableHtml += `<th>${this.escapeHtml(cell)}</th>`;
                });
                tableHtml += '</tr></thead><tbody>';
            } else {
                if (idx === 1 && hasHeader) {
                    // tbody 이미 열림
                } else if (idx === 0 && !hasHeader) {
                    tableHtml += '<tbody>';
                }
                tableHtml += '<tr>';
                cells.forEach(cell => {
                    tableHtml += `<td>${this.escapeHtml(cell)}</td>`;
                });
                tableHtml += '</tr>';
            }
        });

        tableHtml += '</tbody></table>';
        return tableHtml;
    }

    /**
     * HTML 콘텐츠에서 위험한 요소를 제거합니다 (DOMPurify 사용).
     * 블로그 콘텐츠에 필요한 태그만 허용합니다.
     */
    sanitizeHtml(html) {
        if (!html || typeof html !== 'string') return '';

        // 마크다운 테이블이 HTML로 변환되지 않은 경우 변환
        if (html.includes('|') && !html.includes('<table')) {
            html = this.convertMarkdownTables(html);
        }

        // DOMPurify가 로드되었는지 확인
        if (typeof DOMPurify !== 'undefined') {
            return DOMPurify.sanitize(html, {
                ALLOWED_TAGS: [
                    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    'p', 'br', 'hr',
                    'ul', 'ol', 'li',
                    'strong', 'b', 'em', 'i', 'u', 's', 'mark',
                    'a', 'blockquote', 'code', 'pre',
                    'table', 'thead', 'tbody', 'tr', 'th', 'td',
                    'div', 'span', 'img'
                ],
                ALLOWED_ATTR: [
                    'href', 'target', 'rel', 'src', 'alt', 'title',
                    'class', 'id', 'style'
                ],
                ALLOW_DATA_ATTR: false,
                ADD_ATTR: ['target'],
                FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'form', 'input'],
                FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover']
            });
        }

        // DOMPurify 미로드 시 기본 sanitize (폴백)
        return html
            .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
            .replace(/<iframe\b[^>]*>.*?<\/iframe>/gi, '')
            .replace(/\bon\w+\s*=\s*["'][^"']*["']/gi, '')
            .replace(/\bon\w+\s*=\s*[^\s>]+/gi, '')
            .replace(/javascript:/gi, '');
    }

    getKoreanErrorMessage(error) {
        if (error && error.message) {
            if (error.message.toLowerCase().includes('failed to fetch')) {
                return '서버 연결에 실패했습니다. 네트워크 상태를 확인해주세요.';
            }
            return error.message;
        }
        return '알 수 없는 오류가 발생했습니다.';
    }

    isYouTubeUrl(url) {
        const patterns = [
            /^(https?:\/\/)?(www\.)?youtube\.com\/watch\?v=[\w-]+/,
            /^(https?:\/\/)?(www\.)?youtube\.com\/shorts\/[\w-]+/,
            /^(https?:\/\/)?youtu\.be\/[\w-]+/,
            /^(https?:\/\/)?(www\.)?youtube\.com\/embed\/[\w-]+/
        ];
        return patterns.some(pattern => pattern.test(url));
    }

    generateReportId() {
        return `#${Math.random().toString(36).substring(2, 7).toUpperCase()}`;
    }
}
