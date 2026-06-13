#!/usr/bin/env bash
# Select AI Demo Studio — 로컬 개발 동시 기동 스크립트
# 백엔드(FastAPI :8000) + 프론트엔드(Vite :5173)를 함께 띄운다.
# 프론트 dev 서버가 /api → :8000으로 프록시하므로 브라우저는 http://localhost:5173 만 열면 된다.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

cleanup() {
  echo "\n[run.sh] 종료 중…"
  [[ -n "${BACK_PID:-}" ]] && kill "$BACK_PID" 2>/dev/null || true
  [[ -n "${FRONT_PID:-}" ]] && kill "$FRONT_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "[run.sh] 백엔드 기동 (FastAPI :8000)…"
( cd "$BACKEND" && uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload ) &
BACK_PID=$!

echo "[run.sh] 프론트엔드 기동 (Vite :5173)…"
( cd "$FRONTEND" && npm run dev ) &
FRONT_PID=$!

echo "[run.sh] 준비 완료 → 브라우저에서 http://localhost:5173 열기 (Ctrl+C로 동시 종료)"
wait
