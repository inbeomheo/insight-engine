# 데드코드 감사 결과 (2026-06-10)

멀티에이전트 감사(에이전트 52개)로 소비자 없는 엔드포인트/모듈/의존성 354건을 발굴하고,
각 후보를 적대적 검증(동적 import, url_for, 프론트엔드/확장/n8n/문서/배포설정/OpenAPI 전수 grep)했다.

## 이번에 삭제 완료
- services/mcp/plugin_sdk.py + plugins/{linkedin,tistory,twitter,velog}.py (+테스트 4개) — 레지스트리 미등록 죽은 모듈
- static/ 잔여 7개 파일, 루트 postcss/tailwind 설정, 깨진 CSS 빌드 스크립트
- frontend devDeps: jsdom, @types/dompurify (락파일 재생성 완료)

## 삭제 안전 판정이지만 보류한 엔드포인트 (343건) — 제품 결정 필요

전부 "호출자 0" 확인됨. 단, 분석 대시보드/콘텐츠 관리/결제 등 기능군 전체가 포함되므로
기능 폐기 여부를 결정한 뒤 일괄 제거할 것. 각 항목의 blocking_refs(같이 지워야 할 테스트 목록)는
감사 원본 JSON 참조.

### routes/advanced/rewrite.py (1건)
- GET /api/rewrite/platforms

### routes/advanced_routes.py (9건)
- POST /api/channel-analysis
- POST /api/generate-clips
- POST /api/generate-podcast
- POST /api/generate-multilang
- POST /api/content-brief
- POST /api/competitor-analysis
- POST /api/commentary
- POST /api/finetune/collect
- POST /api/finetune/collect-local

### routes/analytics_routes.py (48건)
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

### routes/auth/admin.py (6건)
- GET /api/admin/check
- GET /api/admin/users
- POST /api/admin/users/<user_id>/reset
- GET /api/admin/stats
- GET /api/admin/contents
- GET /api/admin/contents/<report_id>

### routes/auth/history_account.py (4건)
- GET /api/user/history
- PUT /api/user/profile
- PUT /api/user/password
- DELETE /api/user/account

### routes/auth/misc.py (8건)
- GET /api/admin/audit-logs
- GET /api/user/usage-alerts
- POST /api/user/usage-alerts/check
- POST /api/user/usage-alerts/reset
- POST /api/sso/<workspace_id>/config
- GET /api/sso/<workspace_id>/config
- POST /api/sso/<workspace_id>/login
- POST /api/sso/<workspace_id>/disable

### routes/auth/user_settings.py (6건)
- GET /api/user/keys
- POST /api/user/keys
- GET /api/user/styles
- POST /api/user/styles
- DELETE /api/user/styles/<style_id>
- GET /api/user/usage

### routes/auth_routes.py (2건)
- GET /api/auth/status
- GET /api/auth/config

### routes/blog/voice_capture.py (2건)
- POST /api/capture/speech
- POST /api/capture/merge

### routes/blog_routes.py (1건)
- POST /regenerate

### routes/content_mgmt/backup_io.py (5건)
- POST /api/content/backup
- GET /api/content/backup
- POST /api/content/backup/<filename>/restore
- GET /api/content/export/<fmt>
- POST /api/content/import/<fmt>

### routes/content_mgmt/trash_pin.py (7건)
- GET /api/content/trash
- POST /api/content/trash/<item_id>/restore
- DELETE /api/content/trash/<item_id>
- POST /api/content/trash/empty
- POST /api/content/<item_id>/pin
- DELETE /api/content/<item_id>/pin
- GET /api/content/pinned

### routes/content_mgmt_routes.py (45건)
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

### routes/integrations/automation.py (8건)
- POST /api/sync/airtable
- POST /api/sync/gsheets
- GET /api/integrations/discord/status
- POST /api/integrations/discord/send
- POST /api/integrations/discord/send-embed
- GET /api/integrations/slack/status
- POST /api/integrations/slack/send
- POST /api/integrations/slack/send-blocks

### routes/integrations/content_workspace.py (1건)
- PUT /api/content/<content_id>/folder

### routes/integrations/imports.py (2건)
- POST /api/gdocs/import
- POST /api/email/ingest

### routes/integrations/knowledge.py (5건)
- POST /api/rag/graph/search/local
- GET /api/rag/graph/search/global
- POST /api/rag/multimodal/detect-type
- POST /api/rag/multimodal/ingest
- POST /api/rag/multimodal/query

### routes/integrations/misc.py (2건)
- GET /api/openapi.json
- GET /api/docs

### routes/integrations/workflow.py (3건)
- POST /api/cms/publish-all
- GET /api/cms/plugins
- POST /api/cms/validate-config

### routes/marketplace_routes.py (2건)
- GET /api/marketplace/<template_id>
- POST /api/marketplace/<template_id>/rate

### routes/payment/crypto.py (2건)
- POST /api/crypto/charge
- GET /api/crypto/charge/<charge_id>

### routes/payment/paddle.py (2건)
- GET /api/paddle/status
- GET /api/paddle/subscription/<subscription_id>

### routes/payment_routes.py (17건)
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

### routes/utility/content_evaluation.py (18건)
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

### routes/utility/content_meta.py (31건)
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

### routes/utility/external.py (2건)
- POST /api/wordcloud
- GET /api/schema

### routes/utility/feedback_quality.py (2건)
- DELETE /api/cache/ai
- GET /api/feedback/stats/<style_id>

### routes/utility/generation.py (2건)
- POST /api/recommend-style
- POST /api/generate-style

### routes/utility/operations.py (1건)
- POST /api/close

### routes/utility/seo_aeo.py (31건)
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

### routes/utility/text_quality.py (30건)
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

### routes/utility/text_structure.py (31건)
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