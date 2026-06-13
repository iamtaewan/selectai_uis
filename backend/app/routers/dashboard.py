"""대시보드 라우터 — /api/v1/dashboard (FR-09, P1 / api-spec §9).

엔드포인트 (인덱스 #39):
- GET /dashboard/health  데모 상태 신호등 (커넥션·권한·Data Access·기본 프로파일·데모 스키마)

짧은 타임아웃으로 일괄 점검하고 결과를 30초 캐시한다 (api-spec §9.1).
"""
from __future__ import annotations

import time

from fastapi import APIRouter, Header

from app.db import oracle, pool_registry
from app.errors import AppError
from app.schemas.models import DashboardHealth, Envelope, HealthSignal
from app.services import common, prereq_service

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_CACHE_TTL_SECONDS = 30
# connection_id → (monotonic 시각, DashboardHealth, executed_sql)
_cache: dict[str, tuple[float, DashboardHealth, list[str]]] = {}

_DEMO_TABLES_SQL = (
    "SELECT table_name FROM ALL_TABLES "
    "WHERE owner = SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') "
    "AND table_name IN ('TABLE1', 'TABLE2', 'TABLE3')"
)


async def _collect(connection_id: str, recorder: oracle.SqlRecorder) -> DashboardHealth:
    """신호 5종 수집 — 각 점검 실패는 해당 신호 red로 격리한다."""
    signals: list[HealthSignal] = []

    # 1) DB 연결 (5초 타임아웃 — FR-02와 동일 기준)
    try:
        probe_started = common.start_timer()
        recorder.record("SELECT 1 FROM dual")
        async with pool_registry.acquire(
            connection_id, pool_registry.CALL_TIMEOUT_TEST_MS
        ) as conn:
            await common.call_db(oracle.fetch_value(conn, "SELECT 1 FROM dual"), recorder)
        latency_ms = int((time.perf_counter() - probe_started) * 1000)
        signals.append(HealthSignal(
            id="connection", status="green", title_ko="DB 연결",
            detail_ko=f"접속 정상 ({latency_ms}ms)",
        ))
        connected = True
    except AppError as exc:
        signals.append(HealthSignal(
            id="connection", status="red", title_ko="DB 연결",
            detail_ko=f"접속 실패 — {exc.message_ko}",
        ))
        connected = False

    # 2) 권한 점검 (연결 실패 시 판정 불가 → red)
    if connected:
        try:
            check = await prereq_service.run_checks(
                connection_id, provider="oci", target_user="ADMIN",
                include=set(), recorder=recorder,
            )
            failed = [c.check_id for c in check.checks if c.status == "fail"]
            if not failed:
                signals.append(HealthSignal(
                    id="privileges", status="green", title_ko="권한 점검",
                    detail_ko="필수 항목 전부 통과",
                ))
            else:
                signals.append(HealthSignal(
                    id="privileges", status="yellow", title_ko="권한 점검",
                    detail_ko=f"미통과 항목: {', '.join(failed)}",
                    fix_endpoint="POST /api/v1/privileges/apply",
                ))
        except AppError as exc:
            signals.append(HealthSignal(
                id="privileges", status="red", title_ko="권한 점검",
                detail_ko=f"점검 실패 — {exc.message_ko}",
            ))
    else:
        signals.append(HealthSignal(
            id="privileges", status="red", title_ko="권한 점검",
            detail_ko="DB 연결 불가로 점검할 수 없습니다",
        ))

    # 3) Data Access — settings.json 적용 이력 기반 (api-spec §3.1과 동일 판정)
    state = await common.get_data_access_state(connection_id)
    if state == "enabled":
        signals.append(HealthSignal(
            id="data_access", status="green", title_ko="Data Access",
            detail_ko="활성 — narrate/합성 데이터 가능",
        ))
    elif state == "disabled":
        signals.append(HealthSignal(
            id="data_access", status="red", title_ko="Data Access",
            detail_ko="비활성 — narrate 데모 불가 (ORA-20000)",
            fix_endpoint="POST /api/v1/privileges/apply",
        ))
    else:
        signals.append(HealthSignal(
            id="data_access", status="yellow", title_ko="Data Access",
            detail_ko="적용 이력 없음 — 상태 미확정 (기본값은 활성)",
            fix_endpoint="POST /api/v1/privileges/apply",
        ))

    # 4) 기본 프로파일 — 앱 설정 + DB 상태 교차 확인
    default_profile = await common.get_default_profile(connection_id)
    if not default_profile:
        signals.append(HealthSignal(
            id="default_profile", status="yellow", title_ko="기본 프로파일",
            detail_ko="기본 프로파일 미설정",
            fix_endpoint="PUT /api/v1/settings/default-profile",
        ))
    elif connected:
        try:
            recorder.record(
                "SELECT status FROM USER_CLOUD_AI_PROFILES "
                f"WHERE profile_name = '{common.escape_literal(default_profile)}'"
            )
            async with pool_registry.acquire(
                connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
            ) as conn:
                row = await common.call_db(
                    oracle.fetch_one(
                        conn,
                        "SELECT status FROM USER_CLOUD_AI_PROFILES "
                        "WHERE profile_name = :profile_name",
                        {"profile_name": default_profile.upper()},
                    ),
                    recorder,
                )
            if row and str(row[0]) == "ENABLED":
                signals.append(HealthSignal(
                    id="default_profile", status="green", title_ko="기본 프로파일",
                    detail_ko=f"{default_profile.upper()} (ENABLED)",
                ))
            elif row:
                signals.append(HealthSignal(
                    id="default_profile", status="red", title_ko="기본 프로파일",
                    detail_ko=f"{default_profile.upper()} 비활성(DISABLED) 상태",
                ))
            else:
                signals.append(HealthSignal(
                    id="default_profile", status="red", title_ko="기본 프로파일",
                    detail_ko=f"{default_profile.upper()}이(가) DB에 존재하지 않습니다",
                    fix_endpoint="PUT /api/v1/settings/default-profile",
                ))
        except AppError as exc:
            signals.append(HealthSignal(
                id="default_profile", status="red", title_ko="기본 프로파일",
                detail_ko=f"확인 실패 — {exc.message_ko}",
            ))
    else:
        signals.append(HealthSignal(
            id="default_profile", status="yellow", title_ko="기본 프로파일",
            detail_ko="DB 연결 불가로 상태를 확인할 수 없습니다",
        ))

    # 5) 데모 스키마 (FR-08 모호 스키마 존재 여부)
    if connected:
        try:
            recorder.record(_DEMO_TABLES_SQL)
            async with pool_registry.acquire(
                connection_id, pool_registry.CALL_TIMEOUT_DEFAULT_MS
            ) as conn:
                _, rows = await common.call_db(
                    oracle.fetch_all(conn, _DEMO_TABLES_SQL), recorder
                )
            if len(rows) == 3:
                signals.append(HealthSignal(
                    id="demo_schema", status="green", title_ko="데모 스키마",
                    detail_ko="증강 비교용 모호 스키마(TABLE1~3) 준비됨",
                ))
            else:
                signals.append(HealthSignal(
                    id="demo_schema", status="yellow", title_ko="데모 스키마",
                    detail_ko="증강 비교용 모호 스키마 미생성",
                    fix_endpoint="POST /api/v1/enrichment/demo-schema",
                ))
        except AppError as exc:
            signals.append(HealthSignal(
                id="demo_schema", status="yellow", title_ko="데모 스키마",
                detail_ko=f"확인 실패 — {exc.message_ko}",
                fix_endpoint="POST /api/v1/enrichment/demo-schema",
            ))
    else:
        signals.append(HealthSignal(
            id="demo_schema", status="yellow", title_ko="데모 스키마",
            detail_ko="DB 연결 불가로 상태를 확인할 수 없습니다",
        ))

    statuses = {signal.status for signal in signals}
    overall = "red" if "red" in statuses else ("yellow" if "yellow" in statuses else "green")
    return DashboardHealth(overall=overall, signals=signals)


@router.get("/health", response_model=Envelope)
async def dashboard_health(
    x_connection_id: str | None = Header(default=None, alias="X-Connection-Id"),
) -> Envelope:
    """§9.1 일괄 점검 (짧은 타임아웃, 캐시 30초) — data: DashboardHealth."""
    started = common.start_timer()
    connection_id = common.require_connection_id(x_connection_id)
    cached = _cache.get(connection_id)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return common.make_envelope(cached[1], cached[2], started)
    recorder = oracle.SqlRecorder()
    health = await _collect(connection_id, recorder)
    _cache[connection_id] = (time.monotonic(), health, recorder.statements)
    return common.make_envelope(health, recorder.statements, started)
