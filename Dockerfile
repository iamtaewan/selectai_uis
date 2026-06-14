# syntax=docker/dockerfile:1
# Select AI Studio — 단일 컨테이너 이미지
#  · 1단계: 프론트(Vite) 정적 빌드
#  · 2단계: 백엔드(FastAPI) 런타임 + 빌드된 SPA를 같은 포트(8000)에서 서빙
# python-oracledb는 thin 모드라 Oracle Instant Client가 필요 없습니다.

# ---- 1) 프론트엔드 빌드 ----------------------------------------------------------
FROM node:22-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ ./
RUN npm run build   # → /fe/dist (정적 SPA)

# ---- 2) 런타임 (백엔드 + 정적 SPA) ----------------------------------------------
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    APP_DATA_DIR=/data \
    STATIC_DIR=/app/app/static
WORKDIR /app

# uv 설치 후 백엔드 의존성 동기화 (uv.lock 고정)
RUN pip install --no-cache-dir uv
COPY backend/ ./
RUN uv sync --frozen --no-dev

# 빌드된 SPA를 백엔드 정적 디렉터리로 복사 (main.py가 STATIC_DIR에서 서빙)
COPY --from=frontend /fe/dist ./app/static

# 영속 데이터(커넥션·wallet·secret.key) 디렉터리 — 반드시 볼륨으로 마운트
RUN mkdir -p /data && chmod 700 /data
VOLUME ["/data"]

EXPOSE 8000
# 0.0.0.0 바인딩으로 컨테이너 외부 노출
CMD ["uv", "run", "--no-dev", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
