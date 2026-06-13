"""공통 서비스 유틸 — 커넥션 헤더 검증, 식별자/리터럴 처리, settings.json 접근.

백엔드 Select AI 에이전트 담당 서비스(profiles/prereq/selectai/chat/enrichment/
schema/resources)가 공유하는 최소 유틸. 코어(db/·security/) 모듈이 아니므로
이 파일은 Select AI 에이전트가 관리한다.

[사용하는 코어 헬퍼 — 코어 에이전트 구현 확정본 기준]
db/pool_registry.py:
    acquire(connection_id, call_timeout_ms) -> async context (커넥션 대여,
        존재하지 않는 connection_id는 404 CONNECTION_NOT_FOUND AppError)
db/oracle.py:
    async fetch_all(conn, sql, binds=None, recorder=None, max_rows=None)
        -> (columns, rows) / fetch_one / fetch_value / execute, SqlRecorder
db/local_store.py:
    async read_json(filename) / write_json(filename, data) / update_json(...),
    load_settings()/save_settings(), load_resources()/append_resource() 등

헤더 누락(400 CONNECTION_REQUIRED)만 여기서 검증한다 (api-spec §1.2).
"""
from __future__ import annotations

import asyncio
import re
import time
from typing import Any, Awaitable, TypeVar

from app.db import local_store
from app.errors import AppError
from app.schemas.models import Envelope

T = TypeVar("T")

MASKED = "***MASKED***"

# architecture.md §4.2 — 바인드 불가 위치(식별자) 화이트리스트 검증 패턴
_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,127}$")

_SETTINGS_FILE = "settings.json"

# api-spec §12.2 계층별 call_timeout (ms)
TIMEOUT_TEST_MS = 5_000
TIMEOUT_META_MS = 15_000
TIMEOUT_PRIV_MS = 30_000
TIMEOUT_SHOWSQL_MS = 60_000
TIMEOUT_GENERATE_MS = 120_000
TIMEOUT_SEED_MS = 60_000


def require_connection_id(x_connection_id: str | None) -> str:
    """X-Connection-Id 헤더 필수 검증 (api-spec §1.2 — 누락 시 400)."""
    if not x_connection_id:
        raise AppError(
            status_code=400,
            code="CONNECTION_REQUIRED",
            app_code="CONNECTION_REQUIRED",
            message_ko="대상 커넥션이 지정되지 않았습니다 (X-Connection-Id 헤더 누락).",
            hint_ko="커넥션 화면에서 사용할 DB 커넥션을 먼저 선택하세요.",
        )
    return x_connection_id


def validate_identifier(name: str, what: str = "식별자") -> str:
    """Oracle 식별자 화이트리스트 검증 — 바인드 불가 위치(테이블명 등) 전용."""
    if not _IDENTIFIER_RE.match(name or ""):
        raise AppError(
            status_code=400,
            code="INVALID_IDENTIFIER",
            app_code="INVALID_IDENTIFIER",
            message_ko=f"{what} '{name}'이(가) 올바른 Oracle 식별자 형식이 아닙니다.",
            hint_ko="영문자로 시작하고 영문/숫자/_/$/#만 사용할 수 있습니다 (최대 128자).",
        )
    return name


def escape_literal(value: str) -> str:
    """SQL 리터럴 표시용 작은따옴표 이중화 (api-spec §1.6 — 표시 전용)."""
    return value.replace("'", "''")


def start_timer() -> float:
    """elapsed_ms 측정 시작."""
    return time.perf_counter()


def make_envelope(data: Any, executed_sql: list[str], started: float) -> Envelope:
    """성공 응답 공통 envelope 생성 (api-spec §1.3)."""
    return Envelope(
        data=data,
        executed_sql=executed_sql,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )


async def call_db(awaitable: Awaitable[T], recorder: Any) -> T:
    """DB 호출 래퍼 — 실패 시 AppError에 지금까지의 executed_sql을 동봉한다 (§1.4).

    표시용 SQL(리터럴 치환본)을 recorder에 먼저 기록하고 바인드 경로로 실행하는
    패턴에서, db 레이어가 recorder를 모르고 던진 AppError를 보강한다.
    """
    try:
        return await awaitable
    except AppError as exc:
        if not exc.executed_sql:
            exc.executed_sql = list(getattr(recorder, "statements", []) or [])
        raise


# 커넥션 단위 전역 Lock — DDL/권한 적용 직렬화 (api-spec §12.5).
# asyncio.Lock은 이벤트 루프에 바인딩되므로 (loop id, key)로 키잉한다.
_locks: dict[tuple[int, str], asyncio.Lock] = {}


def get_lock(key: str) -> asyncio.Lock:
    """현재 이벤트 루프 기준 키별 Lock 반환 (lazy 생성)."""
    loop_key = (id(asyncio.get_running_loop()), key)
    lock = _locks.get(loop_key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[loop_key] = lock
    return lock


# ---------------------------------------------------------------- settings.json
# 구조: { "default_profiles": {conn_id: profile_name},
#         "data_access":      {conn_id: "enabled"|"disabled"} }


async def _read_settings() -> dict[str, Any]:
    data = await local_store.load_settings()
    return data if isinstance(data, dict) else {}


async def get_default_profile(connection_id: str) -> str | None:
    """커넥션별 앱 기본 프로파일 조회 (api-spec §4.8 — DB 미사용)."""
    settings = await _read_settings()
    return (settings.get("default_profiles") or {}).get(connection_id)


async def set_default_profile(connection_id: str, profile_name: str) -> None:
    """커넥션별 앱 기본 프로파일 저장."""
    settings = await _read_settings()
    settings.setdefault("default_profiles", {})[connection_id] = profile_name
    await local_store.write_json(_SETTINGS_FILE, settings)


async def clear_default_profile(connection_id: str, profile_name: str) -> bool:
    """기본 프로파일이 profile_name이면 해제. 해제 여부 반환 (§4.7 default_cleared)."""
    settings = await _read_settings()
    defaults = settings.get("default_profiles") or {}
    if defaults.get(connection_id) == profile_name:
        del defaults[connection_id]
        settings["default_profiles"] = defaults
        await local_store.write_json(_SETTINGS_FILE, settings)
        return True
    return False


async def get_data_access_state(connection_id: str) -> str | None:
    """직전 ENABLE/DISABLE_DATA_ACCESS 적용 이력 조회 ("enabled"/"disabled"/None)."""
    settings = await _read_settings()
    return (settings.get("data_access") or {}).get(connection_id)


async def set_data_access_state(connection_id: str, enabled: bool) -> None:
    """Data Access 적용 이력 기록 (api-spec §3.1 data_access 판정 보조)."""
    settings = await _read_settings()
    settings.setdefault("data_access", {})[connection_id] = (
        "enabled" if enabled else "disabled"
    )
    await local_store.write_json(_SETTINGS_FILE, settings)
