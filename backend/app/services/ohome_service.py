"""o-home-shopping 데이터 적재 — DDL(47 테이블) 생성 + CSV 벌크 적재.

DDL은 백엔드에 번들(app/data/o_home_shopping/oracle_ddl.sql), CSV는 설정 경로
(settings.ohome_dir, 기본 ~/projects/o-home-shopping/demo)에서 읽는다. CSV 헤더가
대상 테이블 컬럼명과 일치하므로 헤더 기준으로 INSERT 바인드를 구성해 executemany 배치 적재.

날짜/시각: DATE='YYYY-MM-DD', TIMESTAMP='YYYY-MM-DD HH24:MI:SS' (세션 NLS로 자동 변환).
빈 문자열은 NULL로 변환한다.
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.db import oracle, pool_registry
from app.errors import AppError
from app.services import common

_BUNDLE = Path(__file__).resolve().parent.parent / "data" / "o_home_shopping"
_DDL_PATH = _BUNDLE / "oracle_ddl.sql"
_MANIFEST_PATH = _BUNDLE / "manifest.json"

_BATCH_ROWS = 10_000
# 세션 NLS — CSV의 날짜/시각 형식과 일치시켜 문자열 바인드를 자동 변환
_NLS_SQL = (
    "ALTER SESSION SET "
    "NLS_DATE_FORMAT='YYYY-MM-DD' "
    "NLS_TIMESTAMP_FORMAT='YYYY-MM-DD HH24:MI:SS' "
    "NLS_TIMESTAMP_TZ_FORMAT='YYYY-MM-DD HH24:MI:SS'"
)


def _manifest() -> list[dict[str, str]]:
    """[{table, csv}] 적재 순서 (vertices 22 → edges 25)."""
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


def _ddl_statements() -> list[str]:
    """번들 DDL을 개별 CREATE TABLE 문으로 분리 (주석 제거, ';' 분리)."""
    raw = _DDL_PATH.read_text(encoding="utf-8")
    # 라인 주석(-- ...) 제거
    lines = [ln for ln in raw.splitlines() if not ln.strip().startswith("--")]
    body = "\n".join(lines)
    stmts = [s.strip() for s in body.split(";") if s.strip()]
    return stmts


def _local_path(rel: str) -> Path | None:
    """OHOME_DATA_DIR이 설정돼 있고 파일이 있으면 로컬 경로, 아니면 None(버킷 사용)."""
    configured = get_settings().ohome_data_dir
    if not configured:
        return None
    p = Path(configured).expanduser() / rel
    return p if p.is_file() else None


def _object_url(rel: str) -> str:
    """버킷 공개 URL — 객체명의 '/'는 %2F로 인코딩."""
    base = get_settings().ohome_bucket_base_url.rstrip("/")
    return f"{base}/{urllib.parse.quote(rel, safe='')}"


def _source_label(rel: str) -> str:
    return str(_local_path(rel)) if _local_path(rel) else _object_url(rel)


def _read_csv_text(rel: str) -> str:
    """CSV 본문을 문자열로 — 로컬 우선, 없으면 버킷 공개 URL에서 다운로드(블로킹)."""
    local = _local_path(rel)
    if local is not None:
        return local.read_text(encoding="utf-8")
    url = _object_url(rel)
    try:
        with urllib.request.urlopen(url, timeout=120) as resp:  # noqa: S310 — 고정 신뢰 URL
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise AppError(
            status_code=404, code="OHOME_CSV_MISSING", app_code="OHOME_CSV_MISSING",
            message_ko=f"버킷에서 CSV를 가져오지 못했습니다 ({exc.code}): {rel}",
            hint_ko="버킷 공개 설정(ObjectRead) 또는 OHOME_BUCKET_BASE_URL을 확인하세요.",
        ) from exc
    except OSError as exc:
        raise AppError(
            status_code=503, code="OHOME_SOURCE_UNREACHABLE", app_code="OHOME_SOURCE_UNREACHABLE",
            message_ko=f"CSV 소스에 연결하지 못했습니다: {exc}", retryable=True,
        ) from exc


def _source_reachable() -> bool:
    """소스 접근성 — 로컬 데이터 디렉터리가 있거나, 버킷의 한 객체가 응답하면 True."""
    if get_settings().ohome_data_dir and Path(get_settings().ohome_data_dir).expanduser().is_dir():
        return True
    try:
        req = urllib.request.Request(_object_url("02_data/vertices/channel.csv"), method="HEAD")
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return resp.status == 200
    except Exception:
        return False


# ---------------------------------------------------------------- 점검
async def check_ohome(connection_id: str, recorder: oracle.SqlRecorder) -> dict[str, Any]:
    """CSV 소스(버킷/로컬) 접근성 + 접속 사용자 + 테이블 인벤토리."""
    settings = get_settings()
    manifest = _manifest()
    using_local = bool(settings.ohome_data_dir)
    reachable = await asyncio.to_thread(_source_reachable)
    tables = [{"table": m["table"], "csv": m["csv"]} for m in manifest]
    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
    ) as conn:
        current_user = str(
            await oracle.fetch_value(conn, "SELECT USER FROM dual", recorder=recorder)
        ).upper()
    return {
        "current_user": current_user,
        "source": "local" if using_local else "bucket",
        "source_url": settings.ohome_data_dir or settings.ohome_bucket_base_url,
        "source_reachable": reachable,
        "table_count": len(manifest),
        "tables": tables,
    }


# ---------------------------------------------------------------- DDL (47 테이블 생성)
async def setup_ddl(
    connection_id: str, *, overwrite: bool, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """번들 DDL 실행 — overwrite면 기존 OHV2 테이블 DROP 후 생성."""
    steps: list[dict[str, Any]] = []
    stmts = _ddl_statements()
    # CREATE TABLE <name> 에서 테이블명 추출 (drop 용)
    table_names: list[str] = []
    for s in stmts:
        m = re.search(r"create\s+table\s+([A-Za-z0-9_$#]+)", s, re.IGNORECASE)
        if m:
            table_names.append(m.group(1).upper())

    async with pool_registry.acquire(
        connection_id, pool_registry.CALL_TIMEOUT_GENERATE_MS
    ) as conn:
        if overwrite:
            # FK 의존성 회피 위해 CASCADE CONSTRAINTS, 존재하지 않으면 무시
            for t in reversed(table_names):
                drop = f'DROP TABLE "{t}" CASCADE CONSTRAINTS PURGE'
                try:
                    await oracle.execute(conn, drop, recorder=recorder)
                except AppError:
                    pass
        created = 0
        for s in stmts:
            m = re.search(r"create\s+table\s+([A-Za-z0-9_$#]+)", s, re.IGNORECASE)
            label = m.group(1).upper() if m else "(stmt)"
            try:
                await oracle.execute(conn, s, recorder=recorder)
                created += 1
                steps.append({"object": label, "status": "ok", "detail": "테이블 생성"})
            except AppError as exc:
                steps.append({"object": label, "status": "error", "detail": exc.message_ko})
    return {
        "summary": {"tables_total": len(table_names), "created": created},
        "steps": steps,
    }


# ---------------------------------------------------------------- 테이블 1개 CSV 적재
def _row_values(header: list[str], row: list[str]) -> list[Any]:
    """CSV 한 행 → 바인드 값. 빈 문자열은 NULL(None)로 변환."""
    return [None if (v is None or v == "") else v for v in row]


# COPY_DATA 포맷 — CSV, 헤더 스킵, 빈값 NULL, 날짜/시각 포맷
_COPY_FORMAT = json.dumps({
    "type": "csv",
    "skipheaders": "1",
    "blankasnull": "true",
    "dateformat": "YYYY-MM-DD",
    "timestampformat": "YYYY-MM-DD HH24:MI:SS",
    "ignoremissingcolumns": "true",
    "rejectlimit": "unlimited",
})


async def _table_count(conn: Any, table: str, recorder: oracle.SqlRecorder) -> int:
    n = await oracle.fetch_value(conn, f'SELECT COUNT(*) FROM "{table}"', recorder=recorder)
    return int(n or 0)


async def _copy_data(conn: Any, table: str, rel: str, recorder: oracle.SqlRecorder) -> None:
    """ADB가 버킷 공개 URL에서 직접 병렬 적재 (DBMS_CLOUD.COPY_DATA). 백엔드 다운로드 불필요."""
    uri = _object_url(rel)
    recorder.record(
        f"BEGIN DBMS_CLOUD.COPY_DATA(table_name=>'{table}', file_uri_list=>'{uri}', "
        f"format=>'{_COPY_FORMAT}'); END;"
    )
    await oracle.execute(
        conn,
        "BEGIN DBMS_CLOUD.COPY_DATA(table_name => :t, file_uri_list => :u, format => :f); END;",
        {"t": table, "u": uri, "f": _COPY_FORMAT},
    )


async def _load_via_executemany(
    connection_id: str, table: str, rel: str, recorder: oracle.SqlRecorder
) -> int:
    """로컬 파일 폴백 경로 — CSV를 executemany 배치로 적재."""
    text = await asyncio.to_thread(_read_csv_text, rel)
    reader = csv.reader(io.StringIO(text))
    try:
        header = next(reader)
    except StopIteration:
        return 0
    cols = ", ".join(f'"{c.strip().upper()}"' for c in header)
    binds = ", ".join(f":{i + 1}" for i in range(len(header)))
    insert = f'INSERT INTO "{table}" ({cols}) VALUES ({binds})'
    recorder.record(f"{insert} -- batch load {rel}")
    loaded = 0
    async with pool_registry.acquire(connection_id, pool_registry.CALL_TIMEOUT_GENERATE_MS) as conn:
        await oracle.execute(conn, _NLS_SQL, recorder=recorder)
        cursor = conn.cursor()
        try:
            batch: list[list[Any]] = []
            for row in reader:
                if len(row) != len(header):
                    continue
                batch.append(_row_values(header, row))
                if len(batch) >= _BATCH_ROWS:
                    await cursor.executemany(insert, batch)
                    loaded += len(batch)
                    batch = []
            if batch:
                await cursor.executemany(insert, batch)
                loaded += len(batch)
            await conn.commit()
        finally:
            cursor.close()
    return loaded


async def load_table(
    connection_id: str, table: str, *, recorder: oracle.SqlRecorder
) -> dict[str, Any]:
    """한 테이블 적재 — 기본은 버킷에서 COPY_DATA(고속), OHOME_DATA_DIR 지정 시 로컬 executemany."""
    common.validate_identifier(table, "테이블 이름")
    tbl = table.upper()
    manifest = {m["table"]: m["csv"] for m in _manifest()}
    rel = manifest.get(tbl)
    if rel is None:
        raise AppError(
            status_code=400, code="OHOME_TABLE_UNKNOWN", app_code="OHOME_TABLE_UNKNOWN",
            message_ko=f"매니페스트에 없는 테이블입니다: {table}",
        )
    try:
        if _local_path(rel) is not None:
            loaded = await _load_via_executemany(connection_id, tbl, rel, recorder)
        else:
            async with pool_registry.acquire(
                connection_id, pool_registry.CALL_TIMEOUT_GENERATE_MS
            ) as conn:
                await _copy_data(conn, tbl, rel, recorder)
                loaded = await _table_count(conn, tbl, recorder)
    except AppError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            status_code=500, code="OHOME_LOAD_FAILED", app_code="OHOME_LOAD_FAILED",
            message_ko=f"{tbl} 적재 실패: {exc}", detail=str(exc),
        ) from exc
    return {"table": tbl, "rows_loaded": loaded, "source": _source_label(rel)}


# ---------------------------------------------------------------- 비동기 병렬 적재 (백그라운드 작업)
# 커넥션별 진행 상태(인메모리). 프론트는 load-all 시작 후 load-status를 폴링한다.
_load_jobs: dict[str, dict[str, Any]] = {}
_PARALLEL = 4  # 동시 COPY_DATA 수 (풀 max에 맞춤)


async def _ohv2_fk_names(conn: Any, recorder: oracle.SqlRecorder) -> list[tuple[str, str]]:
    """현재 사용자 스키마의 OHV2 테이블 FK 제약 (table, constraint)."""
    _, rows = await oracle.fetch_all(
        conn,
        "SELECT table_name, constraint_name FROM user_constraints "
        "WHERE constraint_type = 'R' AND table_name LIKE 'OHV2%'",
        recorder=recorder,
    )
    return [(r[0], r[1]) for r in rows]


async def _toggle_fks(conn: Any, enable: bool, recorder: oracle.SqlRecorder) -> None:
    """OHV2 FK 일괄 비활성/활성 — 병렬 적재 중 순서 의존성 제거(활성은 NOVALIDATE로 빠르게)."""
    state = "ENABLE NOVALIDATE" if enable else "DISABLE"
    for table, cons in await _ohv2_fk_names(conn, recorder):
        try:
            await oracle.execute(
                conn, f'ALTER TABLE "{table}" {state} CONSTRAINT "{cons}"', recorder=recorder
            )
        except AppError:
            pass  # 일부 실패는 무시(존재하지 않거나 이미 해당 상태)


def get_load_status(connection_id: str) -> dict[str, Any] | None:
    """진행 상태 스냅샷."""
    job = _load_jobs.get(connection_id)
    return dict(job) if job else None


async def start_load_all(connection_id: str, *, overwrite: bool) -> dict[str, Any]:
    """비동기 전체 적재 시작 — DDL → FK 비활성 → 병렬 COPY_DATA → FK 활성. 진행은 폴링으로."""
    existing = _load_jobs.get(connection_id)
    if existing and existing.get("running"):
        return existing
    manifest = _manifest()
    job: dict[str, Any] = {
        "running": True,
        "phase": "시작",
        "total": len(manifest),
        "done": 0,
        "rows": 0,
        "ok": 0,
        "failed": 0,
        "steps": [],
        "finished": False,
    }
    _load_jobs[connection_id] = job
    asyncio.create_task(_run_load_all(connection_id, overwrite, manifest, job))
    return dict(job)


async def _run_load_all(
    connection_id: str, overwrite: bool, manifest: list[dict[str, str]], job: dict[str, Any]
) -> None:
    rec = oracle.SqlRecorder()

    def log(text: str, status: str = "ok") -> None:
        job["steps"].append({"status": status, "text": text})

    try:
        # 1) DDL
        job["phase"] = "DDL 생성"
        ddl = await setup_ddl(connection_id, overwrite=overwrite, recorder=rec)
        log(f"DDL 테이블 생성 {ddl['summary']['created']}/{ddl['summary']['tables_total']}")

        # 2) FK 비활성 (병렬 적재 위해)
        job["phase"] = "FK 비활성화"
        async with pool_registry.acquire(
            connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
        ) as conn:
            await _toggle_fks(conn, enable=False, recorder=rec)
        log("FK 제약 일시 비활성화")

        # 3) 병렬 COPY_DATA
        job["phase"] = "적재"
        sem = asyncio.Semaphore(_PARALLEL)

        async def _one(item: dict[str, str]) -> None:
            table = item["table"]
            async with sem:
                r = oracle.SqlRecorder()
                try:
                    async with pool_registry.acquire(
                        connection_id, pool_registry.CALL_TIMEOUT_GENERATE_MS
                    ) as conn:
                        await _copy_data(conn, table, item["csv"], r)
                        cnt = await _table_count(conn, table, r)
                    job["rows"] += cnt
                    job["ok"] += 1
                    log(f"{table} — {cnt:,}행")
                except Exception as exc:  # noqa: BLE001
                    job["failed"] += 1
                    log(f"{table} 실패 — {str(exc).splitlines()[0]}", status="error")
                finally:
                    job["done"] += 1

        await asyncio.gather(*[_one(m) for m in manifest])

        # 4) FK 재활성 (NOVALIDATE)
        job["phase"] = "FK 재활성화"
        async with pool_registry.acquire(
            connection_id, pool_registry.CALL_TIMEOUT_PRIVILEGE_MS
        ) as conn:
            await _toggle_fks(conn, enable=True, recorder=rec)
        log(f"FK 제약 재활성화 — 총 {job['rows']:,}행 적재")
        job["phase"] = "완료"
    except Exception as exc:  # noqa: BLE001
        log(f"작업 중단 — {exc}", status="error")
        job["phase"] = "오류"
    finally:
        job["running"] = False
        job["finished"] = True
