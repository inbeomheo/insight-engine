/**
 * AuthManager - 인증 관리 모듈
 * Supabase Auth 연동, 세션 관리
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
    }

    async init() {
        console.log('[AuthManager] init() 시작');
        try {
            const response = await fetch('/api/auth/status');
            const data = await response.json();
            this.isEnabled = data.enabled;
            console.log('[AuthManager] Supabase enabled:', this.isEnabled);
        } catch (e) {
            console.error('[AuthManager] auth/status 오류:', e);
            this.isEnabled = false;
        }

        if (this.isEnabled) {
            // OAuth 콜백 처리 (URL에 code 또는 access_token이 있는 경우)
            console.log('[AuthManager] OAuth 콜백 처리 시작');
            await this.handleOAuthCallback();
            console.log('[AuthManager] 세션 복원 시작');
            await this.restoreSession();
            console.log('[AuthManager] Auth UI 설정');
            this.setupAuthUI();
        } else {
            this.setupLocalModeUI();
        }

        console.log('[AuthManager] init() 완료, user:', this.user);
        return this.isEnabled;
    }

    // OAuth 콜백 처리
    async handleOAuthCallback() {
        const url = new URL(window.location.href);
        const hashParams = new URLSearchParams(window.location.hash.substring(1));

        console.log('[AuthManager] handleOAuthCallback - URL:', window.location.href);
        console.log('[AuthManager] handleOAuthCallback - hash:', window.location.hash);
        console.log('[AuthManager] handleOAuthCallback - search:', window.location.search);

        // Supabase는 access_token을 URL 해시에 반환
        const accessToken = hashParams.get('access_token');
        const refreshToken = hashParams.get('refresh_token');
        const expiresAt = hashParams.get('expires_at');

        if (accessToken && refreshToken) {
            // 해시에서 토큰을 찾은 경우 (implicit flow)
            this.session = {
                access_token: accessToken,
                refresh_token: refreshToken,
                expires_at: expiresAt ? parseInt(expiresAt) : null
            };
            this.saveSession();

            // URL 정리 (해시 제거)
            window.history.replaceState({}, document.title, window.location.pathname);

            // 세션 검증
            await this.verifySession();
            this.ui.showAlert('Google 로그인 성공!', 'success');
            return;
        }

        // URL 파라미터에서 code 확인 (PKCE flow)
        const code = url.searchParams.get('code');
        console.log('[AuthManager] OAuth code:', code ? '있음' : '없음');
        if (code) {
            console.log('[AuthManager] 코드를 세션으로 교환 시도');
            // code가 있으면 서버에서 토큰으로 교환해야 함
            const result = await this.exchangeCodeForSession(code);
            console.log('[AuthManager] 코드 교환 결과:', result);

            // URL 정리
            window.history.replaceState({}, document.title, window.location.pathname);

            if (result.success) {
                this.ui.showAlert('Google 로그인 성공!', 'success');
            }
        }
    }

    // 인증 코드를 세션으로 교환
    async exchangeCodeForSession(code) {
        const { ok, data } = await this._fetchJson('/api/auth/oauth/callback', {
            method: 'POST',
            body: JSON.stringify({ code })
        });

        if (ok && data.session) {
            this.user = data.user;
            this.session = data.session;
            this.saveSession();
            this.updateAuthUI(true);
            this.onAuthChange?.(true, this.user);
            return { success: true };
        }

        return { success: false, error: data.error };
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

    // ==================== 세션 관리 ====================

    async restoreSession() {
        const sessionStr = localStorage.getItem('auth_session');
        console.log('[AuthManager] restoreSession - localStorage:', sessionStr ? '있음' : '없음');
        if (!sessionStr) return;

        try {
            const session = JSON.parse(sessionStr);
            const isExpired = session.expires_at && session.expires_at * 1000 <= Date.now();
            console.log('[AuthManager] 세션 만료 여부:', isExpired, 'expires_at:', session.expires_at);

            if (isExpired) {
                console.log('[AuthManager] 토큰 갱신 시도');
                await this.refreshToken(session.refresh_token);
            } else {
                this.session = session;
                console.log('[AuthManager] 세션 검증 시도');
                await this.verifySession();
            }
        } catch (e) {
            console.error('[AuthManager] restoreSession 오류:', e);
            this.clearSession();
        }
    }

    async verifySession() {
        if (!this.session?.access_token) return;

        const { ok, data } = await this._fetchJson('/api/auth/me', {
            headers: this._getAuthHeaders()
        });

        if (ok) {
            this.user = data.user;
            this.updateAuthUI(true);
            this.onAuthChange?.(true, this.user);
        } else {
            this.clearSession();
        }
    }

    async refreshToken(refreshToken) {
        if (!refreshToken) {
            this.clearSession();
            return;
        }

        const { ok, data } = await this._fetchJson('/api/auth/refresh', {
            method: 'POST',
            body: JSON.stringify({ refresh_token: refreshToken })
        });

        if (ok) {
            this.session = data.session;
            this.saveSession();
            this.verifySession();
        } else {
            this.clearSession();
        }
    }

    saveSession() {
        if (this.session) {
            localStorage.setItem('auth_session', JSON.stringify(this.session));
        }
    }

    clearSession() {
        this.user = null;
        this.session = null;
        localStorage.removeItem('auth_session');
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
        if (this.session?.access_token) {
            await this._fetchJson('/api/auth/logout', {
                method: 'POST',
                headers: this._getAuthHeaders()
            });
        }

        this.clearSession();
        this.ui.showAlert('로그아웃되었습니다.', 'info');
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
        try {
            const redirectUrl = window.location.origin;
            const response = await fetch(`/api/auth/oauth/${provider}?redirect_url=${encodeURIComponent(redirectUrl)}`);
            const data = await response.json();

            if (response.ok && data.url) {
                window.location.href = data.url;
            } else {
                this.ui.showAlert(data.error || 'OAuth 로그인 실패', 'error');
            }
        } catch (error) {
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
