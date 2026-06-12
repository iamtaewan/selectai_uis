"""권한 점검 라우터 — /api/v1/privileges (FR-03 / api-spec §3).

엔드포인트 (인덱스 #7, #8):
- GET  /privileges/check  권한 사전 점검 (fix_sql 미리보기 포함)
- POST /privileges/apply  원클릭 적용 + 자동 재점검

대상 커넥션은 X-Connection-Id 헤더 (api-spec §1.2).
"""
from __future__ import annotations

from fastapi import APIRouter, Header, Query

from app.errors import not_implemented
from app.schemas.models import Envelope, PrivilegeApplyRequest

router = APIRouter(prefix="/privileges", tags=["privileges"])


@router.get("/check", response_model=Envelope)
async def check_privileges(
    provider: str = Query(default="oci"),
    target_user: str = Query(default="ADMIN"),
    include: str | None = Query(default=None, description="CSV: feedback(P1), rag(P2)"),
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§3.1 점검 — data: PrivilegeCheckResult. provider=oci면 network_acl은 not_applicable."""
    raise not_implemented("권한 점검")


@router.post("/apply", response_model=Envelope)
async def apply_privileges(
    body: PrivilegeApplyRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§3.2 원클릭 적용 — data: PrivilegeApplyResult (recheck=true면 재점검 동봉)."""
    raise not_implemented("권한 적용")
