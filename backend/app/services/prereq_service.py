"""권한 점검 서비스 — 선언적 점검 카탈로그, 적용 SQL 생성(미리보기=실행 동일 문자열).

근거: architecture.md §3.4, api-spec §3, selectai-reference.md §4.
- provider=oci면 network_acl은 not_applicable (레퍼런스 §4.2 p34)
- resource_principal 적용은 DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider=>'OCI')
  (ENABLE_RESOURCE_PRINCIPAL 아님 — 레퍼런스 §4.4 p81)
- data_access는 settings.json의 직전 적용 이력으로 판정, 미확정 시 unknown
"""
from __future__ import annotations

from typing import Any

from app.db import oracle, pool_registry
from app.errors import AppError
from app.schemas.models import (
    CredentialSpec,
    PrivilegeApplied,
    PrivilegeApplyRequest,
    PrivilegeApplyResult,
    PrivilegeCheck,
    PrivilegeCheckResult,
)
from app.services import common, resource_service

# 외부 공급자 ACL host (selectai-reference §4.2 p36)
PROVIDER_HOSTS: dict[str, str] = {
    "openai": "api.openai.com",
    "cohere": "api.cohere.ai",
    "google": "generativelanguage.googleapis.com",
    "anthropic": "api.anthropic.com",
    "aws": "bedrock-runtime.us-east-1.amazonaws.com",
}

# 점검 SQL (selectai-reference §4.1 p35 쿼리 그대로 — 바인드 변수)
SQL_EXECUTE_PRIV = (
    "SELECT table_name, privilege FROM DBA_TAB_PRIVS "
    "WHERE grantee = :grantee AND table_name = :package_name"
)
SQL_CREDENTIALS = (
    "SELECT credential_name, enabled FROM DBA_CREDENTIALS WHERE owner = :owner"
)
SQL_RESOURCE_PRINCIPAL = (
    "SELECT credential_name FROM DBA_CREDENTIALS "
    "WHERE credential_name = 'OCI$RESOURCE_PRINCIPAL'"
)
SQL_HOST_ACES = (
    "SELECT host, lower_port, upper_port, ace_order FROM DBA_HOST_ACES "
    "WHERE principal = :principal AND host = :host"
)
SQL_FEEDBACK_GRANTS = (
    "SELECT table_name FROM DBA_TAB_PRIVS "
    "WHERE grantee = :grantee AND privilege = 'READ' "
    "AND table_name IN ('V_$MAPPED_SQL', 'V_$SESSION')"
)

# 적용 PL/SQL 고정 템플릿 (api-spec §3.2 — 레퍼런스 §4 원문 그대로)
FIX_RESOURCE_PRINCIPAL = (
    "BEGIN\n  DBMS_CLOUD_ADMIN.ENABLE_PRINCIPAL_AUTH(provider => 'OCI');\nEND;"
)
FIX_ENABLE_DATA_ACCESS = "BEGIN DBMS_CLOUD_AI.ENABLE_DATA_ACCESS; END;"
FIX_DISABLE_DATA_ACCESS = "BEGIN DBMS_CLOUD_AI.DISABLE_DATA_ACCESS; END;"

CREATE_CREDENTIAL_API_KEY_SQL = (
    "BEGIN\n"
    "  DBMS_CLOUD.CREATE_CREDENTIAL(\n"
    "    credential_name => :credential_name,\n"
    "    user_ocid       => :user_ocid,\n"
    "    tenancy_ocid    => :tenancy_ocid,\n"
    "    private_key     => :private_key,\n"
    "    fingerprint     => :fingerprint);\n"
    "END;"
)
CREATE_CREDENTIAL_API_TOKEN_SQL = (
    "BEGIN\n"
    "  DBMS_CLOUD.CREATE_CREDENTIAL(\n"
    "    credential_name => :credential_name,\n"
    "    username        => :username,\n"
    "    password        => :api_token);\n"
    "END;"
)
APPEND_HOST_ACE_SQL = (
    "BEGIN\n"
    "  DBMS_NETWORK_ACL_ADMIN.APPEND_HOST_ACE(\n"
    "    host => :provider_host,\n"
    "    ace  => xs$ace_type(privilege_list => xs$name_list('http'),\n"
    "                        principal_name => :target_user,\n"
    "                        principal_type => xs_acl.ptype_db));\n"
    "END;"
)


def _grant_sql(package_name: str, target_user: str) -> str:
    """GRANT는 식별자 위치라 바인드 불가 — 화이트리스트 검증 후 조립 (security §3.2)."""
    common.validate_identifier(package_name, "패키지 이름")
    common.validate_identifier(target_user, "대상 사용자")
    return f"GRANT EXECUTE ON {package_name} TO {target_user}"


