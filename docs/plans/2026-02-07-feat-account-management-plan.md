# 계정관리 기능 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 로그인 사용자를 위한 계정관리 모달 구현 - 프로필(닉네임) 변경, 비밀번호 변경, 계정 삭제(즉시 완전 삭제)

**Architecture:** 3계층 접근 - (1) 백엔드 계정 삭제 API (admin.deleteUser는 service_role 필수), (2) 프론트엔드 계정관리 모달 (기존 auth-modal 패턴 재활용), (3) 프로필/비밀번호는 Supabase JS SDK 직접 호출 (백엔드 불필요). OAuth 사용자는 비밀번호 변경 비활성화.

**Tech Stack:** Flask (Python), Supabase Auth (JS SDK + Python admin), Vanilla JS (ES modules), Tailwind CSS

---

## Overview

사용자가 사이드바에서 계정관리 모달을 열어 닉네임 변경, 비밀번호 변경, 계정 삭제를 수행할 수 있다. 기존 `auth-modal` HTML/CSS 패턴을 재활용하고, `AuthManager.js`에 계정관리 메서드를 추가한다.

## Proposed Solution

| 기능 | 처리 위치 | API |
|------|----------|-----|
| 닉네임 변경 | 프론트엔드 SDK | `supabaseClient.auth.updateUser({ data: { display_name } })` |
| 비밀번호 변경 | 프론트엔드 SDK | `supabaseClient.auth.updateUser({ password })` |
| 계정 삭제 | 백엔드 API → admin SDK | `DELETE /api/user/account` → `admin.deleteUser(userId)` |

## Technical Considerations

- **계정 삭제는 service_role key 필수**: `SUPABASE_SERVICE_ROLE_KEY` 환경변수 추가 필요. admin client는 기존 anon client와 별도로 초기화.
- **CASCADE 삭제**: `ie_usage`, `ie_histories`, `ie_api_keys`, `ie_custom_styles` 모두 `ON DELETE CASCADE`로 설정되어 있어 `auth.users` 삭제 시 자동 정리됨.
- **JWT 유효기간**: Supabase 문서에 따르면 `deleteUser` 후에도 JWT가 만료될 때까지 유효. 프론트에서 즉시 로그아웃 + localStorage 정리 필수.
- **OAuth 사용자**: `user.app_metadata.provider`가 `email`이 아닌 경우 비밀번호 변경 섹션 비활성화.
- **Storage 주의**: Supabase Storage 오브젝트 소유 사용자는 삭제 불가 → 이 프로젝트는 Storage 미사용이므로 해당 없음.

## Acceptance Criteria

- [ ] 로그인 상태에서 사이드바 클릭 시 계정관리 모달 열림
- [ ] 비로그인 상태에서는 기존처럼 로그인 모달 열림
- [ ] 닉네임 변경 후 사이드바에 새 닉네임 반영
- [ ] 비밀번호 변경 성공 시 알림 표시
- [ ] OAuth 사용자는 비밀번호 변경 영역 비활성화 (안내 메시지 표시)
- [ ] "계정삭제" 입력 시에만 삭제 버튼 활성화
- [ ] 계정 삭제 후 모든 데이터 제거, 로그아웃, 메인 페이지 리다이렉트
- [ ] 기존 smoke 테스트 통과 (3/3)

---

### Task 1: 백엔드 - 계정 삭제 API

**Files:**
- Modify: `services/supabase_service.py` (admin client 초기화 + `delete_user_account` 함수)
- Modify: `routes/auth_routes.py` (import 추가 + DELETE 엔드포인트)

**Step 1: `supabase_service.py`에 admin client + 삭제 함수 추가**

기존 `get_supabase()` 아래에 admin client 싱글톤 추가:

```python
# Admin 클라이언트 (service_role key 사용 - 계정 삭제 등)
_supabase_admin: Client = None

def _get_admin_client() -> Client:
    """Supabase Admin 클라이언트 (service_role key)"""
    global _supabase_admin

    if _supabase_admin is None:
        url = os.getenv('SUPABASE_URL')
        service_role_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY')

        if not url or not service_role_key:
            logger.warning("SUPABASE_SERVICE_ROLE_KEY 미설정 - admin 기능 비활성화")
            return None

        _supabase_admin = create_client(url, service_role_key)

    return _supabase_admin
```

