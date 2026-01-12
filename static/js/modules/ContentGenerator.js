/**
 * ContentGenerator - 콘텐츠 생성 모듈
 * API 호출, 단일/배치 URL 처리 담당
 * API 키는 서버 환경변수에서 관리됩니다.
 * 로그인 필수, 하루 5회 제한 적용.
 */
export class ContentGenerator {
    constructor(storage, providerManager, styleManager, urlManager, reportManager, uiManager, authManager) {
        this.storage = storage;
        this.providerManager = providerManager;
        this.styleManager = styleManager;
        this.urlManager = urlManager;
        this.reportManager = reportManager;
        this.ui = uiManager;
        this.authManager = authManager;
        this.originalContent = '';
        this.lastPrompt = '';
        this.onUsageUpdate = null; // 사용량 업데이트 콜백
    }

    // 인증 헤더 가져오기
    _getAuthHeaders() {
        const headers = { 'Content-Type': 'application/json' };
        const token = this.authManager?.getAccessToken();
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    }

    // ==================== Main Generation ====================

    async handleGenerate() {
        const urlInput = document.getElementById('url-input');
        const rawText = urlInput?.value.trim() || '';
        if (rawText) {
            this.urlManager.parseAndAddUrls(rawText);
            urlInput.value = '';
        }

        const urls = this.urlManager.getUrls();
        const provider = this.providerManager.getSelectedProvider();
        const model = this.providerManager.getSelectedModel();
        const style = this.styleManager.getSelectedStyle();

        if (urls.length === 0) {
            this.ui.showAlert('YouTube URL을 입력해주세요.', 'error');
            return;
        }

        if (!provider || !model) {
            this.ui.showAlert('사용 가능한 AI 서비스가 없습니다. 서버 설정을 확인해주세요.', 'error');
            return;
        }

        // 백그라운드 처리 - 각 URL을 독립적으로 처리
        for (const url of urls) {
            this.processUrlInBackground(url, provider, model, style);
        }

        // URL 목록 클리어
        this.urlManager.clear();
    }

    // 백그라운드에서 단일 URL 처리
    async processUrlInBackground(url, provider, model, style) {
        // 1. 처리 중 카드 먼저 표시
        const pendingId = this.reportManager.createPendingCard(url, style);
        this.ui.incrementPending();

        try {
            const modifiers = this.styleManager.getModifiers();
            const customPrompt = this.styleManager.getCustomPrompt();

            const response = await fetch('/generate', {
                method: 'POST',
                headers: this._getAuthHeaders(),
                body: JSON.stringify({ url, model, style, modifiers, customPrompt })
            });

            const data = await response.json();

            if (response.ok) {
                this.originalContent = data.content;
                this.lastPrompt = data.prompt || '';

                // 성공 - 처리 중 카드를 결과 카드로 교체
                this.reportManager.updatePendingCard(pendingId, {
                    url,
                    title: data.youtube_title || data.title || 'YouTube 영상 분석',
                    style,
                    html: data.html,
                    content: data.content,
                    prompt: data.prompt,
                    usage: data.usage,
                    elapsed_time: data.elapsed_time,
                    transcript: data.transcript
                });

                // 사용량 업데이트 콜백 호출
                this.onUsageUpdate?.();
            } else {
                // 에러 - 처리 중 카드를 에러 카드로 변환 (401은 로그인 필요)
                const errorMsg = response.status === 401 ? '로그인이 필요합니다.' :
                                 response.status === 429 ? data.error || '사용 횟수를 모두 소진했습니다.' :
                                 data.error || '분석 중 오류가 발생했습니다.';
                this.reportManager.updatePendingCard(pendingId, {
                    url,
                    error: errorMsg
                }, true);

                // 401/429 에러 시 사용량 상태 업데이트
                if (response.status === 401 || response.status === 429) {
                    this.onUsageUpdate?.();
                }
            }
        } catch (error) {
            // 네트워크 에러 등
            this.reportManager.updatePendingCard(pendingId, {
                url,
                error: this.ui.getKoreanErrorMessage(error)
            }, true);
        } finally {
            this.ui.decrementPending();
        }
    }

    // ==================== Single URL Processing ====================

    async processSingleUrl(url, provider, model, style) {
        const modifiers = this.styleManager.getModifiers();
        const customPrompt = this.styleManager.getCustomPrompt();

        const response = await fetch('/generate', {
            method: 'POST',
            headers: this._getAuthHeaders(),
            body: JSON.stringify({ url, model, style, modifiers, customPrompt })
        });

        const data = await response.json();

        if (response.ok) {
            this.originalContent = data.content;
            this.lastPrompt = data.prompt || '';
            this.reportManager.displayReportCard({
                url,
                title: data.youtube_title || data.title || 'YouTube 영상 분석',
                style,
                html: data.html,
                content: data.content,
                prompt: data.prompt,
                usage: data.usage,
                elapsed_time: data.elapsed_time
            });
            this.ui.showAlert('분석이 완료되었습니다!', 'success');
            this.onUsageUpdate?.();
        } else {
            const errorMsg = response.status === 401 ? '로그인이 필요합니다.' :
                             response.status === 429 ? data.error || '사용 횟수를 모두 소진했습니다.' :
                             data.error || '분석 중 오류가 발생했습니다.';
            throw new Error(errorMsg);
        }
    }

    // ==================== Batch URL Processing ====================

    async processBatchUrls(urls, provider, model, style) {
        const modifiers = this.styleManager.getModifiers();
        const customPrompt = this.styleManager.getCustomPrompt();

        const response = await fetch('/generate-batch', {
            method: 'POST',
            headers: this._getAuthHeaders(),
            body: JSON.stringify({ urls, model, style, modifiers, customPrompt })
        });

        const data = await response.json();

        if (response.ok) {
            this.originalContent = data.content;
            this.lastPrompt = data.prompt || '';

            data.results.forEach(result => {
                if (result.success) {
                    this.reportManager.displayReportCard({
                        url: result.url,
                        title: result.title || 'YouTube 영상 분석',
                        style,
                        html: result.html,
                        content: result.content,
                        prompt: result.prompt
                    });
                } else {
                    this.reportManager.displayErrorCard({
                        url: result.url,
                        error: result.error
                    });
                }
            });

            this.ui.showAlert(`${urls.length}개의 URL 분석이 완료되었습니다!`, 'success');
            this.onUsageUpdate?.();
        } else {
            const errorMsg = response.status === 401 ? '로그인이 필요합니다.' :
                             response.status === 429 ? data.error || '사용 횟수를 모두 소진했습니다.' :
                             data.error || '배치 처리 중 오류가 발생했습니다.';
            throw new Error(errorMsg);
        }
    }
}
