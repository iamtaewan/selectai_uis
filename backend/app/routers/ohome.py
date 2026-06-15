"""o-home-shopping 데이터 적재 라우터 — 점검 / DDL 생성 / 테이블별 CSV 적재.

- GET  /ohome/check       : 데이터 경로·CSV 존재·테이블 인벤토리
- POST /ohome/ddl         : DDL 47 테이블 생성 (overwrite 옵션)
- POST /ohome/load-table  : 테이블 1개 CSV 벌크 적재 (프론트가 순차 호출)
"""
from __future__ import annotations

from fastapi import APIRouter, Header

from app.db import oracle
from app.schemas.models import Envelope, OhomeDdlRequest, OhomeLoadRequest
from app.services import common, ohome_service

router = APIRouter(prefix="/ohome", tags=["ohome"])


@router.get("/check", response_model=Envelope)
async def ohome_check(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await ohome_service.check_ohome(connection_id, recorder)
    return common.make_envelope(data, recorder.statements, started)


@router.post("/ddl", response_model=Envelope)
async def ohome_ddl(
    body: OhomeDdlRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await ohome_service.setup_ddl(connection_id, overwrite=body.overwrite, recorder=recorder)
    return common.make_envelope(data, recorder.statements, started)


@router.post("/load-table", response_model=Envelope)
async def ohome_load_table(
    body: OhomeLoadRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await ohome_service.load_table(connection_id, body.table, recorder=recorder)
    return common.make_envelope(data, recorder.statements, started)


@router.post("/load-all", response_model=Envelope)
async def ohome_load_all(
    body: OhomeDdlRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """비동기 전체 적재 시작 — 즉시 반환, 진행은 /ohome/load-status 폴링."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    data = await ohome_service.start_load_all(connection_id, overwrite=body.overwrite)
    return common.make_envelope(data, [], started)


@router.get("/load-status", response_model=Envelope)
async def ohome_load_status(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """적재 진행 상태 스냅샷."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    data = ohome_service.get_load_status(connection_id) or {
        "running": False,
        "finished": False,
        "phase": "대기",
        "total": 0,
        "done": 0,
        "rows": 0,
        "ok": 0,
        "failed": 0,
        "steps": [],
    }
    return common.make_envelope(data, [], started)