삭제 함수:

```python
def delete_user_account(user_id: str) -> bool:
    """사용자 계정 완전 삭제 (admin)

    auth.users 삭제 → CASCADE로 ie_* 테이블 자동 정리.
    """
    try:
        admin = _get_admin_client()
        if not admin:
            logger.error("Admin client 미초기화 - 계정 삭제 불가")
            return False

        admin.auth.admin.delete_user(user_id)
        logger.info(f"계정 삭제 완료: user_id={user_id}")
        return True
    except Exception as e:
        logger.error(f"계정 삭제 실패: user_id={user_id}, error={e}")
        return False
```

**Step 2: `auth_routes.py`에 import + 엔드포인트 추가**

import에 `delete_user_account` 추가:

```python
from services.supabase_service import (
    get_supabase, is_supabase_enabled, require_auth,
    save_api_keys, get_api_keys,
    save_custom_style, get_custom_styles, delete_custom_style,
    get_usage, is_admin, get_all_users_usage, reset_user_usage, get_usage_stats,
    get_all_contents, get_content_detail,
    get_histories, delete_history, delete_user_account  # <-- 추가
)
```

히스토리 삭제 API 뒤에 계정 삭제 엔드포인트 추가:

```python
@auth_bp.route('/api/user/account', methods=['DELETE'])
@require_auth
def delete_account():
    """사용자 계정 완전 삭제

    auth.users 삭제 → CASCADE로 모든 사용자 데이터 자동 정리.
    """
    if delete_user_account(g.user_id):
        return _success_response({'message': '계정이 삭제되었습니다.'})
    return _error_response('계정 삭제에 실패했습니다.', 500)
```

**Step 3: `.env.example`에 SERVICE_ROLE_KEY 항목 추가**

```
# Supabase Admin (계정 삭제 기능에 필요)
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
```

**Step 4: 기존 테스트 실행**

Run: `pytest tests/test_routes_smoke.py -v -k "not test_user_history_api"`
Expected: 기존 테스트 3개 PASS

**Step 5: Commit**

```bash
git add services/supabase_service.py routes/auth_routes.py .env.example
git commit -m "feat: 계정 삭제 API 추가 (DELETE /api/user/account)"
```

---

### Task 2: 프론트엔드 - 계정관리 모달 HTML

**Files:**
- Modify: `templates/index.html` (account-modal HTML 추가 + 사이드바 수정)

**Step 1: 사이드바에 계정관리 버튼 추가**

기존 `sidebar-auth-container` 위에 계정관리 버튼 추가 (로그인 시에만 표시):

```html
<!-- User Profile / Auth (Bottom) -->
<div class="p-3 border-t border-border-dark">
    <!-- 계정관리 버튼 (로그인 시에만 표시) -->
    <button id="sidebar-account-btn" class="nav-icon-btn hidden" title="계정관리" aria-label="계정관리">
        <span class="material-symbols-outlined" aria-hidden="true">manage_accounts</span>
        <span class="nav-label">계정관리</span>
    </button>
    <!-- 로그인/로그아웃 -->
    <button id="sidebar-auth-container" class="nav-icon-btn" title="로그인" aria-label="로그인">
        <span id="sidebar-auth-icon" class="material-symbols-outlined" aria-hidden="true">person</span>
        <span id="sidebar-auth-label" class="nav-label">로그인</span>
    </button>
</div>
```

**Step 2: account-modal HTML 추가**

`auth-modal` 뒤에 추가. 기존 모달 패턴(`.modal-overlay` + `.modal-content`) 재활용:

