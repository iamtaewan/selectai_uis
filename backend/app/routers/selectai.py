"""Select AI 라우터 — /api/v1/selectai (FR-06 / api-spec §5).

엔드포인트 (인덱스 #18~#21):
- GET  /selectai/actions            액션 메타데이터 (정적 — 헤더 불필요)
- POST /selectai/generate           액션 실행 (GENERATE 단일 패턴 — 핵심)
- POST /selectai/feedback           피드백 (P1)
- GET  /selectai/suggested-prompts  추천 프롬프트 (정적)

불변 규칙: 모든 실행은 DBMS_CLOUD_AI.GENERATE(prompt=>:1, profile_name=>:2,
action=>:3, params=>:4) 바인드 패턴만. SELECT AI 키워드·SET_PROFILE·
SET_CONVERSATION_ID 금지. runsql은 showsql→SELECT 검증 후 직접 실행 2단계.
"""
from __future__ import annotations

from fastapi import APIRouter, Header

from app.db import oracle
from app.schemas.models import Envelope, FeedbackRequest, GenerateRequest
from app.services import common, selectai_service

router = APIRouter(prefix="/selectai", tags=["selectai"])


@router.get("/actions", response_model=Envelope)
async def list_actions() -> Envelope:
    """§5.1 액션 메타데이터 — 레퍼런스 §1 공식 표만 (showparameter 미존재·미포함)."""
    started = common.start_timer()
    return common.make_envelope(selectai_service.ACTIONS_META, [], started)


@router.post("/generate", response_model=Envelope)
async def generate(
    body: GenerateRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§5.2 액션 실행 — data: GenerateResult. runsql은 2단계(showsql → 검증 실행)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await selectai_service.run_generate(
        connection_id,
        prompt=body.prompt,
        action=body.action,
        profile_name=body.profile_name,
        conversation_id=body.conversation_id,
        row_limit=body.row_limit,
        recorder=recorder,
    )
    return common.make_envelope(result, recorder.statements, started)


@router.post("/feedback", response_model=Envelope)
async def feedback(
    body: FeedbackRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§5.3 피드백 (P1) — DBMS_CLOUD_AI.FEEDBACK."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    result = await selectai_service.send_feedback(connection_id, body, recorder)
    return common.make_envelope(result, recorder.statements, started)


@router.get("/suggested-prompts", response_model=Envelope)
async def suggested_prompts(
    profile_name: str | None = None,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§5.4 추천 프롬프트 — 프로파일 스코프(SH/OHV2 포함 여부)에 따라 예제 쿼리 선별.

    커넥션이 없으면 빈 목록(프론트가 커넥션 활성 시에만 호출).
    """
    started = common.start_timer()
    if not x_connection_id:
        return common.make_envelope({"sh": False, "ohv2": False, "prompts": []}, [], started)
    recorder = oracle.SqlRecorder()
    data = await selectai_service.suggested_prompts_for(x_connection_id, profile_name, recorder)
    return common.make_envelope(data, recorder.statements, started)


@router.get("/feedback/list", response_model=Envelope)
async def feedback_list(
    profile_name: str,
    prompt: str | None = None,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """프로파일에 저장된 피드백 목록 조회 — 적용 여부 명시적 검증(데이터 출력)."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await selectai_service.list_feedback(
        connection_id, profile_name, recorder, prompt=prompt
    )
    return common.make_envelope(data, recorder.statements, started)


@router.get("/feedback/privilege-check", response_model=Envelope)
async def feedback_privilege_check(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """피드백(sql_id 경로) 권한 점검 — V_$MAPPED_SQL/V_$SESSION READ 보유·부여 가능 여부."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await selectai_service.check_feedback_privileges(connection_id, recorder)
    return common.make_envelope(data, recorder.statements, started)


@router.post("/feedback/grant", response_model=Envelope)
async def feedback_grant(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """누락된 feedback 권한(READ on SYS.V_$MAPPED_SQL/V_$SESSION) 부여 시도."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    recorder = oracle.SqlRecorder()
    data = await selectai_service.grant_feedback_privileges(connection_id, recorder)
    return common.make_envelope(data, recorder.statements, started)
