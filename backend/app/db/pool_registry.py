"""커넥션 풀 레지스트리 — connection_id → oracledb.AsyncConnectionPool.

architecture.md §3.2: 저장 커넥션 1개당 풀 1개 (min=0, max=4, increment=1,
getmode=POOL_GETMODE_WAIT, wait_timeout=10s). lazy 생성 + 30분 유휴 close.
세션 상태를 남기는 호출 금지 (SET_PROFILE/SET_CONVERSATION_ID — 원칙 1).

call_timeout 계층 (api-spec §12.2): 테스트 5s / 일반 15s / 권한 30s /
showsql 60s / GENERATE 120s — 상수로 노출해 서비스 레이어가 선택한다.
"""
from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import oracledb

from app.config import get_settings
from app.db import local_store
from app.errors import AppError, map_oracle_error
from app.security.crypto import decrypt_secret

# call_timeout 계층 (ms) — api-spec §12.2 표
CALL_TIMEOUT_TEST_MS = 5_000          # 연결 테스트 (FR-02 수용 기준)
CALL_TIMEOUT_DEFAULT_MS = 15_000      # 메타데이터/일반 쿼리
CALL_TIMEOUT_PRIVILEGE_MS = 30_000    # 권한 점검/적용
CALL_TIMEOUT_SHOWSQL_MS = 60_000      # GENERATE showsql/showprompt
CALL_TIMEOUT_GENERATE_MS = 120_000    # GENERATE runsql/narrate/chat 등

IDLE_CLOSE_SECONDS = 30 * 60          # 30분 미사용 시 풀 close (architecture.md §3.2)
_REAP_INTERVAL_SECONDS = 60
_LAST_USED_WRITE_THROTTLE_SECONDS = 60  # last_used_at JSON 기록 스로틀


@dataclass
class _PoolEntry:
    """풀 + 유휴 추적 메타."""

    pool: Any
    last_used: float = field(default_factory=time.monotonic)
    last_used_persisted: float = 0.0


_pools: dict[str, _PoolEntry] = {}
_reaper_loops: set[int] = set()       # 루프별 리퍼 태스크 중복 생성 방지


def build_connect_kwargs(
    *,
    username: str,
    password: str,
    tns_alias: str,
    wallet_dir: str,
    wallet_password: str | None = None,
) -> dict[str, Any]:
    """thin 모드 mTLS 접속 파라미터 (architecture.md §3.1) — 풀/단건 접속 공용."""
    kwargs: dict[str, Any] = {
        "user": username,
        "password": password,
        "dsn": tns_alias,
        "config_dir": wallet_dir,
        "wallet_location": wallet_dir,
    }
    if wallet_password:
        kwargs["wallet_password"] = wallet_password
    return kwargs


