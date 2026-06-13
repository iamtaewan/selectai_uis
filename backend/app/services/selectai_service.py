"""Select AI 실행 서비스 — GENERATE 단일 호출 경로 (latency 측정, runsql 2단계).

불변 규칙: DBMS_CLOUD_AI.GENERATE(prompt=>:prompt, profile_name=>:profile_name,
action=>:action, params=>:params) 바인드만. params JSON은 json.dumps 직렬화 후
단일 바인드로 전달. SELECT AI 키워드·SET_PROFILE·SET_CONVERSATION_ID 금지.
runsql 2단계(showsql→직접 실행)는 비SELECT 자동 차단 — 수동 오버라이드 없음
(security.md §3.3).
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.db import oracle, pool_registry
from app.errors import AppError
from app.schemas.models import FeedbackRequest, GenerateResult
from app.services import common

# 단일 GENERATE 패턴 (api-spec §5.2 / selectai-reference §2 p129) —
# params 바인드는 conversation_id가 없으면 NULL로 전달된다.
GENERATE_SQL = (
    "SELECT DBMS_CLOUD_AI.GENERATE(\n"
    "         prompt       => :prompt,\n"
    "         profile_name => :profile_name,\n"
    "         action       => :action,\n"
    "         params       => :params\n"
    "       ) AS response\n"
    "  FROM dual"
)

FEEDBACK_SQL_TEXT = (
    "BEGIN\n"
    "  DBMS_CLOUD_AI.FEEDBACK(\n"
    "      profile_name     => :profile_name,\n"
    "      sql_text         => :sql_text,\n"
    "      feedback_type    => :feedback_type,\n"
    "      response         => :response,\n"
    "      feedback_content => :feedback_content,\n"
    "      operation        => :operation);\n"
    "END;"
)
FEEDBACK_SQL_ID = (
    "BEGIN\n"
    "  DBMS_CLOUD_AI.FEEDBACK(\n"
    "      profile_name     => :profile_name,\n"
    "      sql_id           => :sql_id,\n"
    "      feedback_type    => :feedback_type,\n"
    "      response         => :response,\n"
    "      feedback_content => :feedback_content,\n"
    "      operation        => :operation);\n"
    "END;"
)

# 액션 메타데이터 (api-spec §5.1 — 레퍼런스 §1 ch8 공식 표만, showparameter/agent 미포함)
ACTIONS_META: list[dict[str, Any]] = [
    {
        "action": "runsql", "priority": "P0", "title_ko": "SQL 생성+실행",
        "result_type": "table",
        "description_ko": "자연어로 SQL을 생성하고 즉시 실행해 결과를 표로 반환합니다 (기본 액션).",
    },
    {
        "action": "showsql", "priority": "P0", "title_ko": "SQL만 표시",
        "result_type": "sql",
        "description_ko": "생성된 SQL 문장만 표시하고 실행하지 않습니다.",
    },
    {
        "action": "explainsql", "priority": "P0", "title_ko": "SQL+설명",
        "result_type": "text",
        "description_ko": "생성된 SQL과 LLM의 자연어 설명을 함께 반환합니다.",
    },
    {
        "action": "narrate", "priority": "P0", "title_ko": "결과 서술",
        "result_type": "text",
        "description_ko": "SQL 실행 결과를 자연어로 서술합니다. Data Access 비활성 시 ORA-20000으로 실패합니다.",
    },
    {
        "action": "chat", "priority": "P0", "title_ko": "LLM 대화",
        "result_type": "text",
        "description_ko": "프롬프트를 LLM에 직접 전달합니다 (pass-through).",
    },
    {
        "action": "showprompt", "priority": "P1", "title_ko": "증강 프롬프트 보기",
        "result_type": "text",
        "description_ko": "LLM에 전송되는 증강 프롬프트 원문을 표시합니다 (NL2SQL·RAG 지원).",
    },
    {
        "action": "feedback", "priority": "P1", "title_ko": "피드백",
        "result_type": "text",
        "description_ko": "생성 SQL에 긍정/부정 피드백을 제공해 이후 정확도를 개선합니다 (26ai 전용).",
    },
    {
        "action": "summarize", "priority": "P2", "title_ko": "요약", "result_type": "text",
        "description_ko": "긴 텍스트의 요약을 생성합니다.",
    },
    {
        "action": "translate", "priority": "P2", "title_ko": "번역", "result_type": "text",
        "description_ko": "provider가 oci일 때만 지원, target_language 속성 필요.",
    },
]

# 추천 프롬프트 (api-spec §5.4 — SH 스키마 검증 예제, selectai-reference §9)
SUGGESTED_PROMPTS: list[dict[str, str]] = [
    {"prompt": "how many customers exist", "recommended_action": "runsql", "schema": "SH"},
    {
        "prompt": "how many customers in San Francisco are married",
        "recommended_action": "runsql", "schema": "SH",
    },
    {
        "prompt": "what are the top 3 customers in San Francisco",
        "recommended_action": "narrate", "schema": "SH",
    },
    {
        "prompt": "break out count of customers by country",
        "recommended_action": "runsql", "schema": "SH",
    },
    {
        "prompt": "what age group is most common",
        "recommended_action": "narrate", "schema": "SH",
    },
    {"prompt": "what are our total views", "recommended_action": "showsql", "schema": "ADMIN"},
]

# 텍스트 계열 액션의 result_type 매핑
_RESULT_TYPES: dict[str, str] = {
    "runsql": "table",
    "showsql": "sql",
    "explainsql": "text",
    "narrate": "text",
    "chat": "text",
    "showprompt": "text",
    "feedback": "text",
    "summarize": "text",
    "translate": "text",
}

_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*|\s*```$", re.MULTILINE)
_LINE_COMMENT_RE = re.compile(r"--[^\n]*")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def render_generate_sql(
    prompt: str, profile_name: str, action: str, params_json: str | None
) -> str:
    """표시용 GENERATE SQL — 리터럴 치환 + '' 이스케이프 (api-spec §1.6, 표시 전용)."""
    parts = [
        f"prompt => '{common.escape_literal(prompt)}'",
        f"profile_name => '{common.escape_literal(profile_name)}'",
        f"action => '{action}'",
    ]
    if params_json:
        parts.append(f"params => '{common.escape_literal(params_json)}'")
    return f"SELECT DBMS_CLOUD_AI.GENERATE({', '.join(parts)}) AS response FROM dual"


def clean_generated_sql(text: str) -> str:
    """LLM 반환 SQL 정리 — 마크다운 펜스/공백/말미 세미콜론 제거."""
    cleaned = _FENCE_RE.sub("", text or "").strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()
    return cleaned


def ensure_select_only(sql: str) -> str:
    """읽기 전용 게이트 (security.md §3.3) — LLM 생성 SQL은 단일 SELECT만 실행.

    비SELECT(INSERT/UPDATE/DELETE/DROP/...)나 다중 문장은 수동 오버라이드 없이
    자동 차단한다. 차단 시 SQL 원문은 detail로 노출(표시만, 실행 불가).
    """
    stripped = _BLOCK_COMMENT_RE.sub(" ", _LINE_COMMENT_RE.sub(" ", sql)).strip()
    first_word = (stripped.split(None, 1)[0] if stripped else "").upper()
    if first_word not in ("SELECT", "WITH") or ";" in stripped:
        raise AppError(
            status_code=422,
            code="GENERATED_SQL_INVALID",
            app_code="GENERATED_SQL_INVALID",
            message_ko="LLM이 생성한 SQL이 SELECT 단일문이 아니어서 실행을 차단했습니다.",
            hint_ko="읽기 전용 게이트(자동 차단)입니다. 프롬프트를 조회 질의로 바꿔 다시 시도하세요.",
            detail=sql,
            retryable=True,
            docs_ref="security.md §3.3",
        )
    return sql


async def resolve_profile(connection_id: str, profile_name: str | None) -> str:
    """profile_name 미지정 시 앱 기본 프로파일 사용 — 없으면 400 NO_PROFILE (§5.2)."""
    if profile_name:
        return common.validate_identifier(profile_name, "프로파일 이름")
    default = await common.get_default_profile(connection_id)
    if not default:
        raise AppError(
            status_code=400,
            code="NO_PROFILE",
            app_code="NO_PROFILE",
            message_ko="사용할 프로파일이 없습니다. 기본 프로파일을 설정하거나 프로파일을 지정하세요.",
            hint_ko="프로파일 화면에서 프로파일을 만들고 기본으로 지정하세요.",
        )
    return default


async def call_generate(
    conn: Any,
    *,
    prompt: str,
    profile_name: str,
    action: str,
    params_json: str | None,
    recorder: oracle.SqlRecorder,
) -> str:
    """GENERATE 1회 실행 — 표시 SQL 기록 후 바인드 경로로 실행, CLOB→str 반환."""
    recorder.record(render_generate_sql(prompt, profile_name, action, params_json))
    value = await common.call_db(
        oracle.fetch_value(
            conn,
            GENERATE_SQL,
            {
                "prompt": prompt,
                "profile_name": profile_name,
                "action": action,
                "params": params_json,
            },
        ),
        recorder,
    )
    return str(value) if value is not None else ""


async def run_generate(
    connection_id: str,
    *,
    prompt: str,
    action: str,
    profile_name: str | None,
    conversation_id: str | None,
    row_limit: int,
    recorder: oracle.SqlRecorder,
) -> GenerateResult:
    """§5.2 액션 실행 — runsql은 2단계(showsql→게이트→직접 실행), 그 외 단일 GENERATE."""
    resolved = await resolve_profile(connection_id, profile_name)
    params_json = (
        json.dumps({"conversation_id": conversation_id}) if conversation_id else None
    )

    if action == "runsql":
        return await _run_runsql(
            connection_id,
            prompt=prompt,
            profile_name=resolved,
            params_json=params_json,
            row_limit=row_limit,
            recorder=recorder,
        )

    timeout = (
        pool_registry.CALL_TIMEOUT_SHOWSQL_MS
        if action in ("showsql", "showprompt")
        else pool_registry.CALL_TIMEOUT_GENERATE_MS
    )
    async with pool_registry.acquire(connection_id, timeout) as conn:
        response_text = await call_generate(
            conn,
            prompt=prompt,
            profile_name=resolved,
            action=action,
            params_json=params_json,
            recorder=recorder,
        )
    # showsql 반환은 SQL 원문 — explainsql은 SQL+해설 혼합이라 파싱 불확실 시 미설정 (§5.2)
    generated_sql = clean_generated_sql(response_text) if action == "showsql" else None
    return GenerateResult(
        action=action,
        profile_name=resolved,
        result_type=_RESULT_TYPES.get(action, "text"),
        generated_sql=generated_sql,
        response_text=response_text,
    )


async def _run_runsql(
    connection_id: str,
    *,
    prompt: str,
    profile_name: str,
    params_json: str | None,
    row_limit: int,
    recorder: oracle.SqlRecorder,
) -> GenerateResult:
    """runsql 2단계 — ① showsql로 SQL 획득 ② 게이트 통과 SELECT만 직접 실행 (§5.2)."""
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_SHOWSQL_MS
    ) as conn:
        raw_sql = await call_generate(
            conn,
            prompt=prompt,
            profile_name=profile_name,
            action="showsql",
            params_json=params_json,
            recorder=recorder,
        )
    generated_sql = clean_generated_sql(raw_sql)
    if not generated_sql:
        raise AppError(
            status_code=422,
            code="GENERATED_SQL_INVALID",
            app_code="GENERATED_SQL_INVALID",
            message_ko="LLM이 SQL을 생성하지 못했습니다.",
            hint_ko="프롬프트를 구체화하거나 comments 증강을 활성화해 보세요.",
            retryable=True,
            executed_sql=recorder.statements,
        )
    ensure_select_only(generated_sql)

    recorder.record(f"{generated_sql} -- row_limit {row_limit}")
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_GENERATE_MS
    ) as conn:
        columns, rows = await common.call_db(
            oracle.fetch_all(conn, generated_sql, max_rows=row_limit), recorder
        )
    truncated = len(rows) > row_limit
    rows = rows[:row_limit]
    return GenerateResult(
        action="runsql",
        profile_name=profile_name,
        result_type="table",
        generated_sql=generated_sql,
        columns=columns,
        rows=[[_jsonable(v) for v in row] for row in rows],
        row_count=len(rows),
        truncated=truncated,
    )


def _jsonable(value: Any) -> Any:
    """DB 값 → JSON 직렬화 가능 값 (datetime/Decimal 등은 문자열/수치로)."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


