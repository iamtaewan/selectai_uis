"""백엔드 Select AI 서비스 핵심 테스트 — GENERATE 단일 패턴, 비SELECT 게이트, 빌더.

실제 ADB 접속 없음 — pool_registry.acquire를 가짜 커넥션으로 대체한다.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.db import pool_registry
from app.errors import AppError
from app.schemas.models import (
    CommentEntry,
    CommentsApplyRequest,
    ObjectRef,
    ProfileAttributes,
    ProfileCreate,
)
from app.services import enrichment_service, profile_service, selectai_service


# ---------------------------------------------------------------- 가짜 DB 커넥션


class FakeCursor:
    def __init__(self, conn: "FakeConn") -> None:
        self.conn = conn
        self.step: dict[str, Any] = {}
        self.description: list[tuple] | None = None

    async def execute(self, sql: str, binds: Any = None) -> None:
        self.conn.executed.append((sql, binds))
        self.step = self.conn.steps.pop(0) if self.conn.steps else {}
        self.description = [(c,) for c in self.step.get("columns", [])]

    async def fetchone(self):
        return self.step.get("row")

    async def fetchmany(self, n: int):
        return self.step.get("rows", [])[:n]

    async def fetchall(self):
        return self.step.get("rows", [])

    def close(self) -> None:
        pass


class FakeConn:
    """steps: 실행 순서별 결과 시나리오 [{"row": [...]}, {"columns": [...], "rows": [...]}]."""

    def __init__(self, steps: list[dict[str, Any]]) -> None:
        self.steps = list(steps)
        self.executed: list[tuple[str, Any]] = []
        self.call_timeout = None

    def cursor(self) -> FakeCursor:
        return FakeCursor(self)


@pytest.fixture
def fake_db(monkeypatch):
    """pool_registry.acquire를 가짜 커넥션 공급자로 교체한다."""
    holder: dict[str, FakeConn] = {}

    def install(steps: list[dict[str, Any]]) -> FakeConn:
        conn = FakeConn(steps)
        holder["conn"] = conn

        @asynccontextmanager
        async def fake_acquire(connection_id: str, call_timeout_ms: int = 0):
            yield conn

        monkeypatch.setattr(pool_registry, "acquire", fake_acquire)
        return conn

    return install


# ---------------------------------------------------------------- 비SELECT 게이트


def test_gate_allows_select_and_with() -> None:
    assert selectai_service.ensure_select_only("SELECT 1 FROM dual")
    assert selectai_service.ensure_select_only("WITH t AS (SELECT 1 FROM dual) SELECT * FROM t")
    # 선행 주석 무시 후 판정
    assert selectai_service.ensure_select_only("-- cmt\nSELECT c7 FROM table2")


@pytest.mark.parametrize(
    "bad_sql",
    [
        "DROP TABLE table1",
        "DELETE FROM table1",
        "INSERT INTO table1 VALUES (1, 'x', 2)",
        "UPDATE table1 SET c3 = 0",
        "TRUNCATE TABLE table1",
        "SELECT 1 FROM dual; DROP TABLE table1",  # 다중 문장
        "BEGIN NULL; END;",
    ],
)
def test_gate_blocks_non_select(bad_sql: str) -> None:
    with pytest.raises(AppError) as exc_info:
        selectai_service.ensure_select_only(bad_sql)
    assert exc_info.value.app_code == "GENERATED_SQL_INVALID"
    assert exc_info.value.status_code == 422


def test_clean_generated_sql_strips_fence_and_semicolon() -> None:
    raw = "```sql\nSELECT COUNT(*) FROM sh.customers;\n```"
    assert selectai_service.clean_generated_sql(raw) == "SELECT COUNT(*) FROM sh.customers"


def test_render_generate_sql_escapes_quotes() -> None:
    rendered = selectai_service.render_generate_sql(
        "customers who don't own", "GENAI", "showsql", None
    )
    assert "don''t" in rendered  # api-spec §1.6 — 표시용 '' 이스케이프
    assert "DBMS_CLOUD_AI.GENERATE(" in rendered


# ---------------------------------------------------------------- GENERATE 실행 경로


@pytest.mark.anyio
async def test_runsql_two_step_flow(fake_db) -> None:
    """runsql — ① showsql GENERATE ② 게이트 통과 SELECT 직접 실행 (api-spec §5.2)."""
    conn = fake_db(
        [
            {"row": ["SELECT COUNT(*) FROM sh.customers"]},          # ① GENERATE(showsql)
            {"columns": ["COUNT(*)"], "rows": [[55500]]},            # ② 직접 실행
        ]
    )
    from app.db import oracle

    recorder = oracle.SqlRecorder()
    result = await selectai_service.run_generate(
        "conn_test",
        prompt="how many customers exist",
        action="runsql",
        profile_name="GENAI_DEMO",
        conversation_id=None,
        row_limit=100,
        recorder=recorder,
    )
    assert result.result_type == "table"
    assert result.rows == [[55500]]
    assert result.generated_sql == "SELECT COUNT(*) FROM sh.customers"
    # 단일 패턴 검증: 실행 SQL은 바인드 4종 (prompt/profile_name/action/params)
    generate_sql, binds = conn.executed[0]
    assert "DBMS_CLOUD_AI.GENERATE" in generate_sql
    assert ":prompt" in generate_sql and ":params" in generate_sql
    assert binds["action"] == "showsql" and binds["params"] is None
    # 금지 패턴 부재
    assert "SET_PROFILE" not in generate_sql
    assert "SET_CONVERSATION_ID" not in generate_sql
    # executed_sql 2건 노출 (① GENERATE 표시문 ② 실행 SELECT)
    assert len(recorder.statements) == 2
    assert "row_limit 100" in recorder.statements[1]


@pytest.mark.anyio
async def test_runsql_blocks_llm_dml(fake_db) -> None:
    """LLM이 DML을 생성하면 실행 단계 진입 전 자동 차단 (security.md §3.3)."""
    conn = fake_db([{"row": ["DROP TABLE customers"]}])
    from app.db import oracle

    with pytest.raises(AppError) as exc_info:
        await selectai_service.run_generate(
            "conn_test",
            prompt="drop the customers table",
            action="runsql",
            profile_name="GENAI_DEMO",
            conversation_id=None,
            row_limit=100,
            recorder=oracle.SqlRecorder(),
        )
    assert exc_info.value.app_code == "GENERATED_SQL_INVALID"
    assert len(conn.executed) == 1  # 2단계(실행)는 진입하지 않음


@pytest.mark.anyio
async def test_chat_action_passes_conversation_id_as_params(fake_db) -> None:
    """conversation_id는 params JSON 단일 바인드로만 전달 (불변 규칙 1·2)."""
    conn = fake_db([{"row": ["a context-aware answer"]}])
    from app.db import oracle

    result = await selectai_service.run_generate(
        "conn_test",
        prompt="break out count of customers by country",
        action="chat",
        profile_name="GENAI_DEMO",
        conversation_id="30C9DB6E-EA4D",
        row_limit=100,
        recorder=oracle.SqlRecorder(),
    )
    assert result.response_text == "a context-aware answer"
    _, binds = conn.executed[0]
    assert binds["params"] == '{"conversation_id": "30C9DB6E-EA4D"}'


# ---------------------------------------------------------------- 빌더 (미리보기=실행)


def _profile_create() -> ProfileCreate:
    return ProfileCreate(
        profile_name="GENAI_DEMO",
        attributes=ProfileAttributes(
            object_list=[ObjectRef(owner="SH", name="customers")], comments="true"
        ),
    )


def test_build_create_profile_binds_match_display() -> None:
    body = _profile_create()
    attributes = profile_service.build_attributes_dict(body)
    plan = profile_service.build_create_profile(body.profile_name, attributes)
    assert ":profile_name" in plan.sql and ":attributes" in plan.sql
    assert plan.binds["profile_name"] == "GENAI_DEMO"
    assert '"comments": "true"' in plan.binds["attributes"]
    assert '"object_list"' in plan.binds["attributes"]
    # 표시문에는 동일 JSON이 리터럴로 들어간다 (미리보기=실행 동일 빌더)
    assert "CREATE_PROFILE" in plan.display_sql


def test_extra_attributes_conflict_rejected() -> None:
    body = ProfileCreate(
        profile_name="P1",
        attributes=ProfileAttributes(),
        extra_attributes_json='{"comments": "true"}',
    )
    with pytest.raises(AppError) as exc_info:
        profile_service.build_attributes_dict(body)
    assert exc_info.value.app_code == "ATTRIBUTE_CONFLICT"


def test_invalid_profile_identifier_rejected() -> None:
    with pytest.raises(AppError) as exc_info:
        profile_service.build_create_profile("bad-name;drop", {})
    assert exc_info.value.app_code == "INVALID_IDENTIFIER"


def test_comment_ddl_escapes_quotes() -> None:
    body = CommentsApplyRequest(
        owner="ADMIN",
        table_comment=CommentEntry(table="TABLE1", comment="movie's catalog"),
        column_comments=[CommentEntry(table="TABLE2", column="C7", comment="views")],
    )
    ddl = enrichment_service.build_comment_ddl(body)
    assert ddl[0] == "COMMENT ON TABLE ADMIN.TABLE1 IS 'movie''s catalog'"
    assert ddl[1] == "COMMENT ON COLUMN ADMIN.TABLE2.C7 IS 'views'"


def test_seed_scripts_parse() -> None:
    """seeds 3종 — 문장 분리 검증 (PL/SQL 블록 없음, COMMENT는 comments 파일에만)."""
    schema = enrichment_service._load_seed("movie_schema.sql")
    comments = enrichment_service._load_seed("movie_comments.sql")
    reset = enrichment_service._load_seed("movie_reset.sql")
    assert sum(1 for s in schema if s.upper().startswith("CREATE TABLE")) == 3
    assert all(not s.upper().startswith("COMMENT") for s in schema)
    assert all(s.upper().startswith("COMMENT ON") for s in comments)
    assert [s.split()[0:2] for s in reset] == [["DROP", "TABLE"]] * 3


# ---------------------------------------------------------------- 정적 엔드포인트


def test_actions_meta_excludes_showparameter(client: TestClient) -> None:
    res = client.get("/api/v1/selectai/actions")
    assert res.status_code == 200
    actions = {a["action"] for a in res.json()["data"]}
    assert "showparameter" not in actions  # 존재하지 않는 액션 (레퍼런스 §1)
    assert "agent" not in actions          # 범위 외
    assert {"runsql", "showsql", "explainsql", "narrate", "chat", "showprompt"} <= actions


def test_suggested_prompts_static(client: TestClient) -> None:
    res = client.get("/api/v1/selectai/suggested-prompts")
    assert res.status_code == 200
    prompts = res.json()["data"]
    assert any(p["prompt"] == "how many customers exist" for p in prompts)
    assert all(p["schema"] in ("SH", "ADMIN") for p in prompts)


def test_generate_requires_connection_header(client: TestClient) -> None:
    res = client.post(
        "/api/v1/selectai/generate", json={"prompt": "how many customers exist"}
    )
    assert res.status_code == 400
    assert res.json()["error"]["app_code"] == "CONNECTION_REQUIRED"
