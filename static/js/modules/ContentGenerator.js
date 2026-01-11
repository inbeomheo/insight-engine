/**
 * ContentGenerator - 콘텐츠 생성 모듈
 * API 호출, 단일/배치 URL 처리 담당
 */
export class ContentGenerator {
    constructor(storage, providerManager, styleManager, urlManager, reportManager, uiManager) {
        this.storage = storage;
        this.providerManager = providerManager;
        this.styleManager = styleManager;
        this.urlManager = urlManager;
        this.reportManager = reportManager;
        this.ui = uiManager;
        this.originalContent = '';
        this.lastPrompt = '';
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
            this.ui.showAlert('AI 서비스와 모델을 선택해주세요. 설정에서 API 키를 먼저 입력해주세요.', 'error');
            return;
        }

        const apiKey = this.storage.getApiKey(provider);
        if (!apiKey) {
            this.ui.showAlert('선택한 서비스의 API 키가 설정되지 않았습니다.', 'error');
            return;
        }

        const supadataApiKey = this.storage.getSupadataApiKey();

        // 백그라운드 처리 - 각 URL을 독립적으로 처리
        for (const url of urls) {
            this.processUrlInBackground(url, provider, model, style, apiKey, supadataApiKey);
        }

        // URL 목록 클리어
        this.urlManager.clear();
    }

    // 백그라운드에서 단일 URL 처리
    async processUrlInBackground(url, provider, model, style, apiKey, supadataApiKey) {
        // 1. 처리 중 카드 먼저 표시
        const pendingId = this.reportManager.createPendingCard(url, style);
        this.ui.incrementPending();

        try {
            const modifiers = this.styleManager.getModifiers();
            const customPrompt = this.styleManager.getCustomPrompt();

            const response = await fetch('/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, model, style, apiKey, supadataApiKey, modifiers, customPrompt })
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
                    usage: data.usage,
                    elapsed_time: data.elapsed_time
                });
            } else {
                // 에러 - 처리 중 카드를 에러 카드로 변환
                this.reportManager.updatePendingCard(pendingId, {
                    url,
                    error: data.error || '분석 중 오류가 발생했습니다.'
                }, true);
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

    async processSingleUrl(url, provider, model, style, apiKey, supadataApiKey) {
        const modifiers = this.styleManager.getModifiers();
        const customPrompt = this.styleManager.getCustomPrompt();

        const response = await fetch('/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ url, model, style, apiKey, supadataApiKey, modifiers, customPrompt })
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
                usage: data.usage,
                elapsed_time: data.elapsed_time
            });
            this.ui.showAlert('분석이 완료되었습니다!', 'success');
        } else {
            throw new Error(data.error || '분석 중 오류가 발생했습니다.');
        }
    }

    // ==================== Batch URL Processing ====================

    async processBatchUrls(urls, provider, model, style, apiKey, supadataApiKey) {
        const modifiers = this.styleManager.getModifiers();
        const customPrompt = this.styleManager.getCustomPrompt();

        const response = await fetch('/generate-batch', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ urls, model, style, apiKey, supadataApiKey, modifiers, customPrompt })
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
                        content: result.content
                    });
                } else {
                    this.reportManager.displayErrorCard({
                        url: result.url,
                        error: result.error
                    });
                }
            });

            this.ui.showAlert(`${urls.length}개의 URL 분석이 완료되었습니다!`, 'success');
        } else {
            throw new Error(data.error || '배치 처리 중 오류가 발생했습니다.');
        }
    }
}
