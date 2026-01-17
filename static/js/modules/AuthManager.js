/**
 * AuthManager - 인증 관리 모듈
 * Supabase JS SDK 연동, PKCE OAuth Flow 지원
 */
export class AuthManager {
    constructor(storage, uiManager) {
        this.storage = storage;
        this.ui = uiManager;
        this.user = null;
        this.session = null;
        this.isEnabled = false;
        this.onAuthChange = null;
        this._modalEventsSetup = false;
        this.supabaseClient = null;  // Supabase JS SDK 클라이언트
    }

    async init() {
        console.log('[AuthManager] init() 시작');
        try {
            // Supabase 설정 가져오기
            const response = await fetch('/api/auth/config');
            const config = await response.json();
            this.isEnabled = config.enabled;
            console.log('[AuthManager] Supabase enabled:', this.isEnabled);

            // Supabase JS SDK 초기화
            if (this.isEnabled && config.url && config.anonKey && window.supabase) {
                this.supabaseClient = window.supabase.createClient(config.url, config.anonKey);
                console.log('[AuthManager] Supabase JS SDK 초기화 완료');

                // 인증 상태 변경 리스너 등록
                this.supabaseClient.auth.onAuthStateChange((event, session) => {
                    console.log('[AuthManager] onAuthStateChange:', event, session?.user?.email);
                    this._handleAuthStateChange(event, session);
                });

                // 현재 세션 확인 (OAuth 콜백 자동 처리 포함)
                const { data: { session } } = await this.supabaseClient.auth.getSession();
                if (session) {
                    this.session = session;
                    this.user = session.user;
                    console.log('[AuthManager] 기존 세션 복원됨:', session.user?.email);
                }
            }
        } catch (e) {
            console.error('[AuthManager] init 오류:', e);
            this.isEnabled = false;
        }

        if (this.isEnabled) {
            this.setupAuthUI();
            this.updateAuthUI(this.isLoggedIn());
        } else {
            this.setupLocalModeUI();
        }

        console.log('[AuthManager] init() 완료, user:', this.user?.email);
        return this.isEnabled;
    }

    // SDK 인증 상태 변경 핸들러
    _handleAuthStateChange(event, session) {
        console.log('[AuthManager] Auth event:', event);

        if (event === 'INITIAL_SESSION') {
            // 초기 세션 로드 - 알림 없이 상태만 업데이트
            if (session) {
                this.session = session;
                this.user = session.user;
                this.updateAuthUI(true);
                this.onAuthChange?.(true, this.user);
            }
        } else if (event === 'SIGNED_IN' && session) {
            this.session = session;
            this.user = session.user;
            this.updateAuthUI(true);
            this.onAuthChange?.(true, this.user);
            // OAuth 콜백 또는 새로운 로그인 시에만 알림
            this.ui.showAlert('로그인 성공!', 'success');
            // OAuth 콜백 URL 정리
            this.handleOAuthCallback();
        } else if (event === 'SIGNED_OUT') {
            this.session = null;
            this.user = null;
            this.updateAuthUI(false);
            this.onAuthChange?.(false, null);
        } else if (event === 'TOKEN_REFRESHED' && session) {
            this.session = session;
            console.log('[AuthManager] 토큰 갱신됨');
        }
    }

