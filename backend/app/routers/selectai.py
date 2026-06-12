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

from app.errors import not_implemented
from app.schemas.models import Envelope, FeedbackRequest, GenerateRequest

router = APIRouter(prefix="/selectai", tags=["selectai"])


@router.get("/actions", response_model=Envelope)
async def list_actions() -> Envelope:
    """§5.1 액션 메타데이터 — 레퍼런스 §1 공식 표만 (showparameter 미존재·미포함)."""
    raise not_implemented("액션 메타데이터")


@router.post("/generate", response_model=Envelope)
async def generate(
    body: GenerateRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§5.2 액션 실행 — data: GenerateResult. runsql은 2단계(showsql → 검증 실행)."""
    raise not_implemented("Select AI 실행")


@router.post("/feedback", response_model=Envelope)
async def feedback(
    body: FeedbackRequest,
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§5.3 피드백 (P1) — DBMS_CLOUD_AI.FEEDBACK."""
    raise not_implemented("피드백")


@router.get("/suggested-prompts", response_model=Envelope)
async def suggested_prompts() -> Envelope:
    """§5.4 추천 프롬프트 (canned, SH 스키마 검증 예제) — 정적."""
    raise not_implemented("추천 프롬프트")
