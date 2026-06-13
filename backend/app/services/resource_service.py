"""리소스 대장 서비스 — resources.json ledger CRUD, cleanup 실행/파일 정리, 실패 격리.

근거: architecture.md §3.3.1, api-spec §10. cleanup_order 순 실행, 한 항목 실패해도
계속 진행. 대장 항목은 삭제하지 않고 cleanup_status만 갱신 (감사 기록 유지).
"""
from __future__ import annotations

import shutil
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import local_store, oracle, pool_registry
from app.errors import AppError
from app.schemas.models import (
    CleanupItemResult,
    CleanupLedgerItem,
    CleanupListResult,
    CleanupRequest,
    CleanupResult,
    ErrorBody,
)
from app.security.crypto import mask_secrets
from app.services import common

# 의존성 정리 순서 (architecture.md §3.3.1): 대화 → 프로파일/벡터 인덱스 →
# credential/ACL/grant → 데모 테이블 → 앱 파일(wallet/connection)
CLEANUP_ORDER: dict[str, int] = {
    "conversation": 10,
    "profile": 20,
    "vector_index": 20,
    "credential": 30,
    "acl": 30,
    "grant": 30,
    "demo_table": 40,
    "wallet": 50,
    "connection": 50,
}

_FILE_TYPES = frozenset({"wallet", "connection"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def record(
    connection_id: str,
    *,
    resource_type: str,
    resource_name: str,
    create_sql: str,
    cleanup_sql: str,
    owner: str | None = None,
    cleanup_order: int | None = None,
) -> dict[str, Any]:
    """생성 작업 성공 직후 ledger 항목을 기록한다 (FR-10). 비밀값은 기록 전 마스킹."""
    entry = {
        "id": f"led_{uuid.uuid4().hex[:12]}",
        "connection_id": connection_id,
        "resource_type": resource_type,
        "resource_name": resource_name,
        "owner": owner,
        "create_sql": mask_secrets(create_sql),
        "cleanup_sql": mask_secrets(cleanup_sql),
        "cleanup_order": cleanup_order
        if cleanup_order is not None
        else CLEANUP_ORDER.get(resource_type, 90),
        "cleanup_status": "pending",
        "created_at": _now_iso(),
        "cleaned_at": None,
        "last_error": None,
    }
    await local_store.append_resource(entry)
    return entry


async def mark_done_by_name(
    connection_id: str, resource_type: str, resource_name: str
) -> None:
    """앱의 정규 삭제 API(DROP_PROFILE 등)로 정리된 항목을 done으로 동기화한다."""

    def _mutate(items: Any) -> Any:
        for item in items:
            if (
                item.get("connection_id") == connection_id
                and item.get("resource_type") == resource_type
                and item.get("resource_name") == resource_name
                and item.get("cleanup_status") in ("pending", "failed")
            ):
                item["cleanup_status"] = "done"
                item["cleaned_at"] = _now_iso()
        return items

    await local_store.update_json(local_store.RESOURCES_FILE, _mutate)


def _to_ledger_item(raw: dict[str, Any]) -> CleanupLedgerItem:
    """저장 포맷 → API 모델 (cleanup_preview = cleanup_sql, §10.1)."""
    return CleanupLedgerItem(
        id=raw["id"],
        connection_id=raw.get("connection_id", ""),
        resource_type=raw.get("resource_type", "profile"),
        resource_name=raw.get("resource_name", ""),
        owner=raw.get("owner"),
        cleanup_order=raw.get("cleanup_order", 90),
        cleanup_status=raw.get("cleanup_status", "pending"),
        cleanup_preview=raw.get("cleanup_sql", ""),
        created_at=raw.get("created_at") or _now_iso(),
        cleaned_at=raw.get("cleaned_at"),
        last_error=raw.get("last_error"),
    )


async def list_resources(
    connection_id: str, status: str = "pending", resource_type: str | None = None
) -> CleanupListResult:
    """§10.1 대장 목록 — 현재 커넥션 항목만, status/type 필터."""
    items = [
        raw
        for raw in await local_store.load_resources()
        if raw.get("connection_id") == connection_id
    ]
    summary: dict[str, int] = {"pending": 0, "failed": 0, "done": 0, "skipped": 0}
    for raw in items:
        key = raw.get("cleanup_status", "pending")
        summary[key] = summary.get(key, 0) + 1
    if status != "all":
        items = [raw for raw in items if raw.get("cleanup_status") == status]
    if resource_type:
        items = [raw for raw in items if raw.get("resource_type") == resource_type]
    items.sort(key=lambda raw: (raw.get("cleanup_order", 90), raw.get("created_at") or ""))
    return CleanupListResult(items=[_to_ledger_item(raw) for raw in items], summary=summary)


async def _run_cleanup_sql(connection_id: str, sql: str, recorder: oracle.SqlRecorder) -> None:
    """ledger의 cleanup_sql 실행 — 기록 시점에 검증·마스킹된 고정 문장만 (security.md §3.3)."""
    recorder.record(sql)
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
    ) as conn:
        await common.call_db(oracle.execute(conn, sql), recorder)


async def _cleanup_app_file(raw: dict[str, Any]) -> str:
    """wallet/connection 파일 리소스 정리 — SQL이 아닌 작업 설명을 반환한다 (§10.3)."""
    resource_type = raw["resource_type"]
    name = raw["resource_name"]
    if resource_type == "wallet":
        target = local_store.wallets_dir() / name
        if target.exists():
            shutil.rmtree(target)
        return f"wallet 디렉토리 삭제: ~/.selectai/wallets/{name}/"
    # connection — 커넥션 레코드 제거 + 풀 종료
    await pool_registry.close_pool(name)

    def _remove(doc: dict[str, Any]) -> dict[str, Any]:
        doc["connections"] = [c for c in doc["connections"] if c.get("id") != name]
        return doc

    await local_store.update_connections_doc(_remove)
    return f"커넥션 레코드 삭제: {name}"


async def _set_status(ledger_id: str, status: str, error: str | None = None) -> None:
    def _mutate(item: dict[str, Any]) -> None:
        item["cleanup_status"] = status
        item["last_error"] = error
        if status == "done":
            item["cleaned_at"] = _now_iso()

    await local_store.update_resource(ledger_id, _mutate)


async def _execute_item(
    connection_id: str, raw: dict[str, Any], recorder: oracle.SqlRecorder
) -> CleanupItemResult:
    """항목 1건 정리 — 실패해도 예외를 올리지 않고 결과 객체로 격리한다."""
    base = {
        "id": raw["id"],
        "resource_type": raw["resource_type"],
        "resource_name": raw["resource_name"],
    }
    try:
        if raw["resource_type"] in _FILE_TYPES:
            action = await _cleanup_app_file(raw)
            await _set_status(raw["id"], "done")
            return CleanupItemResult(**base, ok=True, status="done", cleanup_action=action)
        await _run_cleanup_sql(connection_id, raw.get("cleanup_sql", ""), recorder)
        await _set_status(raw["id"], "done")
        return CleanupItemResult(**base, ok=True, status="done")
    except AppError as exc:
        await _set_status(raw["id"], "failed", error=exc.message_ko)
        return CleanupItemResult(
            **base,
            ok=False,
            status="failed",
            error=ErrorBody(
                code=exc.code,
                app_code=exc.app_code,
                message_ko=exc.message_ko,
                hint_ko=exc.hint_ko,
                detail=exc.detail,
                retryable=exc.retryable,
            ),
        )
    except OSError as exc:  # 파일 삭제 실패
        await _set_status(raw["id"], "failed", error=str(exc))
        return CleanupItemResult(
            **base,
            ok=False,
            status="failed",
            error=ErrorBody(
                code="FILE_CLEANUP_FAILED",
                app_code="FILE_CLEANUP_FAILED",
                message_ko="앱 파일 정리에 실패했습니다.",
                detail=str(exc),
            ),
        )


async def _get_raw(ledger_id: str) -> dict[str, Any]:
    for raw in await local_store.load_resources():
        if raw.get("id") == ledger_id:
            return raw
    raise AppError(
        status_code=404,
        code="RESOURCE_NOT_FOUND",
        app_code="RESOURCE_NOT_FOUND",
        message_ko="대장에 없는 리소스 항목입니다.",
        hint_ko="리소스 목록을 새로고침한 뒤 다시 시도하세요.",
    )


async def cleanup_item(
    connection_id: str, ledger_id: str, recorder: oracle.SqlRecorder
) -> CleanupItemResult:
    """§10.2 개별 정리 — done 항목 재정리는 409, 실패는 200 + ok=false."""
    raw = await _get_raw(ledger_id)
    if raw.get("cleanup_status") == "done":
        raise AppError(
            status_code=409,
            code="RESOURCE_ALREADY_CLEANED",
            app_code="RESOURCE_ALREADY_CLEANED",
            message_ko="이미 정리가 완료된 항목입니다.",
        )
    return await _execute_item(connection_id, raw, recorder)


async def cleanup(
    connection_id: str, request: CleanupRequest, recorder: oracle.SqlRecorder
) -> CleanupResult:
    """§10.3 일괄 정리 — cleanup_order 순 실행, 실패 격리, dry_run 지원."""
    targets = [
        raw
        for raw in await local_store.load_resources()
        if raw.get("connection_id") == connection_id
        and raw.get("cleanup_status") in ("pending", "failed")
    ]
    if request.item_ids:
        wanted = set(request.item_ids)
        targets = [raw for raw in targets if raw["id"] in wanted]
    if request.resource_types:
        wanted_types = set(request.resource_types)
        targets = [raw for raw in targets if raw.get("resource_type") in wanted_types]
    targets.sort(key=lambda raw: (raw.get("cleanup_order", 90), raw.get("created_at") or ""))

    results: list[CleanupItemResult] = []
    summary = {"done": 0, "failed": 0, "skipped": 0}
    for raw in targets:
        base = {
            "id": raw["id"],
            "resource_type": raw["resource_type"],
            "resource_name": raw["resource_name"],
        }
        if request.dry_run:
            results.append(
                CleanupItemResult(
                    **base,
                    ok=True,
                    status="preview",
                    cleanup_action=raw.get("cleanup_sql", ""),
                )
            )
            continue
        if raw["resource_type"] in _FILE_TYPES and not request.include_app_files:
            await _set_status(raw["id"], "skipped")
            results.append(
                CleanupItemResult(
                    **base,
                    ok=True,
                    status="skipped",
                    cleanup_action="include_app_files=false — 앱 파일 삭제 건너뜀",
                )
            )
            summary["skipped"] += 1
            continue
        result = await _execute_item(connection_id, raw, recorder)
        summary["done" if result.ok else "failed"] += 1
        results.append(result)
    return CleanupResult(results=results, summary=summary)
