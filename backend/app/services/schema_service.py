"""스키마 서비스 — 인증 사용자 가시 스키마/테이블/컬럼 조회 (ALL_* 뷰).

근거: api-spec §8. object_list 브라우저(PG-03a) 지원 — 선택 테이블이 그대로
ObjectRef({owner, name})로 매핑된다. ALL_* 뷰만 사용 — "DB에 보이는 것"과 일치.
"""
from __future__ import annotations

from typing import Any

from app.db import oracle, pool_registry
from app.services import common

CURRENT_SCHEMA_SQL = "SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') AS current_schema FROM dual"
OWNERS_SQL = (
    "SELECT username AS owner FROM ALL_USERS "
    "WHERE oracle_maintained = 'N' OR username IN ('SH') "
    "ORDER BY username"
)
# ADB의 ADMIN 등 대형 스키마에서 ALL_TABLES⨝ALL_TAB_COMMENTS 전체 조인은 매우 느려
# 15초 call timeout(DPY-4024)을 넘긴다. owner로 필터된 두 쿼리로 분리 후 파이썬에서 병합한다.
TABLES_SQL = "SELECT table_name, num_rows FROM ALL_TABLES WHERE owner = :owner ORDER BY table_name"
TAB_COMMENTS_SQL = (
    "SELECT table_name, comments FROM ALL_TAB_COMMENTS "
    "WHERE owner = :owner AND comments IS NOT NULL"
)
# 데이터 딕셔너리 조회는 ADB에서 느릴 수 있어 일반(15s)보다 넉넉한 타임아웃 사용
METADATA_TIMEOUT_MS = pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
COLUMNS_SQL = (
    "SELECT col.column_name, col.data_type, col.nullable, cc.comments "
    "FROM ALL_TAB_COLUMNS col LEFT JOIN ALL_COL_COMMENTS cc "
    "ON cc.owner = col.owner AND cc.table_name = col.table_name "
    "AND cc.column_name = col.column_name "
    "WHERE col.owner = :owner AND col.table_name = :table_name "
    "ORDER BY col.column_id"
)


async def get_current_schema(connection_id: str, recorder: oracle.SqlRecorder) -> str:
    """인증 사용자 자신의 스키마 (UI 기본 선택값, §8.1)."""
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        value = await oracle.fetch_value(conn, CURRENT_SCHEMA_SQL, recorder=recorder)
    return str(value)


async def list_owners(connection_id: str, recorder: oracle.SqlRecorder) -> dict[str, Any]:
    """§8.1 접근 가능 스키마 목록 — 인증 스키마 is_current=true 표시."""
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        current = str(await oracle.fetch_value(conn, CURRENT_SCHEMA_SQL, recorder=recorder))
        _, rows = await oracle.fetch_all(conn, OWNERS_SQL, recorder=recorder)
    owners = [{"owner": str(row[0]), "is_current": str(row[0]) == current} for row in rows]
    if not any(o["is_current"] for o in owners):
        owners.insert(0, {"owner": current, "is_current": True})
    return {"current_schema": current, "owners": owners}


async def list_tables(
    connection_id: str, owner: str | None, recorder: oracle.SqlRecorder
) -> list[dict[str, Any]]:
    """§8.2 테이블 목록 — owner 미지정 시 CURRENT_SCHEMA. ObjectRef 매핑용 owner 포함.

    조인 대신 owner로 필터된 두 쿼리(테이블/코멘트)를 받아 파이썬에서 병합한다 (DPY-4024 회피).
    """
    if owner:
        common.validate_identifier(owner, "스키마 이름")
        target = owner.upper()
    else:
        target = None

    async with pool_registry.acquire(connection_id, METADATA_TIMEOUT_MS) as conn:
        if target is None:
            target = str(await oracle.fetch_value(conn, CURRENT_SCHEMA_SQL, recorder=recorder))
        _, rows = await oracle.fetch_all(conn, TABLES_SQL, {"owner": target}, recorder=recorder)
        _, comment_rows = await oracle.fetch_all(
            conn, TAB_COMMENTS_SQL, {"owner": target}, recorder=recorder
        )

    comments_by_table = {str(name): comment for name, comment in comment_rows}
    return [
        {
            "owner": target,
            "table_name": str(table_name),
            "comment": comments_by_table.get(str(table_name)),
            "num_rows": int(num_rows) if num_rows is not None else None,
        }
        for table_name, num_rows in rows
    ]


async def list_columns(
    connection_id: str, owner: str, table: str, recorder: oracle.SqlRecorder
) -> list[dict[str, Any]]:
    """§8.3 컬럼 목록 (타입/NULL 허용/코멘트)."""
    common.validate_identifier(owner, "스키마 이름")
    common.validate_identifier(table, "테이블 이름")
    async with pool_registry.acquire(connection_id, METADATA_TIMEOUT_MS) as conn:
        _, rows = await oracle.fetch_all(
            conn,
            COLUMNS_SQL,
            {"owner": owner.upper(), "table_name": table.upper()},
            recorder=recorder,
        )
    return [
        {
            "column_name": str(column_name),
            "data_type": str(data_type),
            "nullable": str(nullable) == "Y",
            "comment": comments,
        }
        for column_name, data_type, nullable, comments in rows
    ]
