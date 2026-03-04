# 6-Agent Code Review Summary (2026-03-02)

## Scope
- Workspace: `E:\자동화 프로젝트\250705_스마트 콘텐츠 생성기(완성)`
- Review mode: 5 parallel explorer agents + final merge
- Focus areas:
  - Functional regression
  - Error handling and stability
  - Security
  - Performance
  - Test quality

## Critical Findings

### 1) Auth bypass risk (require_auth effectively disabled)
- Files:
  - `services/supabase_service.py:42`
  - `services/supabase_service.py:176`
- Issue:
  - `is_supabase_enabled()` returns `False`, so auth gates can become ineffective.
- Impact:
  - Unauthorized access to protected APIs and paid resources.
- Recommended fix:
  - Restore env-based enable logic and fail-closed in production.

### 2) Usage decrement likely not applied in fusion flow
- Files:
  - `routes/advanced_routes.py:202`
  - `services/usage/usage_service.py:62`
- Issue:
  - `UsageService.decrement(g.usage.get('user_id'))` may pass `None`.
- Impact:
  - Successful requests may not consume quota.
- Recommended fix:
  - Use `g.user_id` (or `require_usage`) and remove ambiguous decrement path.

### 3) Secondary exception in error handler path
- Files:
  - `routes/advanced_routes.py:210`
  - `utils/responses.py:70`
- Issue:
  - Passing `Exception` object into `handle_error` can trigger another exception.
- Impact:
  - Original error is masked and response quality degrades.
- Recommended fix:
  - Convert to string before handling (`handle_error(str(e))`) and normalize in handler.

## High Findings

### 4) SSRF exposure on user-provided URLs
- Files:
  - `routes/blog_routes.py:210`
  - `services/multi_source_collector.py:183`
  - `services/web_scraper_service.py:108`
- Issue:
  - Server fetches user URLs without internal network guardrails.
- Recommended fix:
  - Block private/link-local/metadata ranges, restrict schemes/ports, enforce outbound policy.

### 5) XSS risk via unsanitized HTML rendering
- Files:
  - `routes/auth_routes.py:446`
  - `frontend/components/result/ResultCard.tsx:142`
  - `frontend/hooks/useExport.ts:66`
- Issue:
  - Stored HTML is rendered with `document.write` without sanitization.
- Recommended fix:
  - Sanitize on server and client, remove script/event attributes, avoid raw HTML rendering where possible.

### 6) Plaintext API key storage fallback
- Files:
  - `services/supabase_service.py:68`
  - `services/supabase_service.py:105`
  - `services/supabase_service.py:443`
- Issue:
  - Missing `ENCRYPTION_SECRET` can lead to plaintext key storage.
- Recommended fix:
  - Make encryption secret mandatory in production and block storage if unavailable.

### 7) Cache clear API contract mismatch (frontend vs backend)
- Files:
  - `frontend/lib/api.ts:223`
  - `routes/utility_routes.py:87`
- Issue:
  - Frontend calls `POST /api/cache/clear`, backend exposes `DELETE /api/cache`.
- Recommended fix:
  - Align method/path on one contract and add a contract test.

### 8) Unauthenticated cache deletion endpoint
- File:
  - `routes/utility_routes.py:87`
- Issue:
  - Cache clear endpoint is accessible without auth.
- Recommended fix:
  - Add `@require_auth` (and admin guard if needed).

### 9) Transcript return type assumption causes 500
- File:
  - `routes/blog_routes.py:1182`
- Issue:
  - Code assumes dict; service can return string.
- Recommended fix:
  - Add dict/string branching (same pattern as other route path).

### 10) GLM retry lock contention
- File:
  - `services/ai_service.py:310`
- Issue:
  - `sleep` occurs while holding global lock.
- Impact:
  - Requests become serialized under failure/retry scenarios.
- Recommended fix:
  - Lock only around provider call, move retry wait outside lock.

## Medium Findings

### 11) JSON null/non-JSON input can return 500
- File:
  - `routes/advanced_routes.py:174`
- Recommended fix:
  - `request.get_json(silent=True) or {}` + explicit dict validation + 400 response.

### 12) Invalid numeric input mapped to 500 instead of 400
- File:
  - `routes/utility_routes.py:281`
- Recommended fix:
  - Catch `ValueError` and return 400 with range validation.

### 13) Function signature mismatch silently swallowed
- Files:
  - `services/fusion_service.py:63`
  - `services/content_service.py:727`
- Recommended fix:
  - Align function signature and log warnings instead of broad silent pass.

### 14) Missing timeout controls in network/LLM calls
- Files:
  - `services/web_research_service.py:58`
  - `services/video_qa_service.py:258`
- Recommended fix:
  - Add per-call timeout + overall timeout and map timeout errors to 503/504.

### 15) Test quality gaps reduce signal
- Files:
  - `tests/e2e/core-flow/user-journey.spec.ts:105` (always-true assertion)
  - `tests/web_feature_test.py:21` (not pytest-collected)
  - `tests/e2e/responsive/ui-quality.spec.ts:47` (fixed sleeps, flaky risk)
- Recommended fix:
  - Replace weak assertions, convert script tests to real suite tests, remove fixed sleeps.

## Immediate Priority Order
1. Fix auth bypass (`is_supabase_enabled`) and enforce fail-closed.
2. Fix usage decrement path in fusion route.
3. Patch SSRF and XSS surfaces.
4. Protect cache-clear endpoint and align frontend/backend API contract.
5. Stabilize critical error/input handling paths (`handle_error`, JSON parsing).

## Notes
- No code changes were applied in this review pass.
- This document is a merged summary of parallel agent findings with duplicates removed.
