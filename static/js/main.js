/**
 * Content Analysis Dashboard - 메인 진입점
 * 모든 모듈을 초기화하고 연결하는 오케스트레이터
 */
import { StorageManager } from './modules/StorageManager.js';
import { UIManager } from './modules/UIManager.js';
import { UrlManager } from './modules/UrlManager.js';
import { ProviderManager } from './modules/ProviderManager.js';
import { ModalManager } from './modules/ModalManager.js';
import { StyleManager } from './modules/StyleManager.js';
import { ReportManager } from './modules/ReportManager.js';
import { ContentGenerator } from './modules/ContentGenerator.js';
import { MindmapManager } from './modules/MindmapManager.js';
import { AuthManager } from './modules/AuthManager.js';

class ContentAnalysis {
    constructor() {
        // 모듈 초기화
        this.storage = new StorageManager();
        this.ui = new UIManager();
        this.urlManager = new UrlManager(this.ui);
        this.providerManager = new ProviderManager(this.storage, this.ui);
        this.modalManager = new ModalManager(this.storage, this.providerManager, this.ui);
        this.styleManager = new StyleManager(this.storage, this.ui, this.modalManager);
        this.reportManager = new ReportManager(this.storage, this.styleManager, this.ui);
        this.mindmapManager = new MindmapManager(this.storage, this.providerManager, this.ui);
        this.authManager = new AuthManager(this.storage, this.ui);
        this.generator = new ContentGenerator(
            this.storage,
            this.providerManager,
            this.styleManager,
            this.urlManager,
            this.reportManager,
            this.ui
        );

        // ReportManager에 MindmapManager 연결
        this.reportManager.setMindmapManager(this.mindmapManager);

        // 모달 매니저에 커스텀 스타일 변경 콜백 연결
        this.modalManager.onCustomStylesChange = () => this.styleManager.renderCustomStyles();

        this.init();
    }

    async init() {
        // 인증 초기화 (Supabase 활성화 여부 확인)
        await this.authManager.init();

        await this.providerManager.loadProviders();
        this.setupEventListeners();
        this.modalManager.setupSettingsModal();
        this.providerManager.setupProviderSelectEvents();
        this.styleManager.setupAdvancedOptions();
        this.modalManager.setupCustomStyleModal();
        this.styleManager.renderCustomStyles();
        this.modalManager.checkFirstTimeUser();
        this.providerManager.updateProviderLabel();
        this.reportManager.loadHistory();
    }

