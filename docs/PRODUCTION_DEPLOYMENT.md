# 프로덕션 배포 가이드 — Insight Engine

이 문서는 Insight Engine을 실제 사용자가 사용하는 프로덕션 환경에 배포하기 위한 보안/운영 체크리스트입니다.

> **현재 코드 상태 가정**: Flask + Next.js, gunicorn 4 워커, Redis rate limit, APScheduler 단일 컨테이너, Sentry 옵션 통합 완료. (`docker-compose.yml`, `Dockerfile`, `app.py`, `extensions.py` 참조)

---

## 1. 시크릿 & API 키 로테이션 (필수)

### 1-1. 로컬 `.env` 노출 가정

`.env` 파일은 `git history`에 들어가지 않았지만 **로컬 디스크에 평문으로 존재**합니다. 화면 공유, 스크린샷, 백업, 다른 도구의 인덱싱 등으로 *간접 노출*되었을 가능성을 0으로 만들 수 없습니다. **프로덕션 배포 전에 모든 키를 새로 발급**하세요.

### 1-2. 로테이션 대상

| 키 | 콘솔 |
|----|------|
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey |
| `DEEPSEEK_API_KEY` | https://platform.deepseek.com/api_keys |
| `ZHIPUAI_API_KEY` / `ZAI_API_KEY` | https://open.bigmodel.cn/usercenter/apikeys |
| `YOUTUBE_API_KEY` | https://console.cloud.google.com/apis/credentials |
| `SUPADATA_API_KEY` | https://supadata.ai/ |
| `TAVILY_API_KEY` | https://tavily.com/ |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `OPENROUTER_API_KEY` | 각 콘솔의 "Revoke / Create" |
| `SUPABASE_ANON_KEY` / `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard → Settings → API → **Rotate JWT secret** |
| `ENCRYPTION_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

`FLASK_ENV=production`에서는 `ENCRYPTION_SECRET`이 32자 미만이거나 기본 placeholder이면 부팅을 차단합니다.

### 1-3. 절차

1. 위 콘솔에서 **기존 키 즉시 revoke**
2. 새 키 발급
3. 새 키는 `.env` 로컬 파일이 아닌 **배포 플랫폼의 secret 관리자**에 저장
   - Railway: Project → Variables
   - Docker: `docker secret create` 또는 `.env.production` (gitignored, `chmod 600`)
   - Kubernetes: `Secret` 리소스 + 적절한 RBAC
4. 로컬 `.env`는 키만 비워두거나, 개발 전용 별도 키 사용

---

## 2. 인프라 체크리스트

### 2-1. 컨테이너 / WSGI

- [x] `Dockerfile` CMD = `gunicorn -w 4 -k gthread --threads 8 -b 0.0.0.0:5001 app:app`
- [x] `docker-compose.yml` backend command = gunicorn
- [x] 스케줄러는 **별도 컨테이너**(`insight-scheduler`)로 단일 워커 운영
- [ ] `gunicorn --workers` 값 = CPU 코어 수 × 2 + 1 (트래픽 측정 후 조정)
- [ ] 헬스체크 endpoint `/health` 200 응답 확인

### 2-2. Rate Limiter / Redis

- [x] `FLASK_ENV=production`이면 `REDIS_URL` 없을 때 부팅 실패 (`extensions.py`)
- [x] `docker-compose.yml`에 Redis 서비스 + healthcheck
- [ ] 외부 Redis 사용 시 TLS + 인증 필수

### 2-3. CORS / CSRF / CSP

- [x] `CORS_ORIGINS` 환경변수로 도메인 화이트리스트
- [x] CSRF Origin/Referer 검증 (`app.py`)
- [x] `Content-Security-Policy` 헤더 기본 적용
- [x] `FLASK_ENV=production`에서 localhost/wildcard/non-HTTPS `CORS_ORIGINS` 부팅 차단
- [ ] 실제 프로덕션 도메인으로 `CORS_ORIGINS` 설정
- [ ] CSP `'unsafe-inline'` / `'unsafe-eval'` 제거 검토 (Next.js 인라인 스크립트 nonce 적용 시)

### 2-4. 관측

