"""Comment 증강 라우터 — /api/v1/enrichment (FR-08 / api-spec §7).

엔드포인트 (인덱스 #30~#35):
- POST   /enrichment/demo-schema   모호 스키마 원클릭 생성/초기화 (seeds/movie_schema.sql)
- DELETE /enrichment/demo-schema   데모 스키마 정리 (seeds/movie_reset.sql)
- GET    /enrichment/comments      코멘트 조회 (ALL_TAB/COL_COMMENTS)
- PUT    /enrichment/comments      코멘트 적용 (DDL 미리보기 지원)
- POST   /enrichment/profile-pair  comments off/on 프로파일 쌍 생성
- POST   /enrichment/compare       전/후 좌우 비교 실행 (병렬, 한쪽 실패 허용)
"""
from __future__ import annotations

from fastapi import APIRouter, Header, Query, status

from app.db import oracle
from app.schemas.models import (
    CommentsApplyRequest,
    DemoSchemaRequest,
    EnrichCompareRequest,
    Envelope,
    ProfilePairRequest,
)
from app.services import common, enrichment_service

router = APIRouter(prefix="/enrichment", tags=["enrichment"])


@router.post("/demo-schema", response_model=Envelope, status_code=status.HTTP_201_CREATED)
async def create_demo_schema(
    body: DemoSchemaRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§7.1 모호 스키마(c1~c7) 생성/시드 — data: {tables, seeded_rows}."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await enrichment_service.create_demo_schema(connection_id, body.reset, recorder)
    return common.make_envelope(result, recorder.statements, started)


@router.delete("/demo-schema", response_model=Envelope)
async def delete_demo_schema(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§7.1 데모 테이블/비교용 프로파일 쌍 정리 (movie_reset.sql 기준)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await enrichment_service.drop_demo_schema(connection_id, recorder)
    return common.make_envelope(result, recorder.statements, started)


@router.get("/comments", response_model=Envelope)
async def get_comments(
    owner: str = Query(default="ADMIN"),
    table: str | None = Query(default=None),
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§7.2 코멘트 조회 — 테이블 코멘트 + 컬럼별 코멘트 목록."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await enrichment_service.get_comments(connection_id, owner, table, recorder)
    return common.make_envelope(result, recorder.statements, started)


@router.put("/comments", response_model=Envelope)
async def apply_comments(
    body: CommentsApplyRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§7.3 COMMENT DDL 적용 — preview_only=true면 sql_preview 배열만 반환."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    if body.preview_only:
        # 미리보기=실행 동일 빌더 — 실행 없이 DDL 목록만 (FR-08 수용 기준)
        statements = enrichment_service.build_comment_ddl(body)
        return common.make_envelope({"sql_preview": statements}, [], started)
    result = await enrichment_service.apply_comments(connection_id, body, recorder)
    return common.make_envelope(result, recorder.statements, started)


@router.post("/profile-pair", response_model=Envelope, status_code=status.HTTP_201_CREATED)
async def create_profile_pair(
    body: ProfilePairRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§7.4 전/후 프로파일 쌍 생성 — data: {profile_off, profile_on}."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await enrichment_service.create_profile_pair(connection_id, body, recorder)
    return common.make_envelope(result, recorder.statements, started)


@router.post("/compare", response_model=Envelope)
async def compare_enrichment(
    body: EnrichCompareRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§7.5 전/후 비교 실행 — data: EnrichCompareResult (한쪽 실패는 error 필드로)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await enrichment_service.compare(connection_id, body, recorder)
    return common.make_envelope(result, recorder.statements, started)
