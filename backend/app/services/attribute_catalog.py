"""속성 카탈로그 — 검증 21개 속성의 한국어 해설·기본값·근거 페이지 (정적).

근거: api-spec §4.1, selectai-reference.md §3 (해설 문구 그대로 사용).
화이트리스트 외 속성은 "고급 JSON 직접 입력"으로 격리한다 (R4).

검증 속성 21종 — azure_resource_name/azure_deployment_name은 레퍼런스 §3에서
한 슬롯으로 검증된 쌍이므로 엔트리는 22개다 (schemas.ProfileAttributes 필드와 1:1).
"""
from __future__ import annotations

from typing import Any

from app.config import get_settings

# 컴파트먼트 OCID는 환경변수(DEFAULT_OCI_COMPARTMENT_ID)에서 주입 — 코드 하드코딩 금지.
_DEFAULT_COMPARTMENT_ID = get_settings().default_oci_compartment_id

# api-spec §4.1 defaults
DEFAULTS: dict[str, str] = {
    "provider": "oci",
    "credential_name": "OCI$RESOURCE_PRINCIPAL",
    "model": "meta.llama-3.3-70b-instruct",
    "region": "us-chicago-1",
    "oci_compartment_id": _DEFAULT_COMPARTMENT_ID,
}

# OCI GenAI Chat 모델 — us-chicago-1 ACTIVE/CHAT 모델 목록(2026-06 OCI CLI 기준).
# 벤더별·최신/빠른 모델 우선 정렬. (voice/tts 모델은 NL2SQL 부적합으로 제외)
OCI_CHAT_MODELS: list[str] = [
    # xAI Grok — 최신/빠른 변형 우선 (NL2SQL 권장: grok-4.3, grok-4-fast-non-reasoning)
    "xai.grok-4.3",
    "xai.grok-4-fast-non-reasoning",
    "xai.grok-4-fast-reasoning",
    "xai.grok-4-1-fast-non-reasoning",
    "xai.grok-4-1-fast-reasoning",
    "xai.grok-4",
    "xai.grok-4.20-reasoning",
    "xai.grok-4.20-non-reasoning",
    "xai.grok-4.20-0309-reasoning",
    "xai.grok-4.20-0309-non-reasoning",
    "xai.grok-4.20-multi-agent",
    "xai.grok-4.20-multi-agent-0309",
    "xai.grok-code-fast-1",
    "xai.grok-3",
    "xai.grok-3-fast",
    "xai.grok-3-mini",
    "xai.grok-3-mini-fast",
    # Google Gemini
    "google.gemini-2.5-pro",
    "google.gemini-2.5-flash",
    "google.gemini-2.5-flash-lite",
    # Meta Llama
    "meta.llama-4-maverick-17b-128e-instruct-fp8",
    "meta.llama-4-scout-17b-16e-instruct",
    "meta.llama-3.3-70b-instruct",
    "meta.llama-3.1-405b-instruct",
    "meta.llama-3.1-70b-instruct",
    "meta.llama-3.2-90b-vision-instruct",
    "meta.llama-3.2-11b-vision-instruct",
    "meta.llama-3-70b-instruct",
    # Cohere Command
    "cohere.command-a-03-2025",
    "cohere.command-a-reasoning",
    "cohere.command-a-vision",
    "cohere.command-latest",
    "cohere.command-plus-latest",
    "cohere.command-r-plus-08-2024",
    "cohere.command-r-08-2024",
    "cohere.command-r-16k",
    "cohere.command-r-plus",
    # OpenAI (OCI 제공 OSS)
    "openai.gpt-oss-120b",
    "openai.gpt-oss-20b",
]

# 구형/대체 권장 모델 — UI에서 비활성/경고 배지로 표기
DEPRECATED_MODELS: list[str] = [
    "cohere.command-r-16k",
    "cohere.command-r-plus",
    "meta.llama-3-70b-instruct",
]