async def _load_records(connection_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    """커넥션·wallet 레코드 로드 — 없으면 404 CONNECTION_NOT_FOUND (api-spec §1.2)."""
    record = await local_store.get_connection_record(connection_id)
    if record is None:
        raise AppError(
            status_code=404,
            code="CONNECTION_NOT_FOUND",
            app_code="CONNECTION_NOT_FOUND",
            message_ko="존재하지 않는 커넥션입니다.",
            hint_ko="커넥션 목록에서 유효한 커넥션을 선택하세요.",
        )
    wallet = await local_store.get_wallet_record(record["wallet_id"])
    if wallet is None:
        raise AppError(
            status_code=404,
            code="WALLET_NOT_FOUND",
            app_code="WALLET_NOT_FOUND",
            message_ko="커넥션에 연결된 wallet을 찾을 수 없습니다.",
            hint_ko="wallet을 다시 업로드하거나 커넥션을 재생성하세요.",
        )
    return record, wallet


def _ensure_reaper() -> None:
    """현재 루프에 유휴 풀 정리 태스크를 1회 기동한다 (lazy)."""
    loop = asyncio.get_running_loop()
    if id(loop) in _reaper_loops:
        return
    _reaper_loops.add(id(loop))
    loop.create_task(_reap_idle_pools(loop))


async def _reap_idle_pools(loop: asyncio.AbstractEventLoop) -> None:
    """30분 유휴 풀을 주기적으로 close한다 (백그라운드 타이머)."""
    try:
        while True:
            await asyncio.sleep(_REAP_INTERVAL_SECONDS)
            now = time.monotonic()
            for connection_id, entry in list(_pools.items()):
                if now - entry.last_used >= IDLE_CLOSE_SECONDS:
                    _pools.pop(connection_id, None)
                    try:
                        await entry.pool.close(force=True)
                    except Exception:  # 풀 종료 실패는 무시 (다음 요청에서 재생성)
                        pass
    finally:
        _reaper_loops.discard(id(loop))


async def get_pool(connection_id: str):
    """connection_id의 풀을 반환한다 — 닫혀 있으면 lazy 재생성 (api-spec §1.2)."""
    entry = _pools.get(connection_id)
    if entry is not None:
        entry.last_used = time.monotonic()
        return entry.pool

    record, wallet = await _load_records(connection_id)
    settings = get_settings()
    wallet_dir = str(local_store.wallets_dir() / record["wallet_id"])
    wallet_password_enc = wallet.get("wallet_password_enc")
    kwargs = build_connect_kwargs(
        username=record["username"],
        password=decrypt_secret(record["password_enc"]),
        tns_alias=record["tns_alias"],
        wallet_dir=wallet_dir,
        wallet_password=decrypt_secret(wallet_password_enc) if wallet_password_enc else None,
    )
    try:
        pool = oracledb.create_pool_async(
            min=0,
            max=settings.db_pool_max,
            increment=1,
            getmode=oracledb.POOL_GETMODE_WAIT,
            wait_timeout=10_000,  # ms — 풀 대기 10초 (architecture.md §3.2)
            **kwargs,
        )
    except oracledb.Error as exc:
        raise map_oracle_error(str(exc)) from exc
    _pools[connection_id] = _PoolEntry(pool=pool)
    _ensure_reaper()
    return pool


async def _persist_last_used(connection_id: str, entry: _PoolEntry) -> None:
    """last_used_at을 connections.json에 스로틀 기록 (FR-02 '마지막 사용 커넥션')."""
    now = time.monotonic()
    if now - entry.last_used_persisted < _LAST_USED_WRITE_THROTTLE_SECONDS:
        return
    entry.last_used_persisted = now
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).isoformat()

    def _mutate(doc: dict[str, Any]) -> dict[str, Any]:
        for record in doc["connections"]:
            if record.get("id") == connection_id:
                record["last_used_at"] = stamp
                break
        return doc

    await local_store.update_connections_doc(_mutate)


@asynccontextmanager
async def acquire(
    connection_id: str, call_timeout_ms: int = CALL_TIMEOUT_DEFAULT_MS
) -> AsyncIterator[Any]:
    """풀에서 커넥션을 빌려 call_timeout을 설정하고 반환한다.

    사용 패턴: ``async with pool_registry.acquire(conn_id, CALL_TIMEOUT_GENERATE_MS) as conn:``
    세션 상태를 남기는 호출(SET_PROFILE 등)은 금지 — stateless 원칙 (R3).
    """
    pool = await get_pool(connection_id)
    entry = _pools.get(connection_id)
    try:
        async with pool.acquire() as conn:
            try:
                conn.call_timeout = call_timeout_ms
            except (AttributeError, TypeError):
                pass  # 테스트 모킹 등 call_timeout 미지원 객체 허용
            if entry is not None:
                entry.last_used = time.monotonic()
                await _persist_last_used(connection_id, entry)
            yield conn
    except oracledb.Error as exc:
        message = str(exc)
        if "DPY-4005" in message:  # 풀 대기 타임아웃 → 503 (api-spec §12.1)
            raise AppError(
                status_code=503,
                code="DPY-4005",
                app_code="POOL_EXHAUSTED",
                message_ko="동시 실행이 많아 DB 커넥션을 확보하지 못했습니다.",
                hint_ko="진행 중인 작업이 끝난 뒤 다시 시도하세요.",
                retryable=True,
            ) from exc
        raise map_oracle_error(message) from exc


async def close_pool(connection_id: str) -> None:
    """커넥션 삭제/수정 시 풀 종료 — 다음 요청에서 lazy 재생성된다."""
    entry = _pools.pop(connection_id, None)
    if entry is not None:
        try:
            await entry.pool.close(force=True)
        except Exception:  # 이미 닫힌 풀 등은 무시
            pass


async def close_all() -> None:
    """앱 종료 시 전체 풀 정리."""
    for connection_id in list(_pools):
        await close_pool(connection_id)