def _check(
    check_id: str,
    title_ko: str,
    status: str,
    description_ko: str,
    *,
    evidence_sql: str | None = None,
    fix_sql: str | None = None,
    docs_ref: str | None = None,
) -> PrivilegeCheck:
    return PrivilegeCheck(
        check_id=check_id,
        title_ko=title_ko,
        status=status,
        description_ko=description_ko,
        evidence_sql=evidence_sql,
        fix_sql=fix_sql,
        docs_ref=docs_ref,
    )


async def run_checks(
    connection_id: str,
    *,
    provider: str,
    target_user: str,
    include: set[str],
    recorder: oracle.SqlRecorder,
) -> PrivilegeCheckResult:
    """§3.1 점검 카탈로그 실행 — fix_sql은 항상 동봉 (적용 전 미리보기 수용 기준)."""
    common.validate_identifier(target_user, "대상 사용자")
    grantee = target_user.upper()
    checks: list[PrivilegeCheck] = []

    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
    ) as conn:
        # 1) DBMS_CLOUD_AI EXECUTE (admin은 기본 보유 — 시연용으로 항상 표시)
        _, rows = await oracle.fetch_all(
            conn, SQL_EXECUTE_PRIV,
            {"grantee": grantee, "package_name": "DBMS_CLOUD_AI"}, recorder=recorder,
        )
        has_execute = bool(rows) or grantee == "ADMIN"
        checks.append(_check(
            "execute_dbms_cloud_ai", "DBMS_CLOUD_AI 실행 권한",
            "pass" if has_execute else "fail",
            "Select AI의 모든 기능은 DBMS_CLOUD_AI 패키지 EXECUTE 권한이 필요합니다.",
            evidence_sql=SQL_EXECUTE_PRIV,
            fix_sql=_grant_sql("DBMS_CLOUD_AI", grantee),
            docs_ref="selectai-reference.md §4.1 (p33-35)",
        ))

        # 2) RAG용 DBMS_CLOUD_PIPELINE (include=rag 시)
        if "rag" in include:
            _, rows = await oracle.fetch_all(
                conn, SQL_EXECUTE_PRIV,
                {"grantee": grantee, "package_name": "DBMS_CLOUD_PIPELINE"},
                recorder=recorder,
            )
            checks.append(_check(
                "execute_dbms_cloud_pipeline", "DBMS_CLOUD_PIPELINE 실행 권한 (RAG)",
                "pass" if (rows or grantee == "ADMIN") else "fail",
                "RAG(벡터 인덱스 파이프라인) 사용 시 DBMS_CLOUD_PIPELINE EXECUTE 권한이 필요합니다.",
                evidence_sql=SQL_EXECUTE_PRIV,
                fix_sql=_grant_sql("DBMS_CLOUD_PIPELINE", grantee),
                docs_ref="selectai-reference.md §4.1 (p34)",
            ))

        # 3) credential 존재
        _, cred_rows = await oracle.fetch_all(
            conn, SQL_CREDENTIALS, {"owner": grantee}, recorder=recorder
        )
        checks.append(_check(
            "credential", "AI 공급자 자격증명",
            "pass" if cred_rows else "fail",
            "AI 공급자 접근용 자격증명(DBMS_CLOUD.CREATE_CREDENTIAL)이 필요합니다. "
            "OCI GenAI는 Resource Principal로 대체할 수 있습니다.",
            evidence_sql=SQL_CREDENTIALS,
            fix_sql=CREATE_CREDENTIAL_API_KEY_SQL,
            docs_ref="selectai-reference.md §4.3 (p36)",
        ))

        # 4) Resource Principal (OCI$RESOURCE_PRINCIPAL)
        _, rp_rows = await oracle.fetch_all(
            conn, SQL_RESOURCE_PRINCIPAL, recorder=recorder
        )
        checks.append(_check(
            "resource_principal", "Resource Principal 인증",
            "pass" if rp_rows else "fail",
            "자격증명 키 없이 OCI GenAI를 호출하려면 Resource Principal을 활성화해야 합니다.",
            evidence_sql=SQL_RESOURCE_PRINCIPAL,
            fix_sql=FIX_RESOURCE_PRINCIPAL,
            docs_ref="selectai-reference.md §4.4 (p81)",
        ))

        # 5) 네트워크 ACL — provider=oci면 점검 불필요 (p34)
        if provider == "oci":
            checks.append(_check(
                "network_acl", "네트워크 ACL", "not_applicable",
                "OCI Generative AI는 네트워크 ACL이 필요 없습니다 (p34). "
                "외부 공급자 선택 시에만 점검합니다.",
                docs_ref="selectai-reference.md §4.2 (p34)",
            ))
        else:
            host = PROVIDER_HOSTS.get(provider)
            if host:
                _, acl_rows = await oracle.fetch_all(
                    conn, SQL_HOST_ACES, {"principal": grantee, "host": host},
                    recorder=recorder,
                )
                checks.append(_check(
                    "network_acl", "네트워크 ACL",
                    "pass" if acl_rows else "fail",
                    f"외부 공급자({provider}) 호출에는 {host}에 대한 host ACL이 필요합니다.",
                    evidence_sql=SQL_HOST_ACES,
                    fix_sql=APPEND_HOST_ACE_SQL.replace(":provider_host", f"'{host}'")
                    .replace(":target_user", f"'{grantee}'"),
                    docs_ref="selectai-reference.md §4.2 (p34-36)",
                ))
            else:
                checks.append(_check(
                    "network_acl", "네트워크 ACL", "unknown",
                    f"공급자 '{provider}'의 ACL host가 카탈로그에 없습니다. "
                    "provider_endpoint 사용 시 해당 host로 직접 ACL을 구성하세요.",
                    docs_ref="selectai-reference.md §4.2 (p36)",
                ))

        # 6) feedback grants (include=feedback 시, P1)
        if "feedback" in include:
            _, fb_rows = await oracle.fetch_all(
                conn, SQL_FEEDBACK_GRANTS, {"grantee": grantee}, recorder=recorder
            )
            granted = {str(row[0]) for row in fb_rows}
            ok = {"V_$MAPPED_SQL", "V_$SESSION"} <= granted
            checks.append(_check(
                "feedback_grants", "Feedback용 뷰 READ 권한",
                "pass" if ok else "fail",
                "feedback 액션에서 마지막 AI SQL을 참조하려면 SYS.V_$MAPPED_SQL / "
                "SYS.V_$SESSION READ 권한이 필요합니다.",
                evidence_sql=SQL_FEEDBACK_GRANTS,
                fix_sql=(
                    f"GRANT READ ON SYS.V_$MAPPED_SQL TO {grantee};\n"
                    f"GRANT READ ON SYS.V_$SESSION TO {grantee};"
                ),
                docs_ref="selectai-reference.md §4.5 (p64)",
            ))

    # 7) Data Access — DB 프로브 대신 직전 적용 이력으로 판정 (api-spec §3.1)
    state = await common.get_data_access_state(connection_id)
    if state == "enabled":
        da_status, da_desc = "pass", "Data Access가 활성 상태입니다 (narrate/합성 데이터 가능)."
    elif state == "disabled":
        da_status, da_desc = (
            "fail",
            "Data Access가 비활성 상태입니다 — narrate/합성 데이터가 ORA-20000으로 차단됩니다. "
            "민감 데이터 환경에서는 이 상태가 거버넌스 선택일 수 있습니다.",
        )
    else:
        da_status, da_desc = (
            "unknown",
            "Data Access 적용 이력이 없어 상태를 확정할 수 없습니다. "
            "ENABLE/DISABLE 원클릭으로 상태를 설정하세요 (기본값은 활성).",
        )
    checks.append(_check(
        "data_access", "Data Access (실데이터 LLM 전송)",
        da_status, da_desc,
        fix_sql=FIX_ENABLE_DATA_ACCESS,
        docs_ref="selectai-reference.md §2 데이터 액세스 제어 (p174-176)",
    ))

    overall = (
        "pass"
        if all(c.status in ("pass", "not_applicable") for c in checks)
        else "action_required"
    )
    return PrivilegeCheckResult(
        provider=provider, target_user=grantee, overall=overall, checks=checks
    )


