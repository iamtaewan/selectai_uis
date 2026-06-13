"""챗봇(Conversations) 라우터 — /api/v1/chat (FR-07 / api-spec §6).

엔드포인트 (인덱스 #22~#29):
- POST   /chat/conversations                          CREATE_CONVERSATION (Function형)
- GET    /chat/conversations                          대화 목록 (USER_CLOUD_AI_CONVERSATIONS)
- POST   /chat/conversations/{conversation_id}/messages  턴 실행 (params conversation_id)
- GET    /chat/conversations/{conversation_id}/messages  턴 이력
- PATCH  /chat/conversations/{conversation_id}        UPDATE_CONVERSATION
- DELETE /chat/conversations/{conversation_id}        DROP_CONVERSATION
- DELETE /chat/conversations/{conversation_id}/messages/{prompt_id}  턴 1건 삭제
- POST   /chat/compare                                맥락 유무 비교 (병렬 2회)

불변 규칙: SET_CONVERSATION_ID 금지 — conversation_id는 GENERATE params JSON
(json.dumps 직렬화, 단일 바인드)으로만 전달한다.
"""
from __future__ import annotations

from fastapi import APIRouter, Header, status

from app.db import oracle
from app.schemas.models import (
    ChatCompareRequest,
    ChatMessageRequest,
    ConversationCreate,
    ConversationUpdate,
    Envelope,
)
from app.services import common, conversation_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/conversations", response_model=Envelope, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.1 대화 생성 — data: ConversationOut (conversation_id = UUID)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await conversation_service.create_conversation(connection_id, body, recorder)
    return common.make_envelope(result, recorder.statements, started)


@router.get("/conversations", response_model=Envelope)
async def list_conversations(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.3 대화 목록 — data: list[ConversationOut]."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await conversation_service.list_conversations(connection_id, recorder)
    return common.make_envelope(result, recorder.statements, started)


@router.post("/conversations/{conversation_id}/messages", response_model=Envelope)
async def send_message(
    conversation_id: str,
    body: ChatMessageRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.2 턴 실행 — data: GenerateResult + conversation_id 에코. 대화 지원 5액션만."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await conversation_service.send_message(
        connection_id,
        conversation_id,
        prompt=body.prompt,
        action=body.action,
        profile_name=body.profile_name,
        recorder=recorder,
    )
    payload = result.model_dump()
    payload["conversation_id"] = conversation_id  # §6.2 — conversation_id 에코
    return common.make_envelope(payload, recorder.statements, started)


@router.get("/conversations/{conversation_id}/messages", response_model=Envelope)
async def list_messages(
    conversation_id: str,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.4 턴 이력 — data: {conversation_id, messages: list[ChatMessageOut]}."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    messages = await conversation_service.list_messages(
        connection_id, conversation_id, recorder
    )
    return common.make_envelope(
        {"conversation_id": conversation_id, "messages": messages},
        recorder.statements,
        started,
    )


@router.patch("/conversations/{conversation_id}", response_model=Envelope)
async def update_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.5 UPDATE_CONVERSATION — data: ConversationOut."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await conversation_service.update_conversation(
        connection_id, conversation_id, body, recorder
    )
    return common.make_envelope(result, recorder.statements, started)


@router.delete("/conversations/{conversation_id}", response_model=Envelope)
async def delete_conversation(
    conversation_id: str,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.6 DROP_CONVERSATION."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await conversation_service.drop_conversation(
        connection_id, conversation_id, recorder
    )
    return common.make_envelope(result, recorder.statements, started)


@router.delete("/conversations/{conversation_id}/messages/{prompt_id}", response_model=Envelope)
async def delete_message(
    conversation_id: str,
    prompt_id: str,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.6 보조 — DELETE_CONVERSATION_PROMPT(:prompt_id) 턴 1건 삭제."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await conversation_service.delete_prompt(connection_id, prompt_id, recorder)
    return common.make_envelope(result, recorder.statements, started)


@router.post("/compare", response_model=Envelope)
async def compare_context(
    body: ChatCompareRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.7 맥락 유무 비교 — data: ChatCompareResult. GENERATE 2회 병렬(asyncio.gather)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await conversation_service.compare_context(
        connection_id,
        prompt=body.prompt,
        action=body.action,
        conversation_id=body.conversation_id,
        profile_name=body.profile_name,
        recorder=recorder,
    )
    return common.make_envelope(result, recorder.statements, started)
