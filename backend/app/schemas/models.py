"""Select AI Demo Studio — API 스키마 (Pydantic v2).

docs/api-spec.md §11과 1:1 — 모든 에이전트의 공유 계약이므로 임의 변경 금지.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# ---------------------------------------------------------------- 공통


class ErrorBody(BaseModel):
    code: str                      # ORA-20000 / DPY-6005 / 앱 코드
    app_code: str                  # DATA_ACCESS_DISABLED 등
    message_ko: str
    hint_ko: Optional[str] = None
    detail: Optional[str] = None
    retryable: bool = False
    executed_sql: list[str] = []
    docs_ref: Optional[str] = None
    candidates: Optional[list["AdbCandidate"]] = None  # ADB_AMBIGUOUS(§2.7) 전용


class ErrorResponse(BaseModel):
    error: ErrorBody


class Envelope(BaseModel):
    """모든 성공 응답의 공통 래퍼. data는 엔드포인트별 모델."""
    data: Any
    executed_sql: list[str] = []   # 비밀 값은 ***MASKED*** 처리 후 노출
    elapsed_ms: int


# ---------------------------------------------------------------- connections


class WalletUploadResult(BaseModel):
    wallet_id: str
    tns_aliases: list[str]
    files_found: list[str]


class WalletGenerateRequest(BaseModel):
    """wallet 자동 다운로드 (§2.7, OCI CLI 경로)."""
    adb_name: str = Field(min_length=1, max_length=255)
    wallet_password: str = Field(repr=False)        # 다운로드 zip에 설정할 암호 — 로그 마스킹
    compartment_id: str = (
        "ocid1.compartment.oc1..aaaaaaaaihv5qjkvzwovuc6bwm32ikrjjtz3syuevn47b44ssikueho2umxq"
    )                                               # 기본: TAEWAN.KIM (CLAUDE.md 전역 규칙)
    oci_profile: str = "DEFAULT"                    # ~/.oci/config 프로파일
    adb_ocid: Optional[str] = None                  # 복수 매칭 후 재호출 시 지정


class WalletGenerateResult(WalletUploadResult):
    """§2.1 업로드와 동일 스키마 + adb_ocid."""
    adb_ocid: str


class AdbCandidate(BaseModel):
    """ADB_AMBIGUOUS(409) 오류의 후보 목록 항목 (§2.7)."""
    adb_ocid: str
    display_name: str
    workload_type: Optional[str] = None


class ConnectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    wallet_id: str
    tns_alias: str
    username: Literal["admin", "ADMIN"] = "admin"   # v1: admin 고정
    password: str = Field(repr=False)               # 로그/repr 마스킹
    validate_: bool = Field(default=True, alias="validate")


class ConnectionUpdate(BaseModel):
    """§2.6 — 모든 필드 optional. 비밀번호 변경 시 재검증."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    tns_alias: Optional[str] = None
    password: Optional[str] = Field(default=None, repr=False)


class ConnectionOut(BaseModel):
    id: str
    name: str
    tns_alias: str
    username: str
    db_version: Optional[str] = None
    db_name: Optional[str] = None
    status: Literal["VALID", "INVALID", "UNKNOWN"]
    last_used_at: Optional[datetime] = None
    created_at: datetime


class ConnectionTestResult(BaseModel):
    ok: bool
    db_version: Optional[str] = None
    latency_ms: Optional[int] = None
    app_code: Optional[str] = None
    message_ko: Optional[str] = None
    hint_ko: Optional[str] = None


# ---------------------------------------------------------------- privileges


class CheckStatus(str, Enum):
    pass_ = "pass"
    fail = "fail"
    not_applicable = "not_applicable"
    unknown = "unknown"


class PrivilegeCheck(BaseModel):
    check_id: str                  # execute_dbms_cloud_ai / network_acl / data_access ...
    title_ko: str
    status: CheckStatus
    description_ko: str
    evidence_sql: Optional[str] = None
    fix_sql: Optional[str] = None  # 적용 전 미리보기 (FR-03)
    docs_ref: Optional[str] = None


class PrivilegeCheckResult(BaseModel):
    provider: str
    target_user: str
    overall: Literal["pass", "action_required"]
    checks: list[PrivilegeCheck]


class CredentialSpec(BaseModel):
    credential_name: str
    auth_type: Literal["api_key", "api_token", "resource_principal"]
    # api_key (OCI 서명 키)
    user_ocid: Optional[str] = None
    tenancy_ocid: Optional[str] = None
    private_key: Optional[str] = Field(default=None, repr=False)
    fingerprint: Optional[str] = None
    # api_token (외부 공급자)
    username: Optional[str] = None
    api_token: Optional[str] = Field(default=None, repr=False)


class PrivilegeApplyItem(BaseModel):
    check_id: str
    credential: Optional[CredentialSpec] = None    # check_id == "credential"
    enable: Optional[bool] = None                  # check_id == "data_access"


