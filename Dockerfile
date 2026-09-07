# Insight Engine Dockerfile (F9-10)
# 멀티스테이지 빌드: Next.js 프론트엔드 + Flask 백엔드

# ── 스테이지 1: Next.js 빌드 ──────────────────────────────────────────────────
FROM node:22-bookworm-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
# Build needs devDependencies because next.config.ts requires TypeScript at build time.
RUN npm ci

COPY frontend/ ./
ARG NEXT_BACKEND_URL=http://backend:5001
ENV NEXT_BACKEND_URL=$NEXT_BACKEND_URL
RUN npm run build

# ── 스테이지 2: Python 의존성 ──────────────────────────────────────────────────
FROM python:3.11-slim AS python-deps

WORKDIR /app

# 빌드 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libffi-dev libssl-dev git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ── CLIProxyAPI: 공식 릴리스와 소스 커밋을 함께 고정 ────────────────────────
FROM golang:1.26-bookworm AS cliproxyapi-builder
ARG CLIPROXYAPI_VERSION=7.2.152
ARG CLIPROXYAPI_COMMIT=c76dfd4e0edabab9000628b1560ab8ab379eadb8
WORKDIR /src
RUN git clone --depth 1 --branch "v${CLIPROXYAPI_VERSION}" \
        https://github.com/router-for-me/CLIProxyAPI.git . \
    && test "$(git rev-parse HEAD)" = "$CLIPROXYAPI_COMMIT" \
    && CGO_ENABLED=1 GOOS=linux go build -buildvcs=false \
        -ldflags="-s -w -X main.Version=${CLIPROXYAPI_VERSION} -X main.Commit=${CLIPROXYAPI_COMMIT}" \
        -o /out/CLIProxyAPI ./cmd/server/

FROM python:3.11-slim-bookworm AS cliproxyapi
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin cliproxyapi \
    && mkdir -p /data/cliproxyapi/auth /opt/cliproxyapi \
    && chown -R cliproxyapi:cliproxyapi /data/cliproxyapi
COPY --from=cliproxyapi-builder /out/CLIProxyAPI /usr/local/bin/CLIProxyAPI
COPY scripts/cliproxyapi_runtime.py /opt/cliproxyapi/runtime.py
ENV PYTHONDONTWRITEBYTECODE=1 \
    CLIPROXYAPI_BIND_HOST=0.0.0.0 \
    CLIPROXYAPI_AUTH_DIR=/data/cliproxyapi/auth
USER cliproxyapi
WORKDIR /tmp
EXPOSE 8317
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=5 \
    CMD ["python", "/opt/cliproxyapi/runtime.py", "healthcheck"]
ENTRYPOINT ["python", "/opt/cliproxyapi/runtime.py"]
CMD ["serve"]

# ── 스테이지 3: 최종 이미지 ───────────────────────────────────────────────────
FROM python:3.11-slim AS final

WORKDIR /app
ENV HOME=/app/persist/data/home \
    XDG_CACHE_HOME=/app/persist/cache \
    FLASK_ENV=production \
    NODE_ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_PERSIST_ROOT=/app/persist \
    APP_DATA_DIR=/app/persist/data \
    APP_DATA_BACKUP_DIR=/app/persist/backups \
    CONTENT_CACHE_DIR=/app/persist/cache/content \
    CHROMA_DB_PATH=/app/persist/data/chroma_db \
    GRAPH_STORE_PATH=/app/persist/data/graph_store \
    KNOWLEDGE_NOTES_DIR=/app/persist/data/notes \
    SHARE_PAGE_DIR=/app/persist/data/shared_pages \
    FEEDBACK_DATA_DIR=/app/persist/data/feedback \
    FEEDBACK_STORE_DIR=/app/persist/data/feedback \
    AUTO_BACKUP_ENABLED=false \
    PLATFORM_VOLUME_BACKUPS_ENABLED=false \
    BACKUP_INITIAL_DELAY_SECONDS=300 \
    BACKUP_SHUTDOWN_TIMEOUT_SECONDS=10 \
    BACKEND_GRACEFUL_TIMEOUT_SECONDS=600 \
    NGINX_DRAIN_TIMEOUT_SECONDS=605 \
    PROCESS_SHUTDOWN_TIMEOUT_SECONDS=605

# 런타임 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ffmpeg libatomic1 libstdc++6 nginx tini \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 복사
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# 빌더와 동일한 Debian/glibc Node 런타임을 그대로 복사합니다.
COPY --from=frontend-builder /usr/local/bin/node /usr/local/bin/node
COPY --from=frontend-builder /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx

# 애플리케이션 소스 복사
COPY . .

# Next.js 빌드 결과물 복사
COPY --from=frontend-builder /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder /app/frontend/node_modules ./frontend/node_modules

# Railway는 서비스당 하나의 볼륨만 지원합니다. 기존 상대경로 소비자는 모두
# 단일 mount 아래의 하위 디렉토리로 연결합니다.
RUN groupadd --gid 10001 appuser \
    && useradd --uid 10001 --gid appuser --home-dir /app/persist/data/home --no-create-home \
        --shell /usr/sbin/nologin appuser \
    && rm -rf /app/data /app/cache /app/logs /app-backups \
    && mkdir -p /app/persist/data/chroma_db /app/persist/data/home /app/persist/backups \
        /app/persist/cache /app/persist/logs /app/frontend/.next/cache \
    && ln -s /app/persist/data /app/data \
    && ln -s /app/persist/cache /app/cache \
    && ln -s /app/persist/logs /app/logs \
    && ln -s /app/persist/backups /app-backups \
    && chown -R appuser:appuser /app/persist /app/frontend/.next/cache

# Railway의 root-owned mount를 초기화하기 위해 supervisor만 root로 시작합니다.
# scripts/run_full_stack.py가 저장소 권한을 고친 직후 setuid/setgid로 영구 강등하며,
# Flask/Next.js/nginx/선택적 백업 데몬은 절대 root로 시작하지 않습니다.

# 포트 노출
EXPOSE 8080

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl --fail --silent --show-error "http://127.0.0.1:${PORT:-8080}/ready" >/dev/null || exit 1

# Flask + Next.js + nginx를 동일 산출물에서 실행합니다.
CMD ["tini", "--", "python", "scripts/run_full_stack.py", "full-stack"]