async def send_feedback(
    connection_id: str, body: FeedbackRequest, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """§5.3 DBMS_CLOUD_AI.FEEDBACK — sql_id 또는 sql_text 중 하나 필수."""
    common.validate_identifier(body.profile_name, "프로파일 이름")
    if not body.sql_id and not body.sql_text:
        raise AppError(
            status_code=400,
            code="FEEDBACK_INVALID",
            app_code="FEEDBACK_INVALID",
            message_ko="sql_id 또는 sql_text 중 하나를 지정해야 합니다.",
        )
    use_sql_id = bool(body.sql_id)
    sql = FEEDBACK_SQL_ID if use_sql_id else FEEDBACK_SQL_TEXT
    binds: dict[str, Any] = {
        "profile_name": body.profile_name,
        "feedback_type": body.feedback_type,
        "response": body.response,
        "feedback_content": body.feedback_content,
        "operation": body.operation,
    }
    if use_sql_id:
        binds["sql_id"] = body.sql_id
        ref = f"sql_id => '{common.escape_literal(body.sql_id or '')}'"
    else:
        binds["sql_text"] = body.sql_text
        ref = f"sql_text => '{common.escape_literal(body.sql_text or '')}'"
    recorder.record(
        "BEGIN DBMS_CLOUD_AI.FEEDBACK("
        f"profile_name => '{common.escape_literal(body.profile_name)}', {ref}, "
        f"feedback_type => '{body.feedback_type}', operation => '{body.operation}'); END;"
    )
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_GENERATE_MS
    ) as conn:
        await common.call_db(oracle.execute(conn, sql, binds), recorder)
    return {"ok": True, "feedback_type": body.feedback_type, "operation": body.operation}
