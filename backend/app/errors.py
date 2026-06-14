"""오류 처리 — AppError, ORA→한국어 매핑 (api-spec §1.4·§1.5 기준).

모든 오류 응답은 단일 envelope 포맷:
  { "error": { code, app_code, message_ko, hint_ko, detail, retryable, executed_sql, docs_ref } }
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


class AppError(Exception):
    """도메인 오류 — main.py 예외 핸들러가 §1.4 envelope으로 직렬화한다."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        app_code: str,
        message_ko: str,
        hint_ko: str | None = None,
        detail: str | None = None,
        retryable: bool = False,
        executed_sql: list[str] | None = None,
        docs_ref: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message_ko)
        self.status_code = status_code
        self.code = code
        self.app_code = app_code
        self.message_ko = message_ko
        self.hint_ko = hint_ko
        self.detail = detail
        self.retryable = retryable
        self.executed_sql = executed_sql or []
        self.docs_ref = docs_ref
        self.extra = extra or {}  # ADB_AMBIGUOUS의 candidates 등 부가 필드

    def to_body(self) -> dict[str, Any]:
        """§1.4 오류 envelope 본문 생성."""
        body: dict[str, Any] = {
            "code": self.code,
            "app_code": self.app_code,
            "message_ko": self.message_ko,
            "hint_ko": self.hint_ko,
            "detail": self.detail,
            "retryable": self.retryable,
            "executed_sql": self.executed_sql,
            "docs_ref": self.docs_ref,
        }
        body.update(self.extra)
        return {"error": body}


def not_implemented(feature: str) -> AppError:
    """스캐폴딩 스텁 공통 응답 — 구현 에이전트가 본문을 채우기 전까지 501."""
    return AppError(
        status_code=501,
        code="NOT_IMPLEMENTED",
        app_code="NOT_IMPLEMENTED",
        message_ko=f"'{feature}' 기능은 아직 구현되지 않았습니다.",
        hint_ko="스캐폴딩 스텁입니다. 구현 단계에서 채워집니다.",
    )


@dataclass(frozen=True)
class OraMapping:
    """ORA/DPY 코드 → 한국어 해설 매핑 항목 (api-spec §1.5 표)."""

    app_code: str
    http_status: int
    message_ko: str
    retryable: bool = False
    hint_ko: str | None = None
    docs_ref: str | None = None


# api-spec §1.5 매핑 표 — 주요 코드. 매핑에 없는 오류는 ORACLE_ERROR + 원문 노출.
ORA_ERROR_MAP: dict[str, OraMapping] = {
    "ORA-01017": OraMapping(
        "INVALID_CREDENTIALS", 401, "admin 비밀번호가 올바르지 않습니다.",
        hint_ko="커넥션 설정에서 비밀번호를 다시 입력하세요.",
    ),
    "DPY-6005": OraMapping(
        "DB_UNREACHABLE", 502,
        "DB에 연결할 수 없습니다. wallet/TNS alias/네트워크를 확인하세요.", retryable=True,
        hint_ko="ADB 인스턴스가 STOPPED 상태인지 OCI 콘솔에서 확인하세요.",
    ),
    "ORA-12506": OraMapping(
        "DB_UNREACHABLE", 502,
        "DB에 연결할 수 없습니다. wallet/TNS alias/네트워크를 확인하세요.", retryable=True,
    ),
    "ORA-28759": OraMapping(
        "WALLET_INVALID", 400,
        "wallet 파일을 열 수 없습니다. ADB 콘솔에서 wallet을 다시 다운로드하세요.",
    ),
    "ORA-00923": OraMapping(
        "PROFILE_NOT_SET", 400,
        "프로파일 없이 SELECT AI가 실행되었습니다 — 백엔드 버그(세션 상태 의존 코드 혼입) 가능성. "
        "GENERATE 패턴 위반 점검이 필요합니다.",
        docs_ref="selectai-reference.md §1 (p45)",
    ),
    "ORA-20000": OraMapping(
        "DATA_ACCESS_DISABLED", 409,
        "Select AI의 데이터 액세스가 비활성화되어 있어 narrate/합성 데이터를 실행할 수 없습니다.",
        hint_ko="권한 점검 화면에서 'Data Access 활성화' 버튼을 눌러 ENABLE_DATA_ACCESS를 적용한 뒤 다시 시도하세요.",
        docs_ref="selectai-reference.md §2 데이터 액세스 제어 (p174-176)",
    ),
    "ORA-00942": OraMapping(
        "OBJECT_NOT_FOUND", 404,
        "생성된 SQL이 존재하지 않는 테이블을 참조했습니다 (LLM 환각 가능).", retryable=True,
        hint_ko="다시 시도하거나 comments 증강 시연(FR-08)으로 정확도를 높여 보세요.",
        docs_ref="selectai-reference.md (p14·p45)",
    ),
    "ORA-00904": OraMapping(
        "GENERATED_SQL_INVALID", 422,
        "LLM이 생성한 SQL이 유효하지 않습니다. 프롬프트를 구체화하거나 comments 증강을 활성화해 보세요.",
        retryable=True,
    ),
    "ORA-00936": OraMapping(
        "GENERATED_SQL_INVALID", 422,
        "LLM이 생성한 SQL이 유효하지 않습니다. 프롬프트를 구체화하거나 comments 증강을 활성화해 보세요.",
        retryable=True,
    ),
    "ORA-01031": OraMapping(
        "INSUFFICIENT_PRIVILEGE", 403,
        "권한이 부족합니다. 권한 점검 화면에서 누락 항목을 적용하세요.",
    ),
    "ORA-20404": OraMapping(
        "PROFILE_NOT_FOUND", 404, "지정한 프로파일이 존재하지 않습니다.",
    ),
    "ORA-11552": OraMapping(
        "ANNOTATION_EXISTS", 409, "어노테이션이 이미 존재합니다 (ADD 대신 REPLACE로 갱신해야 합니다).",
        retryable=True,
    ),
    "ORA-11560": OraMapping(
        "ANNOTATION_EXISTS", 409, "컬럼 어노테이션이 이미 존재합니다 (ADD 대신 REPLACE로 갱신해야 합니다).",
        retryable=True,
    ),
    "ORA-11553": OraMapping(
        "ANNOTATION_MISSING", 409, "어노테이션이 존재하지 않습니다 (REPLACE 대신 ADD로 추가해야 합니다).",
        retryable=True,
    ),
    "ORA-11561": OraMapping(
        "ANNOTATION_MISSING", 409, "컬럼 어노테이션이 존재하지 않습니다 (REPLACE 대신 ADD로 추가해야 합니다).",
        retryable=True,
    ),
    "ORA-01002": OraMapping(
        "DB_CONNECTION_UNSTABLE", 503,
        "DB 세션이 일시적으로 불안정합니다 (fetch out of sequence). 다시 시도하세요.",
        retryable=True,
        hint_ko="GENERATE 내부 커밋이나 풀 세션 상태 영향일 수 있어, 새 커넥션으로 재시도하면 대개 해소됩니다.",
    ),
    "DPY-4011": OraMapping(
        "LLM_TIMEOUT", 504, "AI 응답이 제한 시간을 초과했습니다. 다시 시도하세요.", retryable=True,
    ),
    "DPY-4024": OraMapping(
        "QUERY_TIMEOUT", 504,
        "쿼리 시간이 초과되었습니다. 대형 스키마(예: ADMIN) 조회는 느릴 수 있습니다.",
        retryable=True,
        hint_ko="잠시 후 다시 시도하거나, 대상 스키마를 더 좁혀 선택하세요.",
    ),
}

