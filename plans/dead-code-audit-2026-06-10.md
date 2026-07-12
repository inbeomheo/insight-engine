# 데드코드 감사 결과 (2026-06-10)

멀티에이전트 감사(에이전트 52개)로 소비자 없는 엔드포인트/모듈/의존성 354건을 발굴하고,
각 후보를 적대적 검증(동적 import, url_for, 프론트엔드/확장/n8n/문서/배포설정/OpenAPI 전수 grep)했다.

## 2026-07-12 갱신 — 사용자 스니펫 잔여 체인 제거

- 프론트 소비 0으로 재검증된 `GET/POST /api/user/snippets`, `DELETE /api/user/snippets/<snippet_id>`와 전용 `snippet_facade`, Supabase CRUD 헬퍼, 전용 테스트를 제거.
- `supabase/migrations/003_snippets.sql`과 기존 DB 테이블·정책은 적용 이력 및 데이터 보존을 위해 수정하지 않음.

## 2026-07-05 갱신 (dev-loop cycle 27b)

- `routes/advanced_routes.py` 9건은 재검증 결과 이미 PR #81(Dep-2 batch 1, 2026-07-04)에서 라우트 자체가 제거되어 있었음. 이번 배치는 해당 라우트가 유일하게 호출하던 orphan 서비스 `services/finetune/`(data_collector, dataset_builder, reward_model) + 전용 테스트 3개를 제거.
- 파일 존재 재검사 결과 아래 그룹은 파일 자체가 트리에서 사라져 이미 삭제 완료된 것으로 확인(이후 사이클에서 처리됨). 목록은 이력 보존을 위해 남기되 "완료" 표기만 추가: `routes/advanced/rewrite.py`, `routes/analytics_routes.py`, `routes/blog/voice_capture.py`, `routes/content_mgmt/trash_pin.py`, `routes/integrations/workflow.py`, `routes/utility/content_evaluation.py`, `routes/utility/content_meta.py`, `routes/utility/generation.py`, `routes/utility/seo_aeo.py`, `routes/utility/text_quality.py`, `routes/utility/text_structure.py`.
- 그 외 그룹(auth/*, content_mgmt*, integrations/automation·content_workspace·imports·knowledge·misc, marketplace_routes.py, payment*, utility/external·feedback_quality·operations 등)은 파일이 여전히 존재하며 개별 엔드포인트 재검증은 이번 배치 범위 밖 — 다음 배치에서 재확인 필요.

## 2026-07-05 갱신 2 (dev-loop cycle 28b, batch 3)

payment/marketplace 그룹을 제외한 잔여 그룹을 파일 존재 여부 + 엔드포인트 단위로 재검증(약 1개월 경과로 코드가 이미 크게 재구성됨):

- **routes/content_mgmt_routes.py + routes/content_mgmt/backup_io.py (실제 54건, 목록 45건 대비 `GET/PATCH/DELETE /api/content/<item_id>` 3건 + `POST /api/content/bulk` 1건 누락 확인 — 전부 소비자 0 재확인)**: 전 엔드포인트 삭제, 파일 자체 삭제(라우트가 파일의 전부였음), app.py의 `content_mgmt_bp` 등록 제거. 연쇄 orphan 서비스 15개 삭제: `services/data/{content_library,archive,lock,expiry,custom_field,workflow,rbac,backup,data_migration,trash}_service.py`, `services/media/media_library_service.py`, `services/seo/{link_manager,seo_checklist}_service.py`, `services/platform/share_service.py`, `services/content/comment_service.py`. 전용 테스트 16개 삭제. `POST /api/content/bulk`의 유일한 프론트 참조는 `frontend/components/library/BulkActions.tsx`인데 이 컴포넌트 자체가 어디에서도 import되지 않는 죽은 컴포넌트임을 확인(참고로만 기록, 프론트 정리는 이번 배치 범위 밖이라 손대지 않음).
- **routes/integrations/knowledge.py (5건 중 4건)**: `POST /api/rag/graph/search/local`, `GET /api/rag/graph/search/global`, `POST /api/rag/multimodal/{detect-type,ingest,query}` 제거(5건 목록이었으나 detect-type/ingest/query 3개가 1그룹이라 실질 4개 라우트). `POST /api/rag/graph/ingest`는 기존 유지 판정 그대로 보존. `GraphRAGEngine.global_search` 메서드 제거(local_search는 build_context가 내부 호출하므로 유지), `services/rag/multimodal_rag.py` 전체 삭제(오직 이 3개 라우트만 사용). 관련 테스트 정리: `tests/test_multimodal_rag_routes.py` 삭제, `tests/test_graph_rag_routes.py`/`tests/test_graph_rag_engine.py`에서 제거된 라우트/메서드 테스트만 삭제.
- **[완료: 재검증 결과 이미 삭제됨]** 아래 그룹은 감사 당시(2026-06-10) 존재했던 특정 엔드포인트가 현재 코드에 없음을 확인(파일 자체는 남아있으나 내용이 다른 활성 기능으로 대체됨 — 별도 조치 불필요):
  - `routes/auth_routes.py`의 `GET /api/auth/status`, `GET /api/auth/config` — **[완료: 2026-07-05 cycle 29a 삭제]** (auth/* 그룹 전체는 dev-loop cycle 29a에서 일괄 삭제 완료. 상세는 아래 개별 섹션 참조)
  - `routes/integrations/automation.py`의 8건(`/api/sync/airtable`, `/api/sync/gsheets`, `/api/integrations/discord/*`, `/api/integrations/slack/*`) — 모두 삭제됨, 파일은 현재 Slack/Discord/Telegram 봇 웹훅 + Zapier/Make/IFTTT 연동(활성 기능)으로 재구성됨. **[완료: 삭제 확인]**
  - `routes/integrations/content_workspace.py`의 `PUT /api/content/<content_id>/folder` — 삭제됨, 파일은 현재 버전 히스토리(`VersionHistory.tsx` 소비)/검색/폴더/알림/협업 세션(활성 기능)으로 재구성됨. **[완료: 삭제 확인]**
  - `routes/integrations/imports.py`의 `POST /api/gdocs/import`, `POST /api/email/ingest` — 삭제됨. 후속 2026-07-10 Dep-14에서 파일에 남아 있던 Notion/RSS 구독/북마크 임포트 라우트도 소비자 0으로 재검증 후 파일 전체 삭제. **[완료: 삭제 확인]**
  - `routes/integrations/misc.py`의 `GET /api/openapi.json`, `GET /api/docs` — **[완료: 2026-07-05 cycle 29a 삭제]** `services/data/openapi_service.py`(`build_openapi_spec` 포함 모듈 전체) 함께 삭제. `misc.py`의 앱 피드백/OAuth 2.0 라우트는 그대로 유지.
  - `routes/blog_routes.py`의 `POST /regenerate` — 삭제 확인. **[완료: 삭제 확인]**
  - `routes/utility/external.py`의 `POST /api/wordcloud`, `GET /api/schema` — 삭제됨, 파일은 현재 webhook-test/playlist-videos/feed.xml(활성+유지판정 혼재)로 재구성됨. **[완료: 삭제 확인]**
  - `routes/utility/feedback_quality.py`의 `DELETE /api/cache/ai`, `GET /api/feedback/stats/<style_id>` — 삭제됨, 파일은 현재 피드백/팩트체크/표절/가독성/감정분석(활성 기능)으로 재구성됨. **[완료: 삭제 확인]**
  - `routes/utility/operations.py`의 `POST /api/close` — 삭제됨, 파일은 헬스체크/heartbeat/providers/ollama-health(활성 기능)로 재구성됨. **[완료: 삭제 확인]**
- **routes/marketplace_routes.py, routes/payment/*, routes/payment_routes.py** — 이번 배치 범위 밖(지시에 따라 제외), 미처리.

## 이번에 삭제 완료
- services/mcp/plugin_sdk.py + plugins/{linkedin,tistory,twitter,velog}.py (+테스트 4개) — 레지스트리 미등록 죽은 모듈
- static/ 잔여 7개 파일, 루트 postcss/tailwind 설정, 깨진 CSS 빌드 스크립트
- frontend devDeps: jsdom, @types/dompurify (락파일 재생성 완료)

## 2026-07-05 갱신 3 (dev-loop cycle 29a, batch [Dep-2e]) — auth 그룹 + openapi 완료

`plans/dead-code-audit-2026-06-10.md` "2026-07-05 갱신 2"에서 캐스케이드 규모로 이월됐던 auth/* 그룹 + integrations/misc.py의 openapi/docs를 일괄 삭제:

- **routes/auth/admin.py (6건)** — 파일 삭제.
- **routes/auth/history_account.py (실제 7건 확인 — 목록 4건에 없던 `DELETE /api/user/history/<report_id>`, `POST .../favorite`, `PUT /api/user/history/<report_id>` 3건도 소비자 0 재확인)** — 파일 삭제.
- **routes/auth/misc.py (8건 + 목록에 없던 `POST /api/sso/<workspace_id>/callback` 1건, sso_service 전체 orphan이라 함께 삭제)** — 해당 라우트만 제거. 스타일 메모리·활동피드는 유지하고, 이후 프론트 소비 0으로 재검증된 스니펫 라우트는 2026-07-12 dead-code 20차에서 제거.
- **routes/auth/user_settings.py (6건)** — 파일 삭제.
- **routes/auth_routes.py의 GET /api/auth/status, GET /api/auth/config (2건)** — 공유 라이브 파일이라 해당 2개 라우트만 제거, signup/login/oauth/refresh/me 등 기존 유지 판정 라우트는 그대로.
- **routes/integrations/misc.py의 GET /api/openapi.json, GET /api/docs (2건)** — 앱 피드백(`/api/app-feedback`)/OAuth 2.0 공급자(`/oauth/*`) 라우트는 그대로 유지.
- **routes/auth/__init__.py** — admin/history_account/user_settings 서브모듈 import 제거, 남은 서브모듈(workspace, channel_monitoring, misc) 로드로 갱신.
- **cascade 삭제**: `services/data/supabase_admin/admin_queries.py`의 `get_admin_permissions`, `get_all_users_usage`, `reset_user_usage`, `get_usage_stats`, `get_all_contents`, `get_content_detail` (6개 함수, `is_admin`은 `services/usage/usage_service.py`가 계속 사용하므로 유지) + `services/data/supabase_admin/__init__.py`/`services/data/usage_admin_facade.py`/`services/data/supabase_service.py`의 관련 re-export 정리.
- **cascade 삭제**: `services/data/content_admin_facade.py`, `account_admin_facade.py`, `api_key_storage_facade.py`, `custom_style_facade.py` 전체 삭제(전부 삭제된 라우트에서만 소비).
- **cascade 삭제**: `services/data/supabase_service.py`의 `delete_user_account`, `update_user_profile`, `update_user_password`, `save_api_keys`, `get_api_keys`, `save_custom_style`, `get_custom_styles`, `delete_custom_style` 8개 함수 + `_API_KEY_FIELDS` (facade를 통해서만 호출되던 함수, `get_histories`/`delete_history`/`update_history`/`toggle_favorite`는 `src/contexts/content_library/infrastructure/supabase_history_repository.py`가 계속 사용하므로 유지).
- **cascade 삭제**: `services/usage/usage_alert_service.py`, `services/auth/sso_service.py`, `services/data/audit_log_service.py`, `services/data/openapi_service.py` — 전부 whole-orphan 확인.
- **테스트 정리**: `tests/test_openapi_service.py`, `tests/test_sso_service.py`, `tests/test_sso_routes.py`, `tests/test_usage_alert_routes.py`, `tests/test_usage_alert_service.py`, `tests/test_audit_log_service.py` 삭제. `tests/test_auth_routes_cov.py`에서 `TestAuthStatusDisabled`의 auth_status/auth_config, `TestAuthEndpointsNoSupabase`의 user_settings 계열(키/스타일/사용량) 테스트, `TestHistoryRoutes`/`TestProfileRoutes`/`TestAdminRoutes` 클래스 전체, `TestMaskApiKey` 클래스(헬퍼 자체 삭제) 제거. `tests/test_supabase_service_extended.py`에서 `TestDeleteUserAccount`/`TestUpdateUserProfile`/`TestUpdateUserPassword`/`TestSaveApiKeys`/`TestGetApiKeys`/`TestCustomStyles`/`TestGetAdminPermissions`/`TestGetAllUsersUsage`/`TestResetUserUsage`/`TestGetUsageStats`/`TestGetAllContents`/`TestGetContentDetail` 제거.
- **범위 밖(손대지 않음)**: `src/contexts/content_library/` BC 자체의 `list_history_entries`/`delete_history_entry`/`update_history_entry`/`toggle_favorite` export가 이제 이 BC 밖에서는 미사용이지만, 지시서 캐스케이드 맵에 없는 도메인 계층이라 그대로 둠 — 별도 배치에서 재검토 필요.
- 검증: `pytest tests/` 4931 passed, 1 skipped / `npx tsc --noEmit` 0 errors / `npx next build` 성공 / `create_app()` 로드 확인 + url_map에서 삭제 대상 경로 전부 부재 확인.

## 2026-07-05 갱신 4 (dev-loop cycle 30b, batch 5) — payment/marketplace 그룹 완료, 이 문서의 마지막 남은 잔여 그룹

`plans/dead-code-audit-2026-06-10.md`에서 유일하게 미처리로 남아있던 payment/marketplace 그룹(2026-07-05 갱신 2, 라인 28)을 엔드포인트 단위로 전수 재검증 후 제거:

- **소비자 맵 방법론**: 프론트엔드(`frontend/lib/api.ts`, 컴포넌트, hooks, stores) 전수 grep + 해당 컴포넌트가 실제로 앱 페이지 트리(`frontend/app/**`)에서 import되는지 재귀 확인 + 백엔드 교차 호출(`services/usage/*`가 payment/subscription을 참조하는지 — 참조 없음, usage 도메인은 payment와 완전 독립) + `agent/tools/`의 pkgutil 동적 로드 루프(payment/marketplace 무관) + `services/mcp/mcp_server.py`(무관) + `services/data/scheduler_worker.py`(RSS 구독만, 결제 구독 아님 — grep 오탐 확인) + `services/platform/webhook_service.py`(무관) + `.env.example`/`README.md`의 Stripe/Paddle/Coinbase 설정 문서화 여부.
- **판정**: `frontend/components/billing/*`(CreditBalance, PricingPage, ReferralCard, SubscriptionManager, UsageDashboard, CouponInput, UsageAlert), `frontend/components/marketplace/MarketplaceBrowser.tsx`, `frontend/components/settings/ApiKeyManager.tsx`가 각 엔드포인트를 호출하는 코드를 담고 있었으나, 이 컴포넌트들 자체가 `frontend/app/**` 어디에서도 import되지 않는 고아 컴포넌트임을 확인(결제/마켓플레이스 페이지 라우트 자체가 앱에 없음). Stripe/Paddle/Coinbase Webhook 3개(`/api/payment/webhook`, `/api/crypto/webhook`, `/api/paddle/webhook`)는 이론상 외부 프로바이더가 호출자이나, `.env.example`에 `STRIPE_*`/`PADDLE_*`/`COINBASE_*` 설정이 전혀 문서화되지 않았고 체크아웃 진입 플로우 자체가 죽어있어 실질적으로 트리거 불가능 — 전량 삭제 판정.
- **재검증 결과 실제 라우트 수가 감사 목록과 상이**(1개월 경과로 코드 재구성): `routes/payment_routes.py`는 목록 17건이 아닌 실제 29건(고유 경로 26개), `routes/payment/crypto.py`/`routes/payment/paddle.py`는 각 목록 2건이 아닌 실제 3건(webhook 라우트가 목록에 누락되어 있었음), `routes/marketplace_routes.py`는 목록의 `GET /api/marketplace/<template_id>`/`POST /api/marketplace/<template_id>/rate`가 이미 사라지고 `GET/POST /api/marketplace`, `POST /api/marketplace/<template_id>/download`로 재구성되어 있었음 — 전부 소비자 0 재확인 후 삭제.
- **제거된 파일**: `routes/payment_routes.py`, `routes/payment/`(crypto.py, paddle.py, _shared.py, __init__.py) 전체, `routes/marketplace_routes.py`, `services/payment/` 패키지 전체(stripe/subscription/trial/coupon/invoice/paddle/crypto/team_billing/hybrid_billing_service.py + __init__.py, 9개+1), `services/platform/marketplace_service.py`, `services/platform/referral_service.py`(오직 `/api/referral/*`에서만 소비), `services/data/api_key_service.py`(오직 `/api/keys*`에서만 소비)
- **제거된 프론트엔드**: `frontend/components/billing/` 디렉토리 전체(7개 파일), `frontend/components/marketplace/` 디렉토리 전체(1개 파일), `frontend/components/settings/ApiKeyManager.tsx` — 전부 import 0 확인(BulkActions.tsx 고아 정리 선례, c29b 따름)
- **제거된 테스트**: `tests/test_{coupon,crypto,hybrid_billing,invoice,marketplace,paddle,stripe,subscription,team_billing,trial,api_key,referral}_service.py`, `tests/test_crypto_routes.py`, `tests/test_paddle_routes.py`, `tests/test_hybrid_billing_routes.py`, `tests/test_payment_routes_cov.py` (16개)
- **`app.py`**: `routes.payment_routes` import 제거, `marketplace_bp` 블루프린트 등록 제거
- **의도적 유지(범위 밖, 손대지 않음)**: `services/usage/credit_service.py`, `services/usage/credit_plan.py` — usage 도메인 소속이라 이번 배치(payment/marketplace) 범위 밖. `get_plan_credits`/`get_plan_features`가 이제 사실상 미사용이지만 usage 패키지 내부 문제라 별도 배치에서 재검토 필요.
- 검증: `pytest tests/` 4725 passed, 1 skipped, 17 subtests / `npx tsc --noEmit` 0 errors / `npx next build` 성공 / `create_app()` 로드 확인 + url_map에서 삭제 대상 경로(credits/payment/subscription/trial/referral/keys/invoices/coupons/team-billing/billing/crypto/paddle/marketplace 패턴) 전부 부재 확인.
- **이 감사 문서의 처리 대상 그룹은 이번 배치로 전량 완료** — 남은 항목은 "삭제 안전 판정이지만 보류한 엔드포인트 (343건)" 섹션(제품 결정 필요, 별도 트랙)뿐.

## 삭제 안전 판정이지만 보류한 엔드포인트 (343건) — 제품 결정 필요

전부 "호출자 0" 확인됨. 단, 분석 대시보드/콘텐츠 관리/결제 등 기능군 전체가 포함되므로
기능 폐기 여부를 결정한 뒤 일괄 제거할 것. 각 항목의 blocking_refs(같이 지워야 할 테스트 목록)는
감사 원본 JSON 참조.

### routes/advanced/rewrite.py (1건) — [완료: 파일 삭제 확인, PR #96 Dep-4로 추정]
- GET /api/rewrite/platforms

### routes/advanced_routes.py (9건) — [완료: 라우트는 PR #81(Dep-2 batch 1)에서 제거, 잔존 orphan 서비스 services/finetune/ 는 2026-07-05 배치에서 제거]
- POST /api/channel-analysis
- POST /api/generate-clips
- POST /api/generate-podcast
- POST /api/generate-multilang
- POST /api/content-brief
- POST /api/competitor-analysis
- POST /api/commentary
- POST /api/finetune/collect
- POST /api/finetune/collect-local

### routes/analytics_routes.py (48건) — [완료: 파일 삭제 확인]
- GET /api/admin/dashboard/extended
- POST /api/admin/dashboard/record
- GET /api/performance/<content_id>
- POST /api/performance/<content_id>/view
- POST /api/performance/<content_id>/share
- GET /api/performance/top
- GET /api/performance/aggregate
- GET /api/admin/costs
- POST /api/admin/roi
- POST /api/heatmap/<content_id>/click
- POST /api/heatmap/<content_id>/scroll
- GET /api/heatmap/<content_id>
- POST /api/ab-tests
- GET /api/ab-tests
- GET /api/ab-tests/<test_id>/results
- POST /api/ab-tests/<test_id>/event
- POST /api/behavior/record
- GET /api/admin/behavior/features
- GET /api/admin/behavior/sessions
- GET /api/admin/quality/trend
- GET /api/admin/styles/performance
- GET /api/admin/models/benchmark
- GET /api/admin/realtime/status
- GET /api/admin/anomalies
- POST /api/admin/anomalies/metric
- GET /api/admin/export-data
- POST /api/admin/digest
- POST /api/dashboard/share
- GET /api/dashboard/shared/<token>
- GET /api/logs/stream
- GET /api/logs/recent
- POST /api/admin/cohort/event
- GET /api/admin/cohort/retention
- GET /api/admin/cohort/ltv
- GET /api/admin/ga/pageviews
- GET /api/admin/ga/events
- GET /api/admin/gsc/search-analytics
- GET /api/admin/gsc/top-pages
- POST /api/admin/segments/update
- GET /api/admin/segments/classify/<user_id>
- GET /api/admin/segments/counts
- GET /api/admin/segments/<segment_id>/users
- GET /api/admin/trends/keywords
- POST /api/admin/trends/keywords
- DELETE /api/admin/trends/keywords
- POST /api/admin/trends/fetch
- GET /api/admin/trends/cached
- POST /api/admin/trends/rising

### routes/auth/admin.py (6건) — [완료: 2026-07-05 cycle 29a 삭제, 파일 자체 삭제]
- GET /api/admin/check
- GET /api/admin/users
- POST /api/admin/users/<user_id>/reset
- GET /api/admin/stats
- GET /api/admin/contents
- GET /api/admin/contents/<report_id>

### routes/auth/history_account.py (실제 7건, 목록 4건 대비 `DELETE/PUT/POST /api/user/history/<report_id>` 계열 3건 누락 확인 — 전부 소비자 0 재확인) — [완료: 2026-07-05 cycle 29a 삭제, 파일 자체 삭제]
- GET /api/user/history
- DELETE /api/user/history/<report_id>
- POST /api/user/history/<report_id>/favorite
- PUT /api/user/history/<report_id>
- PUT /api/user/profile
- PUT /api/user/password
- DELETE /api/user/account

### routes/auth/misc.py (8건) — [완료: 2026-07-05 cycle 29a 삭제, 파일은 스타일 메모리/스니펫/활동피드(활성 기능)로 잔존]
- GET /api/admin/audit-logs
- GET /api/user/usage-alerts
- POST /api/user/usage-alerts/check
- POST /api/user/usage-alerts/reset
- POST /api/sso/<workspace_id>/config
- GET /api/sso/<workspace_id>/config
- POST /api/sso/<workspace_id>/login
- POST /api/sso/<workspace_id>/disable
- (연쇄 확인) POST /api/sso/<workspace_id>/callback — 목록에 없었으나 sso_service 전체 orphan이라 함께 삭제

### routes/auth/user_settings.py (6건) — [완료: 2026-07-05 cycle 29a 삭제, 파일 자체 삭제]
- GET /api/user/keys
- POST /api/user/keys
- GET /api/user/styles
- POST /api/user/styles
- DELETE /api/user/styles/<style_id>
- GET /api/user/usage

### routes/auth_routes.py (2건) — [완료: 2026-07-05 cycle 29a 삭제, auth_routes.py 자체는 공유 라이브 파일이라 해당 2개 라우트만 제거]
- GET /api/auth/status
- GET /api/auth/config

### routes/blog/voice_capture.py (2건) — [완료: 파일 삭제 확인]
- POST /api/capture/speech
- POST /api/capture/merge

### routes/blog_routes.py (1건) — [완료: 재검증 결과 이미 삭제됨]
- POST /regenerate

### routes/content_mgmt/backup_io.py (5건) — [완료: 2026-07-05 삭제, content_mgmt_routes.py와 함께 파일 삭제]
- POST /api/content/backup
- GET /api/content/backup
- POST /api/content/backup/<filename>/restore
- GET /api/content/export/<fmt>
- POST /api/content/import/<fmt>

### routes/content_mgmt/trash_pin.py (7건) — [완료: 파일 삭제 확인]
- GET /api/content/trash
- POST /api/content/trash/<item_id>/restore
- DELETE /api/content/trash/<item_id>
- POST /api/content/trash/empty
- POST /api/content/<item_id>/pin
- DELETE /api/content/<item_id>/pin
- GET /api/content/pinned

### routes/content_mgmt_routes.py (45건, 실제 51건 확인) — [완료: 2026-07-05 전체 삭제, 파일 자체 삭제 + 15개 orphan 서비스 삭제]
- POST /api/content
- GET /api/content
- POST /api/content/<item_id>/clone
- POST /api/content/<item_id>/archive
- POST /api/content/<item_id>/unarchive
- GET /api/content/archive
- POST /api/content/<item_id>/lock
- DELETE /api/content/<item_id>/lock
- POST /api/content/<item_id>/lock/heartbeat
- GET /api/content/<item_id>/lock
- POST /api/content/<item_id>/expiry
- DELETE /api/content/<item_id>/expiry
- GET /api/content/<item_id>/expiry
- POST /api/content/media
- GET /api/content/media
- DELETE /api/content/media/<media_id>
- GET /api/content/media/stats
- POST /api/content/fields
- GET /api/content/fields
- GET /api/content/<item_id>/fields
- PUT /api/content/<item_id>/fields/<field_id>
- POST /api/content/<item_id>/links
- GET /api/content/<item_id>/links
- DELETE /api/content/links/<link_id>
- POST /api/content/seo-check
- GET /api/content/<item_id>/seo-check
- GET /api/content/embed/<item_id>
- POST /api/content/<item_id>/share
- GET /api/content/share/<token>
- DELETE /api/content/share/<token>
- POST /api/content/<item_id>/comments
- GET /api/content/<item_id>/comments
- PATCH /api/content/comments/<comment_id>
- DELETE /api/content/comments/<comment_id>
- POST /api/content/comments/<comment_id>/resolve
- POST /api/content/comments/<comment_id>/react
- POST /api/content/workflows
- GET /api/content/workflows
- PATCH /api/content/workflows/<wf_id>
- DELETE /api/content/workflows/<wf_id>
- POST /api/content/workflows/fire
- POST /api/content/roles
- GET /api/content/roles
- POST /api/content/roles/assign
- POST /api/content/roles/check

### routes/integrations/automation.py (8건) — [완료: 재검증 결과 이미 삭제됨, 파일은 활성 봇/자동화 연동으로 재구성]
- POST /api/sync/airtable
- POST /api/sync/gsheets
- GET /api/integrations/discord/status
- POST /api/integrations/discord/send
- POST /api/integrations/discord/send-embed
- GET /api/integrations/slack/status
- POST /api/integrations/slack/send
- POST /api/integrations/slack/send-blocks

### routes/integrations/content_workspace.py (1건) — [완료: 재검증 결과 이미 삭제됨, 파일은 활성 버전 히스토리/검색/폴더/알림/협업 기능으로 재구성]
- PUT /api/content/<content_id>/folder

### routes/integrations/imports.py (2건) — [완료: 재검증 결과 이미 삭제됨, 후속 Dep-14에서 파일 전체 삭제]
- POST /api/gdocs/import
- POST /api/email/ingest

### routes/integrations/knowledge.py (5건) — [완료: 2026-07-05 삭제, ingest는 기존 유지판정대로 보존]
- POST /api/rag/graph/search/local
- GET /api/rag/graph/search/global
- POST /api/rag/multimodal/detect-type
- POST /api/rag/multimodal/ingest
- POST /api/rag/multimodal/query

### routes/integrations/misc.py (2건) — [완료: 2026-07-05 cycle 29a 삭제, services/data/openapi_service.py 모듈 전체 함께 삭제, 앱 피드백/OAuth 2.0 라우트는 파일에 잔존]
- GET /api/openapi.json
- GET /api/docs

### routes/integrations/workflow.py (3건) — [완료: 파일 삭제 확인]
- POST /api/cms/publish-all
- GET /api/cms/plugins
- POST /api/cms/validate-config

### routes/marketplace_routes.py (2건) — [완료: 2026-07-05 cycle 30b, batch 5 삭제. 재검증 결과 실제 라우트는 목록과 달랐음(rate 없음, download 신규) — GET/POST /api/marketplace, POST /api/marketplace/<template_id>/download 3건 전부 소비자 0 확인 후 삭제, services/platform/marketplace_service.py 함께 삭제]
- GET /api/marketplace/<template_id>
- POST /api/marketplace/<template_id>/rate

### routes/payment/crypto.py (2건) — [완료: 2026-07-05 cycle 30b, batch 5 삭제. 실제 3건(charge, charge/<id>, webhook) 전부 소비자 0]
- POST /api/crypto/charge
- GET /api/crypto/charge/<charge_id>

### routes/payment/paddle.py (2건) — [완료: 2026-07-05 cycle 30b, batch 5 삭제. 실제 3건(status, webhook, subscription/<id>) 전부 소비자 0]
- GET /api/paddle/status
- GET /api/paddle/subscription/<subscription_id>

### routes/payment_routes.py (17건) — [완료: 2026-07-05 cycle 30b, batch 5 삭제. 재검증 결과 실제 29개 라우트 전부 소비자 0 확인(목록 17건 대비 credits/balance·plans, payment/checkout·webhook, subscription(GET)·cancel, usage/my-usage, keys*, team-billing* 등 누락분 포함). 상세는 CLAUDE.md "dead-code 제거 batch 5" 참조]
- POST /api/credits/purchase
- POST /api/subscription/upgrade
- POST /api/trial/start
- GET /api/trial/status
- GET /api/invoices
- POST /api/invoices
- POST /api/invoices/<invoice_id>/pay
- GET /api/coupons
- POST /api/coupons
- POST /api/coupons/validate
- POST /api/coupons/redeem
- GET /api/team-billing/<team_id>
- GET /api/team-billing/<team_id>/members
- POST /api/billing/setup
- POST /api/billing/consume
- GET /api/billing/summary
- POST /api/billing/reset-monthly

### routes/utility/content_evaluation.py (18건) — [완료: 파일 삭제 확인]
- POST /api/grade-content
- POST /api/optimize-headline
- POST /api/freshness-check
- POST /api/generate-quiz
- POST /api/check-cannibalization
- POST /api/generate-debate
- POST /api/analyze-sentiment
- POST /api/generate-hooks
- POST /api/extract-snippets
- POST /api/benchmark-readability
- POST /api/generate-outline
- POST /api/reading-time
- POST /api/analyze-cta
- POST /api/predict-performance
- POST /api/score-content-depth
- POST /api/analyze-conclusion-strength
- POST /api/check-content-freshness
- POST /api/score-content-scanability

### routes/utility/content_meta.py (31건) — [완료: 파일 삭제 확인]
- POST /api/extract-acronyms
- POST /api/brand-voice
- POST /api/audience-persona
- POST /api/suggest-visuals
- POST /api/information-gain
- POST /api/detect-artifacts
- POST /api/validate-instruction-sequence
- POST /api/generate-word-frequency
- POST /api/map-emotional-arc
- POST /api/check-material-connection-disclosure
- POST /api/check-ai-disclosure
- POST /api/analyze-tradeoff-coverage
- POST /api/check-primary-source-preference
- POST /api/detect-high-stakes-advice-risk
- POST /api/check-evaluation-criteria-disclosure
- POST /api/analyze-recommendation-justification
- POST /api/check-prerequisite-disclosure
- POST /api/analyze-troubleshooting-coverage
- POST /api/analyze-extractability
- POST /api/analyze-community-evidence
- POST /api/check-update-delta-summary
- POST /api/analyze-audience-fit-framing
- POST /api/detect-geo-scope-assumptions
- POST /api/detect-absolute-claim-risk
- POST /api/analyze-step-verification-coverage
- POST /api/check-comparison-criteria-completeness
- POST /api/analyze-original-evidence
- POST /api/analyze-claim-evidence-distance
- POST /api/detect-definition-gaps
- POST /api/check-methodology-transparency
- GET /api/scheduler/status

### routes/utility/external.py (2건) — [완료: 재검증 결과 이미 삭제됨, 파일은 활성 webhook-test/playlist-videos/feed.xml로 재구성]
- POST /api/wordcloud
- GET /api/schema

### routes/utility/feedback_quality.py (2건) — [완료: 재검증 결과 이미 삭제됨, 파일은 활성 피드백/팩트체크/표절/가독성/감정분석으로 재구성]
- DELETE /api/cache/ai
- GET /api/feedback/stats/<style_id>

### routes/utility/generation.py (2건) — [완료: 파일 삭제 확인]
- POST /api/recommend-style
- POST /api/generate-style

### routes/utility/operations.py (1건) — [완료: 재검증 결과 이미 삭제됨, 파일은 활성 헬스체크/heartbeat/providers/ollama-health로 재구성]
- POST /api/close

### routes/utility/seo_aeo.py (31건) — [완료: 파일 삭제 확인]
- POST /api/generate-faq
- POST /api/analyze-aeo
- POST /api/search-intent
- POST /api/internal-links
- POST /api/check-originality
- POST /api/topic-gaps
- POST /api/analyze-eeat
- POST /api/serp-features
- POST /api/topic-clusters
- POST /api/analyze-entities
- POST /api/verify-claims
- POST /api/schema-opportunities
- POST /api/audit-anchors
- POST /api/audit-promises
- POST /api/check-consistency
- POST /api/detect-subheading-gaps
- POST /api/detect-actionability-gaps
- POST /api/detect-list-table-opportunities
- POST /api/audit-image-seo
- POST /api/audit-source-diversity
- POST /api/detect-chapter-breakpoints
- POST /api/analyze-question-density
- POST /api/check-meta-description-quality
- POST /api/generate-toc
- POST /api/check-article-format
- POST /api/check-title-tag-length
- POST /api/detect-keyword-stuffing
- POST /api/check-url-health
- POST /api/find-visualization-opportunities
- POST /api/check-qa-closure
- POST /api/analyze-example-coverage

### routes/utility/text_quality.py (30건) — [완료: 파일 삭제 확인]
- POST /api/power-words
- POST /api/emotional-tone
- POST /api/engagement-score
- POST /api/check-redundancy
- POST /api/detect-passive
- POST /api/detect-fillers
- POST /api/check-inclusive-language
- POST /api/check-promotional-tone
- POST /api/check-numerical-promises
- POST /api/analyze-jargon
- POST /api/analyze-speakability
- POST /api/detect-section-drift
- POST /api/detect-adverb-overuse
- POST /api/analyze-statistics-coverage
- POST /api/find-simple-alternatives
- POST /api/check-thesis-frontload
- POST /api/audit-whitespace-formatting
- POST /api/analyze-bullet-density
- POST /api/check-code-block-quality
- POST /api/check-parenthetical-overuse
- POST /api/detect-anaphora-repetition
- POST /api/analyze-emoji-usage
- POST /api/detect-rhetorical-devices
- POST /api/detect-cliches
- POST /api/check-gender-neutral
- POST /api/check-temporal-references
- POST /api/analyze-quotation-usage
- POST /api/analyze-quantifier-specificity
- POST /api/analyze-terminology-drift
- POST /api/analyze-concept-load

### routes/utility/text_structure.py (31건) — [완료: 파일 삭제 확인]
- POST /api/keyword-density
- POST /api/analyze-transitions
- POST /api/paragraph-balance
- POST /api/sentence-variety
- POST /api/check-heading-parallelism
- POST /api/check-pronoun-clarity
- POST /api/detect-clause-overload
- POST /api/audit-heading-terms
- POST /api/check-acronym-expansion
- POST /api/check-paragraph-opening-variety
- POST /api/check-tone-consistency
- POST /api/detect-linking-verb-overuse
- POST /api/analyze-connector-variety
- POST /api/analyze-sentence-rhythm
- POST /api/analyze-sentence-ending-variety
- POST /api/analyze-passive-ratio
- POST /api/analyze-avg-words-per-sentence
- POST /api/check-acronym-consistency
- POST /api/analyze-heading-keyword-density
- POST /api/analyze-content-symmetry
- POST /api/score-sentence-complexity
- POST /api/analyze-sentence-starter-diversity
- POST /api/analyze-avg-paragraph-length
- POST /api/analyze-noun-verb-ratio
- POST /api/analyze-passive-active-trend
- POST /api/check-list-parallelism
- POST /api/check-heading-hierarchy
- POST /api/check-numeric-unit-consistency
- POST /api/analyze-topic-sentence-alignment
- POST /api/check-paragraph-unity
- POST /api/analyze-adjacent-cohesion

### 기타 (2건)
- jsdom (frontend/package.json devDependency)
- @types/dompurify (frontend/package.json devDependency)

## 유지 판정 (삭제 금지)
- **POST /api/auth/signup (routes/auth_routes.py:99)** — No in-repo client caller (verified), but this is the system's SOLE account-creation path: auth_routes.py:114 is the only...
- **POST /api/auth/reset-password (routes/auth_routes.py:137)** — No in-repo client caller (verified), but auth_routes.py:149 is the only reset_password_email call site in the codebase —...
- **GET /api/auth/oauth/<provider> (routes/auth_routes.py:161)** — No in-repo client caller (verified), but auth_routes.py:181 is the only sign_in_with_oauth call site, and this endpoint ...
- **POST /api/auth/login (routes/auth_routes.py:227)** — No in-repo client caller (verified: Next.js frontend sends no Authorization headers anywhere and has no login UI — Notif...
- **POST /api/auth/logout (routes/auth_routes.py:258)** — No in-repo caller found, and unlike login/refresh it is not strictly load-bearing (token expiry would eventually end ses...
- **POST /api/auth/refresh (routes/auth_routes.py:274)** — No in-repo client caller (verified), but auth_routes.py:286 is the codebase's ONLY refresh_session call site — the sole ...
- **GET /api/auth/me (routes/auth_routes.py:307)** — No caller found anywhere (in-repo or docs), and it is not structurally load-bearing like login/refresh. However it is th...
- **GET,POST /graphql (routes/graphql_routes.py:188)** — No internal clients or tests, but README.md:51 advertises 'GraphQL API — 유연한 쿼리 지원' as a product feature and README.md:1...
- **GET /graphql/schema (routes/graphql_routes.py:213)** — Tied to the /graphql endpoint verdict: it is the SDL discovery endpoint of the README-advertised GraphQL API and is unau...
- **POST /api/rag/graph/ingest (routes/integrations/knowledge.py:108)** — STILL USED as the sole population mechanism of a live, documented feature. GraphRAGEngine.ingest (only production caller...
- **GET /feed.xml (routes/utility/external.py:177)** — Two independent blockers. (1) Deliberate retention with explicit roadmap: the route was rewritten in the MOST RECENT com...
