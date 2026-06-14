"""SH 스키마 → 커넥션 user 스키마 복제 (테이블·뷰·제약).

전략:
 - 테이블: CTAS(CREATE TABLE ... AS SELECT * FROM SH.t)로 구조+데이터+NOT NULL 복제.
 - 제약: ALL_CONSTRAINTS/ALL_CONS_COLUMNS에서 PK/UK → CHECK(NOT NULL 제외) → FK 순으로 재생성.
         (FK는 참조 테이블의 PK/UK가 먼저 있어야 하므로 순서 중요. 참조 스키마는 대상 스키마로 remap.)
 - 뷰: ALL_VIEWS.TEXT_VC로 CREATE OR REPLACE VIEW 재생성 (미한정 참조는 대상 스키마로 해석됨).

권한: 대상 user가 SH에 SELECT 권한이 없으면(ALL_TABLES 미노출/probe 실패) 복제 불가로 차단.
모든 단계는 steps 로그로 반환해 UI에 표시한다.
"""
from __future__ import annotations

from typing import Any

from app.db import oracle, pool_registry
from app.errors import AppError
from app.services import common

SOURCE_SCHEMA = "SH"


# ---------------------------------------------------------------- 메타 조회 헬퍼
async def _current_user(conn: Any, recorder: oracle.SqlRecorder) -> str:
    return str(await oracle.fetch_value(conn, "SELECT USER FROM dual", recorder=recorder)).upper()


async def _sh_tables(conn: Any, recorder: oracle.SqlRecorder) -> list[str]:
    cols_rows = await oracle.fetch_all(
        conn,
        "SELECT table_name FROM all_tables WHERE owner = :o ORDER BY table_name",
        {"o": SOURCE_SCHEMA},
        recorder,
    )
    return [r[0] for r in cols_rows[1]]


async def _sh_views(conn: Any, recorder: oracle.SqlRecorder) -> list[str]:
    _, rows = await oracle.fetch_all(
        conn,
        "SELECT view_name FROM all_views WHERE owner = :o ORDER BY view_name",
        {"o": SOURCE_SCHEMA},
        recorder,
    )
    return [r[0] for r in rows]


# ---------------------------------------------------------------- 권한 점검
async def check_sh_access(connection_id: str, recorder: oracle.SqlRecorder) -> dict[str, Any]:
    """대상 user의 SH 읽기 권한 + 복제 대상 인벤토리를 반환."""
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
    ) as conn:
        current_user = await _current_user(conn, recorder)
        tables = await _sh_tables(conn, recorder)
        has_read = bool(tables)
        blocked = None
        if not tables:
            blocked = (
                f"현재 접속 사용자({current_user})는 {SOURCE_SCHEMA} 스키마 객체에 접근 권한이 "
                "없습니다. SH 테이블에 대한 SELECT 권한이 필요합니다."
            )
        else:
            # 실제 SELECT 가능 여부 probe (ALL_TABLES 노출만으로는 불충분할 수 있음)
            try:
                await oracle.fetch_value(
                    conn,
                    f'SELECT COUNT(*) FROM "{SOURCE_SCHEMA}"."{tables[0]}" WHERE ROWNUM <= 1',
                    recorder=recorder,
                )
            except AppError as exc:
                has_read = False
                blocked = (
                    f"{SOURCE_SCHEMA}.{tables[0]} SELECT 시도가 거부되었습니다 "
                    f"({exc.app_code}). SH에 대한 읽기 권한을 확인하세요."
                )
        views = await _sh_views(conn, recorder) if has_read else []
        pk = fk = 0
        if has_read:
            _, crows = await oracle.fetch_all(
                conn,
                "SELECT constraint_type, COUNT(*) FROM all_constraints "
                "WHERE owner = :o AND constraint_type IN ('P','U','R') GROUP BY constraint_type",
                {"o": SOURCE_SCHEMA},
                recorder,
            )
            cmap = {r[0]: r[1] for r in crows}
            pk = int(cmap.get("P", 0)) + int(cmap.get("U", 0))
            fk = int(cmap.get("R", 0))
    return {
        "current_user": current_user,
        "source_schema": SOURCE_SCHEMA,
        "has_read": has_read,
        "blocked_reason_ko": blocked,
        "tables": tables,
        "views": views,
        "table_count": len(tables),
        "view_count": len(views),
        "key_count": pk,
        "fk_count": fk,
    }


