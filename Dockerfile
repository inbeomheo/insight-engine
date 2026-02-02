# Cloud Run 배포용 Dockerfile
FROM python:3.11-slim

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# 시스템 의존성 설치 (cryptography 빌드용)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 앱 코드 복사
COPY . .

# 비root 사용자로 실행 (보안)
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Cloud Run은 PORT 환경변수를 자동 주입
ENV PORT=8080
EXPOSE 8080

# Gunicorn 실행
CMD exec gunicorn app:app \
    --bind 0.0.0.0:$PORT \
    --workers 1 \
    --threads 4 \
    --timeout 120 \
    --preload
