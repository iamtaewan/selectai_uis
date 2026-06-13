"""쿼리 실행 헬퍼 — bind 실행, CLOB→str(fetch_lobs=False), 오류 매핑, executed_sql 수집.

architecture.md §2.2 db 레이어: 도메인 지식 금지. 모든 SQL은 바인드 변수만 사용
(문자열 연결 금지). 표시용 executed_sql은 비밀값 마스킹 후 바인드 자리표시자를
그대로 노출한다 (api-spec §1.3). oracledb 오류는 §1.5 매핑으로 AppError 변환.
"""
from __future__ import annotations

import re
from typing import Any, Sequence

import oracledb

from app.errors import AppError, map_oracle_error
from app.security.crypto import mask_secrets

# CLOB/BLOB을 str/bytes로 직접 페치 — GENERATE의 CLOB 반환 처리 (api-spec §12.4)
oracledb.defaults.fetch_lobs = False

_WS_RE = re.compile(r"\s+")


def normalize_sql(sql: str) -> str:
    """표시용 SQL 정규화 — 연속 공백/개행을 한 칸으로 줄인다."""
    return _WS_RE.sub(" ", sql).strip()


class SqlRecorder:
    """요청 단위 executed_sql 수집기 (api-spec §1.3).

    기록 시점에 비밀값을 마스킹한다 — 표시용 문자열 어디에도 평문 비밀 금지 (R5).
    """

    def __init__(self) -> None:
        self.statements: list[str] = []

    def record(self, statement: str) -> None:
        """실행 문장(또는 CLI 명령 원문)을 마스킹 후 순서대로 누적한다."""
        self.statements.append(mask_secrets(normalize_sql(statement)))


def require_connection_id(x_connection_id: str | None) -> str:
    """X-Connection-Id 헤더 검증 — 누락 시 400 CONNECTION_REQUIRED (api-spec §1.2)."""
    if not x_connection_id:
        raise AppError(
            status_code=400,
            code="CONNECTION_REQUIRED",
            app_code="CONNECTION_REQUIRED",
            message_ko="대상 커넥션이 지정되지 않았습니다 (X-Connection-Id 헤더 누락).",
            hint_ko="커넥션을 먼저 선택하세요.",
        )
    return x_connection_id


def _raise_mapped(exc: oracledb.Error, recorder: SqlRecorder | None) -> None:
    """oracledb 오류 → AppError 변환 (실행 이력 동봉, §1.5)."""
    executed = recorder.statements if recorder else []
    raise map_oracle_error(str(exc), executed) from exc


async def execute(
    conn: Any,
    sql: str,
    binds: dict[str, Any] | Sequence[Any] | None = None,
    recorder: SqlRecorder | None = None,
) -> None:
    """DDL/PLSQL 등 결과 없는 문장 실행 (바인드 변수만)."""
    if recorder is not None:
        recorder.record(sql)
    cursor = conn.cursor()
    try:
        await cursor.execute(sql, binds or {})
    except oracledb.Error as exc:
        _raise_mapped(exc, recorder)
    finally:
        cursor.close()


async def fetch_all(
    conn: Any,
    sql: str,
    binds: dict[str, Any] | Sequence[Any] | None = None,
    recorder: SqlRecorder | None = None,
    max_rows: int | None = None,
) -> tuple[list[str], list[list[Any]]]:
    """SELECT 실행 — (컬럼명 목록, 행 목록) 반환. max_rows 지정 시 +1행까지만 페치."""
    if recorder is not None:
        recorder.record(sql)
    cursor = conn.cursor()
    try:
        await cursor.execute(sql, binds or {})
        if max_rows is not None:
            rows = await cursor.fetchmany(max_rows + 1)
        else:
            rows = await cursor.fetchall()
        columns = [d[0] for d in cursor.description or []]
        return columns, [list(row) for row in rows]
    except oracledb.Error as exc:
        _raise_mapped(exc, recorder)
        raise  # 도달 불가 — 타입 체커용
    finally:
        cursor.close()


async def fetch_one(
    conn: Any,
    sql: str,
    binds: dict[str, Any] | Sequence[Any] | None = None,
    recorder: SqlRecorder | None = None,
) -> list[Any] | None:
    """단일 행 페치 (없으면 None)."""
    if recorder is not None:
        recorder.record(sql)
    cursor = conn.cursor()
    try:
        await cursor.execute(sql, binds or {})
        row = await cursor.fetchone()
        return list(row) if row is not None else None
    except oracledb.Error as exc:
        _raise_mapped(exc, recorder)
        raise
    finally:
        cursor.close()


async def fetch_value(
    conn: Any,
    sql: str,
    binds: dict[str, Any] | Sequence[Any] | None = None,
    recorder: SqlRecorder | None = None,
) -> Any:
    """첫 행 첫 컬럼 값 페치 — GENERATE CLOB 반환 등 (없으면 None)."""
    row = await fetch_one(conn, sql, binds, recorder)
    return row[0] if row else None


def escape_sql_literal(value: str) -> str:
    """SQL 미리보기/리터럴 위치용 작은따옴표 이스케이프 (api-spec §1.6).

    실제 실행은 항상 바인드 경로 — 이 함수는 표시용 문자열·COMMENT 텍스트 전용.
    """
    return value.replace("'", "''")
