"""메타 강화 서비스 — 대상 테이블의 comment/annotation 조회·추가 + grok LLM 제안.

준비하기 단계에서 NL2SQL 정확도를 높이기 위해 테이블/컬럼에 의미(comment·annotation)를
부여한다. LLM 제안은 사용자 프로파일을 오염시키지 않도록 전용 grok 프로파일(META_GROK)로 호출한다.
근거: selectai-reference §3(comments/annotations), §5(xai.grok-4), security §4(narrate 데이터 전송).
"""
from __future__ import annotations

import json
from typing import Any

from app.db import oracle, pool_registry
from app.errors import AppError
from app.services import attribute_catalog, common, profile_service, resource_service, selectai_service

# 메타 강화 LLM 제안 전용 프로파일 (xai.grok-4)
GROK_PROFILE = "META_GROK"
GROK_MODEL = "xai.grok-4"
SAMPLE_ROWS = 5  # LLM에 보내는 샘플 행 수 (개인정보 노출 최소화)

OBJECT_LIST_ATTR_SQL = (
    "SELECT attribute_value FROM USER_CLOUD_AI_PROFILE_ATTRIBUTES "
    "WHERE profile_name = :profile_name AND attribute_name = 'object_list'"
)
COLUMNS_SQL = (
    "SELECT col.column_name, col.data_type, col.nullable, cc.comments "
    "FROM ALL_TAB_COLUMNS col LEFT JOIN ALL_COL_COMMENTS cc "
    "ON cc.owner = col.owner AND cc.table_name = col.table_name "
    "AND cc.column_name = col.column_name "
    "WHERE col.owner = :owner AND col.table_name = :table_name "
    "ORDER BY col.column_id"
)
TABLE_COMMENT_SQL = (
    "SELECT comments FROM ALL_TAB_COMMENTS WHERE owner = :owner AND table_name = :table_name"
)
# 23ai/26ai 어노테이션 사용 현황 (뷰 미존재 버전 대비 호출부에서 예외 처리)
ANNOTATIONS_SQL = (
    # ALL_ANNOTATIONS_USAGE에는 OWNER 컬럼이 없다 — 객체 소유자는 ANNOTATION_OWNER로 필터해야 한다.
    # (owner 사용 시 ORA-00904로 조회가 깨져 적용된 annotation이 화면에 안 보임)
    "SELECT column_name, annotation_name, annotation_value "
    "FROM ALL_ANNOTATIONS_USAGE WHERE annotation_owner = :owner AND object_name = :table_name"
)


# 다른 스키마 객체에 comment/annotation을 적용하려면 필요한 시스템 권한
REQUIRED_PRIVS = {"comment": "COMMENT ANY TABLE", "annotation": "ALTER ANY TABLE"}
ALLOWED_GRANT_PRIVS = {"COMMENT ANY TABLE", "ALTER ANY TABLE"}

SESSION_USER_SQL = "SELECT SYS_CONTEXT('USERENV', 'SESSION_USER') FROM dual"
OWNER_MAINTAINED_SQL = "SELECT oracle_maintained FROM ALL_USERS WHERE username = :owner"
SESSION_PRIVS_SQL = (
    "SELECT privilege FROM SESSION_PRIVS "
    "WHERE privilege IN ('COMMENT ANY TABLE', 'ALTER ANY TABLE', 'GRANT ANY PRIVILEGE')"
)
ADMIN_OPTION_PRIVS_SQL = (
    "SELECT privilege FROM USER_SYS_PRIVS "
    "WHERE privilege IN ('COMMENT ANY TABLE', 'ALTER ANY TABLE') AND admin_option = 'YES'"
)


def _qualified(owner: str, table: str) -> str:
    return f'"{owner.upper()}"."{table.upper()}"'


