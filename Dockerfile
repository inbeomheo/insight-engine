# Insight Engine Dockerfile (F9-10)
# 멀티스테이지 빌드: Next.js 프론트엔드 + Flask 백엔드

# ── 스테이지 1: Next.js 빌드 ──────────────────────────────────────────────────
FROM node:20-bookworm-slim AS frontend-builder

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

# ── 스테이지 3: 최종 이미지 ───────────────────────────────────────────────────
FROM python:3.11-slim AS final

WORKDIR /app

# 비루트 사용자. Kubernetes runAsUser와 맞추기 위해 UID/GID를 고정한다.
RUN groupadd --system --gid 999 appuser \
    && useradd --system --uid 999 --gid appuser --home-dir /app --shell /bin/false appuser \
    && chown 999:999 /app

# 런타임 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 복사
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Next.js 서버 실행용 Node 런타임. final stage에서 외부 설치 스크립트를
# 다시 내려받지 않고 frontend-builder stage의 검증된 런타임을 재사용한다.
COPY --from=frontend-builder /usr/local/bin/node /usr/local/bin/node

# 릴리즈 메타데이터
ARG APP_VERSION=v2.0
ARG APP_RELEASE=local
ARG GIT_SHA=local
ARG BUILD_TIME=unknown
ENV APP_VERSION=$APP_VERSION \
    APP_RELEASE=$APP_RELEASE \
    GIT_SHA=$GIT_SHA \
    BUILD_TIME=$BUILD_TIME \
    SENTRY_RELEASE=$APP_RELEASE \
    FLASK_ENV=production \
    FLASK_DEBUG=0 \
    PORT=5001 \
    HOME=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    XDG_CACHE_HOME=/app/cache/xdg \
    APP_DATA_DIR=/app/data \
    AGENT_DB_PATH=/app/data/agent_state.db \
    CHROMA_DB_PATH=/app/data/chroma_db \
    FEEDBACK_DATA_DIR=/app/data/feedback \
    FEEDBACK_STORE_DIR=/app/data/feedback \
    FINETUNE_OUTPUT_DIR=/app/data/finetune \
    GRAPH_STORE_PATH=/app/data/graph_store \
    JOB_STORE_DIR=/app/data/jobs \
    PREFERENCE_DATA_PATH=/app/data/preferences.jsonl \
    SHARE_PAGE_DIR=/app/data/shared_pages \
    USER_MEMORY_PATH=/app/data/user_memory \
    APP_CACHE_DIR=/app/cache \
    AI_CACHE_DB=/app/cache/ai_cache.db \
    SCHEDULER_HEARTBEAT_FILE=/tmp/insight-engine-scheduler.heartbeat
LABEL org.opencontainers.image.title="Insight Engine" \
      org.opencontainers.image.version=$APP_VERSION \
      org.opencontainers.image.revision=$GIT_SHA \
      org.opencontainers.image.created=$BUILD_TIME \
      org.opencontainers.image.description="Insight Engine production image"

# 애플리케이션 소스 복사
COPY --chown=999:999 . .

# Next.js 빌드 결과물 복사
COPY --chown=999:999 --from=frontend-builder /app/frontend/.next ./frontend/.next
COPY --chown=999:999 --from=frontend-builder /app/frontend/node_modules ./frontend/node_modules

# 런타임 쓰기 지점. 배포 compose에서는 루트 파일시스템을 read-only로 두고
# 이 경로들만 volume/tmpfs로 열어 둔다.
RUN mkdir -p \
        /app/data/chroma_db \
        /app/backups \
        /app/backup-replica \
        /app/cache \
        /app/logs \
        /app/.gunicorn \
        /app/frontend/.next/cache \
        /app/frontend/.next/diagnostics \
    && chown -R 999:999 \
        /app/data \
        /app/backups \
        /app/backup-replica \
        /app/cache \
        /app/logs \
        /app/.gunicorn \
        /app/frontend/.next/cache \
        /app/frontend/.next/diagnostics
USER 999:999

# 포트 노출
EXPOSE 5001 3000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# 기본 시작 명령. 환경변수가 완비되지 않은 production 실행은 앱 부팅 검증에서 fail-closed 된다.
CMD ["gunicorn", "--workers=2", "--threads=4", "--timeout=300", "--bind=0.0.0.0:5001", "app:app"]