```html
<!-- Account Management Modal -->
<div class="modal-overlay" id="account-modal" role="dialog" aria-modal="true" aria-labelledby="account-modal-title">
    <div class="modal-content p-6" style="max-width: 440px;">
        <div class="flex items-center justify-between mb-6">
            <h2 id="account-modal-title" class="text-xl font-bold flex items-center gap-2">
                <span class="material-symbols-outlined text-primary" aria-hidden="true">manage_accounts</span>
                계정관리
            </h2>
            <button id="account-modal-close" class="modal-close-btn" aria-label="계정관리 창 닫기" title="닫기 (ESC)">
                <span class="material-symbols-outlined" aria-hidden="true">close</span>
            </button>
        </div>

        <!-- 프로필 섹션 -->
        <div class="space-y-4 mb-6">
            <h3 class="text-sm font-semibold text-text-subtle flex items-center gap-1">
                <span class="material-symbols-outlined text-sm" aria-hidden="true">person</span>
                프로필
            </h3>
            <div>
                <label class="block text-xs text-text-subtle mb-2">이메일</label>
                <input type="email" id="account-email" class="w-full bg-background-dark/50 border border-border-dark rounded-lg px-4 py-3 text-sm text-text-subtle cursor-not-allowed" disabled>
            </div>
            <div>
                <label class="block text-xs text-text-subtle mb-2">닉네임</label>
                <input type="text" id="account-display-name" class="w-full bg-background-dark border border-border-dark rounded-lg px-4 py-3 text-sm text-warm-white focus:border-primary focus:outline-none transition-colors" placeholder="닉네임 입력 (최대 20자)" maxlength="20">
            </div>
            <button id="account-save-profile" class="w-full bg-gradient-to-r from-primary to-primary-glow text-background-dark font-semibold py-2.5 rounded-lg hover:opacity-90 transition-opacity text-sm">
                프로필 저장
            </button>
        </div>

        <hr class="border-border-dark mb-6">

        <!-- 비밀번호 변경 섹션 -->
        <div id="account-password-section" class="space-y-4 mb-6">
            <h3 class="text-sm font-semibold text-text-subtle flex items-center gap-1">
                <span class="material-symbols-outlined text-sm" aria-hidden="true">lock</span>
                비밀번호 변경
            </h3>
            <div>
                <label class="block text-xs text-text-subtle mb-2">새 비밀번호</label>
                <input type="password" id="account-new-password" class="w-full bg-background-dark border border-border-dark rounded-lg px-4 py-3 text-sm text-warm-white focus:border-primary focus:outline-none transition-colors" placeholder="6자 이상">
            </div>
            <div>
                <label class="block text-xs text-text-subtle mb-2">새 비밀번호 확인</label>
                <input type="password" id="account-confirm-password" class="w-full bg-background-dark border border-border-dark rounded-lg px-4 py-3 text-sm text-warm-white focus:border-primary focus:outline-none transition-colors" placeholder="비밀번호 재입력">
            </div>
            <button id="account-change-password" class="w-full bg-gradient-to-r from-primary to-primary-glow text-background-dark font-semibold py-2.5 rounded-lg hover:opacity-90 transition-opacity text-sm">
                비밀번호 변경
            </button>
        </div>

        <!-- OAuth 사용자 안내 (비밀번호 변경 대체) -->
        <div id="account-oauth-notice" class="mb-6 hidden">
            <h3 class="text-sm font-semibold text-text-subtle flex items-center gap-1 mb-3">
                <span class="material-symbols-outlined text-sm" aria-hidden="true">lock</span>
                비밀번호 변경
            </h3>
            <p class="text-xs text-text-subtle bg-background-dark/50 rounded-lg p-4">
                소셜 로그인(Google 등)으로 가입한 계정은 비밀번호 변경이 불가합니다. 해당 소셜 서비스에서 비밀번호를 관리해주세요.
            </p>
        </div>

        <hr class="border-border-dark mb-6">

        <!-- 계정 삭제 섹션 -->
        <div class="space-y-4">
            <h3 class="text-sm font-semibold text-red-400 flex items-center gap-1">
                <span class="material-symbols-outlined text-sm" aria-hidden="true">warning</span>
                계정 삭제
            </h3>
            <p class="text-xs text-text-subtle">
                계정을 삭제하면 모든 데이터(히스토리, API 키, 커스텀 스타일)가 <strong class="text-red-400">즉시 영구 삭제</strong>되며 복구할 수 없습니다.
            </p>
            <div>
                <label class="block text-xs text-text-subtle mb-2">확인을 위해 <strong class="text-red-400">계정삭제</strong>를 입력하세요</label>
                <input type="text" id="account-delete-confirm" class="w-full bg-background-dark border border-red-900/50 rounded-lg px-4 py-3 text-sm text-warm-white focus:border-red-500 focus:outline-none transition-colors" placeholder="계정삭제">
            </div>
            <button id="account-delete-btn" class="w-full bg-red-600/20 text-red-400 border border-red-600/30 font-semibold py-2.5 rounded-lg transition-all text-sm opacity-50 cursor-not-allowed" disabled>
                계정 영구 삭제
            </button>
        </div>
    </div>
</div>
```

