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

from app.errors import not_implemented
from app.schemas.models import (
    ChatCompareRequest,
    ChatMessageRequest,
    ConversationCreate,
    ConversationUpdate,
    Envelope,
)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/conversations", response_model=Envelope, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    body: ConversationCreate,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.1 대화 생성 — data: ConversationOut (conversation_id = UUID)."""
    raise not_implemented("대화 생성")


@router.get("/conversations", response_model=Envelope)
async def list_conversations(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.3 대화 목록 — data: list[ConversationOut]."""
    raise not_implemented("대화 목록")


@router.post("/conversations/{conversation_id}/messages", response_model=Envelope)
async def send_message(
    conversation_id: str,
    body: ChatMessageRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.2 턴 실행 — data: GenerateResult + conversation_id 에코. 대화 지원 5액션만."""
    raise not_implemented("메시지 전송")


@router.get("/conversations/{conversation_id}/messages", response_model=Envelope)
async def list_messages(
    conversation_id: str,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.4 턴 이력 — data: {conversation_id, messages: list[ChatMessageOut]}."""
    raise not_implemented("턴 이력")


@router.patch("/conversations/{conversation_id}", response_model=Envelope)
async def update_conversation(
    conversation_id: str,
    body: ConversationUpdate,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.5 UPDATE_CONVERSATION — data: ConversationOut."""
    raise not_implemented("대화 수정")


@router.delete("/conversations/{conversation_id}", response_model=Envelope)
async def delete_conversation(
    conversation_id: str,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.6 DROP_CONVERSATION."""
    raise not_implemented("대화 삭제")


@router.delete("/conversations/{conversation_id}/messages/{prompt_id}", response_model=Envelope)
async def delete_message(
    conversation_id: str,
    prompt_id: str,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.6 보조 — DELETE_CONVERSATION_PROMPT(:prompt_id) 턴 1건 삭제."""
    raise not_implemented("턴 삭제")


@router.post("/compare", response_model=Envelope)
async def compare_context(
    body: ChatCompareRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§6.7 맥락 유무 비교 — data: ChatCompareResult. GENERATE 2회 병렬(asyncio.gather)."""
    raise not_implemented("맥락 비교")
