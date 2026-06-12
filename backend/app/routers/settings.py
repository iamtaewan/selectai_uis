"""앱 설정 라우터 — /api/v1/settings (FR-05 / api-spec §4.8).

엔드포인트 (인덱스 #17):
- GET /settings/default-profile  앱 수준 기본 프로파일 조회 (settings.json)
- PUT /settings/default-profile  기본 프로파일 설정 (존재·ENABLED 검증 후 저장)

설계 결정: SET_PROFILE(세션 상태)은 사용하지 않는다 — 기본 프로파일은 커넥션별 앱 설정.
"""
from __future__ import annotations

from fastapi import APIRouter, Header

from app.errors import not_implemented
from app.schemas.models import DefaultProfileSetting, Envelope

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("/default-profile", response_model=Envelope)
async def get_default_profile(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.8 기본 프로파일 조회 — data: {profile_name}."""
    raise not_implemented("기본 프로파일 조회")


@router.put("/default-profile", response_model=Envelope)
async def put_default_profile(
    body: DefaultProfileSetting,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.8 기본 프로파일 설정 — 404 PROFILE_NOT_FOUND / 409 PROFILE_DISABLED."""
    raise not_implemented("기본 프로파일 설정")
