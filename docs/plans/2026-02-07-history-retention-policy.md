# 히스토리 7일 보존 정책 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 무한으로 저장되는 히스토리(ie_histories)에 7일 보존 정책을 적용하고, 프론트엔드 삭제와 클라우드 삭제를 동기화한다.

**Architecture:** 3계층 접근 - (1) 백엔드 DELETE API 추가, (2) 프론트엔드 삭제 시 클라우드 동기화, (3) pg_cron으로 매일 7일 초과 데이터 자동 정리. 삭제 실패 시 UX는 유지하고 로그만 남기는 graceful degradation 적용.

**Tech Stack:** Flask (Python), Supabase (PostgreSQL + pg_cron), Vanilla JS (ES modules)

---

### Task 1: 히스토리 삭제 API 엔드포인트 추가

**Files:**
- Modify: `routes/auth_routes.py:6-13` (import에 `delete_history` 추가)
- Modify: `routes/auth_routes.py:404` 뒤 (새 엔드포인트 추가)
- Test: `tests/test_routes_smoke.py` (수동 검증)

**Step 1: import에 `delete_history` 추가**

```python
# routes/auth_routes.py 라인 6-13
from services.supabase_service import (
    get_supabase, is_supabase_enabled, require_auth,
    save_api_keys, get_api_keys,
    save_custom_style, get_custom_styles, delete_custom_style,
    get_usage, is_admin, get_all_users_usage, reset_user_usage, get_usage_stats,
    get_all_contents, get_content_detail,
    get_histories, delete_history  # <-- 추가
)
```

**Step 2: DELETE 엔드포인트 추가**

히스토리 조회 API (`get_user_history`) 뒤, 관리자 API 섹션 앞에 추가:

```python
@auth_bp.route('/api/user/history/<report_id>', methods=['DELETE'])
@require_auth
def delete_user_history(report_id):
    """사용자 히스토리 삭제 (클라우드)

    RLS + user_id 매칭으로 본인 데이터만 삭제 가능.
    """
    if not report_id:
        return _error_response('report_id가 필요합니다.')

    if delete_history(g.user_id, report_id):
        return _success_response()
    return _error_response('삭제에 실패했습니다.', 500)
```

**Step 3: 테스트 실행**

Run: `pytest tests/test_routes_smoke.py -v -k "not test_user_history_api"`
Expected: 기존 테스트 3개 PASS

**Step 4: Commit**

```bash
git add routes/auth_routes.py
git commit -m "feat: 히스토리 삭제 API 엔드포인트 추가 (DELETE /api/user/history/<report_id>)"
```

---

### Task 2: 프론트엔드 삭제 시 클라우드 동기화

**Files:**
- Modify: `static/js/modules/report/CardEventHandler.js:14-21` (constructor에 authManager 파라미터 추가)
- Modify: `static/js/modules/report/CardEventHandler.js:218-226` (`_handleDeleteClick` + `_deleteFromCloud` 추가)
- Modify: `static/js/modules/ReportManager.js:42-48` (CardEventHandler 생성 시 authManager 전달)

**Step 1: CardEventHandler constructor에 authManager 추가**

```javascript
// CardEventHandler.js constructor
constructor(storage, uiManager, mindmapManager, onCardDelete, onCollapseChange = null, authManager = null) {
    this.storage = storage;
    this.ui = uiManager;
    this.mindmapManager = mindmapManager;
    this.onCardDelete = onCardDelete;
    this.onCollapseChange = onCollapseChange;
    this.authManager = authManager;  // <-- 추가
}
```

**Step 2: `_handleDeleteClick` 수정 + `_deleteFromCloud` 추가**

