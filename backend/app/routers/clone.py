"""SH 스키마 복제 라우터 — 권한 점검 / 복제 실행.

- GET  /clone/sh/check : 대상 user의 SH 읽기 권한 + 복제 인벤토리
- POST /clone/sh/run   : SH → 대상 user 스키마 복제 (테이블·제약·뷰), 단계별 로그 반환
"""
from __future__ import annotations

from fastapi import APIRouter, Header

from app.db import oracle
from app.schemas.models import CloneRequest, Envelope
from app.services import clone_service, common

router = APIRouter(prefix="/clone", tags=["clone"])


@router.get("/sh/check", response_model=Envelope)
async def clone_sh_check(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await clone_service.check_sh_access(connection_id, recorder)
    return common.make_envelope(data, recorder.statements, started)


@router.post("/sh/run", response_model=Envelope)
async def clone_sh_run(
    body: CloneRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await clone_service.clone_sh(connection_id, overwrite=body.overwrite, recorder=recorder)
    return common.make_envelope(data, recorder.statements, started)
