"""생성 리소스 대장 라우터 — /api/v1/resources (FR-10 / api-spec §10).

엔드포인트 (인덱스 #40~#42):
- GET    /resources           대장 목록 조회 (status/type 필터) — 로컬 resources.json
- DELETE /resources/{ledger_id}  개별 리소스 정리
- POST   /resources/cleanup   일괄 정리 실행 (cleanup_order 순, 실패 격리)
"""
from __future__ import annotations

from fastapi import APIRouter, Header, Query

from app.errors import not_implemented
from app.schemas.models import CleanupRequest, Envelope

router = APIRouter(prefix="/resources", tags=["resources"])


@router.get("", response_model=Envelope)
async def list_resources(
    status: str = Query(default="pending", description="pending(기본)/failed/done/all"),
    resource_type: str | None = Query(default=None),
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§10.1 대장 목록 — data: CleanupListResult. 로컬 파일 조회라 executed_sql=[]."""
    raise not_implemented("리소스 대장 목록")


@router.delete("/{ledger_id}", response_model=Envelope)
async def cleanup_resource(
    ledger_id: str,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§10.2 개별 정리 — data: CleanupItemResult 1건. 실패 시 200 + ok=false."""
    raise not_implemented("개별 리소스 정리")


@router.post("/cleanup", response_model=Envelope)
async def cleanup_resources(
    body: CleanupRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§10.3 일괄 정리 — data: CleanupResult. 한 항목 실패가 전체 실패가 되지 않는다."""
    raise not_implemented("일괄 정리")