# ---------------------------------------------------------------- 제약 메타 추출
async def _key_constraints(
    conn: Any, recorder: oracle.SqlRecorder
) -> list[dict[str, Any]]:
    """PK/UK 제약 — 테이블·컬럼(순서) 그룹화."""
    _, rows = await oracle.fetch_all(
        conn,
        "SELECT ac.table_name, ac.constraint_name, ac.constraint_type, acc.column_name "
        "FROM all_constraints ac "
        "JOIN all_cons_columns acc "
        "  ON acc.owner = ac.owner AND acc.constraint_name = ac.constraint_name "
        "WHERE ac.owner = :o AND ac.constraint_type IN ('P','U') "
        "ORDER BY ac.table_name, ac.constraint_name, acc.position",
        {"o": SOURCE_SCHEMA},
        recorder,
    )
    grouped: dict[str, dict[str, Any]] = {}
    for table, name, ctype, col in rows:
        g = grouped.setdefault(
            name, {"table": table, "name": name, "type": ctype, "cols": []}
        )
        g["cols"].append(col)
    return list(grouped.values())


async def _fk_constraints(conn: Any, recorder: oracle.SqlRecorder) -> list[dict[str, Any]]:
    """FK 제약 — FK 컬럼 ↔ 참조 테이블·컬럼(위치 매칭) 그룹화."""
    _, rows = await oracle.fetch_all(
        conn,
        "SELECT ac.table_name, ac.constraint_name, acc.column_name, "
        "       rc.table_name AS ref_table, rcc.column_name AS ref_col, acc.position "
        "FROM all_constraints ac "
        "JOIN all_cons_columns acc "
        "  ON acc.owner = ac.owner AND acc.constraint_name = ac.constraint_name "
        "JOIN all_constraints rc "
        "  ON rc.owner = ac.r_owner AND rc.constraint_name = ac.r_constraint_name "
        "JOIN all_cons_columns rcc "
        "  ON rcc.owner = rc.owner AND rcc.constraint_name = rc.constraint_name "
        "     AND rcc.position = acc.position "
        "WHERE ac.owner = :o AND ac.constraint_type = 'R' "
        "ORDER BY ac.constraint_name, acc.position",
        {"o": SOURCE_SCHEMA},
        recorder,
    )
    grouped: dict[str, dict[str, Any]] = {}
    for table, name, col, ref_table, ref_col, _pos in rows:
        g = grouped.setdefault(
            name,
            {"table": table, "name": name, "ref_table": ref_table, "cols": [], "ref_cols": []},
        )
        g["cols"].append(col)
        g["ref_cols"].append(ref_col)
    return list(grouped.values())


async def _check_constraints(conn: Any, recorder: oracle.SqlRecorder) -> list[dict[str, Any]]:
    """NOT NULL이 아닌 CHECK 제약 (CTAS가 NOT NULL은 이미 복제하므로 제외)."""
    try:
        _, rows = await oracle.fetch_all(
            conn,
            "SELECT table_name, constraint_name, search_condition_vc "
            "FROM all_constraints WHERE owner = :o AND constraint_type = 'C' "
            "AND search_condition_vc IS NOT NULL "
            "AND UPPER(search_condition_vc) NOT LIKE '%IS NOT NULL%'",
            {"o": SOURCE_SCHEMA},
            recorder,
        )
    except AppError:
        return []  # search_condition_vc 미지원 등은 무시 (NOT NULL은 CTAS로 충분)
    return [{"table": r[0], "name": r[1], "cond": r[2]} for r in rows]


