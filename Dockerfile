# Insight Engine Dockerfile (F9-10)
# 멀티스테이지 빌드: Next.js 프론트엔드 + Flask 백엔드

# ── 스테이지 1: Next.js 빌드 ──────────────────────────────────────────────────
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build
RUN npm prune --omit=dev

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

# 런타임 의존성
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python 패키지 복사
COPY --from=python-deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=python-deps /usr/local/bin /usr/local/bin

# Node.js 설치 (Next.js 서버 실행용)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# 애플리케이션 소스 복사
COPY . .

# Next.js 빌드 결과물 복사
COPY --from=frontend-builder /app/frontend/.next ./frontend/.next
COPY --from=frontend-builder /app/frontend/node_modules ./frontend/node_modules

# 데이터 디렉토리
RUN mkdir -p /app/data/chroma_db /app/cache /app/logs

# 비루트 사용자
RUN useradd -r -s /bin/false appuser \
    && chown -R appuser:appuser /app
USER appuser

# 포트 노출
EXPOSE 5001 3000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5001/health || exit 1

# 기본 시작 명령: gunicorn 프로덕션 WSGI 서버
# docker-compose 또는 외부 오케스트레이터에서 오버라이드 가능
CMD ["gunicorn", "-w", "4", "-k", "gthread", "--threads", "8", "--timeout", "120", "-b", "0.0.0.0:5001", "app:app"]
