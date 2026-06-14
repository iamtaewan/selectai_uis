"""프로파일 라우터 — /api/v1/profiles (FR-04, FR-05 / api-spec §4).

엔드포인트 (인덱스 #9~#16):
- GET    /profiles/attribute-meta   검증 21개 속성 스키마/한국어 해설 (정적 — 헤더 불필요)
- POST   /profiles/preview          CREATE_PROFILE SQL 미리보기 (실행 안 함)
- POST   /profiles                  프로파일 생성
- GET    /profiles                  프로파일 목록
- GET    /profiles/{profile_name}   속성 상세 (USER_CLOUD_AI_PROFILE_ATTRIBUTES 뷰)
- PATCH  /profiles/{profile_name}   SET_ATTRIBUTE(S) 수정
- DELETE /profiles/{profile_name}   DROP_PROFILE
- POST   /profiles/{profile_name}/status  ENABLE/DISABLE (P1)
"""
from __future__ import annotations

from fastapi import APIRouter, Header, status

from app.db import oracle
from app.schemas.models import (
    Envelope,
    ProfileCreate,
    ProfileStatusRequest,
    ProfileUpdate,
)
from app.services import attribute_catalog, common, profile_service

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/attribute-meta", response_model=Envelope)
async def get_attribute_meta() -> Envelope:
    """§4.1 정적 메타데이터 — DB 미접속. data: verified_attributes(21개) + defaults."""
    started = common.start_timer()
    return common.make_envelope(attribute_catalog.attribute_meta_payload(), [], started)


@router.get("/credentials", response_model=Envelope)
async def list_credentials(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """현재 DB에서 사용 가능한 credential 이름 목록 — credential_name select 채움용.

    USER_CREDENTIALS의 자격증명 + (활성 시) OCI$RESOURCE_PRINCIPAL을 포함한다.
    """
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    names = await profile_service.list_credentials(connection_id, recorder)
    return common.make_envelope({"credentials": names}, recorder.statements, started)


@router.post("/preview", response_model=Envelope)
async def preview_profile(
    body: ProfileCreate,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.2 CREATE_PROFILE SQL 미리보기 — data: {sql_preview, warnings_ko}. 실행 안 함."""
    started = common.start_timer()
    # 미리보기=실행 동일 빌더 (architecture.md §2.2) — DB 접속 없이 표시문만 생성
    attributes = profile_service.build_attributes_dict(body)
    plan = profile_service.build_create_profile(body.profile_name, attributes)
    warnings = profile_service.build_warnings(attributes)
    return common.make_envelope(
        {"sql_preview": plan.display_sql, "warnings_ko": warnings}, [], started
    )


@router.post("", response_model=Envelope, status_code=status.HTTP_201_CREATED)
async def create_profile(
    body: ProfileCreate,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.3 프로파일 생성 (DBMS_CLOUD_AI.CREATE_PROFILE) — data: 생성 결과."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await profile_service.create_profile(connection_id, body, recorder)
    return common.make_envelope(result, recorder.statements, started)


@router.get("", response_model=Envelope)
async def list_profiles(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.4 목록 — data: list[ProfileSummary] (is_default는 앱 설정에서 합성)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await profile_service.list_profiles(connection_id, recorder)
    return common.make_envelope(result, recorder.statements, started)


@router.get("/{profile_name}", response_model=Envelope)
async def get_profile(
    profile_name: str,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.5 속성 상세 — data: ProfileDetail (showparameter 대체 — 뷰 기반)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await profile_service.get_profile_detail(connection_id, profile_name, recorder)
    return common.make_envelope(result, recorder.statements, started)


@router.patch("/{profile_name}", response_model=Envelope)
async def update_profile(
    profile_name: str,
    body: ProfileUpdate,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.6 SET_ATTRIBUTE(S) 수정 — preview_only=true면 sql_preview만 반환."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    if body.preview_only:
        plan = profile_service.build_update_attributes(profile_name, body.attributes)
        return common.make_envelope({"sql_preview": plan.display_sql}, [], started)
    result = await profile_service.update_profile(
        connection_id, profile_name, body.attributes, recorder
    )
    return common.make_envelope(result, recorder.statements, started)


@router.delete("/{profile_name}", response_model=Envelope)
async def delete_profile(
    profile_name: str,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.7 DROP_PROFILE — 200 + data: {dropped, default_cleared} (204 아님 — 기본 해제 통지)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await profile_service.drop_profile(connection_id, profile_name, recorder)
    return common.make_envelope(result, recorder.statements, started)


@router.post("/{profile_name}/status", response_model=Envelope)
async def set_profile_status(
    profile_name: str,
    body: ProfileStatusRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.9 ENABLE/DISABLE_PROFILE 토글 (P1)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await profile_service.set_profile_status(
        connection_id, profile_name, body.enabled, recorder
    )
    return common.make_envelope(result, recorder.statements, started)