    setupEventListeners() {
        // Start button
        const startBtn = document.getElementById('start-btn');
        if (startBtn) {
            startBtn.addEventListener('click', () => this.generator.handleGenerate());
        }

        // Run Analysis button
        const runBtn = document.getElementById('run-analysis-btn');
        if (runBtn) {
            runBtn.addEventListener('click', () => this.generator.handleGenerate());
        }

        // AI Analyze button (세팅 + 분석 자동 실행)
        const aiAnalyzeBtn = document.getElementById('ai-analyze-btn');
        if (aiAnalyzeBtn) {
            aiAnalyzeBtn.addEventListener('click', () => this.handleAiAnalyze());
        }

        // Generate Style button (AI 스타일 생성)
        const generateStyleBtn = document.getElementById('generate-style-btn');
        if (generateStyleBtn) {
            generateStyleBtn.addEventListener('click', () => this.handleGenerateStyle());
        }

        // URL input events
        const urlInput = document.getElementById('url-input');
        if (urlInput) {
            urlInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    const url = urlInput.value.trim();
                    if (url) {
                        const added = this.urlManager.parseAndAddUrls(url);
                        if (added > 0) {
                            urlInput.value = '';
                        } else if (this.urlManager.getUrls().length > 0) {
                            this.generator.handleGenerate();
                        } else {
                            this.ui.showAlert('유효한 YouTube URL을 입력해주세요.', 'warning');
                        }
                    } else if (this.urlManager.getUrls().length > 0) {
                        this.generator.handleGenerate();
                    }
                }
            });

            // Paste handler
            urlInput.addEventListener('paste', (e) => {
                setTimeout(() => {
                    const text = urlInput.value;
                    const added = this.urlManager.parseAndAddUrls(text);
                    if (added > 0) {
                        urlInput.value = '';
                    }
                }, 100);
            });
        }

        // Ctrl+Enter shortcut
        document.addEventListener('keydown', (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this.generator.handleGenerate();
            }
        });
    }

    getFirstUrl() {
        const urlInput = document.getElementById('url-input');
        const inputUrl = urlInput?.value.trim();
        if (inputUrl) return inputUrl;

        const urls = this.urlManager.getUrls();
        return urls.length > 0 ? urls[0] : null;
    }

    async handleAiAnalyze() {
        const url = this.getFirstUrl();
        if (!url) {
            this.ui.showAlert('YouTube URL을 먼저 입력해주세요.', 'warning');
            return;
        }

        const provider = this.providerManager.getSelectedProvider();
        if (!provider) {
            this.ui.showAlert('AI 서비스를 먼저 선택해주세요.', 'warning');
            return;
        }

        const apiKey = this.storage.getApiKey(provider);
        if (!apiKey) {
            this.ui.showAlert('설정에서 API 키를 먼저 입력해주세요.', 'warning');
            return;
        }

        const aiAnalyzeBtn = document.getElementById('ai-analyze-btn');
        const originalContent = aiAnalyzeBtn.innerHTML;
        aiAnalyzeBtn.disabled = true;
        aiAnalyzeBtn.innerHTML = '<span class="material-symbols-outlined text-base animate-spin">progress_activity</span><span class="hidden sm:inline">세팅중...</span>';

        try {
            const model = this.providerManager.getSelectedModel() || 'gpt-4o';
            const response = await fetch('/api/recommend-style', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, apiKey, model })
            });

            const data = await response.json();
            if (data.error) {
                this.ui.showAlert(data.error, 'error');
                return;
            }

            // 스타일 적용 (라디오 버튼)
            if (data.style) {
                const styleRadio = document.querySelector(`input[name="style"][value="${data.style}"]`);
                if (styleRadio) {
                    styleRadio.checked = true;
                    styleRadio.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }

            // 모디파이어 적용
            if (data.modifiers) {
                const { length, tone, emoji } = data.modifiers;
                if (length) {
                    const lengthSelect = document.getElementById('length-select');
                    if (lengthSelect) lengthSelect.value = length;
                }
                if (tone) {
                    const toneSelect = document.getElementById('tone-select');
                    if (toneSelect) toneSelect.value = tone;
                }
                if (emoji) {
                    const emojiSelect = document.getElementById('emoji-select');
                    if (emojiSelect) emojiSelect.value = emoji;
                }
            }

            const checkedStyle = document.querySelector('input[name="style"]:checked');
            const styleLabel = checkedStyle?.closest('label')?.querySelector('.font-medium')?.textContent || data.style;
            this.ui.showAlert(`"${data.title}" → ${styleLabel} 세팅 완료! 분석을 시작합니다...`, 'success');

            // URL 입력창에 URL이 있으면 urlManager에 추가
            const urlInput = document.getElementById('url-input');
            if (urlInput?.value.trim()) {
                this.urlManager.parseAndAddUrls(urlInput.value.trim());
                urlInput.value = '';
            }

            // 바로 분석 실행
            aiAnalyzeBtn.innerHTML = '<span class="material-symbols-outlined text-base animate-spin">progress_activity</span><span class="hidden sm:inline">분석중...</span>';
            await this.generator.handleGenerate();

        } catch (error) {
            console.error('AI analyze error:', error);
            this.ui.showAlert('AI 분석 중 오류가 발생했습니다.', 'error');
        } finally {
            aiAnalyzeBtn.disabled = false;
            aiAnalyzeBtn.innerHTML = originalContent;
        }
    }

    async handleGenerateStyle() {
        const url = this.getFirstUrl();
        if (!url) {
            this.ui.showAlert('YouTube URL을 먼저 입력해주세요.', 'warning');
            return;
        }

        const provider = this.providerManager.getSelectedProvider();
        if (!provider) {
            this.ui.showAlert('AI 서비스를 먼저 선택해주세요.', 'warning');
            return;
        }

        const apiKey = this.storage.getApiKey(provider);
        if (!apiKey) {
            this.ui.showAlert('설정에서 API 키를 먼저 입력해주세요.', 'warning');
            return;
        }

        const generateBtn = document.getElementById('generate-style-btn');
        const originalContent = generateBtn.innerHTML;
        generateBtn.disabled = true;
        generateBtn.innerHTML = '<span class="material-symbols-outlined text-base animate-spin">progress_activity</span><span class="hidden sm:inline">생성중...</span>';

        try {
            const model = this.providerManager.getSelectedModel() || 'gpt-4o';
            const supadataApiKey = this.storage.getSupadataApiKey() || '';

            const response = await fetch('/api/generate-style', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url, apiKey, model, supadataApiKey })
            });

            const data = await response.json();
            if (data.error) {
                this.ui.showAlert(data.error, 'error');
                return;
            }

            // 새 커스텀 스타일로 저장
            const customStyle = {
                id: 'generated-' + Date.now(),
                name: data.styleName || 'AI 생성 스타일',
                prompt: data.stylePrompt,
                createdAt: Date.now()
            };

            const customStyles = this.storage.getCustomStyles() || [];
            customStyles.push(customStyle);
            this.storage.saveCustomStyles(customStyles);

            // 커스텀 스타일 UI 갱신
            this.styleManager.renderCustomStyles();

            // 생성된 스타일 선택
            setTimeout(() => {
                const styleRadio = document.querySelector(`input[name="style"][value="${customStyle.id}"]`);
                if (styleRadio) {
                    styleRadio.checked = true;
                    styleRadio.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }, 100);

            this.ui.showAlert(`"${data.styleName}" 스타일이 생성되었습니다. ${data.description}`, 'success');

        } catch (error) {
            console.error('Generate style error:', error);
            this.ui.showAlert('스타일 생성 중 오류가 발생했습니다.', 'error');
        } finally {
            generateBtn.disabled = false;
            generateBtn.innerHTML = originalContent;
        }
    }
}

// 커스텀 애니메이션 스타일 추가
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        to {
            opacity: 0;
            transform: translateX(-20px);
        }
    }

    .custom-style-card .style-card {
        position: relative;
    }

    .custom-style-edit-btn {
        opacity: 0;
        transition: opacity 0.2s;
    }

    .custom-style-card:hover .custom-style-edit-btn {
        opacity: 1;
    }

    #custom-style-modal.active,
    #settings-modal.active,
    #onboarding-modal.active,
    #mindmap-modal.active,
    #auth-modal.active {
        display: flex;
    }
`;
document.head.appendChild(style);

// DOM 로드 시 초기화
window.addEventListener('DOMContentLoaded', () => {
    new ContentAnalysis();
});