- [x] `SENTRY_DSN` 환경변수로 백엔드 Sentry 옵트인 (`app.py`)
- [x] 프론트엔드 `window.Sentry` 폴백 (`frontend/lib/errorReporting.ts`) — SDK 없어도 console fallback
- [x] `X-Response-Time` 헤더 + 1초 초과 시 warn 로그
- [x] `/metrics` Prometheus 스타일 — `METRICS_AUTH_TOKEN` 으로 토큰 보호 가능
- [x] `FLASK_ENV=production`에서 `METRICS_AUTH_TOKEN` 미설정 시 부팅 차단
- [x] `/health` (liveness) + `/ready` (readiness with Redis/Supabase/ChromaDB 검사)
- [ ] 프론트엔드 `@sentry/nextjs` 실제 설치 (선택, 절차는 아래 2-6 참조)
- [ ] 로그 수집 (Railway, CloudWatch, Loki 등)
- [ ] uptime 외부 모니터링 (UptimeRobot, Better Stack 등)

### 2-6. 프론트엔드 Sentry 정식 통합 (선택)

현재는 `window.Sentry` 폴백 패턴만 적용되어 있어 SDK가 설치돼 있으면 자동으로 캡쳐, 없으면 console로 로그합니다. 정식 통합 절차:

```bash
cd frontend
npm install --save @sentry/nextjs

# Sentry 설정 파일 생성 (next.config.ts에 withSentryConfig 래핑)
npx @sentry/wizard@latest -i nextjs

# 환경변수 추가 (frontend/.env.local)
# NEXT_PUBLIC_SENTRY_DSN=https://...@o-id.ingest.sentry.io/project-id

# 빌드 시 source map 업로드 — auth token은 secret manager에서
# SENTRY_AUTH_TOKEN=sntrys_...
```

설치 후 `lib/errorReporting.ts`의 폴백은 그대로 두면 됩니다 — Sentry가 `window.Sentry`로 노출되면 자동으로 활용됩니다.

### 2-5. 데이터 영속성

- [ ] `app_data` 볼륨 정기 백업 (RAG ChromaDB, 큐, 캐시)
- [ ] Supabase는 자체 PITR 사용
- [ ] `publish_queue.json` 다중 워커 동시 쓰기 불가 — scheduler 컨테이너에서만 접근

---

## 3. 배포 직전 검증

```bash
# 1. 테스트 통과
python -m pytest tests/ -q --tb=no

# 2. 빌드 검증
docker build -t insight-engine:test .
cd frontend && npx tsc --noEmit && npx next build

# 3. 시크릿 누락 검증
grep -E "sk-[a-zA-Z0-9]{20}|AIza[a-zA-Z0-9_-]{30}" -r . --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=.next || echo "OK"

# 4. 컨테이너 부팅
docker-compose --env-file .env.production up -d
docker-compose logs -f backend  # ENCRYPTION_SECRET 에러 없는지
curl -f http://localhost:5001/health

# 5. Rate limit 검증 (Redis 연결)
docker-compose exec redis redis-cli keys "LIMITER/*"
```

---

## 4. 사고 대응 (Runbook 초안)

| 증상 | 1차 확인 |
|------|----------|
| 500 에러 급증 | Sentry 대시보드 → 최근 1시간 issues |
| 응답 지연 | `docker-compose logs backend | grep "느린 응답"` |
| 발행 실패 | `insight-scheduler` 컨테이너 로그, `publish_queue.json` |
| 사용자 인증 실패 | Supabase Auth 로그, `ie_admins` 테이블 |
| AI API 호출 실패 | Provider 상태 페이지, 키 사용량 확인 |

긴급 롤백: `git revert <commit> && docker-compose up -d --build`

---

## 5. 알려진 제약 (Known Limitations)

### 5-1. 프론트엔드 인증 — 완료 ✅

Next.js 프론트엔드 인증이 통합되었습니다. (`fcda20f` 이후 커밋 참조)

**구조:**
- `frontend/lib/supabaseClient.ts` — Supabase 클라이언트 싱글톤 (`NEXT_PUBLIC_SUPABASE_URL`/`_ANON_KEY` 필요)
- `frontend/lib/auth.ts` — `getAccessToken()`, `fetchWithAuth()`, `fetchJsonWithAuth()`
- `frontend/components/AuthProvider.tsx` — `<AuthProvider>` 컨텍스트 + `useAuth()` 훅
- `frontend/app/login/page.tsx` — 로그인/회원가입 UI (Suspense + useSearchParams `?redirect=`)
- `frontend/lib/api.ts` — 모든 `request()`/`requestBlob()`이 자동으로 Authorization 헤더 첨부

