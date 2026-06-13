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

import time

from fastapi import APIRouter, File, UploadFile, status

from app.schemas.models import (
    ConnectionCreate,
    ConnectionUpdate,
    Envelope,
    WalletGenerateRequest,
)
from app.services import connection_service

router = APIRouter(prefix="/connections", tags=["connections"])


def _envelope(data: object, executed_sql: list[str], started: float) -> Envelope:
    """성공 envelope 생성 (api-spec §1.3) — elapsed_ms는 서버 측 총 처리 시간."""
    return Envelope(
        data=data,
        executed_sql=executed_sql,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )


@router.post("/wallet", response_model=Envelope)
async def upload_wallet(file: UploadFile = File(...)) -> Envelope:
    """§2.1 wallet zip 업로드 — data: WalletUploadResult."""
    started = time.perf_counter()
    zip_bytes = await file.read()
    result = await connection_service.upload_wallet(zip_bytes)
    return _envelope(result, [], started)


@router.post("/wallet/generate", response_model=Envelope)
async def generate_wallet(body: WalletGenerateRequest) -> Envelope:
    """§2.7 wallet 자동 다운로드 (OCI CLI) — data: WalletGenerateResult.

    executed_sql[]에는 SQL 대신 OCI CLI 명령 원문(--password는 ***MASKED***)을 담는다.
    """
    started = time.perf_counter()
    result, executed_cli = await connection_service.generate_wallet(body)
    return _envelope(result, executed_cli, started)


@router.post("", response_model=Envelope, status_code=status.HTTP_201_CREATED)
async def create_connection(body: ConnectionCreate) -> Envelope:
    """§2.2 커넥션 생성(검증 포함) — data: ConnectionOut."""
    started = time.perf_counter()
    result, executed_sql = await connection_service.create_connection(body)
    return _envelope(result, executed_sql, started)


@router.get("", response_model=Envelope)
async def list_connections() -> Envelope:
    """§2.3 커넥션 목록 — data: list[ConnectionOut] (last_used_at 내림차순)."""
    started = time.perf_counter()
    result = await connection_service.list_connections()
    return _envelope(result, [], started)


@router.post("/{connection_id}/test", response_model=Envelope)
async def test_connection(connection_id: str) -> Envelope:
    """§2.4 연결 테스트 (5초 타임아웃) — data: ConnectionTestResult. 실패도 200."""
    started = time.perf_counter()
    result, executed_sql = await connection_service.test_connection(connection_id)
    return _envelope(result, executed_sql, started)


@router.patch("/{connection_id}", response_model=Envelope)
async def update_connection(connection_id: str, body: ConnectionUpdate) -> Envelope:
    """§2.6 커넥션 수정 — data: ConnectionOut."""
    started = time.perf_counter()
    result, executed_sql = await connection_service.update_connection(connection_id, body)
    return _envelope(result, executed_sql, started)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_connection(connection_id: str) -> None:
    """§2.5 커넥션 삭제 — 풀 종료 + 자격/메타 삭제, wallet은 참조 없을 때만 삭제."""
    await connection_service.delete_connection(connection_id)
