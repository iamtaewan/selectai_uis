"""FastAPI 앱 진입점 — Select AI Demo Studio Backend.

스캐폴딩 규칙(병렬 작업 충돌 방지):
이 파일은 스캐폴딩/통합 단계에서만 수정한다. 구현 에이전트는 라우터 등록부와
예외 핸들러를 변경하지 않는다 — 모든 라우터는 이미 /api/v1 prefix로 등록되어 있다.
"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.errors import AppError, map_oracle_error
from app.routers import (
    chat,
    clone,
    connections,
    dashboard,
    enrichment,
    meta,
    ohome,
    privileges,
    profiles,
    resources,
    schema,
    selectai,
    settings as settings_router,
)

logger = logging.getLogger("selectai")

API_PREFIX = "/api/v1"

app = FastAPI(
    title="Select AI Demo Studio API",
    version="0.1.0",
    description="Oracle ADB 26ai Select AI(NL2SQL) 데모 도구 백엔드",
)

# CORS — Vite dev 서버 (배포 시에는 nginx 동일 출처 프록시라 불필요)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """도메인 오류 → api-spec §1.4 오류 envelope."""
    return JSONResponse(status_code=exc.status_code, content=exc.to_body())


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """예상치 못한 오류 — oracledb 오류는 §1.5 매핑, 그 외 500 envelope.

    비밀값은 errors/마스킹 필터(security.crypto)에서 처리되므로 여기서는 원문 노출 금지
    원칙만 지킨다 (detail은 오류 클래스명 + 메시지).
    """
    message = str(exc)
    if exc.__class__.__module__.startswith("oracledb"):
        mapped = map_oracle_error(message)
        return JSONResponse(status_code=mapped.status_code, content=mapped.to_body())
    logger.exception("처리되지 않은 오류: %s", message)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "app_code": "INTERNAL_ERROR",
                "message_ko": "서버 내부 오류가 발생했습니다.",
                "hint_ko": "백엔드 로그를 확인하세요.",
                "detail": f"{exc.__class__.__name__}: {message}",
                "retryable": False,
                "executed_sql": [],
                "docs_ref": None,
            }
        },
    )


@app.get(f"{API_PREFIX}/health")
async def health() -> dict:
    """헬스 체크 — 배포(nginx)/프론트 가용성 확인용. DB는 건드리지 않는다."""
    started = time.perf_counter()
    settings = get_settings()
    return {
        "data": {"status": "ok", "app_env": settings.app_env, "version": app.version},
        "executed_sql": [],
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
    }


# ---- 라우터 등록 (api-spec §13 인덱스 42개 전체 — 구현 에이전트는 이 블록 수정 금지) ----
app.include_router(connections.router, prefix=API_PREFIX)   # #1, #1a, #2~#6
app.include_router(privileges.router, prefix=API_PREFIX)    # #7~#8
app.include_router(profiles.router, prefix=API_PREFIX)      # #9~#16
app.include_router(settings_router.router, prefix=API_PREFIX)  # #17 (GET/PUT)
app.include_router(selectai.router, prefix=API_PREFIX)      # #18~#21
app.include_router(chat.router, prefix=API_PREFIX)          # #22~#29
app.include_router(enrichment.router, prefix=API_PREFIX)    # #30~#35
app.include_router(schema.router, prefix=API_PREFIX)        # #36~#38
app.include_router(dashboard.router, prefix=API_PREFIX)     # #39
app.include_router(resources.router, prefix=API_PREFIX)     # #40~#42
app.include_router(meta.router, prefix=API_PREFIX)          # 메타 강화 (comment/annotation/grok 제안)
app.include_router(clone.router, prefix=API_PREFIX)         # SH 스키마 복제 (테이블·제약·뷰)
app.include_router(ohome.router, prefix=API_PREFIX)         # o-home-shopping 데이터 적재 (버킷 CSV)


# ---- 정적 SPA 서빙 (단일 컨테이너 배포) ----------------------------------------
# 빌드된 프론트(dist)를 STATIC_DIR로 복사해 두면 FastAPI가 같은 포트에서 SPA를 서빙한다.
# /api/v1 라우터는 위에서 이미 등록되어 우선 매칭되고, 그 외 경로는 정적 파일 또는
# index.html(클라이언트 라우팅 폴백)로 응답한다. STATIC_DIR가 없으면(개발 환경) 비활성.
_static_dir = Path(os.environ.get("STATIC_DIR", Path(__file__).parent / "static"))
if (_static_dir / "index.html").is_file():
    _assets = _static_dir / "assets"
    if _assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        """비-API 경로 → 정적 파일이 있으면 그 파일, 없으면 index.html (SPA 라우팅)."""
        if full_path.startswith("api/"):
            # 매칭 안 된 API 경로는 SPA로 흘리지 않고 404 JSON 유지
            raise AppError(
                status_code=404, code="NOT_FOUND", app_code="NOT_FOUND",
                message_ko="존재하지 않는 API 경로입니다.",
            )
        candidate = _static_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_static_dir / "index.html")