**Step 3: Commit**

```bash
git add templates/index.html
git commit -m "feat: 계정관리 모달 HTML + 사이드바 버튼 추가"
```

---

### Task 3: 프론트엔드 - 계정관리 JS 로직

**Files:**
- Modify: `static/js/modules/AuthManager.js` (계정관리 메서드 추가)
- Modify: `templates/index.html` (사이드바 클릭 핸들러 수정 + 계정관리 이벤트 바인딩)

**Step 1: AuthManager에 계정관리 메서드 추가**

`resetPassword()` 메서드 뒤, `oauthLogin()` 앞에 추가:

```javascript
// ==================== 계정관리 ====================

async updateDisplayName(displayName) {
    if (!this.supabaseClient) return { success: false, error: '인증 서비스 미초기화' };

    try {
        const { data, error } = await this.supabaseClient.auth.updateUser({
            data: { display_name: displayName }
        });
        if (error) throw error;

        this.user = data.user;
        this.updateAuthUI(true);
        return { success: true };
    } catch (e) {
        console.error('[AuthManager] 닉네임 변경 실패:', e);
        return { success: false, error: e.message };
    }
}

async changePassword(newPassword) {
    if (!this.supabaseClient) return { success: false, error: '인증 서비스 미초기화' };

    try {
        const { data, error } = await this.supabaseClient.auth.updateUser({
            password: newPassword
        });
        if (error) throw error;
        return { success: true };
    } catch (e) {
        console.error('[AuthManager] 비밀번호 변경 실패:', e);
        return { success: false, error: e.message };
    }
}

async deleteAccount() {
    if (!this.isLoggedIn()) return { success: false, error: '로그인 필요' };

    try {
        const token = this.getAccessToken();
        const res = await fetch('/api/user/account', {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || '계정 삭제 실패');

        // 로그아웃 + 세션 정리
        if (this.supabaseClient) {
            await this.supabaseClient.auth.signOut();
        }
        this.clearSession();
        localStorage.clear();
        return { success: true };
    } catch (e) {
        console.error('[AuthManager] 계정 삭제 실패:', e);
        return { success: false, error: e.message };
    }
}

isOAuthUser() {
    const provider = this.user?.app_metadata?.provider;
    return provider && provider !== 'email';
}

getDisplayName() {
    return this.user?.user_metadata?.display_name
        || this.user?.email?.split('@')[0]
        || '사용자';
}
```

**Step 2: `updateSidebarAuthUI` 수정 - 닉네임 표시 + 계정관리 버튼 제어**

기존 `updateSidebarAuthUI` 메서드의 로그인 상태 부분 수정:

```javascript
updateSidebarAuthUI(isLoggedIn) {
    const container = document.getElementById('sidebar-auth-container');
    const icon = document.getElementById('sidebar-auth-icon');
    const label = document.getElementById('sidebar-auth-label');
    const accountBtn = document.getElementById('sidebar-account-btn');

    if (!container || !icon || !label) return;

    // 계정관리 버튼 표시/숨김
    accountBtn?.classList.toggle('hidden', !isLoggedIn);

    if (isLoggedIn) {
        const displayName = this.getDisplayName();
        icon.textContent = 'account_circle';
        label.textContent = displayName;
        container.title = this.user?.email || '';
        container.setAttribute('aria-label', `${this.user?.email} - 클릭하여 로그아웃`);
    } else {
        icon.textContent = 'person';
        label.textContent = '로그인';
        container.title = '로그인';
        container.setAttribute('aria-label', '로그인');
    }
}
```