async def check_privileges(
    connection_id: str, owner: str, table: str, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """메타 보강 권한 점검 — 소유 여부 / 보유 권한 / 부여 가능 여부."""
    common.validate_identifier(owner, "스키마 이름")
    common.validate_identifier(table, "테이블 이름")
    o = owner.upper()
    async with pool_registry.acquire(connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS) as conn:
        current = str(await oracle.fetch_value(conn, SESSION_USER_SQL, recorder=recorder)).upper()
        _, sp_rows = await oracle.fetch_all(conn, SESSION_PRIVS_SQL, recorder=recorder)
        _, ao_rows = await oracle.fetch_all(conn, ADMIN_OPTION_PRIVS_SQL, recorder=recorder)
        maintained_val = await oracle.fetch_value(
            conn, OWNER_MAINTAINED_SQL, {"owner": o}, recorder=recorder
        )

    session_privs = {str(r[0]) for r in sp_rows}
    admin_option = {str(r[0]) for r in ao_rows}
    has_grant_any = "GRANT ANY PRIVILEGE" in session_privs

    owns_table = o == current
    # Oracle 관리 스키마(oracle_maintained='Y')는 권한이 있어도 COMMENT/ALTER 불가
    schema_protected = (not owns_table) and str(maintained_val or "N").upper() == "Y"

    required = [] if owns_table else ["COMMENT ANY TABLE", "ALTER ANY TABLE"]
    held = [p for p in required if p in session_privs]
    missing = [p for p in required if p not in session_privs]
    grantable = [p for p in missing if has_grant_any or p in admin_option]
    can_grant_all = bool(missing) and all(p in grantable for p in missing)

    # 최종 적용 가능 여부: 소유 OR (권한 부족 없음 AND 보호 스키마 아님)
    can_apply = owns_table or (not missing and not schema_protected)

    blocked_reason = None
    if schema_protected:
        blocked_reason = (
            f"대상 스키마({o})는 Oracle이 관리하는 보호 스키마(oracle_maintained)라 "
            "COMMENT/ALTER ANY TABLE 권한이 있어도 수정할 수 없습니다. 본인이 소유한 스키마의 "
            "테이블(예: 데모 스키마)을 대상으로 사용하세요."
        )
    elif missing and not can_grant_all:
        blocked_reason = (
            "이 접속 사용자는 시스템 권한을 부여할 권한(GRANT ANY PRIVILEGE 또는 admin option)이 "
            "없어 부여할 수 없습니다. DBA에게 권한 부여를 요청하거나, 본인이 소유한 스키마의 "
            "테이블을 대상으로 사용하세요."
        )

    return {
        "current_user": current,
        "owner": o,
        "owns_table": owns_table,
        "schema_protected": schema_protected,
        "required": required,
        "held": held,
        "missing": missing,
        "grantable": grantable,
        "can_grant_all": can_grant_all,
        "can_apply": can_apply,
        "grant_sql": [f"GRANT {p} TO {current}" for p in grantable],
        "blocked_reason_ko": blocked_reason,
    }


async def grant_privileges(
    connection_id: str, privileges: list[str], recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """현재 접속 사용자에게 시스템 권한 부여 시도 — 부여분은 ledger에 기록(REVOKE 정리용)."""
    results: list[dict[str, Any]] = []
    done = 0
    failed = 0
    async with pool_registry.acquire(connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS) as conn:
        current = str(await oracle.fetch_value(conn, SESSION_USER_SQL, recorder=recorder)).upper()
        for priv in privileges:
            if priv not in ALLOWED_GRANT_PRIVS:
                results.append({"privilege": priv, "ok": False, "error": "허용되지 않은 권한입니다."})
                failed += 1
                continue
            sql = f"GRANT {priv} TO {current}"
            recorder.record(sql)
            try:
                await common.call_db(oracle.execute(conn, sql), recorder)
                done += 1
                results.append({"privilege": priv, "ok": True})
                await resource_service.record(
                    connection_id,
                    resource_type="grant",
                    resource_name=f"{priv}:{current}",
                    create_sql=sql,
                    cleanup_sql=f"REVOKE {priv} FROM {current}",
                )
            except AppError as exc:
                failed += 1
                msg = exc.message_ko
                if "01031" in (exc.detail or "") or "권한" in msg:
                    msg = "이 사용자에게는 해당 시스템 권한을 부여할 권한이 없습니다 (ADB 제약)."
                results.append({"privilege": priv, "ok": False, "error": msg})
    return {"current_user": current, "results": results, "summary": {"done": done, "failed": failed}}


async def list_profile_tables(
    connection_id: str, profile_name: str, recorder: oracle.SqlRecorder
) -> list[dict[str, str]]:
    """선택한 프로파일의 object_list(대상 테이블) 목록 — [{owner, name}]."""
    common.validate_identifier(profile_name, "프로파일 이름")
    async with pool_registry.acquire(connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS) as conn:
        value = await oracle.fetch_value(
            conn, OBJECT_LIST_ATTR_SQL, {"profile_name": profile_name.upper()}, recorder=recorder
        )
    if not value:
        return []
    try:
        parsed = json.loads(str(value))
    except (ValueError, TypeError):
        return []
    tables: list[dict[str, str]] = []
    for ref in parsed if isinstance(parsed, list) else []:
        if isinstance(ref, dict) and ref.get("owner") and ref.get("name"):
            tables.append({"owner": str(ref["owner"]).upper(), "name": str(ref["name"]).upper()})
    return tables


async def get_table_metadata(
    connection_id: str, owner: str, table: str, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """테이블 메타데이터 — 컬럼별 data_type/comment/annotations + 테이블 코멘트."""
    common.validate_identifier(owner, "스키마 이름")
    common.validate_identifier(table, "테이블 이름")
    o, t = owner.upper(), table.upper()
    async with pool_registry.acquire(connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS) as conn:
        _, col_rows = await oracle.fetch_all(
            conn, COLUMNS_SQL, {"owner": o, "table_name": t}, recorder=recorder
        )
        table_comment = await oracle.fetch_value(
            conn, TABLE_COMMENT_SQL, {"owner": o, "table_name": t}, recorder=recorder
        )
        # 어노테이션 뷰는 버전에 따라 없을 수 있음 — 실패 시 빈 목록으로 진행
        annotation_rows: list[Any] = []
        try:
            _, annotation_rows = await oracle.fetch_all(
                conn, ANNOTATIONS_SQL, {"owner": o, "table_name": t}, recorder=recorder
            )
        except AppError:
            annotation_rows = []

    # 어노테이션을 컬럼별로 그룹화 (column_name null = 테이블 레벨)
    ann_by_col: dict[str | None, list[dict[str, Any]]] = {}
    for column_name, ann_name, ann_value in annotation_rows:
        key = str(column_name) if column_name is not None else None
        ann_by_col.setdefault(key, []).append(
            {"name": str(ann_name), "value": None if ann_value is None else str(ann_value)}
        )

    columns = [
        {
            "column_name": str(name),
            "data_type": str(data_type),
            "nullable": str(nullable) == "Y",
            "comment": comment,
            "annotations": ann_by_col.get(str(name), []),
        }
        for name, data_type, nullable, comment in col_rows
    ]
    return {
        "owner": o,
        "table_name": t,
        "table_comment": table_comment,
        "table_annotations": ann_by_col.get(None, []),
        "columns": columns,
    }


def _build_comment_sql(owner: str, table: str, column: str | None, comment: str) -> tuple[str, str]:
    """COMMENT DDL (sql, display). column=None이면 테이블 코멘트."""
    common.validate_identifier(owner, "스키마 이름")
    common.validate_identifier(table, "테이블 이름")
    literal = common.escape_literal(comment)
    if column:
        common.validate_identifier(column, "컬럼 이름")
        target = f'COLUMN {_qualified(owner, table)}."{column.upper()}"'
    else:
        target = f"TABLE {_qualified(owner, table)}"
    sql = f"COMMENT ON {target} IS '{literal}'"
    return sql, sql


def _build_annotation_sql(
    owner: str, table: str, column: str | None, name: str, value: str | None, operation: str
) -> str:
    """ANNOTATIONS DDL — 컬럼/테이블 레벨, operation = add/replace/drop.

    add/replace는 value 선택, drop은 이름만.
    """
    common.validate_identifier(owner, "스키마 이름")
    common.validate_identifier(table, "테이블 이름")
    common.validate_identifier(name, "어노테이션 이름")
    op = operation.upper()
    if op not in ("ADD", "REPLACE", "DROP"):
        raise AppError(
            status_code=400, code="ANNOTATION_OP_INVALID", app_code="ANNOTATION_OP_INVALID",
            message_ko="어노테이션 작업은 add/replace/drop만 지원합니다.",
        )
    if op == "DROP":
        clause = f"DROP {name.upper()}"
    else:
        val = f" '{common.escape_literal(value)}'" if value else ""
        clause = f"{op} {name.upper()}{val}"
    if column:
        common.validate_identifier(column, "컬럼 이름")
        return f'ALTER TABLE {_qualified(owner, table)} MODIFY ("{column.upper()}" ANNOTATIONS ({clause}))'
    return f"ALTER TABLE {_qualified(owner, table)} ANNOTATIONS ({clause})"


async def apply_comment(
    connection_id: str, owner: str, table: str, column: str | None, comment: str,
    recorder: oracle.SqlRecorder,
) -> dict[str, Any]:
    """COMMENT 적용 (DDL)."""
    sql, display = _build_comment_sql(owner, table, column, comment)
    recorder.record(display)
    async with pool_registry.acquire(connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS) as conn:
        await common.call_db(oracle.execute(conn, sql), recorder)
    return {"applied_sql": display}


# 이미 존재(ADD 실패) / 미존재(REPLACE 실패) ORA 코드 — add↔replace upsert 자가복구용
_ANN_EXISTS = ("ORA-11552", "ORA-11560")       # annotation already exists (table/column)
_ANN_MISSING = ("ORA-11553", "ORA-11561")      # annotation does not exist (table/column)


async def apply_annotation(
    connection_id: str, owner: str, table: str, column: str | None, name: str, value: str | None,
    operation: str, recorder: oracle.SqlRecorder,
) -> dict[str, Any]:
    """ANNOTATION 적용 (DDL) — operation = add/replace/drop.

    ADD/REPLACE는 단독으로 idempotent하지 않다(ADD는 기존에 ORA-11552/11560, REPLACE는 미존재에
    ORA-11553/11561 실패). 메타 제안 재적용을 위해 ADD↔REPLACE 자동 전환(upsert)으로 자가복구한다.
    """
    op = operation.lower()
    sql = _build_annotation_sql(owner, table, column, name, value, operation)
    recorder.record(sql)
    async with pool_registry.acquire(connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS) as conn:
        try:
            await common.call_db(oracle.execute(conn, sql), recorder)
        except AppError as exc:
            detail = exc.detail or ""
            alt: str | None = None
            if op == "add" and any(c in detail for c in _ANN_EXISTS):
                alt = "replace"   # 이미 있으면 값 갱신
            elif op == "replace" and any(c in detail for c in _ANN_MISSING):
                alt = "add"       # 없으면 새로 추가
            if alt is None:
                raise
            sql = _build_annotation_sql(owner, table, column, name, value, alt)
            recorder.record(sql)
            await common.call_db(oracle.execute(conn, sql), recorder)
    return {"applied_sql": sql}


async def _ensure_grok_profile(
    connection_id: str, owner: str, table: str, conn: Any, recorder: oracle.SqlRecorder
) -> None:
    """메타 강화 전용 grok 프로파일을 (재)생성 — model=xai.grok-4, 대상 테이블 1개."""
    attributes: dict[str, Any] = {
        **attribute_catalog.DEFAULTS,
        "model": GROK_MODEL,
        "object_list": [{"owner": owner.upper(), "name": table.upper()}],
    }
    # 존재 시 DROP 후 재생성 (대상 테이블이 바뀔 수 있으므로)
    recorder.record(f"BEGIN DBMS_CLOUD_AI.DROP_PROFILE('{GROK_PROFILE}'); END;")
    try:
        await common.call_db(
            oracle.execute(conn, profile_service.DROP_PROFILE_SQL, {"profile_name": GROK_PROFILE}),
            recorder,
        )
    except AppError:
        pass  # 미존재 — 무시
    plan = profile_service.build_create_profile(GROK_PROFILE, attributes)
    recorder.record(plan.display_sql)
    await common.call_db(oracle.execute(conn, plan.sql, plan.binds), recorder)
    await resource_service.record(
        connection_id,
        resource_type="profile",
        resource_name=GROK_PROFILE,
        create_sql=plan.display_sql,
        cleanup_sql=f"BEGIN DBMS_CLOUD_AI.DROP_PROFILE('{GROK_PROFILE}'); END;",
    )


# 표준 어노테이션 키 (가이드 §4) — 프롬프트에 명시해 LLM이 통제 어휘만 쓰게 한다
COLUMN_KEYS = (
    "business_name, synonyms, unit, range, value_map(JSON 코드-라벨 매핑), note, "
    "join_hint, pk, fk, pii, classification, column_hidden"
)
TABLE_KEYS = "domain, source_system, refresh, owner"

RELATED_COLUMNS_SQL = (
    "SELECT column_name FROM ALL_TAB_COLUMNS WHERE owner = :owner AND table_name = :table_name "
    "ORDER BY column_id"
)
FK_SQL = (
    "SELECT acc.column_name, ac.r_owner, rcc.table_name, rcc.column_name "
    "FROM ALL_CONSTRAINTS ac "
    "JOIN ALL_CONS_COLUMNS acc ON acc.owner = ac.owner AND acc.constraint_name = ac.constraint_name "
    "JOIN ALL_CONS_COLUMNS rcc ON rcc.owner = ac.r_owner "
    "AND rcc.constraint_name = ac.r_constraint_name AND rcc.position = acc.position "
    "WHERE ac.owner = :owner AND ac.table_name = :table_name AND ac.constraint_type = 'R'"
)


def _norm_annotations(raw: Any) -> list[dict[str, Any]]:
    """LLM annotations(배열 또는 객체) → [{name, value}] 정규화."""
    out: list[dict[str, Any]] = []
    if isinstance(raw, list):
        for a in raw:
            if isinstance(a, dict) and a.get("name"):
                v = a.get("value")
                out.append({"name": str(a["name"]).strip(), "value": None if v in (None, "") else str(v)})
            elif isinstance(a, str) and a.strip():
                out.append({"name": a.strip(), "value": None})
    elif isinstance(raw, dict):
        for k, v in raw.items():
            out.append({"name": str(k).strip(), "value": None if v in (None, "") else str(v)})
    return out


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
        if cleaned[:4].lower() == "json":
            cleaned = cleaned[4:]
        cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start >= 0 and end > start:
        cleaned = cleaned[start : end + 1]
    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, dict) else {}
    except (ValueError, TypeError):
        return {}


def _parse_suggestions(text: str) -> dict[str, Any]:
    """LLM 응답 → {table: {comment, annotations}, columns: [{column, comment, annotations}]}."""
    parsed = _extract_json(text)
    tbl = parsed.get("table") if isinstance(parsed.get("table"), dict) else {}
    table_out = {
        "comment": str(tbl.get("comment", "")).strip() or None,
        "annotations": _norm_annotations(tbl.get("annotations")),
    }
    cols_out: list[dict[str, Any]] = []
    for c in parsed.get("columns", []) if isinstance(parsed.get("columns"), list) else []:
        if isinstance(c, dict) and c.get("column"):
            cols_out.append(
                {
                    "column": str(c["column"]).upper(),
                    "comment": str(c.get("comment", "")).strip() or None,
                    "annotations": _norm_annotations(c.get("annotations")),
                }
            )
    return {"table": table_out, "columns": cols_out}


async def _relationship_context(
    connection_id: str, owner: str, table: str, profile: str | None,
    conn: Any, recorder: oracle.SqlRecorder,
) -> str:
    """프로파일 내 다른 테이블의 컬럼 목록 + 대상 테이블 FK를 텍스트로 — 관계 분석 컨텍스트."""
    lines: list[str] = []
    # 같은 프로파일의 다른 대상 테이블 컬럼 (최대 8개 테이블)
    if profile:
        try:
            others = await list_profile_tables(connection_id, profile, recorder)
        except AppError:
            others = []
        for ref in others[:8]:
            if ref["owner"] == owner and ref["name"] == table:
                continue
            _, cols = await oracle.fetch_all(
                conn, RELATED_COLUMNS_SQL,
                {"owner": ref["owner"], "table_name": ref["name"]}, recorder=recorder,
            )
            names = ", ".join(str(r[0]) for r in cols)
            if names:
                lines.append(f"- {ref['owner']}.{ref['name']}: {names}")
    # 대상 테이블 FK 관계
    fk_lines: list[str] = []
    try:
        _, fks = await oracle.fetch_all(
            conn, FK_SQL, {"owner": owner, "table_name": table}, recorder=recorder
        )
        for col, r_owner, r_table, r_col in fks:
            fk_lines.append(f"- {col} → {r_owner}.{r_table}.{r_col} (FK)")
    except AppError:
        pass
    ctx = ""
    if lines:
        ctx += "프로파일 내 다른 테이블(조인 후보):\n" + "\n".join(lines) + "\n"
    if fk_lines:
        ctx += "외래키 관계:\n" + "\n".join(fk_lines) + "\n"
    return ctx


async def suggest(
    connection_id: str, owner: str, table: str, profile: str | None,
    recorder: oracle.SqlRecorder,
) -> dict[str, Any]:
    """grok-4로 샘플 데이터 + 프로파일 내 다른 테이블 관계를 분석해 메타데이터를 제안.

    테이블/컬럼 레벨의 comment·annotation(표준 키)을 구조화 JSON으로 받는다.
    실데이터 일부(최대 5행)가 LLM에 전송된다 (security §4 — UI에 고지).
    """
    common.validate_identifier(owner, "스키마 이름")
    common.validate_identifier(table, "테이블 이름")
    o, t = owner.upper(), table.upper()
    sample_sql = f"SELECT * FROM {_qualified(o, t)} FETCH FIRST {SAMPLE_ROWS} ROWS ONLY"

    async with pool_registry.acquire(connection_id, pool_registry.CALL_TIMEOUT_GENERATE_MS) as conn:
        cols, rows = await oracle.fetch_all(conn, sample_sql, recorder=recorder)
        header = ", ".join(str(c) for c in cols)
        body = "\n".join(", ".join("" if v is None else str(v) for v in row) for row in rows)
        rel_ctx = await _relationship_context(connection_id, o, t, profile, conn, recorder)

        prompt = (
            "당신은 데이터 모델링/메타데이터 전문가입니다. 아래 Oracle 테이블의 컬럼·샘플 데이터와 "
            "프로파일 내 관련 테이블/FK 관계를 분석하여, NL2SQL 정확도를 높이는 메타데이터를 제안하세요.\n\n"
            "규칙:\n"
            f"1) 테이블 레벨: 한국어 한 줄 comment + annotations(키는 다음만 사용: {TABLE_KEYS}).\n"
            f"2) 컬럼 레벨: 컬럼마다 한국어 comment + annotations(키는 다음만 사용: {COLUMN_KEYS}).\n"
            "3) 약어/코드 컬럼엔 business_name 필수, 코드성 컬럼엔 value_map(JSON), FK/조인 컬럼엔 "
            "join_hint(관련 테이블 참조), 식별자엔 pk/fk, 민감정보엔 pii/classification.\n"
            "4) 과도하게 달지 말 것 — '처음 보는 분석가에게 한 줄 설명' 수준. 값 없는 플래그 키는 value를 null로.\n"
            "5) 반드시 아래 JSON으로만 답하세요(다른 텍스트 금지):\n"
            '{"table": {"comment": "...", "annotations": [{"name": "domain", "value": "credit"}]},'
            ' "columns": [{"column": "C1", "comment": "...", "annotations": [{"name": "business_name",'
            ' "value": "..."}]}]}\n\n'
            f"대상 테이블: {o}.{t}\n컬럼: {header}\n샘플 데이터:\n{body}\n\n{rel_ctx}"
        )
        await _ensure_grok_profile(connection_id, o, t, conn, recorder)
        response = await selectai_service.call_generate(
            conn, prompt=prompt, profile_name=GROK_PROFILE, action="chat",
            params_json=None, recorder=recorder,
        )
    suggestion = _parse_suggestions(response)
    return {
        "owner": o,
        "table_name": t,
        "model": GROK_MODEL,
        "sample_rows": len(rows),
        "table": suggestion["table"],
        "columns": suggestion["columns"],
        "raw": response,
    }


async def apply_batch(
    connection_id: str, owner: str, table: str, items: list[Any], recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """선택/일괄 적용 — 각 항목의 comment + annotations를 DDL로 적용. 항목별 결과 반환."""
    results: list[dict[str, Any]] = []
    done = 0
    failed = 0
    for item in items:
        column = item.column if item.level == "column" else None
        label = f"{item.level}:{column or table}"
        # COMMENT
        if item.comment is not None and str(item.comment).strip():
            try:
                await apply_comment(connection_id, owner, table, column, item.comment, recorder)
                done += 1
                results.append({"target": label, "kind": "comment", "ok": True})
            except AppError as exc:
                failed += 1
                results.append({"target": label, "kind": "comment", "ok": False, "error": exc.message_ko})
        # ANNOTATIONS (ADD)
        for ann in item.annotations:
            if not str(ann.name).strip():
                continue
            try:
                await apply_annotation(
                    connection_id, owner, table, column, ann.name, ann.value, "add", recorder
                )
                done += 1
                results.append({"target": label, "kind": f"annotation:{ann.name}", "ok": True})
            except AppError as exc:
                failed += 1
                results.append(
                    {"target": label, "kind": f"annotation:{ann.name}", "ok": False, "error": exc.message_ko}
                )
    return {"results": results, "summary": {"done": done, "failed": failed}}