def _credential_plan(spec: CredentialSpec) -> tuple[str, dict[str, Any], str]:
    """credential 적용 SQL/바인드/표시문 — 비밀값은 표시문에서 ***MASKED*** (§1.5 규칙 2)."""
    common.validate_identifier(spec.credential_name, "자격증명 이름")
    if spec.auth_type == "api_token":
        binds = {
            "credential_name": spec.credential_name,
            "username": spec.username,
            "api_token": spec.api_token,
        }
        display = (
            "BEGIN DBMS_CLOUD.CREATE_CREDENTIAL("
            f"credential_name => '{spec.credential_name}', "
            f"username => '{spec.username or ''}', password => '***MASKED***'); END;"
        )
        return CREATE_CREDENTIAL_API_TOKEN_SQL, binds, display
    binds = {
        "credential_name": spec.credential_name,
        "user_ocid": spec.user_ocid,
        "tenancy_ocid": spec.tenancy_ocid,
        "private_key": spec.private_key,
        "fingerprint": spec.fingerprint,
    }
    display = (
        "BEGIN DBMS_CLOUD.CREATE_CREDENTIAL("
        f"credential_name => '{spec.credential_name}', "
        f"user_ocid => '{spec.user_ocid or ''}', tenancy_ocid => '{spec.tenancy_ocid or ''}', "
        "private_key => '***MASKED***', "
        f"fingerprint => '{spec.fingerprint or ''}'); END;"
    )
    return CREATE_CREDENTIAL_API_KEY_SQL, binds, display


