"""대화 서비스 — CREATE/UPDATE/DROP_CONVERSATION, 이력 뷰 조회, 맥락 비교 병렬 실행.

근거: api-spec §6, architecture.md §5. 대화 상태의 소유자는 ADB —
백엔드는 conversation_id를 저장하지 않고 통과시킨다 (stateless).
SET_CONVERSATION_ID 금지 — conversation_id는 GENERATE params(json.dumps)로만 전달.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from app.db import oracle, pool_registry
from app.errors import AppError
from app.schemas.models import (
    ChatCompareResult,
    ChatMessageOut,
    ConversationCreate,
    ConversationOut,
    ConversationUpdate,
    GenerateResult,
)
from app.services import common, resource_service, selectai_service

# Function형 CREATE_CONVERSATION — 세션 설정 Procedure형 사용 금지 (api-spec §6.1)
CREATE_CONVERSATION_SQL = (
    "SELECT DBMS_CLOUD_AI.CREATE_CONVERSATION(attributes => :attributes) "
    "AS conversation_id FROM dual"
)
UPDATE_CONVERSATION_SQL = (
    "BEGIN DBMS_CLOUD_AI.UPDATE_CONVERSATION(:conversation_id, attributes => :attributes); END;"
)
DROP_CONVERSATION_SQL = "BEGIN DBMS_CLOUD_AI.DROP_CONVERSATION(:conversation_id); END;"
DELETE_PROMPT_SQL = "BEGIN DBMS_CLOUD_AI.DELETE_CONVERSATION_PROMPT(:prompt_id); END;"

LIST_CONVERSATIONS_SQL = (
    "SELECT conversation_id, conversation_title, description, retention_days, "
    "conversation_length FROM USER_CLOUD_AI_CONVERSATIONS"
)
LIST_PROMPTS_SQL = (
    "SELECT * FROM USER_CLOUD_AI_CONVERSATION_PROMPTS "
    "WHERE conversation_id = :conversation_id"
)


async def create_conversation(
    connection_id: str, body: ConversationCreate, recorder: oracle.SqlRecorder
) -> ConversationOut:
    """§6.1 대화 생성 — UUID 반환 + ledger 기록 (cleanup = DROP_CONVERSATION)."""
    attributes = {
        "title": body.title,
        "retention_days": body.retention_days,
        "conversation_length": body.conversation_length,
    }
    if body.description:
        attributes["description"] = body.description
    attributes_json = json.dumps(attributes, ensure_ascii=False)
    display = (
        "SELECT DBMS_CLOUD_AI.CREATE_CONVERSATION("
        f"attributes => '{common.escape_literal(attributes_json)}') AS conversation_id FROM dual"
    )
    recorder.record(display)
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        conversation_id = await common.call_db(
            oracle.fetch_value(
                conn, CREATE_CONVERSATION_SQL, {"attributes": attributes_json}
            ),
            recorder,
        )
    conversation_id = str(conversation_id)
    await resource_service.record(
        connection_id,
        resource_type="conversation",
        resource_name=conversation_id,
        create_sql=display,
        cleanup_sql=f"BEGIN DBMS_CLOUD_AI.DROP_CONVERSATION('{conversation_id}'); END;",
    )
    return ConversationOut(
        conversation_id=conversation_id,
        title=body.title,
        description=body.description,
        retention_days=body.retention_days,
        conversation_length=body.conversation_length,
    )


async def list_conversations(
    connection_id: str, recorder: oracle.SqlRecorder
) -> list[ConversationOut]:
    """§6.3 대화 목록 (USER_CLOUD_AI_CONVERSATIONS)."""
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        _, rows = await oracle.fetch_all(conn, LIST_CONVERSATIONS_SQL, recorder=recorder)
    return [
        ConversationOut(
            conversation_id=str(row[0]),
            title=row[1],
            description=row[2],
            retention_days=_to_int(row[3]),
            conversation_length=_to_int(row[4]),
        )
        for row in rows
    ]


def _to_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _pick(columns: list[str], row: list[Any], *candidates: str) -> Any:
    """뷰 컬럼명 가변 대응 — 후보 이름 중 첫 일치 컬럼 값을 반환."""
    lookup = {name.upper(): idx for idx, name in enumerate(columns)}
    for candidate in candidates:
        idx = lookup.get(candidate.upper())
        if idx is not None:
            return row[idx]
    return None


async def list_messages(
    connection_id: str, conversation_id: str, recorder: oracle.SqlRecorder
) -> list[ChatMessageOut]:
    """§6.4 턴 이력 (USER_CLOUD_AI_CONVERSATION_PROMPTS)."""
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        columns, rows = await oracle.fetch_all(
            conn, LIST_PROMPTS_SQL, {"conversation_id": conversation_id}, recorder=recorder
        )
    messages: list[ChatMessageOut] = []
    for row in rows:
        row = list(row)
        messages.append(
            ChatMessageOut(
                prompt_id=str(
                    _pick(columns, row, "CONVERSATION_PROMPT_ID", "PROMPT_ID", "ID") or ""
                ),
                prompt=str(_pick(columns, row, "PROMPT", "USER_PROMPT") or ""),
                response=_opt_str(_pick(columns, row, "RESPONSE", "ANSWER")),
                action=_opt_str(_pick(columns, row, "ACTION", "PROMPT_ACTION")),
                created_at=_pick(columns, row, "CREATED_AT", "CREATED", "TIMESTAMP"),
            )
        )
    return messages


def _opt_str(value: Any) -> str | None:
    return str(value) if value is not None else None


async def update_conversation(
    connection_id: str,
    conversation_id: str,
    body: ConversationUpdate,
    recorder: oracle.SqlRecorder,
) -> ConversationOut:
    """§6.5 UPDATE_CONVERSATION — 지정 필드만 attributes JSON으로 전달."""
    attributes = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    if not attributes:
        raise AppError(
            status_code=400,
            code="NO_UPDATE_FIELDS",
            app_code="NO_UPDATE_FIELDS",
            message_ko="수정할 대화 속성이 없습니다.",
        )
    attributes_json = json.dumps(attributes, ensure_ascii=False)
    recorder.record(
        "BEGIN DBMS_CLOUD_AI.UPDATE_CONVERSATION("
        f"'{common.escape_literal(conversation_id)}', "
        f"attributes => '{common.escape_literal(attributes_json)}'); END;"
    )
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        await common.call_db(
            oracle.execute(
                conn,
                UPDATE_CONVERSATION_SQL,
                {"conversation_id": conversation_id, "attributes": attributes_json},
            ),
            recorder,
        )
    return ConversationOut(conversation_id=conversation_id, **attributes)


async def drop_conversation(
    connection_id: str, conversation_id: str, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """§6.6 DROP_CONVERSATION + ledger done 동기화."""
    recorder.record(
        f"BEGIN DBMS_CLOUD_AI.DROP_CONVERSATION('{common.escape_literal(conversation_id)}'); END;"
    )
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        await common.call_db(
            oracle.execute(
                conn, DROP_CONVERSATION_SQL, {"conversation_id": conversation_id}
            ),
            recorder,
        )
    await resource_service.mark_done_by_name(connection_id, "conversation", conversation_id)
    return {"dropped": True, "conversation_id": conversation_id}


async def delete_prompt(
    connection_id: str, prompt_id: str, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """§6.6 보조 — DELETE_CONVERSATION_PROMPT 턴 1건 삭제."""
    recorder.record(
        f"BEGIN DBMS_CLOUD_AI.DELETE_CONVERSATION_PROMPT('{common.escape_literal(prompt_id)}'); END;"
    )
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        await common.call_db(
            oracle.execute(conn, DELETE_PROMPT_SQL, {"prompt_id": prompt_id}), recorder
        )
    return {"deleted": True, "prompt_id": prompt_id}


async def send_message(
    connection_id: str,
    conversation_id: str,
    *,
    prompt: str,
    action: str,
    profile_name: str | None,
    recorder: oracle.SqlRecorder,
) -> GenerateResult:
    """§6.2 턴 실행 — per-conversation Lock으로 직렬화 (api-spec §12.5, 턴 순서 보장)."""
    async with common.get_lock(f"conversation:{conversation_id}"):
        return await selectai_service.run_generate(
            connection_id,
            prompt=prompt,
            action=action,
            profile_name=profile_name,
            conversation_id=conversation_id,
            row_limit=100,
            recorder=recorder,
        )


async def compare_context(
    connection_id: str,
    *,
    prompt: str,
    action: str,
    conversation_id: str,
    profile_name: str | None,
    recorder: oracle.SqlRecorder,
) -> ChatCompareResult:
    """§6.7 맥락 유무 비교 — 동일 프롬프트를 params 무/유로 병렬 2회 (asyncio.gather)."""
    recorder_without = oracle.SqlRecorder()
    recorder_with = oracle.SqlRecorder()
    without_result, with_result = await asyncio.gather(
        selectai_service.run_generate(
            connection_id,
            prompt=prompt,
            action=action,
            profile_name=profile_name,
            conversation_id=None,
            row_limit=100,
            recorder=recorder_without,
        ),
        selectai_service.run_generate(
            connection_id,
            prompt=prompt,
            action=action,
            profile_name=profile_name,
            conversation_id=conversation_id,
            row_limit=100,
            recorder=recorder_with,
        ),
    )
    # 실행 순서대로 병합: ① 맥락 없음 ② 맥락 있음 (api-spec §6.7 예시와 동일)
    for statement in recorder_without.statements + recorder_with.statements:
        recorder.statements.append(statement)
    return ChatCompareResult(without_context=without_result, with_context=with_result)
