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

from app.errors import not_implemented
from app.schemas.models import (
    Envelope,
    ProfileCreate,
    ProfileStatusRequest,
    ProfileUpdate,
)

router = APIRouter(prefix="/profiles", tags=["profiles"])


@router.get("/attribute-meta", response_model=Envelope)
async def get_attribute_meta() -> Envelope:
    """§4.1 정적 메타데이터 — DB 미접속. data: verified_attributes(21개) + defaults."""
    raise not_implemented("속성 메타데이터")


@router.post("/preview", response_model=Envelope)
async def preview_profile(
    body: ProfileCreate,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.2 CREATE_PROFILE SQL 미리보기 — data: {sql_preview, warnings_ko}. 실행 안 함."""
    raise not_implemented("프로파일 미리보기")


@router.post("", response_model=Envelope, status_code=status.HTTP_201_CREATED)
async def create_profile(
    body: ProfileCreate,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.3 프로파일 생성 (DBMS_CLOUD_AI.CREATE_PROFILE) — data: 생성 결과."""
    raise not_implemented("프로파일 생성")


@router.get("", response_model=Envelope)
async def list_profiles(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.4 목록 — data: list[ProfileSummary] (is_default는 앱 설정에서 합성)."""
    raise not_implemented("프로파일 목록")


@router.get("/{profile_name}", response_model=Envelope)
async def get_profile(
    profile_name: str,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.5 속성 상세 — data: ProfileDetail (showparameter 대체 — 뷰 기반)."""
    raise not_implemented("프로파일 상세")


@router.patch("/{profile_name}", response_model=Envelope)
async def update_profile(
    profile_name: str,
    body: ProfileUpdate,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.6 SET_ATTRIBUTE(S) 수정 — preview_only=true면 sql_preview만 반환."""
    raise not_implemented("프로파일 수정")


@router.delete("/{profile_name}", response_model=Envelope)
async def delete_profile(
    profile_name: str,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.7 DROP_PROFILE — 200 + data: {dropped, default_cleared} (204 아님 — 기본 해제 통지)."""
    raise not_implemented("프로파일 삭제")


@router.post("/{profile_name}/status", response_model=Envelope)
async def set_profile_status(
    profile_name: str,
    body: ProfileStatusRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§4.9 ENABLE/DISABLE_PROFILE 토글 (P1)."""
    raise not_implemented("프로파일 상태 토글")
