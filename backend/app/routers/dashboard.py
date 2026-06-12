"""대시보드 라우터 — /api/v1/dashboard (FR-09, P1 / api-spec §9).

엔드포인트 (인덱스 #39):
- GET /dashboard/health  데모 상태 신호등 (커넥션·권한·Data Access·기본 프로파일·데모 스키마)
"""
from __future__ import annotations

from fastapi import APIRouter, Header

from app.errors import not_implemented
from app.schemas.models import Envelope

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/health", response_model=Envelope)
async def dashboard_health(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§9.1 일괄 점검 (짧은 타임아웃, 캐시 30초) — data: DashboardHealth."""
    raise not_implemented("대시보드 헬스")