**동작 모드:**
- `NEXT_PUBLIC_SUPABASE_URL` 미설정 시: 로컬 모드 (Authorization 헤더 없음, 백엔드도 `is_supabase_enabled()=False`로 우회 통과)
- 설정 시: Supabase Auth로 로그인 → access_token이 모든 API 호출에 자동 첨부

**남은 작업 (선택):**
- 사이드바/헤더에 로그인 상태 UI 추가 (현재는 `/login`으로 직접 접근)
- 보호 페이지에 미인증 시 `redirect=/원본경로` 쿼리 첨부하여 `/login`으로 라우팅

### 5-2. publish_queue 단일 노드 한계

`filelock` 기반 inter-process 락은 같은 호스트의 여러 워커에서만 작동합니다. 다중 노드 배포 시:
- 옵션 A: 모든 backend 컨테이너를 같은 호스트에 두기 (수직 확장만)
- 옵션 B: 큐 백엔드를 Redis Streams 또는 Supabase 테이블로 이전 (수평 확장 가능)

옵션 B를 권장하지만 별도 작업 필요.

### 5-3. 6개 라우트 파일이 1,000줄 이상

`utility_routes` (3,350), `advanced_routes` (2,341), `integration_routes` (1,981), `auth_routes` (1,432), `blog_routes` (1,381), `content_mgmt_routes` (1,008). 동작에는 문제 없지만 변경 시 blast radius가 큽니다. 점진적 분할 권장.


## Production env verification

Run this gate after loading real production secrets, or in CI with masked variables:

```bash
FLASK_ENV=production \
CORS_ORIGINS=https://app.example.com \
METRICS_AUTH_TOKEN=replace_with_random_token \
ENCRYPTION_SECRET=replace_with_32_plus_random_secret \
REDIS_URL=redis://redis:6379/0 \
AUTO_BACKUP_INTERVAL_HOURS=6 \
MAX_BACKUPS=30 \
APP_DATA_DIR=/app/data \
APP_DATA_BACKUP_DIR=/mnt/backups/insight-engine \
PUBLISH_QUEUE_BACKEND=redis \
npm run verify:production
```


## Production CSP guard

`FLASK_ENV=production` uses a strict default Content-Security-Policy and rejects `CONTENT_SECURITY_POLICY` values containing `'unsafe-inline'` or `'unsafe-eval'`.


## Browser isolation headers

Responses include `Cross-Origin-Opener-Policy: same-origin`, `Cross-Origin-Resource-Policy: same-origin`, `X-Permitted-Cross-Domain-Policies: none`, and HTTPS responses use HSTS `max-age=63072000; includeSubDomains; preload`.


## Production backup readiness gate

`npm run verify:production` now fails unless `AUTO_BACKUP_INTERVAL_HOURS` is configured as a positive integer and `MAX_BACKUPS` keeps at least 7 retained backups in production.


## app_data backup/restore rehearsal

Use the app_data volume backup tool before production cutover and after backup storage changes:

```bash
APP_DATA_DIR=/app/data APP_DATA_BACKUP_DIR=/mnt/backups/insight-engine npm run verify:app-data-backup
python scripts/backup_app_data.py backup --source /app/data --backup-dir /mnt/backups/insight-engine
python scripts/backup_app_data.py restore /mnt/backups/insight-engine/app_data_backup_YYYYMMDD_HHMMSS.zip --target /tmp/app_data_restore
```

The readiness gate requires `APP_DATA_BACKUP_DIR` to be outside `APP_DATA_DIR` so backups do not recursively live on the same data volume.


## Production publish queue backend

Use `PUBLISH_QUEUE_BACKEND=redis` in production. The queue service stores the queue JSON in Redis under `PUBLISH_QUEUE_REDIS_KEY` (default `insight:publish_queue`) and uses a Redis lock for enqueue/process/cancel/retry critical sections. File-backed queue mode remains only for local/single-host fallback.
