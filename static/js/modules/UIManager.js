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
        const container = document.getElementById('alert-container');
        if (!container) return;

        container.innerHTML = '';

        const alert = document.createElement('div');
        alert.className = `alert alert-${type}`;

        const iconMap = {
            success: 'check_circle',
            error: 'error',
            warning: 'warning',
            info: 'info'
        };

        alert.innerHTML = `
            <div class="flex items-center gap-2">
                <span class="material-symbols-outlined">${iconMap[type] || iconMap.info}</span>
                <span>${this.escapeHtml(message)}</span>
            </div>
            <button class="p-1 hover:bg-white/10 transition-colors" onclick="this.parentElement.remove()">
                <span class="material-symbols-outlined text-sm">close</span>
            </button>
        `;

        container.appendChild(alert);

        setTimeout(() => {
            if (alert.parentElement) {
                alert.style.opacity = '0';
                alert.style.transform = 'translateY(-20px)';
                setTimeout(() => alert.remove(), 300);
            }
        }, 5000);
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
     */
    sanitizeUrl(url) {
        if (!url || typeof url !== 'string') return '#';
        const trimmed = url.trim().toLowerCase();
        // 위험한 프로토콜 차단
        if (trimmed.startsWith('javascript:') ||
            trimmed.startsWith('data:') ||
            trimmed.startsWith('vbscript:')) {
            return '#';
        }
        // HTML 속성용 이스케이프
        return this.escapeHtml(url);
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
