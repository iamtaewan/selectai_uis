"""앱 설정 라우터 — /api/v1/settings (FR-05 / api-spec §4.8).

엔드포인트 (인덱스 #17):
- GET /settings/default-profile  앱 수준 기본 프로파일 조회 (settings.json)
- PUT /settings/default-profile  기본 프로파일 설정 (존재·ENABLED 검증 후 저장)

설계 결정: SET_PROFILE(세션 상태)은 사용하지 않는다 — 기본 프로파일은 커넥션별 앱 설정.
"""
from __future__ import annotations

from fastapi import APIRouter, Header

from app.db import oracle
from app.errors import AppError
from app.schemas.models import DefaultProfileSetting, Envelope
from app.services import common, profile_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/default-profile", response_model=Envelope)
async def get_default_profile(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.8 기본 프로파일 조회 — data: {profile_name}. settings.json 조회 (DB 미사용)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    profile_name = await common.get_default_profile(connection_id)
    return common.make_envelope({"profile_name": profile_name}, [], started)


@router.put("/default-profile", response_model=Envelope)
async def put_default_profile(
    body: DefaultProfileSetting,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.8 기본 프로파일 설정 — 404 PROFILE_NOT_FOUND / 409 PROFILE_DISABLED."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    # 존재·ENABLED 검증 후 저장 (api-spec §4.8)
    status = await profile_service.get_profile_status(
        connection_id, body.profile_name, recorder
    )
    if status != "ENABLED":
        raise AppError(
            status_code=409,
            code="PROFILE_DISABLED",
            app_code="PROFILE_DISABLED",
            message_ko=f"프로파일 '{body.profile_name}'이(가) DISABLED 상태입니다.",
            hint_ko="프로파일 상세 화면에서 ENABLE로 전환한 뒤 다시 지정하세요.",
            executed_sql=recorder.statements,
        )
    await common.set_default_profile(connection_id, body.profile_name.upper())
    return common.make_envelope(
        {"profile_name": body.profile_name.upper()}, recorder.statements, started
    )