async def apply_items(
    connection_id: str, body: PrivilegeApplyRequest, recorder: oracle.SqlRecorder
) -> PrivilegeApplyResult:
    """§3.2 원클릭 적용 — 커넥션 전역 Lock(DDL 직렬화, §12.5) 하에 항목별 실행."""
    common.validate_identifier(body.target_user, "대상 사용자")
    grantee = body.target_user.upper()
    # provider=oci에서 network_acl 적용 요청은 요청 자체 오류 — 400 ACL_NOT_REQUIRED (§3.2)
    if body.provider == "oci" and any(
        item.check_id == "network_acl" for item in body.items
    ):
        raise AppError(
            status_code=400,
            code="ACL_NOT_REQUIRED",
            app_code="ACL_NOT_REQUIRED",
            message_ko="OCI Generative AI는 네트워크 ACL이 필요 없습니다.",
            hint_ko="외부 공급자를 선택한 경우에만 network_acl을 적용하세요.",
            docs_ref="selectai-reference.md §4.2 (p34)",
        )
    applied: list[PrivilegeApplied] = []

    async with common.get_lock(f"ddl:{connection_id}"):
        for item in body.items:
            try:
                display = await _apply_one(connection_id, grantee, body.provider, item, recorder)
                applied.append(
                    PrivilegeApplied(check_id=item.check_id, ok=True, executed_sql=display)
                )
            except AppError as exc:
                applied.append(
                    PrivilegeApplied(
                        check_id=item.check_id,
                        ok=False,
                        executed_sql="; ".join(exc.executed_sql) if exc.executed_sql else "",
                        error=exc.to_body()["error"],
                    )
                )

    recheck = None
    if body.recheck:
        recheck = await run_checks(
            connection_id,
            provider=body.provider,
            target_user=grantee,
            include=set(),
            recorder=recorder,
        )
    result = PrivilegeApplyResult(applied=applied, recheck=recheck)

    if any(not entry.ok for entry in applied):
        # 일부 실패 — 409 PARTIAL_APPLY + 항목별 결과 동봉 (api-spec §3.2 오류)
        raise AppError(
            status_code=409,
            code="PARTIAL_APPLY",
            app_code="PARTIAL_APPLY",
            message_ko="일부 권한 적용이 실패했습니다. 항목별 결과를 확인하세요.",
            hint_ko="실패 항목의 오류를 확인한 뒤 해당 항목만 다시 적용하세요.",
            executed_sql=recorder.statements,
            extra={"applied": [entry.model_dump() for entry in applied]},
        )
    return result