```javascript
_handleDeleteClick(card, reportId) {
    this.storage.removeFromHistory(reportId);
    this._deleteFromCloud(reportId);  // <-- 추가

    card.style.animation = 'slideOut 0.3s ease forwards';
    setTimeout(() => {
        card.remove();
        this.onCardDelete?.();
    }, 300);
}

async _deleteFromCloud(reportId) {
    if (!this.authManager?.isLoggedIn?.()) return;

    try {
        const token = this.authManager.getAccessToken?.();
        if (!token) return;

        const res = await fetch(`/api/user/history/${reportId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!res.ok) {
            console.warn(`클라우드 히스토리 삭제 실패: ${res.status}`);
        }
    } catch (e) {
        console.warn('클라우드 히스토리 삭제 중 오류:', e);
    }
}
```

**Step 3: ReportManager에서 authManager 전달**

```javascript
// ReportManager.js 라인 42-48
this.eventHandler = new CardEventHandler(
    storage,
    uiManager,
    null,
    () => this._checkEmptyState(),
    () => this.syncCollapseAllButtonState(),
    authManager  // <-- 추가 (6번째 인자)
);
```

**Step 4: 수동 검증**

1. 앱 실행: `python app.py`
2. 로그인 후 카드 삭제 → 브라우저 DevTools Network 탭에서 `DELETE /api/user/history/xxx` 요청 확인
3. 로그아웃/재로그인 → 삭제한 카드가 다시 나타나지 않는지 확인

**Step 5: Commit**

```bash
git add static/js/modules/report/CardEventHandler.js static/js/modules/ReportManager.js
git commit -m "feat: 카드 삭제 시 클라우드 히스토리도 동기 삭제"
```

---

### Task 3: DB 크론잡 - 7일 자동 정리

**Files:**
- Modify: `supabase/schema.sql` (문서화용 SQL 함수 추가)
- Modify: `config.py:38` 뒤 (`HISTORY_RETENTION_DAYS` 상수 추가)

**Step 1: config.py에 보존 기간 상수 추가**

```python
# config.py - Token Limits 섹션 뒤
HISTORY_RETENTION_DAYS: int = 7
```

**Step 2: schema.sql에 SQL 함수 문서화**

`reset_daily_usage()` 함수 뒤, "완료!" 섹션 앞에 추가:

```sql
-- =============================================
-- 8. RPC 함수: 만료 히스토리 자동 삭제 (7일 보존)
-- =============================================

CREATE OR REPLACE FUNCTION cleanup_expired_histories()
RETURNS INT
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    v_count INT;
BEGIN
    DELETE FROM ie_histories
    WHERE created_at < NOW() - INTERVAL '7 days';

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$ LANGUAGE plpgsql;

-- pg_cron 스케줄 등록 (Supabase Dashboard > Database > Extensions에서 pg_cron 활성화 필요)
-- 매일 새벽 3시(UTC)에 실행:
-- SELECT cron.schedule('cleanup-expired-histories', '0 3 * * *', $$SELECT cleanup_expired_histories()$$);
```

**Step 3: Supabase에서 SQL 실행 (수동)**

Supabase SQL Editor 또는 MCP 도구에서:

```sql
-- 1. 함수 생성
CREATE OR REPLACE FUNCTION cleanup_expired_histories() ...;

-- 2. 크론잡 등록
SELECT cron.schedule('cleanup-expired-histories', '0 3 * * *', $$SELECT cleanup_expired_histories()$$);

-- 3. 초기 정리 (즉시 실행)
SELECT cleanup_expired_histories();
```

**Step 4: 등록 확인**

```sql
SELECT jobid, schedule, command, active FROM cron.job WHERE jobname = 'cleanup-expired-histories';
-- Expected: active = true, schedule = '0 3 * * *'
```

**Step 5: Commit**

```bash
git add config.py supabase/schema.sql
git commit -m "feat: 히스토리 7일 보존 정책 (cleanup_expired_histories + pg_cron)"
```

---

## 구현 확인 체크리스트

- [ ] `DELETE /api/user/history/<report_id>` 엔드포인트가 200 반환
- [ ] 프론트에서 카드 삭제 시 Network 탭에 DELETE 요청 확인
- [ ] 로그아웃/재로그인 후 삭제한 카드 미노출
- [ ] 비로그인 상태 삭제 시 클라우드 API 호출 안 함
- [ ] `cron.job` 테이블에 스케줄 active = true
- [ ] `cleanup_expired_histories()` 수동 실행 시 7일 초과 데이터 삭제됨