class PrivilegeApplyRequest(BaseModel):
    provider: str = "oci"
    target_user: str = "ADMIN"
    items: list[PrivilegeApplyItem]
    recheck: bool = True


class PrivilegeApplied(BaseModel):
    check_id: str
    ok: bool
    executed_sql: str
    error: Optional[ErrorBody] = None


class PrivilegeApplyResult(BaseModel):
    applied: list[PrivilegeApplied]
    recheck: Optional[PrivilegeCheckResult] = None


# ---------------------------------------------------------------- profiles


class ObjectRef(BaseModel):
    owner: str
    name: Optional[str] = None     # 생략 시 스키마 전체


class ProfileAttributes(BaseModel):
    """레퍼런스 §3 검증 21개 속성만 폼 필드로 노출 (R4)."""
    provider: Optional[str] = "oci"
    credential_name: Optional[str] = "OCI$RESOURCE_PRINCIPAL"
    object_list: Optional[list[ObjectRef]] = None
    object_list_mode: Optional[Literal["automated"]] = None
    comments: Optional[Literal["true", "false"]] = None
    annotations: Optional[Literal["true", "false"]] = None
    constraints: Optional[Literal["true", "false"]] = None
    conversation: Optional[Literal["true", "false"]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    model: Optional[str] = "meta.llama-3.3-70b-instruct"
    region: Optional[str] = "us-chicago-1"
    oci_compartment_id: Optional[str] = (
        "ocid1.compartment.oc1..aaaaaaaaihv5qjkvzwovuc6bwm32ikrjjtz3syuevn47b44ssikueho2umxq"
    )
    oci_apiformat: Optional[Literal["GENERIC", "COHERE"]] = None
    oci_endpoint_id: Optional[str] = None
    enforce_object_list: Optional[Literal["true", "false"]] = None
    case_sensitive_values: Optional[Literal["true", "false"]] = None
    target_language: Optional[str] = None
    vector_index_name: Optional[str] = None
    azure_resource_name: Optional[str] = None
    azure_deployment_name: Optional[str] = None
    provider_endpoint: Optional[str] = None


class ProfileCreate(BaseModel):
    profile_name: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,127}$")
    attributes: ProfileAttributes
    extra_attributes_json: Optional[str] = None    # 미검증 속성 "고급 JSON" (R4)


class ProfileAttributeOut(BaseModel):
    name: str
    value: Optional[str]
    verified: bool                 # 21개 검증 목록 포함 여부
    description_ko: Optional[str] = None
    docs_ref: Optional[str] = None


class ProfileDetail(BaseModel):
    profile_name: str
    status: Literal["ENABLED", "DISABLED"]
    attributes: list[ProfileAttributeOut]


class ProfileSummary(BaseModel):
    profile_name: str
    status: Literal["ENABLED", "DISABLED"]
    provider: Optional[str] = None
    model: Optional[str] = None
    is_default: bool = False       # 앱 설정 기준 (DB 아님)


class ProfileUpdate(BaseModel):
    attributes: dict[str, Any]     # SET_ATTRIBUTE(S) 대상 (검증/고급 모두 허용, 서버 검증)
    preview_only: bool = False


class ProfileStatusRequest(BaseModel):
    """§4.9 ENABLE/DISABLE 토글 (P1)."""
    enabled: bool


class DefaultProfileSetting(BaseModel):
    profile_name: str


# ---------------------------------------------------------------- selectai

SelectAIAction = Literal[
    "runsql", "showsql", "explainsql", "narrate", "chat",   # P0
    "showprompt", "feedback",                               # P1
    "summarize", "translate",                               # P2
]   # "showparameter"는 존재하지 않는 액션 — 정의 금지. "agent"는 범위 외.


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    action: SelectAIAction = "runsql"
    profile_name: Optional[str] = None      # None → 앱 기본 프로파일
    conversation_id: Optional[str] = None   # GENERATE params로 전달
    row_limit: int = Field(default=100, ge=1, le=1000)


class GenerateResult(BaseModel):
    action: SelectAIAction
    profile_name: str
    result_type: Literal["table", "sql", "text"]
    generated_sql: Optional[str] = None
    response_text: Optional[str] = None     # GENERATE 반환 CLOB
    columns: Optional[list[str]] = None     # runsql 전용
    rows: Optional[list[list[Any]]] = None
    row_count: Optional[int] = None
    truncated: Optional[bool] = None


class FeedbackRequest(BaseModel):
    profile_name: str
    sql_id: Optional[str] = None            # V$MAPPED_SQL 조회 값
    sql_text: Optional[str] = None          # 프롬프트 전체 텍스트
    feedback_type: Literal["positive", "negative"]
    response: Optional[str] = None          # negative 시 올바른 SQL
    feedback_content: Optional[str] = None
    operation: Literal["add", "delete"] = "add"


