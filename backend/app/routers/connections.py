"""커넥션 라우터 — /api/v1/connections (FR-01, FR-02 / api-spec §2).

엔드포인트 (인덱스 #1, #1a, #2~#6):
- POST   /connections/wallet           wallet zip 업로드 + TNS alias 추출
- POST   /connections/wallet/generate  wallet 자동 다운로드 (OCI CLI)
- POST   /connections                  커넥션 생성(접속 검증 포함)
- GET    /connections                  커넥션 목록
- POST   /connections/{connection_id}/test  연결 테스트 (5초 타임아웃)
- PATCH  /connections/{connection_id}  커넥션 수정
- DELETE /connections/{connection_id}  커넥션 삭제
"""
from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, status

from app.errors import not_implemented
from app.schemas.models import (
    ConnectionCreate,
    ConnectionUpdate,
    Envelope,
    WalletGenerateRequest,
)

router = APIRouter(prefix="/connections", tags=["connections"])


@router.post("/wallet", response_model=Envelope)
async def upload_wallet(file: UploadFile = File(...)) -> Envelope:
    """§2.1 wallet zip 업로드 — data: WalletUploadResult."""
    raise not_implemented("wallet 업로드")


@router.post("/wallet/generate", response_model=Envelope)
async def generate_wallet(body: WalletGenerateRequest) -> Envelope:
    """§2.7 wallet 자동 다운로드 (OCI CLI) — data: WalletGenerateResult.

    executed_sql[]에는 SQL 대신 OCI CLI 명령 원문(--password는 ***MASKED***)을 담는다.
    """
    raise not_implemented("wallet 자동 다운로드")


@router.post("", response_model=Envelope, status_code=status.HTTP_201_CREATED)
async def create_connection(body: ConnectionCreate) -> Envelope:
    """§2.2 커넥션 생성(검증 포함) — data: ConnectionOut."""
    raise not_implemented("커넥션 생성")


@router.get("", response_model=Envelope)
async def list_connections() -> Envelope:
    """§2.3 커넥션 목록 — data: list[ConnectionOut] (last_used_at 내림차순)."""
    raise not_implemented("커넥션 목록")


@router.post("/{connection_id}/test", response_model=Envelope)
async def test_connection(connection_id: str) -> Envelope:
    """§2.4 연결 테스트 (5초 타임아웃) — data: ConnectionTestResult. 실패도 200."""
    raise not_implemented("커넥션 테스트")


@router.patch("/{connection_id}", response_model=Envelope)
async def update_connection(connection_id: str, body: ConnectionUpdate) -> Envelope:
    """§2.6 커넥션 수정 — data: ConnectionOut."""
    raise not_implemented("커넥션 수정")


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(connection_id: str) -> None:
    """§2.5 커넥션 삭제 — 풀 종료 + 자격/메타 삭제, wallet은 참조 없을 때만 삭제."""
    raise not_implemented("커넥션 삭제")
