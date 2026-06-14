"""프로파일 서비스 — CREATE_PROFILE/SET_ATTRIBUTE(S)/DROP, 속성 화이트리스트 검증.

근거: api-spec §4, selectai-reference.md §3·§5. 식별자 검증
(^[A-Za-z][A-Za-z0-9_$#]{0,127}$) 후 사용, attributes JSON은 json.dumps 직렬화.
미리보기와 실행은 동일 빌더(build_create_profile)에서 나온다 (architecture.md §2.2).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.db import oracle, pool_registry
from app.errors import AppError
from app.schemas.models import (
    ProfileAttributeOut,
    ProfileCreate,
    ProfileDetail,
    ProfileSummary,
)
from app.services import attribute_catalog, common, resource_service

# 모든 프로파일 PL/SQL은 바인드 변수 — profile_name도 프로시저 파라미터라 바인드 가능
CREATE_PROFILE_SQL = (
    "BEGIN\n"
    "  DBMS_CLOUD_AI.CREATE_PROFILE(\n"
    "      profile_name => :profile_name,\n"
    "      attributes   => :attributes);\n"
    "END;"
)
SET_ATTRIBUTE_SQL = (
    "BEGIN\n"
    "  DBMS_CLOUD_AI.SET_ATTRIBUTE(\n"
    "      profile_name    => :profile_name,\n"
    "      attribute_name  => :attribute_name,\n"
    "      attribute_value => :attribute_value);\n"
    "END;"
)
SET_ATTRIBUTES_SQL = (
    "BEGIN\n"
    "  DBMS_CLOUD_AI.SET_ATTRIBUTES(\n"
    "      profile_name => :profile_name,\n"
    "      attributes   => :attributes);\n"
    "END;"
)
DROP_PROFILE_SQL = "BEGIN DBMS_CLOUD_AI.DROP_PROFILE(:profile_name); END;"
ENABLE_PROFILE_SQL = "BEGIN DBMS_CLOUD_AI.ENABLE_PROFILE(:profile_name); END;"
DISABLE_PROFILE_SQL = "BEGIN DBMS_CLOUD_AI.DISABLE_PROFILE(:profile_name); END;"

LIST_PROFILES_SQL = (
    "SELECT profile_name, status FROM USER_CLOUD_AI_PROFILES ORDER BY profile_name"
)
LIST_SUMMARY_ATTRS_SQL = (
    "SELECT profile_name, attribute_name, attribute_value "
    "FROM USER_CLOUD_AI_PROFILE_ATTRIBUTES "
    "WHERE attribute_name IN ('provider', 'model')"
)
# credential_name select 채움용 — 현재 사용자가 보유한 자격증명(OCI$RESOURCE_PRINCIPAL 포함)
LIST_CREDENTIALS_SQL = (
    "SELECT credential_name FROM USER_CREDENTIALS ORDER BY credential_name"
)
PROFILE_STATUS_SQL = (
    "SELECT status FROM USER_CLOUD_AI_PROFILES WHERE profile_name = :profile_name"
)
PROFILE_ATTRS_SQL = (
    "SELECT attribute_name, attribute_value "
    "FROM USER_CLOUD_AI_PROFILE_ATTRIBUTES WHERE profile_name = :profile_name"
)


@dataclass(frozen=True)
class ExecutableSql:
    """실행 SQL(바인드) + 표시용 SQL — 미리보기=실행 동일성 보장 (architecture §2.2)."""

    sql: str
    binds: dict[str, Any]
    display_sql: str


def build_attributes_dict(body: ProfileCreate) -> dict[str, Any]:
    """ProfileAttributes(검증 21개) + 고급 JSON 병합 → attributes dict.

    - object_list는 [{"owner","name"}] 배열로 직렬화 (name 없으면 스키마 전체)
    - 고급 JSON 키가 검증 속성과 충돌하면 400 ATTRIBUTE_CONFLICT (api-spec §4.2)
    """
    attrs: dict[str, Any] = {}
    dumped = body.attributes.model_dump(exclude_none=True)
    for key, value in dumped.items():
        if key == "object_list":
            attrs[key] = [
                {"owner": ref["owner"], **({"name": ref["name"]} if ref.get("name") else {})}
                for ref in value
            ]
        else:
            attrs[key] = value

    if body.extra_attributes_json:
        try:
            extra = json.loads(body.extra_attributes_json)
        except json.JSONDecodeError as exc:
            raise AppError(
                status_code=400,
                code="ATTRIBUTE_INVALID",
                app_code="ATTRIBUTE_INVALID",
                message_ko="고급 JSON 속성을 파싱할 수 없습니다.",
                detail=str(exc),
            ) from exc
        if not isinstance(extra, dict):
            raise AppError(
                status_code=400,
                code="ATTRIBUTE_INVALID",
                app_code="ATTRIBUTE_INVALID",
                message_ko="고급 JSON 속성은 객체({})여야 합니다.",
            )
        conflicts = sorted(set(extra) & attribute_catalog.VERIFIED_ATTRIBUTE_NAMES)
        if conflicts:
            raise AppError(
                status_code=400,
                code="ATTRIBUTE_CONFLICT",
                app_code="ATTRIBUTE_CONFLICT",
                message_ko=f"고급 JSON의 키가 검증 속성과 충돌합니다: {', '.join(conflicts)}",
                hint_ko="충돌 키는 폼 필드에서 설정하세요.",
            )
        attrs.update(extra)
    return attrs


def build_create_profile(profile_name: str, attributes: dict[str, Any]) -> ExecutableSql:
    """CREATE_PROFILE 빌더 — preview API와 생성 API가 같은 객체를 사용한다."""
    common.validate_identifier(profile_name, "프로파일 이름")
    attributes_json = json.dumps(attributes, ensure_ascii=False)
    display = (
        "BEGIN\n"
        "  DBMS_CLOUD_AI.CREATE_PROFILE(\n"
        f"      profile_name => '{common.escape_literal(profile_name)}',\n"
        f"      attributes   => '{common.escape_literal(attributes_json)}');\n"
        "END;"
    )
    return ExecutableSql(
        sql=CREATE_PROFILE_SQL,
        binds={"profile_name": profile_name, "attributes": attributes_json},
        display_sql=display,
    )


def build_warnings(attributes: dict[str, Any]) -> list[str]:
    """미리보기 경고 — 외부 공급자 ACL, object_list 미지정 (api-spec §4.2, security §4.2)."""
    warnings: list[str] = []
    provider = attributes.get("provider", "oci")
    if provider != "oci" and not attributes.get("provider_endpoint"):
        warnings.append(
            f"외부 공급자({provider})를 선택하면 네트워크 ACL이 필요합니다. "
            "권한 점검을 먼저 실행하세요."
        )
    if not attributes.get("object_list") and not attributes.get("object_list_mode"):
        warnings.append(
            "object_list가 비어 있습니다. 미지정 시 현재 스키마의 모든 객체가 자동 "
            "선택되어 광범위한 메타데이터가 노출될 수 있습니다."
        )
    return warnings


async def create_profile(
    connection_id: str, body: ProfileCreate, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """§4.3 프로파일 생성 + ledger 기록."""
    attributes = build_attributes_dict(body)
    plan = build_create_profile(body.profile_name, attributes)
    recorder.record(plan.display_sql)
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        try:
            await common.call_db(oracle.execute(conn, plan.sql, plan.binds), recorder)
        except AppError as exc:
            # 이미 존재하는 프로파일 → 409 PROFILE_EXISTS (api-spec §4.3)
            if "already exists" in (exc.detail or "").lower():
                raise AppError(
                    status_code=409,
                    code=exc.code,
                    app_code="PROFILE_EXISTS",
                    message_ko=f"프로파일 '{body.profile_name}'이(가) 이미 존재합니다.",
                    hint_ko="다른 이름을 사용하거나 기존 프로파일을 삭제하세요.",
                    detail=exc.detail,
                    executed_sql=recorder.statements,
                ) from exc
            raise
    profile_upper = body.profile_name.upper()
    await resource_service.record(
        connection_id,
        resource_type="profile",
        resource_name=profile_upper,
        create_sql=plan.display_sql,
        cleanup_sql=f"BEGIN DBMS_CLOUD_AI.DROP_PROFILE('{profile_upper}'); END;",
    )
    return {"profile_name": profile_upper, "status": "ENABLED", "attributes": attributes}


async def list_credentials(
    connection_id: str, recorder: oracle.SqlRecorder
) -> list[str]:
    """현재 사용 가능한 credential 이름 목록 (credential_name select 채움용)."""
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        _, rows = await oracle.fetch_all(conn, LIST_CREDENTIALS_SQL, recorder=recorder)
    return [str(r[0]) for r in rows]


async def list_profiles(
    connection_id: str, recorder: oracle.SqlRecorder
) -> list[ProfileSummary]:
    """§4.4 목록 — provider/model 요약 조인 + is_default(앱 설정) 합성."""
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        _, rows = await oracle.fetch_all(conn, LIST_PROFILES_SQL, recorder=recorder)
        _, attr_rows = await oracle.fetch_all(conn, LIST_SUMMARY_ATTRS_SQL, recorder=recorder)
    summary_attrs: dict[str, dict[str, str]] = {}
    for profile_name, attr_name, attr_value in attr_rows:
        summary_attrs.setdefault(profile_name, {})[attr_name] = attr_value
    default_profile = await common.get_default_profile(connection_id)
    return [
        ProfileSummary(
            profile_name=name,
            status=status,
            provider=summary_attrs.get(name, {}).get("provider"),
            model=summary_attrs.get(name, {}).get("model"),
            is_default=(default_profile or "").upper() == str(name).upper(),
        )
        for name, status in rows
    ]


def _profile_not_found(profile_name: str) -> AppError:
    return AppError(
        status_code=404,
        code="PROFILE_NOT_FOUND",
        app_code="PROFILE_NOT_FOUND",
        message_ko=f"프로파일 '{profile_name}'이(가) 존재하지 않습니다.",
        hint_ko="프로파일 목록을 확인하세요.",
    )


async def get_profile_status(
    connection_id: str, profile_name: str, recorder: oracle.SqlRecorder
) -> str:
    """프로파일 존재/상태 조회 — 없으면 404 (settings PUT 검증에도 사용)."""
    common.validate_identifier(profile_name, "프로파일 이름")
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        row = await oracle.fetch_one(
            conn, PROFILE_STATUS_SQL, {"profile_name": profile_name.upper()},
            recorder=recorder,
        )
    if row is None:
        raise _profile_not_found(profile_name)
    return str(row[0])


async def get_profile_detail(
    connection_id: str, profile_name: str, recorder: oracle.SqlRecorder
) -> ProfileDetail:
    """§4.5 속성 상세 — 뷰 조회 + 카탈로그 한국어 해설 병합 (showparameter 대체)."""
    common.validate_identifier(profile_name, "프로파일 이름")
    upper = profile_name.upper()
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        status_row = await oracle.fetch_one(
            conn, PROFILE_STATUS_SQL, {"profile_name": upper}, recorder=recorder
        )
        if status_row is None:
            raise _profile_not_found(profile_name)
        _, attr_rows = await oracle.fetch_all(
            conn, PROFILE_ATTRS_SQL, {"profile_name": upper}, recorder=recorder
        )
    attributes: list[ProfileAttributeOut] = []
    for attr_name, attr_value in attr_rows:
        meta = attribute_catalog.get_meta(str(attr_name).lower())
        attributes.append(
            ProfileAttributeOut(
                name=str(attr_name).lower(),
                value=str(attr_value) if attr_value is not None else None,
                verified=meta is not None,
                description_ko=meta["description_ko"]
                if meta
                else "본 가이드에서 미검증 속성입니다. Supplied Package Reference를 확인하세요.",
                docs_ref=meta["docs_ref"] if meta else None,
            )
        )
    return ProfileDetail(profile_name=upper, status=str(status_row[0]), attributes=attributes)


def build_update_attributes(
    profile_name: str, attributes: dict[str, Any]
) -> ExecutableSql:
    """§4.6 수정 빌더 — 단일이면 SET_ATTRIBUTE, 복수면 SET_ATTRIBUTES."""
    common.validate_identifier(profile_name, "프로파일 이름")
    # 미설정(null)·빈 값은 제거 — SET_ATTRIBUTE에 빈 값을 주면 ORA-20046(Missing value).
    # (편집 폼이 미설정 옵션 필드를 null로 함께 보내는 경우 방지)
    attributes = {
        k: v for k, v in attributes.items() if v not in (None, "", [], {})
    }
    if not attributes:
        raise AppError(
            status_code=400,
            code="ATTRIBUTE_INVALID",
            app_code="ATTRIBUTE_INVALID",
            message_ko="수정할 속성이 없습니다.",
        )
    if len(attributes) == 1:
        name, value = next(iter(attributes.items()))
        value_str = (
            json.dumps(value, ensure_ascii=False) if isinstance(value, (list, dict)) else str(value)
        )
        display = (
            "BEGIN\n"
            "  DBMS_CLOUD_AI.SET_ATTRIBUTE(\n"
            f"      profile_name    => '{common.escape_literal(profile_name)}',\n"
            f"      attribute_name  => '{common.escape_literal(name)}',\n"
            f"      attribute_value => '{common.escape_literal(value_str)}');\n"
            "END;"
        )
        return ExecutableSql(
            sql=SET_ATTRIBUTE_SQL,
            binds={
                "profile_name": profile_name,
                "attribute_name": name,
                "attribute_value": value_str,
            },
            display_sql=display,
        )
    attributes_json = json.dumps(attributes, ensure_ascii=False)
    display = (
        "BEGIN\n"
        "  DBMS_CLOUD_AI.SET_ATTRIBUTES(\n"
        f"      profile_name => '{common.escape_literal(profile_name)}',\n"
        f"      attributes   => '{common.escape_literal(attributes_json)}');\n"
        "END;"
    )
    return ExecutableSql(
        sql=SET_ATTRIBUTES_SQL,
        binds={"profile_name": profile_name, "attributes": attributes_json},
        display_sql=display,
    )


async def update_profile(
    connection_id: str,
    profile_name: str,
    attributes: dict[str, Any],
    recorder: oracle.SqlRecorder,
) -> ProfileDetail:
    """§4.6 SET_ATTRIBUTE(S) 실행 후 상세 재조회."""
    plan = build_update_attributes(profile_name, attributes)
    recorder.record(plan.display_sql)
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        await common.call_db(oracle.execute(conn, plan.sql, plan.binds), recorder)
    return await get_profile_detail(connection_id, profile_name, recorder)


async def drop_profile(
    connection_id: str, profile_name: str, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """§4.7 DROP_PROFILE — 기본 프로파일이면 설정 해제 + ledger done 동기화."""
    common.validate_identifier(profile_name, "프로파일 이름")
    display = f"BEGIN DBMS_CLOUD_AI.DROP_PROFILE('{common.escape_literal(profile_name)}'); END;"
    recorder.record(display)
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        await common.call_db(
            oracle.execute(conn, DROP_PROFILE_SQL, {"profile_name": profile_name}), recorder
        )
    default_cleared = await common.clear_default_profile(connection_id, profile_name)
    if not default_cleared:
        default_cleared = await common.clear_default_profile(
            connection_id, profile_name.upper()
        )
    await resource_service.mark_done_by_name(
        connection_id, "profile", profile_name.upper()
    )
    return {"dropped": True, "default_cleared": default_cleared}


async def set_profile_status(
    connection_id: str, profile_name: str, enabled: bool, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """§4.9 ENABLE/DISABLE_PROFILE 토글 (P1)."""
    common.validate_identifier(profile_name, "프로파일 이름")
    sql = ENABLE_PROFILE_SQL if enabled else DISABLE_PROFILE_SQL
    proc = "ENABLE_PROFILE" if enabled else "DISABLE_PROFILE"
    recorder.record(
        f"BEGIN DBMS_CLOUD_AI.{proc}('{common.escape_literal(profile_name)}'); END;"
    )
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
    ) as conn:
        await common.call_db(
            oracle.execute(conn, sql, {"profile_name": profile_name}), recorder
        )
    return {
        "profile_name": profile_name.upper(),
        "status": "ENABLED" if enabled else "DISABLED",
    }
