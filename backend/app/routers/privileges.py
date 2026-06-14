"""권한 점검 라우터 — /api/v1/privileges (FR-03 / api-spec §3).

엔드포인트 (인덱스 #7, #8):
- GET  /privileges/check         권한 사전 점검 (fix_sql/remove_sql 미리보기 포함)
- POST /privileges/apply         원클릭 적용/제거(operation) + 자동 재점검
- GET  /privileges/oci-defaults  ~/.oci/config 기반 User Principal 폼 기본값

대상 커넥션은 X-Connection-Id 헤더 (api-spec §1.2).
"""
from __future__ import annotations

from fastapi import APIRouter, Header, Query

from app.db import oracle
from app.schemas.models import Envelope, OciCliDefaults, PrivilegeApplyRequest
from app.services import common, prereq_service

router = APIRouter(prefix="/privileges", tags=["privileges"])


@router.get("/oci-defaults", response_model=Envelope)
async def oci_defaults() -> Envelope:
    """~/.oci/config + key_file 기반 User Principal(API 서명 키) 폼 기본값.

    DB 비의존 — 로컬 파일만 읽는다. config 없으면 available=False.
    """
    started = common.start_timer()
    data = OciCliDefaults(**prereq_service.read_oci_cli_defaults())
    return common.make_envelope(data, [], started)


@router.get("/check", response_model=Envelope)
async def check_privileges(
    provider: str = Query(default="oci"),
    target_user: str = Query(default="ADMIN"),
    include: str | None = Query(default=None, description="CSV: feedback(P1), rag(P2)"),
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§3.1 점검 — data: PrivilegeCheckResult. provider=oci면 network_acl은 not_applicable."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    include_set = {item.strip() for item in (include or "").split(",") if item.strip()}
    result = await prereq_service.run_checks(
        connection_id,
        provider=provider,
        target_user=target_user,
        include=include_set,
        recorder=recorder,
    )
    return common.make_envelope(result, recorder.statements, started)


@router.post("/apply", response_model=Envelope)
async def apply_privileges(
    body: PrivilegeApplyRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§3.2 원클릭 적용 — data: PrivilegeApplyResult (recheck=true면 재점검 동봉)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await prereq_service.apply_items(connection_id, body, recorder)
    return common.make_envelope(result, recorder.statements, started)