# ORA-20000은 DBMS_CLOUD_AI가 RAISE_APPLICATION_ERROR로 던지는 범용 코드라
# 메시지 본문으로 의미를 분기한다 (데이터 액세스 vs 피드백 매칭 실패 등).
ORA20000_VARIANTS: list[tuple[str, OraMapping]] = [
    ("Data access is disabled", OraMapping(
        "DATA_ACCESS_DISABLED", 409,
        "Select AI의 데이터 액세스가 비활성화되어 있어 narrate/합성 데이터를 실행할 수 없습니다.",
        hint_ko="권한 점검 화면에서 'Data Access 활성화' 버튼을 눌러 ENABLE_DATA_ACCESS를 적용한 뒤 다시 시도하세요.",
        docs_ref="selectai-reference.md §2 데이터 액세스 제어 (p174-176)",
    )),
    ("is not a Select AI statement", OraMapping(
        "FEEDBACK_INVALID_STATEMENT", 422,
        "피드백 대상 SQL 텍스트가 Select AI 문장 형식이 아닙니다 ('select ai <액션> <프롬프트>' 필요).",
        hint_ko="백엔드가 자동으로 'select ai showsql <프롬프트>' 형식으로 변환합니다 — 재시도하세요.",
        docs_ref="selectai-reference.md §FEEDBACK (p104)",
    )),
    ("No matching SQL statement found", OraMapping(
        "FEEDBACK_NO_MATCH", 422,
        "해당 프롬프트로 실제 실행된 SQL을 찾지 못해 긍정 피드백을 기록할 수 없습니다.",
        hint_ko="긍정 피드백은 같은 질문을 한 번 실행해 SQL 매핑이 생성된 뒤에 가능합니다. "
        "부정(교정) 피드백은 교정 SQL만 있으면 즉시 기록됩니다.",
        docs_ref="selectai-reference.md §FEEDBACK 긍정 피드백 (p105)",
    )),
]

_ORA_CODE_RE = re.compile(r"\b((?:ORA|DPY)-\d{4,5})\b")


def extract_top_error_code(message: str) -> str | None:
    """오류 메시지에서 최상위 ORA/DPY 코드 추출.

    PL/SQL 래퍼(ORA-06512) 스택 라인은 detail에만 남기고
    message_ko 생성에는 최상위 코드만 사용한다 (§1.5 규칙 1).
    """
    for match in _ORA_CODE_RE.finditer(message):
        if match.group(1) != "ORA-06512":
            return match.group(1)
    return None


def map_oracle_error(message: str, executed_sql: list[str] | None = None) -> AppError:
    """oracledb.DatabaseError 메시지를 §1.5 매핑 표 기준 AppError로 변환."""
    code = extract_top_error_code(message)
    mapping = ORA_ERROR_MAP.get(code or "")
    if code == "ORA-20000":
        # 메시지 본문으로 변형을 식별 — 일치 항목이 없으면 기존 데이터 액세스 매핑으로 폴백.
        for needle, variant in ORA20000_VARIANTS:
            if needle in message:
                mapping = variant
                break
    if mapping is None:
        return AppError(
            status_code=500,
            code=code or "ORACLE_ERROR",
            app_code="ORACLE_ERROR",
            message_ko="DB 오류가 발생했습니다. 원문을 확인하세요.",
            detail=message,
            executed_sql=executed_sql or [],
        )
    return AppError(
        status_code=mapping.http_status,
        code=code or mapping.app_code,
        app_code=mapping.app_code,
        message_ko=mapping.message_ko,
        hint_ko=mapping.hint_ko,
        detail=message,
        retryable=mapping.retryable,
        executed_sql=executed_sql or [],
        docs_ref=mapping.docs_ref,
    )
