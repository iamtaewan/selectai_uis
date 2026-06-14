"""메타 강화 라우터 — /api/v1/meta (FR-04 보강).

준비하기 단계에서 대상 테이블의 comment/annotation을 확인·추가하고,
필요 시 grok-4 LLM으로 데이터 분석 기반 메타데이터 제안을 받는다.

엔드포인트:
- GET  /meta/profile-tables?profile=  프로파일 object_list(대상 테이블) 목록
- GET  /meta/table-metadata?owner=&table=  컬럼 comment/annotation 현황
- PUT  /meta/comments       COMMENT 적용
- PUT  /meta/annotations    ANNOTATIONS 적용
- POST /meta/suggest        grok-4 데이터 분석 제안 (샘플 행 LLM 전송)
"""
from __future__ import annotations

from fastapi import APIRouter, Header, Query

from app.db import oracle
from app.schemas.models import (
    Envelope,
    MetaAnnotationRequest,
    MetaApplyRequest,
    MetaCommentRequest,
    MetaGrantRequest,
    MetaSuggestRequest,
)
from app.services import common, meta_service

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/profile-tables", response_model=Envelope)
async def profile_tables(
    profile: str = Query(...),
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """선택 프로파일의 object_list 대상 테이블 — data: {tables: [{owner, name}]}."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    tables = await meta_service.list_profile_tables(connection_id, profile, recorder)
    return common.make_envelope({"tables": tables}, recorder.statements, started)


@router.get("/privilege-check", response_model=Envelope)
async def privilege_check(
    owner: str = Query(...),
    table: str = Query(...),
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """메타 보강 권한 점검 — 소유/보유/부여 가능 여부."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await meta_service.check_privileges(connection_id, owner, table, recorder)
    return common.make_envelope(data, recorder.statements, started)


@router.post("/grant", response_model=Envelope)
async def grant(
    body: MetaGrantRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """현재 접속 사용자에게 시스템 권한 부여 시도 (부여 권한 없으면 항목별 실패)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await meta_service.grant_privileges(connection_id, body.privileges, recorder)
    return common.make_envelope(data, recorder.statements, started)


@router.get("/table-metadata", response_model=Envelope)
async def table_metadata(
    owner: str = Query(...),
    table: str = Query(...),
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """컬럼별 data_type/comment/annotations + 테이블 코멘트."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await meta_service.get_table_metadata(connection_id, owner, table, recorder)
    return common.make_envelope(data, recorder.statements, started)


@router.put("/comments", response_model=Envelope)
async def apply_comment(
    body: MetaCommentRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await meta_service.apply_comment(
        connection_id, body.owner, body.table, body.column, body.comment, recorder
    )
    return common.make_envelope(data, recorder.statements, started)


@router.put("/annotations", response_model=Envelope)
async def apply_annotation(
    body: MetaAnnotationRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await meta_service.apply_annotation(
        connection_id, body.owner, body.table, body.column, body.name, body.value,
        body.operation, recorder,
    )
    return common.make_envelope(data, recorder.statements, started)


@router.post("/suggest", response_model=Envelope)
async def suggest(
    body: MetaSuggestRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """grok-4 메타 제안 — 샘플 행(최대 5) + 프로파일 관계 분석. table/column 레벨 구조화 제안."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await meta_service.suggest(
        connection_id, body.owner, body.table, body.profile, recorder
    )
    return common.make_envelope(data, recorder.statements, started)


@router.post("/apply", response_model=Envelope)
async def apply_batch(
    body: MetaApplyRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """선택/일괄 적용 — 항목별 comment + annotations DDL 적용, 항목별 결과 반환."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await meta_service.apply_batch(
        connection_id, body.owner, body.table, body.items, recorder
    )
    return common.make_envelope(data, recorder.statements, started)