# 검증 속성 카탈로그 (selectai-reference §3 표 전체 — 해설은 한국어 원문 그대로)
VERIFIED_ATTRIBUTES: list[dict[str, Any]] = [
    {
        "name": "provider",
        "type": "enum",
        "enum": ["oci", "openai", "azure", "google", "cohere", "anthropic", "aws"],
        "default": "oci",
        "required": True,
        "description_ko": (
            "AI 공급자. OpenAI 호환 공급자는 provider 대신 provider_endpoint로 지정합니다."
        ),
        "docs_ref": "p17, p78",
        "ui_group": "provider",
    },
    {
        "name": "credential_name",
        "type": "text",
        "default": "OCI$RESOURCE_PRINCIPAL",
        "required": False,
        "description_ko": (
            "AI 공급자 접근 자격증명 이름. DBMS_CLOUD.CREATE_CREDENTIAL로 생성하며, "
            'OCI Resource Principal 사용 시 "OCI$RESOURCE_PRINCIPAL"을 지정합니다.'
        ),
        "docs_ref": "p81",
        "ui_group": "provider",
    },
    {
        "name": "object_list",
        "type": "object_list",
        "default": None,
        "required": False,
        "description_ko": (
            'NL2SQL 대상 객체의 JSON 배열 ([{"owner":"SH","name":"customers"}] 또는 '
            '스키마 전체 [{"owner":"SH"}]). 미지정 시 현재 스키마의 모든 객체가 자동 '
            "선택되므로 항상 명시를 권장합니다 (security.md §4.2)."
        ),
        "docs_ref": "p78, p151",
        "ui_group": "objects",
    },
    {
        "name": "object_list_mode",
        "type": "enum",
        "enum": ["automated"],
        "default": None,
        "required": False,
        "description_ko": (
            '"automated" 설정 시 26ai에서 질의와 관련 있는 테이블 메타데이터만 자동 '
            "탐지·전송합니다. <profile_name>_OBJECT_LIST_VECINDEX 벡터 인덱스를 자동 생성합니다."
        ),
        "docs_ref": "p151-152",
        "ui_group": "objects",
    },
    {
        "name": "comments",
        "type": "boolean_string",
        "default": "false",
        "required": False,
        "description_ko": (
            '"true"면 테이블/컬럼 COMMENT를 LLM 메타데이터에 포함하여 SQL 생성 정확도를 '
            "높입니다. 메타데이터 증강 전/후 비교 데모의 핵심 속성입니다."
        ),
        "docs_ref": "p147-149",
        "ui_group": "metadata",
    },
    {
        "name": "annotations",
        "type": "boolean_string",
        "default": "false",
        "required": False,
        "description_ko": '"true"면 26ai 테이블/컬럼 ANNOTATIONS를 메타데이터에 포함합니다.',
        "docs_ref": "p149",
        "ui_group": "metadata",
    },
    {
        "name": "constraints",
        "type": "boolean_string",
        "default": "false",
        "required": False,
        "description_ko": (
            '"true"면 FK/참조 무결성 제약을 메타데이터에 포함해 JOIN 정확도를 높입니다.'
        ),
        "docs_ref": "p150",
        "ui_group": "metadata",
    },
    {
        "name": "conversation",
        "type": "boolean_string",
        "default": "false",
        "required": False,
        "description_ko": (
            "세션 기반 단기 대화 활성화(최근 프롬프트 최대 10개를 증강 프롬프트에 포함). "
            "명시적 conversation_id를 쓰면 이 설정은 무시됩니다. 본 앱은 stateless 원칙에 "
            "따라 conversation_id 방식을 사용합니다."
        ),
        "docs_ref": "p47, p93",
        "ui_group": "conversation",
    },
    {
        "name": "temperature",
        "type": "number",
        "default": None,
        "required": False,
        "description_ko": "LLM 샘플링 온도(낮을수록 결정적). 예제 값 0.2.",
        "docs_ref": "p136",
        "ui_group": "generation",
    },
    {
        "name": "max_tokens",
        "type": "number",
        "default": None,
        "required": False,
        "description_ko": "응답 최대 토큰 수. 예제 값 4096.",
        "docs_ref": "p136",
        "ui_group": "generation",
    },
    {
        "name": "model",
        "type": "enum_or_text",
        "enum": OCI_CHAT_MODELS,
        "deprecated": DEPRECATED_MODELS,
        "default": "meta.llama-3.3-70b-instruct",
        "required": False,
        "description_ko": (
            "LLM 모델명. 모델 OCID 지정 시 oci_apiformat이 필요합니다. deprecated 목록의 "
            "모델은 UI에서 비활성/경고 배지로 표기하되 전송 값은 순수 모델명을 사용합니다."
        ),
        "docs_ref": "p15, p84, p91-92",
        "ui_group": "provider",
    },
    {
        "name": "region",
        "type": "text",
        "default": "us-chicago-1",
        "required": False,
        "description_ko": (
            'OCI Generative AI 호출 리전 (예: "eu-frankfurt-1"). 미지정 시 기본 리전을 '
            "사용합니다."
        ),
        "docs_ref": "p84",
        "ui_group": "provider",
    },
    {
        "name": "oci_compartment_id",
        "type": "text",
        "default": _DEFAULT_COMPARTMENT_ID,
        "required": False,
        "description_ko": "OCI Generative AI를 호출할 컴파트먼트 OCID.",
        "docs_ref": "p85",
        "ui_group": "provider",
    },
    {
        "name": "oci_apiformat",
        "type": "enum",
        "enum": ["GENERIC", "COHERE"],
        "default": None,
        "required": False,
        "description_ko": (
            'OCI GenAI API 포맷. Meta Llama/Generic 모델 엔드포인트는 "GENERIC", '
            'Cohere 모델은 "COHERE".'
        ),
        "docs_ref": "p89, p91-92",
        "ui_group": "provider",
    },
    {
        "name": "oci_endpoint_id",
        "type": "text",
        "default": None,
        "required": False,
        "description_ko": "OCI GenAI 전용(Dedicated) 모델 엔드포인트 ID. model 대신 지정합니다.",
        "docs_ref": "p91",
        "ui_group": "provider",
    },
    {
        "name": "enforce_object_list",
        "type": "boolean_string",
        "default": None,
        "required": False,
        "description_ko": (
            '"true"면 LLM이 object_list에 나열된 테이블만 사용하도록 제한합니다. '
            '"false"면 LLM 사전 지식 기반 다른 테이블/뷰도 사용할 수 있습니다. 고객 '
            '실스키마 시연 프로파일에는 "true"를 권장합니다 (security.md §4.3).'
        ),
        "docs_ref": "p190-191",
        "ui_group": "objects",
    },
    {
        "name": "case_sensitive_values",
        "type": "boolean_string",
        "default": None,
        "required": False,
        "description_ko": (
            '"false"면 UPPER() 비교 등 대소문자 무시 SQL을 생성합니다. 프롬프트에서 '
            "큰따옴표로 감싸면 개별적으로 대소문자를 구분할 수 있습니다."
        ),
        "docs_ref": "p191-192",
        "ui_group": "generation",
    },
    {
        "name": "target_language",
        "type": "text",
        "default": None,
        "required": False,
        "description_ko": 'translate 액션의 목표 언어 (provider oci 전용). 예: "french".',
        "docs_ref": "p188",
        "ui_group": "translate",
    },
    {
        "name": "vector_index_name",
        "type": "text",
        "default": None,
        "required": False,
        "description_ko": (
            "RAG용 벡터 인덱스 이름. 지정 시 narrate가 벡터 검색 기반 응답을 생성합니다."
        ),
        "docs_ref": "p136",
        "ui_group": "rag",
    },
    {
        "name": "azure_resource_name",
        "type": "text",
        "default": None,
        "required": False,
        "description_ko": "Azure OpenAI 전용 리소스 이름 (azure_deployment_name과 한 쌍).",
        "docs_ref": "p148",
        "ui_group": "provider",
    },
    {
        "name": "azure_deployment_name",
        "type": "text",
        "default": None,
        "required": False,
        "description_ko": "Azure OpenAI 전용 배포 이름 (azure_resource_name과 한 쌍).",
        "docs_ref": "p148",
        "ui_group": "provider",
    },
    {
        "name": "provider_endpoint",
        "type": "text",
        "default": None,
        "required": False,
        "description_ko": (
            "OpenAI 호환 공급자(Fireworks AI 등)의 베이스 URL. provider 대신 사용합니다."
        ),
        "docs_ref": "p17, p41",
        "ui_group": "provider",
    },
]

VERIFIED_ATTRIBUTE_NAMES: frozenset[str] = frozenset(a["name"] for a in VERIFIED_ATTRIBUTES)

_BY_NAME: dict[str, dict[str, Any]] = {a["name"]: a for a in VERIFIED_ATTRIBUTES}


def get_meta(name: str) -> dict[str, Any] | None:
    """속성명으로 카탈로그 항목 조회 (미검증 속성이면 None)."""
    return _BY_NAME.get(name)


def attribute_meta_payload() -> dict[str, Any]:
    """GET /profiles/attribute-meta 응답 data (api-spec §4.1)."""
    return {"verified_attributes": VERIFIED_ATTRIBUTES, "defaults": DEFAULTS}
