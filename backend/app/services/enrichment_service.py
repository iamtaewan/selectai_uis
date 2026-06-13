"""증강 서비스 — 모호 스키마 시드, COMMENT DDL, 전/후 프로파일 쌍, 비교 실행.

근거: api-spec §7, selectai-reference.md §7, seeds/movie_*.sql.
COMMENT 본문은 '' 이중화(리터럴 위치), 객체명은 식별자 검증 후 사용 (security §3.2).
전/후 비교는 한쪽 실패를 허용한다 — "오답 vs 정답" 시연 자체가 목적 (§7.5).
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Any

from app.db import oracle, pool_registry
from app.errors import AppError
from app.schemas.models import (
    CommentsApplyRequest,
    EnrichCompareRequest,
    EnrichCompareResult,
    EnrichCompareSide,
    ErrorBody,
    ProfilePairRequest,
)
from app.services import (
    attribute_catalog,
    common,
    profile_service,
    resource_service,
    selectai_service,
)

# seeds/ 디렉토리 — backend/seeds/*.sql (스캐폴딩 배치 기준)
SEEDS_DIR = Path(__file__).resolve().parents[2] / "seeds"

DEMO_TABLES = ("TABLE1", "TABLE2", "TABLE3")
PROFILE_PAIR_SUFFIXES = ("OFF", "ON")

GET_TAB_COMMENT_SQL = (
    "SELECT table_name, comments FROM ALL_TAB_COMMENTS "
    "WHERE owner = :owner AND table_name = :table_name"
)
GET_TAB_COMMENTS_ALL_SQL = (
    "SELECT table_name, comments FROM ALL_TAB_COMMENTS WHERE owner = :owner "
    "AND table_name IN (SELECT table_name FROM ALL_TABLES WHERE owner = :owner) "
    "ORDER BY table_name"
)
GET_COL_COMMENTS_SQL = (
    "SELECT c.table_name, c.column_name, c.comments, col.data_type "
    "FROM ALL_COL_COMMENTS c "
    "JOIN ALL_TAB_COLUMNS col ON col.owner = c.owner "
    "AND col.table_name = c.table_name AND col.column_name = c.column_name "
    "WHERE c.owner = :owner AND c.table_name = :table_name "
    "ORDER BY col.column_id"
)


def _split_statements(script: str) -> list[str]:
    """seeds SQL 스크립트를 문장 단위로 분리 — 주석 제거 후 ';' 종결 기준.

    seeds 파일은 PL/SQL 블록 없이 단문(CREATE/INSERT/COMMENT/DROP)만 담는다.
    """
    no_comments = re.sub(r"^\s*--[^\n]*$", "", script, flags=re.MULTILINE)
    return [s.strip() for s in no_comments.split(";") if s.strip()]


def _load_seed(filename: str) -> list[str]:
    path = SEEDS_DIR / filename
    return _split_statements(path.read_text(encoding="utf-8"))


async def create_demo_schema(
    connection_id: str, reset: bool, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """§7.1 모호 스키마(c1~c7) 생성/시드 — reset=true면 DROP 후 재생성. ledger 기록."""
    async with common.get_lock(f"ddl:{connection_id}"):
        async with pool_registry.acquire(
            connection_id, pool_registry.CALL_TIMEOUT_SHOWSQL_MS
        ) as conn:
            if reset:
                for statement in _load_seed("movie_reset.sql"):
                    recorder.record(statement)
                    try:
                        await common.call_db(oracle.execute(conn, statement), recorder)
                    except AppError as exc:
                        if exc.app_code != "OBJECT_NOT_FOUND":  # 미존재 테이블 DROP은 무시
                            raise
            seeded_rows = 0
            for statement in _load_seed("movie_schema.sql"):
                recorder.record(statement)
                await common.call_db(oracle.execute(conn, statement), recorder)
                if statement.upper().startswith("INSERT"):
                    seeded_rows += 1
            recorder.record("COMMIT")
            await common.call_db(oracle.execute(conn, "COMMIT"), recorder)

    for table_name in DEMO_TABLES:
        await resource_service.record(
            connection_id,
            resource_type="demo_table",
            resource_name=table_name,
            owner="ADMIN",
            create_sql=f"CREATE TABLE {table_name.lower()} (...) -- seeds/movie_schema.sql",
            cleanup_sql=f"DROP TABLE {table_name.lower()} PURGE",
        )
    return {"tables": list(DEMO_TABLES), "seeded_rows": seeded_rows}


async def drop_demo_schema(
    connection_id: str, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """§7.1 DELETE — movie_reset.sql 기준 데모 테이블 + 비교용 프로파일 쌍 정리."""
    dropped_tables: list[str] = []
    dropped_profiles: list[str] = []
    async with common.get_lock(f"ddl:{connection_id}"):
        async with pool_registry.acquire(
            connection_id, pool_registry.CALL_TIMEOUT_SHOWSQL_MS
        ) as conn:
            for statement in _load_seed("movie_reset.sql"):
                recorder.record(statement)
                try:
                    await common.call_db(oracle.execute(conn, statement), recorder)
                    match = re.search(r"DROP TABLE (\w+)", statement, re.IGNORECASE)
                    if match:
                        dropped_tables.append(match.group(1).upper())
                except AppError as exc:
                    if exc.app_code != "OBJECT_NOT_FOUND":
                        raise
            # 비교용 프로파일 쌍 정리 (존재하지 않으면 무시)
            for suffix in PROFILE_PAIR_SUFFIXES:
                profile_name = f"ENRICH_DEMO_{suffix}"
                recorder.record(
                    f"BEGIN DBMS_CLOUD_AI.DROP_PROFILE('{profile_name}'); END;"
                )
                try:
                    await common.call_db(
                        oracle.execute(
                            conn,
                            profile_service.DROP_PROFILE_SQL,
                            {"profile_name": profile_name},
                        ),
                        recorder,
                    )
                    dropped_profiles.append(profile_name)
                except AppError as exc:
                    if exc.app_code not in ("PROFILE_NOT_FOUND", "ORACLE_ERROR"):
                        raise

    for table_name in DEMO_TABLES:
        await resource_service.mark_done_by_name(connection_id, "demo_table", table_name)
    for profile_name in dropped_profiles:
        await resource_service.mark_done_by_name(connection_id, "profile", profile_name)
    return {"dropped_tables": dropped_tables, "dropped_profiles": dropped_profiles}


async def get_comments(
    connection_id: str, owner: str, table: str | None, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """§7.2 코멘트 조회 — 테이블 코멘트 + 컬럼별 코멘트(타입 포함)."""
    common.validate_identifier(owner, "스키마 이름")
    owner_upper = owner.upper()
    tables: list[dict[str, Any]] = []
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        if table:
            common.validate_identifier(table, "테이블 이름")
            _, tab_rows = await oracle.fetch_all(
                conn, GET_TAB_COMMENT_SQL,
                {"owner": owner_upper, "table_name": table.upper()}, recorder=recorder,
            )
        else:
            _, tab_rows = await oracle.fetch_all(
                conn, GET_TAB_COMMENTS_ALL_SQL, {"owner": owner_upper}, recorder=recorder
            )
        for table_name, table_comment in tab_rows:
            _, col_rows = await oracle.fetch_all(
                conn, GET_COL_COMMENTS_SQL,
                {"owner": owner_upper, "table_name": str(table_name)}, recorder=recorder,
            )
            tables.append(
                {
                    "owner": owner_upper,
                    "table_name": str(table_name),
                    "comment": table_comment,
                    "columns": [
                        {
                            "column_name": str(column_name),
                            "data_type": str(data_type),
                            "comment": col_comment,
                        }
                        for _, column_name, col_comment, data_type in col_rows
                    ],
                }
            )
    return {"owner": owner_upper, "tables": tables}


def build_comment_ddl(body: CommentsApplyRequest) -> list[str]:
    """§7.3 COMMENT DDL 빌더 — 미리보기=실행 동일 문자열. '' 이스케이프 적용."""
    common.validate_identifier(body.owner, "스키마 이름")
    statements: list[str] = []
    if body.table_comment:
        entry = body.table_comment
        common.validate_identifier(entry.table, "테이블 이름")
        statements.append(
            f"COMMENT ON TABLE {body.owner}.{entry.table} "
            f"IS '{common.escape_literal(entry.comment)}'"
        )
    for entry in body.column_comments:
        common.validate_identifier(entry.table, "테이블 이름")
        if not entry.column:
            raise AppError(
                status_code=400,
                code="COLUMN_REQUIRED",
                app_code="COLUMN_REQUIRED",
                message_ko="column_comments 항목에는 column이 필요합니다.",
            )
        common.validate_identifier(entry.column, "컬럼 이름")
        statements.append(
            f"COMMENT ON COLUMN {body.owner}.{entry.table}.{entry.column} "
            f"IS '{common.escape_literal(entry.comment)}'"
        )
    if not statements:
        raise AppError(
            status_code=400,
            code="NO_COMMENTS",
            app_code="NO_COMMENTS",
            message_ko="적용할 코멘트가 없습니다.",
        )
    return statements


async def apply_comments(
    connection_id: str, body: CommentsApplyRequest, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """§7.3 COMMENT 적용 후 §7.2 재조회 결과 반환."""
    statements = build_comment_ddl(body)
    async with common.get_lock(f"ddl:{connection_id}"):
        async with pool_registry.acquire(
            connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
        ) as conn:
            for statement in statements:
                recorder.record(statement)
                await common.call_db(oracle.execute(conn, statement), recorder)
    target_table = body.table_comment.table if body.table_comment else (
        body.column_comments[0].table if body.column_comments else None
    )
    refreshed = await get_comments(connection_id, body.owner, target_table, recorder)
    return {"applied_ddl": statements, "comments": refreshed}


async def create_profile_pair(
    connection_id: str, body: ProfilePairRequest, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """§7.4 comments off/on 프로파일 쌍 — 기존 쌍은 DROP 후 재생성, ledger 기록."""
    common.validate_identifier(body.base_name, "프로파일 기본 이름")
    base = body.base_name.upper()
    object_list = [
        {"owner": ref.owner, **({"name": ref.name} if ref.name else {})}
        for ref in body.object_list
    ]
    results: dict[str, str] = {}
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        for suffix, comments_on in zip(PROFILE_PAIR_SUFFIXES, (False, True)):
            profile_name = f"{base}_{suffix}"
            # 이미 존재하면 DROP 후 재생성 (api-spec §7.4)
            recorder.record(f"BEGIN DBMS_CLOUD_AI.DROP_PROFILE('{profile_name}'); END;")
            try:
                await common.call_db(
                    oracle.execute(
                        conn,
                        profile_service.DROP_PROFILE_SQL,
                        {"profile_name": profile_name},
                    ),
                    recorder,
                )
            except AppError:
                pass  # 미존재 — 무시
            # 나머지 속성은 기본값(api-spec §4.1 defaults) — comments만 off/on이 다르다
            attributes: dict[str, Any] = {
                **attribute_catalog.DEFAULTS,
                "object_list": object_list,
                "comments": "true" if comments_on else "false",
            }
            if comments_on and body.annotations:
                attributes["annotations"] = "true"
            if comments_on and body.constraints:
                attributes["constraints"] = "true"
            plan = profile_service.build_create_profile(profile_name, attributes)
            recorder.record(plan.display_sql)
            await common.call_db(oracle.execute(conn, plan.sql, plan.binds), recorder)
            await resource_service.record(
                connection_id,
                resource_type="profile",
                resource_name=profile_name,
                create_sql=plan.display_sql,
                cleanup_sql=f"BEGIN DBMS_CLOUD_AI.DROP_PROFILE('{profile_name}'); END;",
            )
            results["profile_off" if not comments_on else "profile_on"] = profile_name
    return results


async def _compare_side(
    connection_id: str,
    *,
    prompt: str,
    profile_name: str,
    action: str,
    recorder: oracle.SqlRecorder,
) -> EnrichCompareSide:
    """비교 한쪽 실행 — 실패는 error 필드로 격리 (오답 시연 목적, §7.5)."""
    try:
        result = await selectai_service.run_generate(
            connection_id,
            prompt=prompt,
            action=action,
            profile_name=profile_name,
            conversation_id=None,
            row_limit=100,
            recorder=recorder,
        )
        return EnrichCompareSide(
            profile_name=profile_name,
            generated_sql=result.generated_sql
            or (result.response_text if action == "showsql" else None),
            columns=result.columns,
            rows=result.rows,
        )
    except AppError as exc:
        return EnrichCompareSide(
            profile_name=profile_name,
            error=ErrorBody(
                code=exc.code,
                app_code=exc.app_code,
                message_ko=exc.message_ko,
                hint_ko=exc.hint_ko,
                detail=exc.detail,
                retryable=exc.retryable,
                executed_sql=exc.executed_sql,
                docs_ref=exc.docs_ref,
            ),
        )


async def compare(
    connection_id: str, body: EnrichCompareRequest, recorder: oracle.SqlRecorder
) -> EnrichCompareResult:
    """§7.5 전/후 비교 — 동일 prompt를 프로파일만 바꿔 병렬 2회 실행."""
    common.validate_identifier(body.profile_off, "프로파일 이름")
    common.validate_identifier(body.profile_on, "프로파일 이름")
    recorder_off = oracle.SqlRecorder()
    recorder_on = oracle.SqlRecorder()
    before, after = await asyncio.gather(
        _compare_side(
            connection_id,
            prompt=body.prompt,
            profile_name=body.profile_off,
            action=body.action,
            recorder=recorder_off,
        ),
        _compare_side(
            connection_id,
            prompt=body.prompt,
            profile_name=body.profile_on,
            action=body.action,
            recorder=recorder_on,
        ),
    )
    for statement in recorder_off.statements + recorder_on.statements:
        recorder.statements.append(statement)

    augmented_prompt: str | None = None
    if body.include_showprompt:
        # P1 — ON 프로파일의 증강 프롬프트에 COMMENT 포함 확인 (showprompt 1회 추가)
        try:
            showprompt = await selectai_service.run_generate(
                connection_id,
                prompt=body.prompt,
                action="showprompt",
                profile_name=body.profile_on,
                conversation_id=None,
                row_limit=100,
                recorder=recorder,
            )
            augmented_prompt = showprompt.response_text
        except AppError:
            augmented_prompt = None  # showprompt 실패는 비교 결과에 영향 없음
    return EnrichCompareResult(
        prompt=body.prompt, before=before, after=after, augmented_prompt=augmented_prompt
    )
