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
from app.services import common, resource_service

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
    {"prompt": "고객은 모두 몇 명인가요?", "recommended_action": "runsql", "schema": "SH"},
    {
        "prompt": "샌프란시스코에 사는 기혼 고객은 몇 명인가요?",
        "recommended_action": "runsql", "schema": "SH",
    },
    {
        "prompt": "샌프란시스코 상위 고객 3명은 누구인가요?",
        "recommended_action": "narrate", "schema": "SH",
    },
    {
        "prompt": "국가별 고객 수를 알려주세요",
        "recommended_action": "runsql", "schema": "SH",
    },
    {
        "prompt": "가장 많은 연령대는 무엇인가요?",
        "recommended_action": "narrate", "schema": "SH",
    },
    {"prompt": "총 시청 횟수는 얼마인가요?", "recommended_action": "showsql", "schema": "ADMIN"},
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
    response_text = await _generate_resilient(
        connection_id,
        prompt=prompt,
        profile_name=resolved,
        action=action,
        params_json=params_json,
        timeout=timeout,
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


# 일시적 커넥션/페치 오류 — 새 커넥션으로 1회 재시도(풀 재생성). ORA-01002(fetch out of sequence) 등:
# GENERATE 내부 커밋이나 풀의 세션 상태 오염(예: 긍정 피드백 시드의 SET_PROFILE 잔존)이 원인일 수 있다.
_TRANSIENT_RETRY_CODES = {"DB_CONNECTION_UNSTABLE"}


async def _generate_resilient(
    connection_id: str,
    *,
    prompt: str,
    profile_name: str,
    action: str,
    params_json: str | None,
    timeout: int,
    recorder: oracle.SqlRecorder,
) -> str:
    """call_generate를 자가복구와 함께 실행.

    ① DATA_ACCESS_DISABLED → 같은 세션에 ENABLE_DATA_ACCESS 적용 후 재시도.
    ② DB_CONNECTION_UNSTABLE(ORA-01002 등) → 풀을 닫아 오염/끊긴 세션을 버리고 새 커넥션으로 1회 재시도.
    """

    async def _attempt() -> str:
        async with pool_registry.acquire(connection_id, timeout) as conn:
            try:
                return await call_generate(
                    conn,
                    prompt=prompt,
                    profile_name=profile_name,
                    action=action,
                    params_json=params_json,
                    recorder=recorder,
                )
            except AppError as exc:
                # Data Access는 세션 단위라 새 세션은 기본 비활성일 수 있다 → 같은 세션에서 자가복구.
                if exc.app_code == "DATA_ACCESS_DISABLED":
                    intent = await common.get_data_access_state(connection_id)
                    if intent != "disabled":
                        await oracle.execute(
                            conn,
                            "BEGIN DBMS_CLOUD_AI.ENABLE_DATA_ACCESS; END;",
                            recorder=recorder,
                        )
                        await common.set_data_access_state(connection_id, True)
                        return await call_generate(
                            conn,
                            prompt=prompt,
                            profile_name=profile_name,
                            action=action,
                            params_json=params_json,
                            recorder=recorder,
                        )
                raise

    try:
        return await _attempt()
    except AppError as exc:
        if exc.app_code in _TRANSIENT_RETRY_CODES:
            await pool_registry.close_pool(connection_id)  # 오염/끊긴 세션 폐기 → 새 커넥션
            return await _attempt()
        raise


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
    raw_sql = await _generate_resilient(
        connection_id,
        prompt=prompt,
        profile_name=profile_name,
        action="showsql",
        params_json=params_json,
        timeout=pool_registry.CALL_TIMEOUT_SHOWSQL_MS,
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

    async def _fetch() -> tuple[list[str], list[list[Any]]]:
        async with pool_registry.acquire(
            connection_id, pool_registry.CALL_TIMEOUT_GENERATE_MS
        ) as conn:
            return await common.call_db(
                oracle.fetch_all(conn, generated_sql, max_rows=row_limit), recorder
            )

    try:
        columns, rows = await _fetch()
    except AppError as exc:
        # 일시적 페치 오류(ORA-01002 등) → 풀 재생성 후 1회 재시도
        if exc.app_code in _TRANSIENT_RETRY_CODES:
            await pool_registry.close_pool(connection_id)
            columns, rows = await _fetch()
        else:
            raise
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


# FEEDBACK의 sql_text는 'select ai <action> <프롬프트>' 형태의 'Select AI 문장'이어야 한다
# (레퍼런스 §FEEDBACK p104 예제). 그냥 프롬프트만 주면 ORA-20000 'is not a Select AI statement'.
FEEDBACK_AI_ACTION = "showsql"


def _ai_statement_text(raw: str) -> str:
    """프롬프트를 FEEDBACK이 요구하는 'select ai <action> <프롬프트>' 형식으로 정규화."""
    text = raw.strip()
    if text.lower().startswith("select ai"):
        return text
    return f"select ai {FEEDBACK_AI_ACTION} {text}"


async def _seed_mapped_sql(
    conn: Any, profile_name: str, ai_text: str, recorder: oracle.SqlRecorder
) -> None:
    """긍정 피드백 사전조건 — v$mapped_sql에 prompt→SQL 매핑을 시드한다.

    긍정 피드백은 '실제로 생성된 SQL'을 확정하므로 v$mapped_sql 매핑이 있어야 한다.
    그러나 본 앱은 stateless 원칙상 GENERATE() 경로로만 실행해 매핑을 남기지 않는다.
    따라서 같은 커넥션에서 프로파일을 설정하고 Select AI 프리픽스 문장을 1회 실행해
    매핑을 생성한다. (이 커넥션에 SET_PROFILE 세션 상태가 남지만, 모든 GENERATE 호출은
    profile_name을 명시 전달하므로 영향 없음 — 긍정 피드백 한정 예외.)
    """
    await oracle.execute(
        conn, "BEGIN DBMS_CLOUD_AI.SET_PROFILE(:p); END;", {"p": profile_name}, recorder
    )
    # 'select ai ...' 프리픽스는 자연어 프롬프트라 바인드 불가 → 완성 문장을 직접 실행.
    await oracle.fetch_value(conn, ai_text, recorder=recorder)


async def send_feedback(
    connection_id: str, body: FeedbackRequest, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """§5.3 DBMS_CLOUD_AI.FEEDBACK — sql_id 또는 sql_text 중 하나 필수.

    sql_text 경로는 'select ai <action> <프롬프트>' 형식으로 정규화한다.
    긍정 피드백은 v$mapped_sql 매핑이 필요하므로 같은 커넥션에서 1회 시드한다.
    """
    common.validate_identifier(body.profile_name, "프로파일 이름")
    if not body.sql_id and not body.sql_text:
        raise AppError(
            status_code=400,
            code="FEEDBACK_INVALID",
            app_code="FEEDBACK_INVALID",
            message_ko="sql_id 또는 sql_text 중 하나를 지정해야 합니다.",
        )
    use_sql_id = bool(body.sql_id)
    ai_text = None if use_sql_id else _ai_statement_text(body.sql_text or "")
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
        binds["sql_text"] = ai_text
        ref = f"sql_text => '{common.escape_literal(ai_text or '')}'"
    recorder.record(
        "BEGIN DBMS_CLOUD_AI.FEEDBACK("
        f"profile_name => '{common.escape_literal(body.profile_name)}', {ref}, "
        f"feedback_type => '{body.feedback_type}', operation => '{body.operation}'); END;"
    )
    is_delete = body.operation == "delete"
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_GENERATE_MS
    ) as conn:
        # 긍정 추가(add) + sql_text 경로만 v$mapped_sql 매핑 시드 필요. 삭제는 시드 불필요.
        if (
            not is_delete
            and not use_sql_id
            and body.feedback_type == "positive"
            and ai_text is not None
        ):
            await _seed_mapped_sql(conn, body.profile_name, ai_text, recorder)
        await common.call_db(oracle.execute(conn, sql, binds), recorder)
        # 적용 확인 — add일 때만 방금 저장된 행을 읽어 증빙으로 반환. delete는 None.
        stored = (
            None
            if is_delete
            else await _read_feedback_row(
                conn, body.profile_name, ai_text=ai_text, sql_id=body.sql_id, recorder=recorder
            )
        )
    return {
        "ok": True,
        "feedback_type": body.feedback_type,
        "operation": body.operation,
        "stored": stored,  # None이면 저장 확인 실패(드묾) — UI는 목록 조회로 폴백
    }


# ---------------------------------------------------------------- feedback 저장 내용 조회(검증)
def feedback_table_name(profile_name: str) -> str:
    """DBMS_CLOUD_AI.FEEDBACK이 자동 생성하는 피드백 벡터 테이블명.

    형식: <PROFILE>_FEEDBACK_VECINDEX$VECTAB (미인용 식별자 → 대문자). 레퍼런스 §FEEDBACK.
    """
    return f"{profile_name.upper()}_FEEDBACK_VECINDEX$VECTAB"


# 피드백 행 선택 — CONTENT(프롬프트) + ATTRIBUTES(JSON)에서 필요한 필드 추출
_FEEDBACK_SELECT = (
    "SELECT t.CONTENT AS prompt, "
    "JSON_VALUE(t.ATTRIBUTES, '$.sql_text') AS sql_text, "
    "JSON_VALUE(t.ATTRIBUTES, '$.sql_id') AS sql_id, "
    "JSON_VALUE(t.ATTRIBUTES, '$.feedback_type') AS feedback_type, "
    "JSON_VALUE(t.ATTRIBUTES, '$.response') AS response, "
    "JSON_VALUE(t.ATTRIBUTES, '$.feedback_content') AS feedback_content "
    'FROM "{table}" t'
)


def _feedback_row_to_dict(columns: list[str], row: list[Any]) -> dict[str, Any]:
    d = {col.lower(): val for col, val in zip(columns, row)}
    return {
        "prompt": d.get("prompt"),
        "sql_text": d.get("sql_text"),
        "sql_id": d.get("sql_id"),
        "feedback_type": d.get("feedback_type"),
        "response": d.get("response"),
        "feedback_content": d.get("feedback_content"),
    }


async def _read_feedback_row(
    conn: Any,
    profile_name: str,
    *,
    ai_text: str | None,
    sql_id: str | None,
    recorder: oracle.SqlRecorder,
) -> dict[str, Any] | None:
    """방금 저장한 피드백 1건을 sql_text 또는 sql_id로 조회 — 적용 확인용."""
    table = feedback_table_name(profile_name)
    if sql_id:
        where, binds = "WHERE JSON_VALUE(t.ATTRIBUTES, '$.sql_id') = :ref", {"ref": sql_id}
    elif ai_text:
        where, binds = "WHERE JSON_VALUE(t.ATTRIBUTES, '$.sql_text') = :ref", {"ref": ai_text}
    else:
        return None
    sql = f"{_FEEDBACK_SELECT.format(table=table)} {where} FETCH FIRST 1 ROWS ONLY"
    try:
        columns, rows = await common.call_db(oracle.fetch_all(conn, sql, binds), recorder)
    except AppError as exc:
        if exc.app_code == "OBJECT_NOT_FOUND":  # 아직 피드백 테이블 없음
            return None
        raise
    return _feedback_row_to_dict(columns, rows[0]) if rows else None


async def list_feedback(
    connection_id: str,
    profile_name: str,
    recorder: oracle.SqlRecorder,
    *,
    prompt: str | None = None,
) -> dict[str, Any]:
    """프로파일에 저장된 피드백 목록 조회(검증 패널용).

    피드백 벡터 테이블이 없으면(0건) exists=False + 빈 목록. prompt 지정 시 해당 프롬프트
    포함 항목만 필터.
    """
    common.validate_identifier(profile_name, "프로파일 이름")
    table = feedback_table_name(profile_name)
    sql = f"{_FEEDBACK_SELECT.format(table=table)} FETCH FIRST 200 ROWS ONLY"
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        try:
            columns, rows = await common.call_db(oracle.fetch_all(conn, sql), recorder)
        except AppError as exc:
            if exc.app_code == "OBJECT_NOT_FOUND":
                return {"profile_name": profile_name, "table": table, "exists": False, "items": []}
            raise
    items = [_feedback_row_to_dict(columns, r) for r in rows]
    if prompt:
        needle = prompt.strip()
        items = [
            it
            for it in items
            if (it.get("sql_text") and needle in it["sql_text"])
            or (it.get("prompt") and needle in it["prompt"])
        ]
    return {"profile_name": profile_name, "table": table, "exists": True, "items": items}


# ---------------------------------------------------------------- feedback 권한 점검/부여
# feedback의 sql_id(마지막 AI SQL) 경로는 SYS.V_$MAPPED_SQL / V_$SESSION READ 권한 필요 (레퍼런스 §14)
FEEDBACK_OBJECTS = ("V_$MAPPED_SQL", "V_$SESSION")
FEEDBACK_GRANTS_SQL = (
    "SELECT table_name FROM DBA_TAB_PRIVS "
    "WHERE grantee = :grantee AND owner = 'SYS' "
    "AND table_name IN ('V_$MAPPED_SQL', 'V_$SESSION') "
    "AND privilege IN ('READ', 'SELECT')"
)
GRANT_ANY_OBJ_SQL = (
    "SELECT privilege FROM SESSION_PRIVS WHERE privilege = 'GRANT ANY OBJECT PRIVILEGE'"
)
_SESSION_USER_SQL = "SELECT SYS_CONTEXT('USERENV', 'SESSION_USER') FROM dual"


async def check_feedback_privileges(
    connection_id: str, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """feedback(sql_id 경로) 권한 점검 — V_$MAPPED_SQL/V_$SESSION READ 보유·부여 가능 여부."""
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
    ) as conn:
        current = str(await oracle.fetch_value(conn, _SESSION_USER_SQL, recorder=recorder)).upper()
        _, granted_rows = await oracle.fetch_all(
            conn, FEEDBACK_GRANTS_SQL, {"grantee": current}, recorder=recorder
        )
        _, ga_rows = await oracle.fetch_all(conn, GRANT_ANY_OBJ_SQL, recorder=recorder)

    held = {str(r[0]) for r in granted_rows}
    missing = [obj for obj in FEEDBACK_OBJECTS if obj not in held]
    can_grant = bool(ga_rows)  # GRANT ANY OBJECT PRIVILEGE 보유 시 SYS 객체 권한 부여 가능
    can_grant_all = bool(missing) and can_grant
    grant_sql = [f"GRANT READ ON SYS.{obj} TO {current}" for obj in missing]

    blocked_reason = None
    if missing and not can_grant_all:
        blocked_reason = (
            "이 접속 사용자는 SYS 객체 권한을 부여할 권한(GRANT ANY OBJECT PRIVILEGE)이 없어 "
            "부여할 수 없습니다. DBA에게 V_$MAPPED_SQL/V_$SESSION READ 권한을 요청하세요. "
            "(권한 없이도 sql_text 기반 피드백은 가능합니다.)"
        )
    return {
        "current_user": current,
        "required": list(FEEDBACK_OBJECTS),
        "held": sorted(held),
        "missing": missing,
        "has_feedback_grants": not missing,
        "can_grant_all": can_grant_all,
        "grant_sql": grant_sql,
        "blocked_reason_ko": blocked_reason,
    }


async def grant_feedback_privileges(
    connection_id: str, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """누락된 feedback 권한(READ on SYS.V_$MAPPED_SQL/V_$SESSION)을 부여 — ledger 기록."""
    results: list[dict[str, Any]] = []
    done = 0
    failed = 0
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
    ) as conn:
        current = str(await oracle.fetch_value(conn, _SESSION_USER_SQL, recorder=recorder)).upper()
        _, granted_rows = await oracle.fetch_all(
            conn, FEEDBACK_GRANTS_SQL, {"grantee": current}, recorder=recorder
        )
        held = {str(r[0]) for r in granted_rows}
        for obj in FEEDBACK_OBJECTS:
            if obj in held:
                results.append({"object": obj, "ok": True, "skipped": True})
                continue
            sql = f"GRANT READ ON SYS.{obj} TO {current}"
            recorder.record(sql)
            try:
                await common.call_db(oracle.execute(conn, sql), recorder)
                done += 1
                results.append({"object": obj, "ok": True})
                await resource_service.record(
                    connection_id,
                    resource_type="grant",
                    resource_name=f"READ:SYS.{obj}:{current}",
                    create_sql=sql,
                    cleanup_sql=f"REVOKE READ ON SYS.{obj} FROM {current}",
                )
            except AppError as exc:
                failed += 1
                msg = exc.message_ko
                if "01031" in (exc.detail or "") or "권한" in msg:
                    msg = "이 사용자에게는 해당 SYS 객체 권한을 부여할 권한이 없습니다 (ADB 제약)."
                results.append({"object": obj, "ok": False, "error": msg})
    return {"current_user": current, "results": results, "summary": {"done": done, "failed": failed}}