    // OAuth 콜백 처리 (SDK가 자동으로 처리하므로 URL 정리만 수행)
    async handleOAuthCallback() {
        // SDK가 URL 해시/파라미터의 인증 정보를 자동으로 처리함
        // URL에 code나 access_token이 있으면 정리만 수행
        const url = new URL(window.location.href);
        const hasAuthParams = url.searchParams.has('code') ||
            url.searchParams.has('error') ||
            window.location.hash.includes('access_token');

        if (hasAuthParams) {
            console.log('[AuthManager] OAuth 콜백 감지 - URL 정리');
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }

    // ==================== API 헬퍼 ====================

    async _fetchJson(url, options = {}) {
        try {
            const response = await fetch(url, {
                headers: { 'Content-Type': 'application/json', ...options.headers },
                ...options
            });
            const data = await response.json();
            return { ok: response.ok, data };
        } catch (error) {
            return { ok: false, data: { error: error.message }, isNetworkError: true };
        }
    }

    _getAuthHeaders() {
        return this.session?.access_token
            ? { 'Authorization': `Bearer ${this.session.access_token}` }
            : {};
    }

    // ==================== 세션 관리 (SDK가 자동 처리) ====================

    // SDK가 localStorage를 자동으로 관리하므로 별도 복원 불필요
    async restoreSession() {
        // SDK 사용 시 getSession()이 자동으로 세션을 복원함
        // init()에서 이미 처리되므로 이 메서드는 하위 호환성을 위해 유지
        console.log('[AuthManager] restoreSession - SDK가 자동 처리');
    }

    // SDK 사용 시 불필요하지만 하위 호환성을 위해 유지
    async verifySession() {
        if (!this.supabaseClient) return;

        const { data: { session } } = await this.supabaseClient.auth.getSession();
        if (session) {
            this.session = session;
            this.user = session.user;
            this.updateAuthUI(true);
            this.onAuthChange?.(true, this.user);
        }
    }

    // SDK가 토큰 갱신을 자동으로 처리
    async refreshToken() {
        if (!this.supabaseClient) return;

        const { data, error } = await this.supabaseClient.auth.refreshSession();
        if (error) {
            console.error('[AuthManager] 토큰 갱신 실패:', error);
            this.clearSession();
        } else if (data.session) {
            this.session = data.session;
            this.user = data.session.user;
            console.log('[AuthManager] 토큰 갱신 성공');
        }
    }

    // SDK가 자동으로 localStorage 관리 - 하위 호환성을 위해 유지
    saveSession() {
        // SDK가 자동으로 처리
    }

    clearSession() {
        this.user = null;
        this.session = null;
        this.updateAuthUI(false);
        this.onAuthChange?.(false, null);
    }

    getAccessToken() {
        return this.session?.access_token || null;
    }

    isLoggedIn() {
        return Boolean(this.user && this.session);
    }

    // ==================== 사용량 관리 ====================

    async getUsage() {
        if (!this.isLoggedIn()) {
            return { usage_count: 0, max_usage: 5, can_use: false };
        }

        const { ok, data } = await this._fetchJson('/api/user/usage', {
            headers: this._getAuthHeaders()
        });

        if (ok) {
            return data;
        }

        return { usage_count: 0, max_usage: 5, can_use: false };
    }

    // ==================== 인증 액션 ====================

    async _authRequest(url, body, successHandler, successMsg, failMsg) {
        console.log('[AuthManager] _authRequest:', url, body);
        const { ok, data, isNetworkError } = await this._fetchJson(url, {
            method: 'POST',
            body: JSON.stringify(body)
        });
        console.log('[AuthManager] Response:', { ok, data, isNetworkError });

        if (isNetworkError) {
            this.ui.showAlert('네트워크 오류', 'error');
            return { success: false, error: data.error };
        }

        if (ok) {
            successHandler?.(data);
            this.ui.showAlert(successMsg, 'success');
            return { success: true };
        }

        this.ui.showAlert(data.error || failMsg, 'error');
        return { success: false, error: data.error };
    }

    async signup(email, password) {
        return this._authRequest(
            '/api/auth/signup',
            { email, password },
            null,
            '회원가입 완료! 이메일을 확인해주세요.',
            '회원가입 실패'
        );
    }

    async login(email, password) {
        return this._authRequest(
            '/api/auth/login',
            { email, password },
            (data) => {
                this.user = data.user;
                this.session = data.session;
                this.saveSession();
                this.updateAuthUI(true);
                this.onAuthChange?.(true, this.user);
            },
            `환영합니다!`,
            '로그인 실패'
        );
    }

    async logout() {
        try {
            if (this.supabaseClient) {
                // SDK를 통한 로그아웃 (세션 자동 정리)
                await this.supabaseClient.auth.signOut();
            }
            this.clearSession();
            this.ui.showAlert('로그아웃되었습니다.', 'info');
        } catch (error) {
            console.error('[AuthManager] 로그아웃 오류:', error);
            this.clearSession();
            this.ui.showAlert('로그아웃되었습니다.', 'info');
        }
    }

    async resetPassword(email) {
        return this._authRequest(
            '/api/auth/reset-password',
            { email },
            null,
            '비밀번호 재설정 이메일을 발송했습니다.',
            '이메일 발송 실패'
        );
    }

    async oauthLogin(provider) {
        // Supabase JS SDK를 사용한 OAuth 로그인 (PKCE 자동 처리)
        if (!this.supabaseClient) {
            this.ui.showAlert('인증 서비스가 초기화되지 않았습니다.', 'error');
            return;
        }

        try {
            const redirectUrl = window.location.origin;
            console.log('[AuthManager] OAuth 로그인 시작:', provider, 'redirect:', redirectUrl);

            const { data, error } = await this.supabaseClient.auth.signInWithOAuth({
                provider: provider,
                options: {
                    redirectTo: redirectUrl
                }
            });

            if (error) {
                console.error('[AuthManager] OAuth 오류:', error);
                this.ui.showAlert(error.message || 'OAuth 로그인 실패', 'error');
            }
            // 성공 시 자동으로 리다이렉트됨
        } catch (error) {
            console.error('[AuthManager] OAuth 요청 오류:', error);
            this.ui.showAlert('OAuth 요청 중 오류가 발생했습니다.', 'error');
        }
    }

    // ==================== UI ====================

    setupAuthUI() {
        console.log('[AuthManager] setupAuthUI() 호출됨');
        const authContainer = document.getElementById('auth-container');
        if (!authContainer) {
            console.error('[AuthManager] auth-container 요소를 찾을 수 없음!');
            return;
        }
        console.log('[AuthManager] auth-container 찾음, UI 설정 중...');

        authContainer.innerHTML = `
            <div id="auth-logged-out" class="flex items-center gap-2">
                <button id="login-btn" class="text-xs text-gray-text hover:text-primary-accent transition-colors px-3 py-1.5 border border-border-dark rounded-lg hover:border-primary-accent/50">
                    로그인
                </button>
            </div>
            <div id="auth-logged-in" class="hidden flex items-center gap-2">
                <span id="user-email" class="text-xs text-gray-text truncate max-w-[120px]"></span>
                <button id="logout-btn" class="text-xs text-gray-text hover:text-red-400 transition-colors px-2 py-1">
                    <span class="material-symbols-outlined text-sm">logout</span>
                </button>
            </div>
        `;

        document.getElementById('login-btn')?.addEventListener('click', () => this.showAuthModal());
        document.getElementById('logout-btn')?.addEventListener('click', () => this.logout());

        // 모달 이벤트 미리 등록 (사이드바에서 직접 모달을 열 수 있으므로)
        if (!this._modalEventsSetup) {
            this.setupAuthModalEvents();
            this._modalEventsSetup = true;
        }
    }

    setupLocalModeUI() {
        const authContainer = document.getElementById('auth-container');
        if (!authContainer) return;

        authContainer.innerHTML = `
            <span class="text-xs text-gray-text/50 flex items-center gap-1">
                <span class="material-symbols-outlined text-sm">cloud_off</span>
                로컬 모드
            </span>
        `;
    }

    updateAuthUI(isLoggedIn) {
        const loggedOut = document.getElementById('auth-logged-out');
        const loggedIn = document.getElementById('auth-logged-in');
        const userEmail = document.getElementById('user-email');

        if (!loggedOut || !loggedIn) return;

        loggedOut.classList.toggle('hidden', isLoggedIn);
        loggedIn.classList.toggle('hidden', !isLoggedIn);

        if (userEmail && isLoggedIn) {
            userEmail.textContent = this.user?.email || '';
        }
    }

    showAuthModal() {
        console.log('[AuthManager] showAuthModal() 호출됨');
        const modal = document.getElementById('auth-modal');
        if (!modal) {
            console.error('[AuthManager] auth-modal 요소를 찾을 수 없음!');
            return;
        }

        modal.classList.add('active');
        console.log('[AuthManager] 모달 active 클래스 추가됨');

        if (!this._modalEventsSetup) {
            this.setupAuthModalEvents();
            this._modalEventsSetup = true;
        }
    }

    hideAuthModal() {
        document.getElementById('auth-modal')?.classList.remove('active');
    }

    _setTabActive(activeTab, inactiveTab, activeForm, inactiveForm) {
        activeTab.classList.add('border-primary-accent', 'text-primary-accent');
        activeTab.classList.remove('border-transparent', 'text-gray-text');
        inactiveTab.classList.remove('border-primary-accent', 'text-primary-accent');
        inactiveTab.classList.add('border-transparent', 'text-gray-text');
        activeForm?.classList.remove('hidden');
        inactiveForm?.classList.add('hidden');
    }

    _validateAuthInputs(email, password) {
        if (!email || !password) {
            this.ui.showAlert('이메일과 비밀번호를 입력해주세요.', 'warning');
            return false;
        }
        return true;
    }

    async _handleSubmit(button, originalText, loadingText, action) {
        button.disabled = true;
        button.textContent = loadingText;

        const result = await action();

        button.disabled = false;
        button.textContent = originalText;

        return result;
    }

    setupAuthModalEvents() {
        const modal = document.getElementById('auth-modal');
        const closeBtn = document.getElementById('auth-modal-close');
        const loginTab = document.getElementById('auth-login-tab');
        const signupTab = document.getElementById('auth-signup-tab');
        const loginForm = document.getElementById('auth-login-form');
        const signupForm = document.getElementById('auth-signup-form');
        const loginSubmit = document.getElementById('auth-login-submit');
        const signupSubmit = document.getElementById('auth-signup-submit');

        // 탭 전환
        loginTab?.addEventListener('click', () => {
            this._setTabActive(loginTab, signupTab, loginForm, signupForm);
        });

        signupTab?.addEventListener('click', () => {
            this._setTabActive(signupTab, loginTab, signupForm, loginForm);
        });

        // 닫기
        closeBtn?.addEventListener('click', () => this.hideAuthModal());
        modal?.addEventListener('click', (e) => {
            if (e.target === modal) this.hideAuthModal();
        });

        // 로그인 제출
        loginSubmit?.addEventListener('click', async () => {
            const email = document.getElementById('login-email')?.value;
            const password = document.getElementById('login-password')?.value;

            if (!this._validateAuthInputs(email, password)) return;

            const result = await this._handleSubmit(
                loginSubmit, '로그인', '로그인 중...',
                () => this.login(email, password)
            );

            if (result.success) this.hideAuthModal();
        });

        // 회원가입 제출
        signupSubmit?.addEventListener('click', async () => {
            const email = document.getElementById('signup-email')?.value;
            const password = document.getElementById('signup-password')?.value;
            const confirmPassword = document.getElementById('signup-confirm-password')?.value;

            if (!this._validateAuthInputs(email, password)) return;

            if (password !== confirmPassword) {
                this.ui.showAlert('비밀번호가 일치하지 않습니다.', 'warning');
                return;
            }

            const result = await this._handleSubmit(
                signupSubmit, '회원가입', '가입 중...',
                () => this.signup(email, password)
            );

            if (result.success) loginTab?.click();
        });

        // Enter 키 처리
        document.getElementById('login-password')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') loginSubmit?.click();
        });
        document.getElementById('signup-confirm-password')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') signupSubmit?.click();
        });

        // 비밀번호 재설정 폼
        const resetForm = document.getElementById('auth-reset-form');
        const resetSubmit = document.getElementById('auth-reset-submit');
        const showResetBtn = document.getElementById('show-reset-password');
        const backToLoginBtn = document.getElementById('back-to-login');

        // 비밀번호 찾기 클릭 → 재설정 폼 표시
        showResetBtn?.addEventListener('click', () => {
            loginForm?.classList.add('hidden');
            signupForm?.classList.add('hidden');
            resetForm?.classList.remove('hidden');
            loginTab?.classList.remove('border-primary-accent', 'text-primary-accent');
            loginTab?.classList.add('border-transparent', 'text-gray-text');
        });

        // 로그인으로 돌아가기
        backToLoginBtn?.addEventListener('click', () => {
            resetForm?.classList.add('hidden');
            loginForm?.classList.remove('hidden');
            this._setTabActive(loginTab, signupTab, loginForm, signupForm);
        });

        // 비밀번호 재설정 제출
        resetSubmit?.addEventListener('click', async () => {
            const email = document.getElementById('reset-email')?.value;
            if (!email) {
                this.ui.showAlert('이메일을 입력해주세요.', 'warning');
                return;
            }

            const result = await this._handleSubmit(
                resetSubmit, '재설정 이메일 발송', '발송 중...',
                () => this.resetPassword(email)
            );

            if (result.success) {
                backToLoginBtn?.click();
            }
        });

        // Enter 키 처리 (재설정 폼)
        document.getElementById('reset-email')?.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') resetSubmit?.click();
        });

        // 소셜 로그인 버튼
        document.getElementById('google-login-btn')?.addEventListener('click', () => {
            this.oauthLogin('google');
        });
    }
}
