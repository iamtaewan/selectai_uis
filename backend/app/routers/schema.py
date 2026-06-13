"""스키마 브라우징 라우터 — /api/v1/schema (FR-04 object_list 선택 / api-spec §8).

엔드포인트 (인덱스 #36~#38):
- GET /schema/owners                          접근 가능 스키마 목록 (is_current 표시)
- GET /schema/tables?owner=...                테이블 목록 (owner 미지정 시 인증 스키마)
- GET /schema/tables/{owner}/{table}/columns  컬럼 목록

모든 조회는 인증 사용자가 접근 가능한 객체만 — ALL_* 데이터 딕셔너리 뷰 사용.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, Query

from app.db import oracle
from app.schemas.models import Envelope
from app.services import common, schema_service

router = APIRouter(prefix="/schema", tags=["schema"])


@router.get("/owners", response_model=Envelope)
async def list_owners(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§8.1 소유자 목록 — data: {current_schema, owners: [{owner, is_current}]}."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await schema_service.list_owners(connection_id, recorder)
    return common.make_envelope(data, recorder.statements, started)


@router.get("/tables", response_model=Envelope)
async def list_tables(
    owner: str | None = Query(default=None, description="미지정 시 CURRENT_SCHEMA"),
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§8.2 테이블 목록 — data: list[TableInfo] (owner 포함 — ObjectRef 매핑용)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await schema_service.list_tables(connection_id, owner, recorder)
    return common.make_envelope(data, recorder.statements, started)


@router.get("/tables/{owner}/{table}/columns", response_model=Envelope)
async def list_columns(
    owner: str,
    table: str,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§8.3 컬럼 목록 — data: list[ColumnInfo]."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await schema_service.list_columns(connection_id, owner, table, recorder)
    return common.make_envelope(data, recorder.statements, started)