async def _apply_one(
    connection_id: str,
    grantee: str,
    provider: str,
    item: Any,
    recorder: oracle.SqlRecorder,
) -> str:
    """항목 1건 적용 — 적용 성공 시 ledger 기록. 표시문(executed_sql 항목용) 반환."""
    check_id = item.check_id

    if check_id in ("execute_dbms_cloud_ai", "execute_dbms_cloud_pipeline"):
        package = "DBMS_CLOUD_AI" if check_id == "execute_dbms_cloud_ai" else "DBMS_CLOUD_PIPELINE"
        sql = _grant_sql(package, grantee)
        recorder.record(sql)
        async with pool_registry.acquire(
            connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
        ) as conn:
            await common.call_db(oracle.execute(conn, sql), recorder)
        await resource_service.record(
            connection_id,
            resource_type="grant",
            resource_name=f"EXECUTE:{package}:{grantee}",
            create_sql=sql,
            cleanup_sql=f"REVOKE EXECUTE ON {package} FROM {grantee}",
        )
        return sql

    if check_id == "resource_principal":
        recorder.record(FIX_RESOURCE_PRINCIPAL)
        async with pool_registry.acquire(
            connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
        ) as conn:
            await common.call_db(oracle.execute(conn, FIX_RESOURCE_PRINCIPAL), recorder)
        await resource_service.record(
            connection_id,
            resource_type="grant",
            resource_name="ENABLE_PRINCIPAL_AUTH:OCI",
            create_sql=FIX_RESOURCE_PRINCIPAL,
            cleanup_sql=(
                "BEGIN\n  DBMS_CLOUD_ADMIN.DISABLE_PRINCIPAL_AUTH(provider => 'OCI');\nEND;"
            ),
        )
        return FIX_RESOURCE_PRINCIPAL

    if check_id == "credential":
        if item.credential is None:
            raise AppError(
                status_code=400,
                code="CREDENTIAL_SPEC_REQUIRED",
                app_code="CREDENTIAL_SPEC_REQUIRED",
                message_ko="credential 적용에는 credential 사양이 필요합니다.",
            )
        sql, binds, display = _credential_plan(item.credential)
        recorder.record(display)
        async with pool_registry.acquire(
            connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
        ) as conn:
            await common.call_db(oracle.execute(conn, sql, binds), recorder)
        cred_name = item.credential.credential_name
        await resource_service.record(
            connection_id,
            resource_type="credential",
            resource_name=cred_name.upper(),
            create_sql=display,
            cleanup_sql=f"BEGIN DBMS_CLOUD.DROP_CREDENTIAL('{cred_name.upper()}'); END;",
        )
        return display

    if check_id == "network_acl":
        if provider == "oci":
            raise AppError(
                status_code=400,
                code="ACL_NOT_REQUIRED",
                app_code="ACL_NOT_REQUIRED",
                message_ko="OCI Generative AI는 네트워크 ACL이 필요 없습니다.",
                docs_ref="selectai-reference.md §4.2 (p34)",
            )
        host = PROVIDER_HOSTS.get(provider)
        if not host:
            raise AppError(
                status_code=400,
                code="ACL_HOST_UNKNOWN",
                app_code="ACL_HOST_UNKNOWN",
                message_ko=f"공급자 '{provider}'의 ACL host를 알 수 없습니다.",
            )
        binds = {"provider_host": host, "target_user": grantee}
        display = APPEND_HOST_ACE_SQL.replace(":provider_host", f"'{host}'").replace(
            ":target_user", f"'{grantee}'"
        )
        recorder.record(display)
        async with pool_registry.acquire(
            connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
        ) as conn:
            await common.call_db(oracle.execute(conn, APPEND_HOST_ACE_SQL, binds), recorder)
        await resource_service.record(
            connection_id,
            resource_type="acl",
            resource_name=f"{host}:{grantee}",
            create_sql=display,
            cleanup_sql=(
                "BEGIN\n"
                "  DBMS_NETWORK_ACL_ADMIN.REMOVE_HOST_ACE(\n"
                f"    host => '{host}',\n"
                "    ace  => xs$ace_type(privilege_list => xs$name_list('http'),\n"
                f"                        principal_name => '{grantee}',\n"
                "                        principal_type => xs_acl.ptype_db));\n"
                "END;"
            ),
        )
        return display

    if check_id == "data_access":
        enable = item.enable if item.enable is not None else True
        sql = FIX_ENABLE_DATA_ACCESS if enable else FIX_DISABLE_DATA_ACCESS
        recorder.record(sql)
        async with pool_registry.acquire(
            connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
        ) as conn:
            await common.call_db(oracle.execute(conn, sql), recorder)
        await common.set_data_access_state(connection_id, enable)
        return sql

    if check_id == "feedback_grants":
        statements = [
            f"GRANT READ ON SYS.V_$MAPPED_SQL TO {grantee}",
            f"GRANT READ ON SYS.V_$SESSION TO {grantee}",
        ]
        async with pool_registry.acquire(
            connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
        ) as conn:
            for sql in statements:
                recorder.record(sql)
                await common.call_db(oracle.execute(conn, sql), recorder)
        # cleanup_sql은 단일 문장만 실행 가능 — 뷰별로 ledger 항목을 분리 기록한다
        for view_name, sql in zip(("V_$MAPPED_SQL", "V_$SESSION"), statements):
            await resource_service.record(
                connection_id,
                resource_type="grant",
                resource_name=f"READ:{view_name}:{grantee}",
                create_sql=sql,
                cleanup_sql=f"REVOKE READ ON SYS.{view_name} FROM {grantee}",
            )
        return "; ".join(statements)

    raise AppError(
        status_code=400,
        code="UNKNOWN_CHECK_ID",
        app_code="UNKNOWN_CHECK_ID",
        message_ko=f"알 수 없는 점검 항목입니다: {check_id}",
    )