**Step 3: `index.html` 스크립트 수정 - 계정관리 모달 이벤트**

기존 sidebar-auth-container 이벤트 아래에 추가:

```javascript
// 계정관리 버튼 클릭
document.getElementById('sidebar-account-btn')?.addEventListener('click', () => {
    const authManager = window.app?.authManager;
    if (!authManager?.isLoggedIn?.()) return;

    const modal = document.getElementById('account-modal');
    if (!modal) return;

    // 모달 데이터 채우기
    document.getElementById('account-email').value = authManager.user?.email || '';
    document.getElementById('account-display-name').value = authManager.getDisplayName();

    // OAuth 사용자 비밀번호 섹션 토글
    const isOAuth = authManager.isOAuthUser();
    document.getElementById('account-password-section')?.classList.toggle('hidden', isOAuth);
    document.getElementById('account-oauth-notice')?.classList.toggle('hidden', !isOAuth);

    // 입력 필드 초기화
    document.getElementById('account-new-password').value = '';
    document.getElementById('account-confirm-password').value = '';
    document.getElementById('account-delete-confirm').value = '';
    const deleteBtn = document.getElementById('account-delete-btn');
    if (deleteBtn) { deleteBtn.disabled = true; deleteBtn.classList.add('opacity-50', 'cursor-not-allowed'); }

    // 모바일: 사이드바 닫기 후 모달
    if (window.innerWidth < 1024) {
        toggleSidebar();
        setTimeout(() => modal.classList.add('active'), 320);
    } else {
        modal.classList.add('active');
    }
});

// 계정관리 모달 닫기
document.getElementById('account-modal-close')?.addEventListener('click', () => {
    document.getElementById('account-modal')?.classList.remove('active');
});
document.getElementById('account-modal')?.addEventListener('click', (e) => {
    if (e.target.id === 'account-modal') e.target.classList.remove('active');
});

// 프로필 저장
document.getElementById('account-save-profile')?.addEventListener('click', async () => {
    const name = document.getElementById('account-display-name')?.value?.trim();
    if (!name || name.length < 1 || name.length > 20) {
        window.app?.uiManager?.showAlert('닉네임은 1~20자로 입력해주세요.', 'warning');
        return;
    }
    const btn = document.getElementById('account-save-profile');
    btn.disabled = true; btn.textContent = '저장 중...';

    const result = await window.app?.authManager?.updateDisplayName(name);
    btn.disabled = false; btn.textContent = '프로필 저장';

    if (result?.success) {
        window.app?.uiManager?.showAlert('프로필이 저장되었습니다.', 'success');
    } else {
        window.app?.uiManager?.showAlert(result?.error || '저장 실패', 'error');
    }
});

// 비밀번호 변경
document.getElementById('account-change-password')?.addEventListener('click', async () => {
    const newPw = document.getElementById('account-new-password')?.value;
    const confirmPw = document.getElementById('account-confirm-password')?.value;

    if (!newPw || newPw.length < 6) {
        window.app?.uiManager?.showAlert('비밀번호는 6자 이상이어야 합니다.', 'warning');
        return;
    }
    if (newPw !== confirmPw) {
        window.app?.uiManager?.showAlert('비밀번호가 일치하지 않습니다.', 'warning');
        return;
    }

    const btn = document.getElementById('account-change-password');
    btn.disabled = true; btn.textContent = '변경 중...';

    const result = await window.app?.authManager?.changePassword(newPw);
    btn.disabled = false; btn.textContent = '비밀번호 변경';

    if (result?.success) {
        window.app?.uiManager?.showAlert('비밀번호가 변경되었습니다.', 'success');
        document.getElementById('account-new-password').value = '';
        document.getElementById('account-confirm-password').value = '';
    } else {
        window.app?.uiManager?.showAlert(result?.error || '비밀번호 변경 실패', 'error');
    }
});

// 계정 삭제 확인 입력 감시
document.getElementById('account-delete-confirm')?.addEventListener('input', (e) => {
    const isMatch = e.target.value.trim() === '계정삭제';
    const btn = document.getElementById('account-delete-btn');
    if (btn) {
        btn.disabled = !isMatch;
        btn.classList.toggle('opacity-50', !isMatch);
        btn.classList.toggle('cursor-not-allowed', !isMatch);
        btn.classList.toggle('hover:bg-red-600/40', isMatch);
    }
});

// 계정 삭제 실행
document.getElementById('account-delete-btn')?.addEventListener('click', async () => {
    if (document.getElementById('account-delete-confirm')?.value?.trim() !== '계정삭제') return;

    const btn = document.getElementById('account-delete-btn');
    btn.disabled = true; btn.textContent = '삭제 중...';

    const result = await window.app?.authManager?.deleteAccount();
    if (result?.success) {
        document.getElementById('account-modal')?.classList.remove('active');
        window.app?.uiManager?.showAlert('계정이 삭제되었습니다.', 'info');
        setTimeout(() => { window.location.href = '/'; }, 1500);
    } else {
        btn.disabled = false; btn.textContent = '계정 영구 삭제';
        window.app?.uiManager?.showAlert(result?.error || '계정 삭제 실패', 'error');
    }
});
```