# ---------------------------------------------------------------- 복제 실행
async def clone_sh(
    connection_id: str, *, overwrite: bool, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """SH → 대상 user 스키마 복제. 단계별 steps 로그를 반환."""
    steps: list[dict[str, Any]] = []

    def log(phase: str, obj: str, status: str, detail: str, sql: str | None = None) -> None:
        steps.append(
            {"phase": phase, "object": obj, "status": status, "detail": detail, "sql": sql}
        )

    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_GENERATE_MS
    ) as conn:
        target = await _current_user(conn, recorder)
        tables = await _sh_tables(conn, recorder)
        if not tables:
            raise AppError(
                status_code=403,
                code="INSUFFICIENT_PRIVILEGE",
                app_code="INSUFFICIENT_PRIVILEGE",
                message_ko=f"{SOURCE_SCHEMA} 스키마에 대한 읽기 권한이 없어 복제할 수 없습니다.",
                hint_ko="SH 테이블에 SELECT 권한을 부여받은 뒤 다시 시도하세요.",
            )
        log("시작", target, "ok", f"{SOURCE_SCHEMA} → {target} 복제 시작 (대상 테이블 {len(tables)}개)")

        # ── 1) 테이블 (CTAS: 구조 + 데이터 + NOT NULL)
        created: list[str] = []
        for t in tables:
            tgt = f'"{target}"."{t}"'
            if overwrite:
                drop = f"DROP TABLE {tgt} CASCADE CONSTRAINTS PURGE"
                try:
                    await oracle.execute(conn, drop, recorder=recorder)
                    log("테이블", t, "ok", "기존 객체 삭제(덮어쓰기)", drop)
                except AppError:
                    pass  # 없으면 무시
            else:
                _, exists = await oracle.fetch_all(
                    conn,
                    "SELECT 1 FROM all_tables WHERE owner = :o AND table_name = :t",
                    {"o": target, "t": t},
                    recorder,
                )
                if exists:
                    log("테이블", t, "skip", "이미 존재 — 건너뜀 (덮어쓰기 꺼짐)")
                    continue
            ctas = f'CREATE TABLE {tgt} AS SELECT * FROM "{SOURCE_SCHEMA}"."{t}"'
            try:
                await oracle.execute(conn, ctas, recorder=recorder)
                created.append(t)
                log("테이블", t, "ok", "구조+데이터 복제 완료", ctas)
            except AppError as exc:
                log("테이블", t, "error", f"복제 실패: {exc.message_ko}", ctas)

        created_set = set(created)

        # ── 2) PK / UK (생성된 테이블에 한해)
        for c in await _key_constraints(conn, recorder):
            if c["table"] not in created_set:
                continue
            kind = "PRIMARY KEY" if c["type"] == "P" else "UNIQUE"
            cols = ", ".join(f'"{col}"' for col in c["cols"])
            ddl = (
                f'ALTER TABLE "{target}"."{c["table"]}" '
                f'ADD CONSTRAINT "{c["name"]}" {kind} ({cols})'
            )
            try:
                await oracle.execute(conn, ddl, recorder=recorder)
                log("키 제약", c["name"], "ok", f'{c["table"]} {kind}', ddl)
            except AppError as exc:
                log("키 제약", c["name"], "error", exc.message_ko, ddl)

        # ── 3) CHECK (NOT NULL 제외)
        for c in await _check_constraints(conn, recorder):
            if c["table"] not in created_set:
                continue
            ddl = (
                f'ALTER TABLE "{target}"."{c["table"]}" '
                f'ADD CONSTRAINT "{c["name"]}" CHECK ({c["cond"]})'
            )
            try:
                await oracle.execute(conn, ddl, recorder=recorder)
                log("CHECK 제약", c["name"], "ok", c["table"], ddl)
            except AppError as exc:
                log("CHECK 제약", c["name"], "error", exc.message_ko, ddl)

        # ── 4) FK (PK 이후, 참조 스키마는 대상으로 remap)
        for c in await _fk_constraints(conn, recorder):
            if c["table"] not in created_set or c["ref_table"] not in created_set:
                log(
                    "FK 제약", c["name"], "skip",
                    f'참조 테이블 {c["ref_table"]} 미복제로 건너뜀',
                )
                continue
            cols = ", ".join(f'"{col}"' for col in c["cols"])
            ref_cols = ", ".join(f'"{col}"' for col in c["ref_cols"])
            ddl = (
                f'ALTER TABLE "{target}"."{c["table"]}" '
                f'ADD CONSTRAINT "{c["name"]}" FOREIGN KEY ({cols}) '
                f'REFERENCES "{target}"."{c["ref_table"]}" ({ref_cols})'
            )
            try:
                await oracle.execute(conn, ddl, recorder=recorder)
                log("FK 제약", c["name"], "ok", f'{c["table"]} → {c["ref_table"]}', ddl)
            except AppError as exc:
                log("FK 제약", c["name"], "error", exc.message_ko, ddl)

        # ── 5) 뷰 (CREATE OR REPLACE)
        views = await _sh_views(conn, recorder)
        for v in views:
            text = await oracle.fetch_value(
                conn,
                "SELECT text_vc FROM all_views WHERE owner = :o AND view_name = :v",
                {"o": SOURCE_SCHEMA, "v": v},
                recorder=recorder,
            )
            if not text:
                log("뷰", v, "skip", "뷰 정의를 읽지 못함")
                continue
            ddl = f'CREATE OR REPLACE VIEW "{target}"."{v}" AS {text}'
            try:
                await oracle.execute(conn, ddl, recorder=recorder)
                log("뷰", v, "ok", "뷰 복제 완료", ddl)
            except AppError as exc:
                log("뷰", v, "error", exc.message_ko, ddl)

    ok = sum(1 for s in steps if s["status"] == "ok")
    failed = sum(1 for s in steps if s["status"] == "error")
    summary = {
        "target_schema": target,
        "source_schema": SOURCE_SCHEMA,
        "tables_created": len(created),
        "tables_total": len(tables),
        "ok": ok,
        "failed": failed,
    }
    log("완료", target, "ok" if failed == 0 else "error",
        f"복제 종료 — 성공 {ok}건, 실패 {failed}건")
    return {"summary": summary, "steps": steps}