# ---------------------------------------------------------------- chat


class ConversationCreate(BaseModel):
    title: str = "Demo chat"
    description: Optional[str] = None
    retention_days: int = 7        # 기본값은 오픈 이슈 O4 결정에 따라 조정
    conversation_length: int = 10


class ConversationUpdate(BaseModel):
    """§6.5 UPDATE_CONVERSATION — 모든 필드 optional."""
    title: Optional[str] = None
    description: Optional[str] = None
    retention_days: Optional[int] = None
    conversation_length: Optional[int] = None


class ConversationOut(BaseModel):
    conversation_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    retention_days: Optional[int] = None
    conversation_length: Optional[int] = None


ConversationAction = Literal["runsql", "showsql", "explainsql", "narrate", "chat"]  # p47 Note


class ChatMessageRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    action: ConversationAction = "narrate"
    profile_name: Optional[str] = None


class ChatMessageOut(BaseModel):
    prompt_id: str
    prompt: str
    response: Optional[str] = None
    action: Optional[str] = None
    created_at: Optional[datetime] = None


class ChatCompareRequest(BaseModel):
    prompt: str
    action: ConversationAction = "chat"
    conversation_id: str
    profile_name: Optional[str] = None


class ChatCompareResult(BaseModel):
    without_context: GenerateResult
    with_context: GenerateResult


# ---------------------------------------------------------------- enrichment


class CommentEntry(BaseModel):
    table: str
    column: Optional[str] = None   # None이면 테이블 코멘트
    comment: str = Field(max_length=4000)


class CommentsApplyRequest(BaseModel):
    owner: str = "ADMIN"
    table_comment: Optional[CommentEntry] = None
    column_comments: list[CommentEntry] = []
    preview_only: bool = False


class DemoSchemaRequest(BaseModel):
    """§7.1 모호 스키마 원클릭 생성/초기화."""
    reset: bool = False


class ProfilePairRequest(BaseModel):
    base_name: str = "ENRICH_DEMO"
    object_list: list[ObjectRef]
    annotations: bool = False      # P1
    constraints: bool = False      # P1


class EnrichCompareRequest(BaseModel):
    prompt: str
    profile_off: str
    profile_on: str
    action: Literal["showsql", "runsql"] = "showsql"
    include_showprompt: bool = False   # P1: 증강 프롬프트에 COMMENT 포함 확인


class EnrichCompareSide(BaseModel):
    profile_name: str
    generated_sql: Optional[str] = None
    columns: Optional[list[str]] = None
    rows: Optional[list[list[Any]]] = None
    error: Optional[ErrorBody] = None  # 한쪽 실패 허용 (오답 시연이 목적)


class EnrichCompareResult(BaseModel):
    prompt: str
    before: EnrichCompareSide
    after: EnrichCompareSide
    augmented_prompt: Optional[str] = None  # include_showprompt=true 시


# ---------------------------------------------------------------- schema / dashboard


class TableInfo(BaseModel):
    table_name: str
    comment: Optional[str] = None
    num_rows: Optional[int] = None


class ColumnInfo(BaseModel):
    column_name: str
    data_type: str
    nullable: bool
    comment: Optional[str] = None


class HealthSignal(BaseModel):
    id: str
    status: Literal["green", "yellow", "red"]
    title_ko: str
    detail_ko: str
    fix_endpoint: Optional[str] = None


class DashboardHealth(BaseModel):
    overall: Literal["green", "yellow", "red"]
    signals: list[HealthSignal]


# ---------------------------------------------------------------- cleanup

CleanupResourceType = Literal[
    "profile", "credential", "acl", "conversation", "demo_table", "grant",
    "wallet", "connection", "vector_index",
]


class CleanupLedgerItem(BaseModel):
    id: str
    connection_id: str
    resource_type: CleanupResourceType
    resource_name: str
    owner: Optional[str] = None
    cleanup_order: int
    cleanup_status: Literal["pending", "done", "failed", "skipped"]
    cleanup_preview: str
    created_at: datetime
    cleaned_at: Optional[datetime] = None
    last_error: Optional[str] = None


class CleanupListResult(BaseModel):
    items: list[CleanupLedgerItem]
    summary: dict[str, int]


class CleanupRequest(BaseModel):
    item_ids: Optional[list[str]] = None
    resource_types: Optional[list[CleanupResourceType]] = None
    dry_run: bool = False
    include_app_files: bool = True


class CleanupItemResult(BaseModel):
    id: str
    resource_type: CleanupResourceType
    resource_name: str
    ok: bool
    status: Literal["done", "failed", "skipped", "preview"]
    cleanup_action: Optional[str] = None
    error: Optional[ErrorBody] = None


class CleanupResult(BaseModel):
    results: list[CleanupItemResult]
    summary: dict[str, int]