**Step 4: ModalManager의 ESC 핸들러에 account-modal 추가**

`static/js/modules/ModalManager.js`의 `closeActiveModal()` 우선순위에 `account-modal` 추가:

```javascript
// closeActiveModal() 내부 - auth-modal 앞에 추가
const accountModal = document.getElementById('account-modal');
if (accountModal?.classList.contains('active')) {
    accountModal.classList.remove('active');
    return;
}
```

**Step 5: Commit**

```bash
git add static/js/modules/AuthManager.js templates/index.html static/js/modules/ModalManager.js
git commit -m "feat: 계정관리 모달 JS 로직 (프로필/비밀번호/삭제)"
```

---

### Task 4: 검증 및 마무리

**Step 1: 기존 테스트 실행**

Run: `pytest tests/test_routes_smoke.py -v -k "not test_user_history_api"`
Expected: 기존 테스트 3개 PASS

**Step 2: 수동 검증 체크리스트**

1. 앱 실행: `python app.py`
2. 비로그인 상태 → 사이드바 클릭 → 로그인 모달 열림 (기존 동작 유지)
3. 로그인 → 사이드바에 계정관리 버튼 표시됨
4. 계정관리 클릭 → 모달 열림, 이메일/닉네임 표시
5. 닉네임 변경 → 저장 → 사이드바에 새 닉네임 반영
6. 비밀번호 변경 → 6자 미만 → 경고 / 불일치 → 경고 / 정상 → 성공 알림
7. OAuth 사용자 → 비밀번호 변경 섹션 비활성화 + 안내 문구 표시
8. 계정삭제 입력 → 삭제 버튼 활성화 → 삭제 → 로그아웃 + 리다이렉트
9. ESC 키 → 모달 닫힘
10. 모달 배경 클릭 → 모달 닫힘

**Step 3: 최종 Commit**

```bash
git add -A
git commit -m "feat: 계정관리 기능 완성 (프로필/비밀번호 변경, 계정 삭제)"
```

---

## Dependencies & Risks

| 항목 | 위험도 | 대응 |
|------|--------|------|
| `SUPABASE_SERVICE_ROLE_KEY` 미설정 | 중 | `_get_admin_client()` null 반환 → 500 에러 + 로그 경고 |
| JWT 만료 전 재사용 | 낮 | 프론트에서 즉시 signOut + localStorage.clear() |
| CASCADE 삭제 실패 | 매우 낮 | Supabase 내장 기능, 스키마에 이미 설정됨 |
| OAuth 제공자 판별 오류 | 낮 | `app_metadata.provider` 미존재 시 email로 간주 |

## References

- Supabase `deleteUser()`: https://supabase.com/docs/reference/javascript/auth-admin-deleteuser
- Supabase `updateUser()`: https://supabase.com/docs/reference/javascript/auth-updateuser
- Supabase User Management: https://supabase.com/docs/guides/auth/managing-user-data
- 기존 auth-modal 패턴: `templates/index.html:322-421`
- AuthManager: `static/js/modules/AuthManager.js`
- supabase_service: `services/supabase_service.py`
- RLS + CASCADE: `supabase/schema.sql:114-193`
