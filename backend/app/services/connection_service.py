"""커넥션 서비스 — wallet 해제/검증, TNS alias 추출, OCI CLI 자동 다운로드, 커넥션 CRUD.

근거: architecture.md §3.1·§3.1.1·§3.3, api-spec §2, security.md §2.
- wallet zip: 검증(tnsnames.ora + ewallet.pem/cwallet.sso) → ~/.selectai/wallets/{id}/(0700)
  해제 → 평문 zip 즉시 삭제 → alias 파싱.
- OCI CLI: asyncio subprocess 비차단 2단계 (list 30s / generate-wallet 120s),
  --password는 ***MASKED*** 처리. 기본 컴파트먼트는 TAEWAN.KIM OCID.
- 비밀번호/wallet 암호는 Fernet 암호화 저장 (평문 저장 금지).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

import oracledb

from app.db import local_store, oracle, pool_registry
from app.errors import AppError, map_oracle_error
from app.schemas.models import (
    AdbCandidate,
    ConnectionCreate,
    ConnectionOut,
    ConnectionTestResult,
    ConnectionUpdate,
    WalletGenerateRequest,
    WalletGenerateResult,
    WalletUploadResult,
)
from app.security.crypto import decrypt_secret, encrypt_secret, mask_secrets

MAX_WALLET_ZIP_BYTES = 5 * 1024 * 1024  # api-spec §2.1 — 최대 5 MB

# 검증용 SQL (api-spec §2.2 — 명세 원문 그대로)
SQL_DB_VERSION = "SELECT banner_full FROM v$version WHERE ROWNUM = 1"
SQL_INSTANCE_META = (
    "SELECT sys_context('USERENV','CURRENT_USER') AS current_user, "
    "sys_context('USERENV','DB_NAME') AS db_name, "
    "sys_context('USERENV','SERVICE_NAME') AS service_name FROM dual"
)
SQL_PING = "SELECT 1 FROM dual"

# tnsnames.ora alias — 행 시작(공백 없음) 식별자만 매칭해 entry 내부 파라미터 오인 방지
_TNS_ALIAS_RE = re.compile(r"^([A-Za-z][\w.-]*)\s*=", re.MULTILINE)

# OCI CLI 인증 실패 식별 문자열 (security.md §2.5 — 앱은 복구하지 않고 폴백 유도)
_OCI_AUTH_ERROR_MARKERS = (
    "NotAuthenticated",
    "ConfigFileNotFound",
    "Could not find config file",
    "InvalidKeyFilePath",
    "InvalidPrivateKey",
    "missing the following",
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6]}"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _wallet_invalid(detail: str) -> AppError:
    return AppError(
        status_code=400,
        code="WALLET_INVALID",
        app_code="WALLET_INVALID",
        message_ko="wallet 파일을 열 수 없습니다. ADB 콘솔에서 wallet을 다시 다운로드하세요.",
        hint_ko="zip 안에 tnsnames.ora와 ewallet.pem(또는 cwallet.sso)이 있어야 합니다.",
        detail=detail,
    )


def _connection_not_found() -> AppError:
    return AppError(
        status_code=404,
        code="CONNECTION_NOT_FOUND",
        app_code="CONNECTION_NOT_FOUND",
        message_ko="존재하지 않는 커넥션입니다.",
        hint_ko="커넥션 목록을 새로고침한 뒤 다시 선택하세요.",
    )


def _record_to_out(record: dict[str, Any]) -> ConnectionOut:
    """저장 레코드 → 응답 모델 (비밀 필드 제외 — FR-01 수용 기준)."""
    return ConnectionOut(
        id=record["id"],
        name=record["name"],
        tns_alias=record["tns_alias"],
        username=record["username"],
        db_version=record.get("db_version"),
        db_name=record.get("db_name"),
        status=record.get("status", "UNKNOWN"),
        last_used_at=record.get("last_used_at"),
        created_at=record["created_at"],
    )


# ---------------------------------------------------------------- wallet 공통(합류) 경로


def parse_tns_aliases(tnsnames_text: str) -> list[str]:
    """tnsnames.ora에서 TNS alias 목록 추출 (architecture.md §3.1)."""
    return [m.group(1).lower() for m in _TNS_ALIAS_RE.finditer(tnsnames_text)]


def _extract_wallet_zip(zip_bytes: bytes, target_dir: Path) -> list[str]:
    """zip을 wallet 디렉토리(0700)에 해제하고 파일 목록을 반환한다 (zip-slip 방지)."""
    try:
        archive = zipfile.ZipFile(BytesIO(zip_bytes))
    except zipfile.BadZipFile as exc:
        raise _wallet_invalid(f"zip 형식이 아닙니다: {exc}") from exc

    target_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(target_dir, 0o700)
    files_found: list[str] = []
    for member in archive.infolist():
        if member.is_dir():
            continue
        name = Path(member.filename).name  # 경로 성분 제거 — zip-slip 방지
        if not name or name.startswith("."):
            continue
        dest = target_dir / name
        with archive.open(member) as src, open(dest, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.chmod(dest, 0o600)
        files_found.append(name)
    return sorted(files_found)


async def _register_wallet(
    zip_bytes: bytes,
    *,
    source: str,
    wallet_password: str | None = None,
    adb_ocid: str | None = None,
) -> dict[str, Any]:
    """업로드/자동 다운로드 공통 합류 경로 — 해제·검증·alias 파싱·메타 저장.

    반환: wallet 메타 레코드 (connections.json의 wallets[] 항목).
    """
    if len(zip_bytes) > MAX_WALLET_ZIP_BYTES:
        raise AppError(
            status_code=413,
            code="FILE_TOO_LARGE",
            app_code="FILE_TOO_LARGE",
            message_ko="wallet zip이 5 MB 제한을 초과했습니다.",
        )

    wallet_id = _new_id("wlt")
    wallet_dir = local_store.wallets_dir() / wallet_id
    try:
        files_found = _extract_wallet_zip(zip_bytes, wallet_dir)

        if "tnsnames.ora" not in files_found:
            raise _wallet_invalid("tnsnames.ora가 없습니다.")
        if "ewallet.pem" not in files_found and "cwallet.sso" not in files_found:
            raise _wallet_invalid("ewallet.pem 또는 cwallet.sso가 없습니다.")

        tns_text = (wallet_dir / "tnsnames.ora").read_text(encoding="utf-8")
        tns_aliases = parse_tns_aliases(tns_text)
        if not tns_aliases:
            raise _wallet_invalid("tnsnames.ora에서 TNS alias를 찾지 못했습니다.")
    except BaseException:
        shutil.rmtree(wallet_dir, ignore_errors=True)  # 실패 잔존물 제거
        raise

    record: dict[str, Any] = {
        "id": wallet_id,
        "source": source,                      # upload | generate
        "tns_aliases": tns_aliases,
        "files_found": files_found,
        "adb_ocid": adb_ocid,
        # wallet 암호는 Fernet 암호화 저장 — 평문 금지 (security.md §2.1)
        "wallet_password_enc": encrypt_secret(wallet_password) if wallet_password else None,
        "created_at": _now_iso(),
    }

    def _mutate(doc: dict[str, Any]) -> dict[str, Any]:
        doc["wallets"].append(record)
        return doc

    await local_store.update_connections_doc(_mutate)

    # 생성 리소스 ledger 기록 (FR-10 / architecture.md §3.3.1)
    await local_store.append_resource(
        {
            "id": f"led_{uuid.uuid4().hex}",
            "connection_id": "",
            "resource_type": "wallet",
            "resource_name": wallet_id,
            "owner": None,
            "create_sql": f"wallet 해제본 저장: ~/.selectai/wallets/{wallet_id}/ ({source})",
            "cleanup_sql": f"wallet 디렉토리 삭제: ~/.selectai/wallets/{wallet_id}/",
            "cleanup_order": 95,
            "cleanup_status": "pending",
            "cleanup_preview": f"wallet 디렉토리 삭제: ~/.selectai/wallets/{wallet_id}/",
            "created_at": _now_iso(),
            "cleaned_at": None,
            "last_error": None,
        }
    )
    return record


async def upload_wallet(
    zip_bytes: bytes, wallet_password: str | None = None
) -> WalletUploadResult:
    """§2.1 wallet zip 업로드 — 검증 후 wallet_id + alias 목록 반환.

    wallet_password는 암호화된 ewallet.pem(thin 모드 mTLS) 해제에 필요하며,
    Fernet 암호화되어 wallet 레코드에 저장된다 (security.md §2.1).
    """
    record = await _register_wallet(
        zip_bytes, source="upload", wallet_password=wallet_password
    )
    return WalletUploadResult(
        wallet_id=record["id"],
        tns_aliases=record["tns_aliases"],
        files_found=record["files_found"],
    )


# ---------------------------------------------------------------- wallet 자동 다운로드 (OCI CLI)


def _display_cmd(args: list[str]) -> str:
    """CLI 명령 원문(표시용) — --password 값은 마스킹 (api-spec §2.7)."""
    return mask_secrets(" ".join(args))


async def _run_oci_cli(
    args: list[str], timeout_s: float, executed: list[str]
) -> tuple[int, str, str]:
    """OCI CLI 비차단 실행 — (returncode, stdout, stderr). 명령 원문은 마스킹 후 누적."""
    executed.append(_display_cmd(args))
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise _oci_cli_not_found(executed) from exc
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except (TimeoutError, asyncio.TimeoutError) as exc:
        proc.kill()
        raise AppError(
            status_code=504,
            code="OCI_CLI_TIMEOUT",
            app_code="OCI_CLI_TIMEOUT",
            message_ko="OCI CLI 호출이 제한 시간을 초과했습니다.",
            hint_ko="네트워크 상태를 확인하고 다시 시도하세요.",
            retryable=True,
            executed_sql=list(executed),
        ) from exc
    return proc.returncode or 0, stdout.decode(errors="replace"), stderr.decode(errors="replace")


def _oci_cli_not_found(executed: list[str]) -> AppError:
    return AppError(
        status_code=424,
        code="OCI_CLI_NOT_FOUND",
        app_code="OCI_CLI_NOT_FOUND",
        message_ko="OCI CLI가 설치되어 있지 않습니다. 수동 업로드를 이용하거나 설치 가이드를 참조하세요.",
        hint_ko="wallet zip 업로드 경로(POST /connections/wallet)로 진행할 수 있습니다.",
        executed_sql=list(executed),
    )


def _raise_oci_cli_failure(stderr: str, executed: list[str]) -> None:
    """CLI 비정상 종료 → 인증 실패(401) 또는 일반 오류(502) 변환."""
    masked = mask_secrets(stderr.strip())
    if any(marker in stderr for marker in _OCI_AUTH_ERROR_MARKERS):
        raise AppError(
            status_code=401,
            code="OCI_CLI_AUTH_FAILED",
            app_code="OCI_CLI_AUTH_FAILED",
            message_ko="OCI CLI 인증에 실패했습니다 (~/.oci/config 확인 필요).",
            hint_ko="OCI CLI 인증은 앱이 관리하지 않습니다. 수동 wallet 업로드로 진행하세요.",
            detail=masked,
            executed_sql=list(executed),
        )
    raise AppError(
        status_code=502,
        code="OCI_CLI_ERROR",
        app_code="OCI_CLI_ERROR",
        message_ko="OCI CLI 호출이 실패했습니다.",
        hint_ko="OCI CLI 출력 원문(detail)을 확인하세요.",
        detail=masked,
        executed_sql=list(executed),
    )


async def _resolve_adb_ocid(
    req: WalletGenerateRequest, executed: list[str]
) -> str:
    """① ADB OCID 조회 — 0건 404 / 복수 건 409 candidates (api-spec §2.7)."""
    args = [
        "oci", "db", "autonomous-database", "list",
        "--compartment-id", req.compartment_id,
        "--display-name", req.adb_name,
        "--lifecycle-state", "AVAILABLE",
        "--profile", req.oci_profile,
    ]
    code, stdout, stderr = await _run_oci_cli(args, timeout_s=30, executed=executed)
    if code != 0:
        _raise_oci_cli_failure(stderr, executed)

    items: list[dict[str, Any]] = []
    if stdout.strip():
        try:
            items = json.loads(stdout).get("data", [])
        except json.JSONDecodeError:
            _raise_oci_cli_failure(stdout, executed)

    if not items:
        raise AppError(
            status_code=404,
            code="ADB_NOT_FOUND",
            app_code="ADB_NOT_FOUND",
            message_ko="해당 이름의 AVAILABLE 상태 ADB를 찾을 수 없습니다. "
            "컴파트먼트와 표시 이름을 확인하세요.",
            executed_sql=list(executed),
        )
    if len(items) > 1:
        candidates = [
            AdbCandidate(
                adb_ocid=item.get("id", ""),
                display_name=item.get("display-name", req.adb_name),
                workload_type=item.get("db-workload"),
            ).model_dump()
            for item in items
        ]
        raise AppError(
            status_code=409,
            code="ADB_AMBIGUOUS",
            app_code="ADB_AMBIGUOUS",
            message_ko="같은 이름의 ADB가 여러 개 발견되었습니다. 목록에서 하나를 선택하세요.",
            hint_ko="선택한 항목의 adb_ocid를 지정해 다시 요청하세요.",
            retryable=True,
            executed_sql=list(executed),
            extra={"candidates": candidates},
        )
    return items[0]["id"]


async def generate_wallet(
    req: WalletGenerateRequest,
) -> tuple[WalletGenerateResult, list[str]]:
    """§2.7 wallet 자동 다운로드 — OCI CLI 2단계 후 업로드 경로와 합류.

    반환: (결과, executed_sql용 CLI 명령 목록 — --password 마스킹 완료).
    """
    executed: list[str] = []
    if shutil.which("oci") is None:
        raise _oci_cli_not_found(executed)

    adb_ocid = req.adb_ocid or await _resolve_adb_ocid(req, executed)

    # ② wallet 다운로드 — 앱 전용 임시 디렉토리 사용 (OS 공용 tmp 금지, security.md §2.1)
    tmp_dir = local_store.wallets_dir() / f".dl_{uuid.uuid4().hex[:8]}"
    tmp_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    zip_path = tmp_dir / "wallet.zip"
    try:
        args = [
            "oci", "db", "autonomous-database", "generate-wallet",
            "--autonomous-database-id", adb_ocid,
            "--file", str(zip_path),
            "--password", req.wallet_password,
            "--profile", req.oci_profile,
        ]
        code, _stdout, stderr = await _run_oci_cli(args, timeout_s=120, executed=executed)
        if code != 0:
            _raise_oci_cli_failure(stderr, executed)
        if not zip_path.exists():
            _raise_oci_cli_failure("wallet.zip이 생성되지 않았습니다.", executed)

        zip_bytes = zip_path.read_bytes()
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)  # 평문 zip 즉시 삭제 (§2.1)

    record = await _register_wallet(
        zip_bytes,
        source="generate",
        wallet_password=req.wallet_password,
        adb_ocid=adb_ocid,
    )
    result = WalletGenerateResult(
        wallet_id=record["id"],
        tns_aliases=record["tns_aliases"],
        files_found=record["files_found"],
        adb_ocid=adb_ocid,
    )
    return result, executed


# ---------------------------------------------------------------- 접속 검증/테스트


async def _validate_connect(
    *,
    username: str,
    password: str,
    tns_alias: str,
    wallet_dir: str,
    wallet_password: str | None,
    recorder: oracle.SqlRecorder,
    call_timeout_ms: int = pool_registry.CALL_TIMEOUT_DEFAULT_MS,
    tcp_connect_timeout: float = 10.0,
) -> tuple[str | None, str | None]:
    """단건 접속 후 (db_version, db_name) 조회 — 커넥션 생성/수정 검증 (api-spec §2.2).

    테스트에서 monkeypatch 대상이 되는 단일 진입점.
    """
    kwargs = pool_registry.build_connect_kwargs(
        username=username,
        password=password,
        tns_alias=tns_alias,
        wallet_dir=wallet_dir,
        wallet_password=wallet_password,
    )
    conn = await oracledb.connect_async(tcp_connect_timeout=tcp_connect_timeout, **kwargs)
    try:
        conn.call_timeout = call_timeout_ms
        db_version = await oracle.fetch_value(conn, SQL_DB_VERSION, recorder=recorder)
        meta = await oracle.fetch_one(conn, SQL_INSTANCE_META, recorder=recorder)
        db_name = meta[1] if meta else None
        return db_version, db_name
    finally:
        await conn.close()


async def _load_wallet_or_404(wallet_id: str) -> dict[str, Any]:
    wallet = await local_store.get_wallet_record(wallet_id)
    if wallet is None:
        raise AppError(
            status_code=404,
            code="WALLET_NOT_FOUND",
            app_code="WALLET_NOT_FOUND",
            message_ko="지정한 wallet_id를 찾을 수 없습니다.",
            hint_ko="wallet을 먼저 업로드(또는 자동 다운로드)하세요.",
        )
    return wallet


def _wallet_password_of(wallet: dict[str, Any]) -> str | None:
    enc = wallet.get("wallet_password_enc")
    return decrypt_secret(enc) if enc else None


async def _persist_wallet_password(wallet_id: str, wallet_password: str) -> None:
    """wallet 레코드에 wallet 암호를 Fernet 암호화 저장 (security.md §2.1 — 평문 금지)."""
    enc = encrypt_secret(wallet_password)

    def _mutate(doc: dict[str, Any]) -> dict[str, Any]:
        for w in doc.get("wallets", []):
            if w["id"] == wallet_id:
                w["wallet_password_enc"] = enc
        return doc

    await local_store.update_connections_doc(_mutate)


def _check_alias(wallet: dict[str, Any], tns_alias: str) -> None:
    if tns_alias.lower() not in [a.lower() for a in wallet.get("tns_aliases", [])]:
        raise AppError(
            status_code=400,
            code="TNS_ALIAS_INVALID",
            app_code="TNS_ALIAS_INVALID",
            message_ko="지정한 TNS alias가 wallet의 tnsnames.ora에 없습니다.",
            hint_ko=f"사용 가능한 alias: {', '.join(wallet.get('tns_aliases', []))}",
        )


# ---------------------------------------------------------------- 커넥션 CRUD


async def create_connection(
    body: ConnectionCreate,
) -> tuple[ConnectionOut, list[str]]:
    """§2.2 커넥션 생성 — validate=true면 즉시 접속 검증 후 Fernet 암호화 저장."""
    if body.username.lower() != "admin":  # v1: admin 고정 (스키마 Literal의 방어적 재확인)
        raise AppError(
            status_code=400,
            code="ADMIN_ONLY",
            app_code="ADMIN_ONLY",
            message_ko="v1에서는 admin 사용자만 지원합니다.",
        )

    doc = await local_store.load_connections_doc()
    if any(r["name"] == body.name for r in doc["connections"]):
        raise AppError(
            status_code=409,
            code="CONNECTION_NAME_EXISTS",
            app_code="CONNECTION_NAME_EXISTS",
            message_ko="같은 이름의 커넥션이 이미 있습니다.",
            hint_ko="다른 이름을 사용하거나 기존 커넥션을 수정하세요.",
        )
    wallet = await _load_wallet_or_404(body.wallet_id)
    _check_alias(wallet, body.tns_alias)

    # wallet 암호가 생성 단계에서 입력되면 wallet 레코드에 영속화(Fernet) — 재접속·풀 재생성에 재사용.
    if body.wallet_password:
        await _persist_wallet_password(body.wallet_id, body.wallet_password)
        effective_wallet_password: str | None = body.wallet_password
    else:
        effective_wallet_password = _wallet_password_of(wallet)

    recorder = oracle.SqlRecorder()
    db_version: str | None = None
    db_name: str | None = None
    status = "UNKNOWN"
    if body.validate_:
        try:
            db_version, db_name = await _validate_connect(
                username="ADMIN",
                password=body.password,
                tns_alias=body.tns_alias,
                wallet_dir=str(local_store.wallets_dir() / body.wallet_id),
                wallet_password=effective_wallet_password,
                recorder=recorder,
            )
        except oracledb.Error as exc:
            raise map_oracle_error(str(exc), recorder.statements) from exc
        status = "VALID"

    record: dict[str, Any] = {
        "id": _new_id("conn"),
        "name": body.name,
        "wallet_id": body.wallet_id,
        "tns_alias": body.tns_alias,
        "username": "ADMIN",
        "password_enc": encrypt_secret(body.password),  # 평문 저장 금지 (R5)
        "db_version": db_version,
        "db_name": db_name,
        "status": status,
        "last_used_at": None,
        "created_at": _now_iso(),
    }

    def _mutate(doc: dict[str, Any]) -> dict[str, Any]:
        doc["connections"].append(record)
        return doc

    await local_store.update_connections_doc(_mutate)
    await local_store.append_resource(
        {
            "id": f"led_{uuid.uuid4().hex}",
            "connection_id": record["id"],
            "resource_type": "connection",
            "resource_name": record["name"],
            "owner": None,
            "create_sql": f"커넥션 등록: {record['name']} ({record['tns_alias']})",
            "cleanup_sql": f"커넥션 삭제: DELETE /api/v1/connections/{record['id']}",
            "cleanup_order": 90,
            "cleanup_status": "pending",
            "cleanup_preview": f"커넥션 메타/자격 삭제: {record['name']}",
            "created_at": _now_iso(),
            "cleaned_at": None,
            "last_error": None,
        }
    )
    return _record_to_out(record), recorder.statements


async def list_connections() -> list[ConnectionOut]:
    """§2.3 목록 — last_used_at 내림차순 (None은 뒤로). 비밀 필드 미포함."""
    doc = await local_store.load_connections_doc()
    records = sorted(
        doc["connections"],
        key=lambda r: (r.get("last_used_at") is None, r.get("last_used_at") or ""),
        reverse=False,
    )
    # last_used_at 있는 항목을 최신순으로 — 문자열 ISO 정렬 후 뒤집기
    with_used = [r for r in records if r.get("last_used_at")]
    without_used = [r for r in records if not r.get("last_used_at")]
    with_used.sort(key=lambda r: r["last_used_at"], reverse=True)
    return [_record_to_out(r) for r in with_used + without_used]


async def test_connection(
    connection_id: str,
) -> tuple[ConnectionTestResult, list[str]]:
    """§2.4 연결 테스트 — 5초 타임아웃, 실패도 200으로 진단 결과 반환."""
    record = await local_store.get_connection_record(connection_id)
    if record is None:
        raise _connection_not_found()
    wallet = await _load_wallet_or_404(record["wallet_id"])

    recorder = oracle.SqlRecorder()
    recorder.record(SQL_PING)
    started = asyncio.get_running_loop().time()
    try:
        db_version, _db_name = await _validate_connect(
            username=record["username"],
            password=decrypt_secret(record["password_enc"]),
            tns_alias=record["tns_alias"],
            wallet_dir=str(local_store.wallets_dir() / record["wallet_id"]),
            wallet_password=_wallet_password_of(wallet),
            recorder=recorder,
            call_timeout_ms=pool_registry.CALL_TIMEOUT_TEST_MS,
            tcp_connect_timeout=5.0,  # FR-02 수용 기준 — 5초
        )
    except (oracledb.Error, AppError) as exc:
        mapped = exc if isinstance(exc, AppError) else map_oracle_error(str(exc))
        await _set_status(connection_id, "INVALID")
        result = ConnectionTestResult(
            ok=False,
            app_code=mapped.app_code,
            message_ko=mapped.message_ko,
            hint_ko=mapped.hint_ko,
        )
        return result, recorder.statements

    latency_ms = int((asyncio.get_running_loop().time() - started) * 1000)
    await _set_status(connection_id, "VALID", touch=True)
    return (
        ConnectionTestResult(ok=True, db_version=db_version, latency_ms=latency_ms),
        recorder.statements,
    )


async def _set_status(connection_id: str, status: str, touch: bool = False) -> None:
    """커넥션 status(/last_used_at) 갱신."""

    def _mutate(doc: dict[str, Any]) -> dict[str, Any]:
        for record in doc["connections"]:
            if record["id"] == connection_id:
                record["status"] = status
                if touch:
                    record["last_used_at"] = _now_iso()
                break
        return doc

    await local_store.update_connections_doc(_mutate)


async def update_connection(
    connection_id: str, body: ConnectionUpdate
) -> tuple[ConnectionOut, list[str]]:
    """§2.6 수정 — 비밀번호/alias 변경 시 재검증 후 풀 재생성."""
    doc = await local_store.load_connections_doc()
    record = next((r for r in doc["connections"] if r["id"] == connection_id), None)
    if record is None:
        raise _connection_not_found()

    if body.name and body.name != record["name"]:
        if any(r["name"] == body.name for r in doc["connections"] if r["id"] != connection_id):
            raise AppError(
                status_code=409,
                code="CONNECTION_NAME_EXISTS",
                app_code="CONNECTION_NAME_EXISTS",
                message_ko="같은 이름의 커넥션이 이미 있습니다.",
            )

    wallet = await _load_wallet_or_404(record["wallet_id"])
    new_alias = body.tns_alias or record["tns_alias"]
    _check_alias(wallet, new_alias)
    new_password = body.password or decrypt_secret(record["password_enc"])

    recorder = oracle.SqlRecorder()
    revalidate = body.password is not None or (
        body.tns_alias is not None and body.tns_alias != record["tns_alias"]
    )
    db_version, db_name = record.get("db_version"), record.get("db_name")
    status = record.get("status", "UNKNOWN")
    if revalidate:
        try:
            db_version, db_name = await _validate_connect(
                username=record["username"],
                password=new_password,
                tns_alias=new_alias,
                wallet_dir=str(local_store.wallets_dir() / record["wallet_id"]),
                wallet_password=_wallet_password_of(wallet),
                recorder=recorder,
            )
        except oracledb.Error as exc:
            raise map_oracle_error(str(exc), recorder.statements) from exc
        status = "VALID"
        await pool_registry.close_pool(connection_id)  # 새 자격으로 lazy 재생성

    updated: dict[str, Any] = {}

    def _mutate(doc: dict[str, Any]) -> dict[str, Any]:
        nonlocal updated
        for r in doc["connections"]:
            if r["id"] == connection_id:
                if body.name:
                    r["name"] = body.name
                r["tns_alias"] = new_alias
                if body.password is not None:
                    r["password_enc"] = encrypt_secret(body.password)
                r["db_version"] = db_version
                r["db_name"] = db_name
                r["status"] = status
                updated = r
                break
        return doc

    await local_store.update_connections_doc(_mutate)
    return _record_to_out(updated), recorder.statements


async def delete_connection(connection_id: str) -> None:
    """§2.5 삭제 — 풀 종료 → 자격/메타 삭제 → wallet은 참조 없을 때만 삭제."""
    record = await local_store.get_connection_record(connection_id)
    if record is None:
        raise _connection_not_found()

    await pool_registry.close_pool(connection_id)
    wallet_id = record["wallet_id"]
    wallet_orphaned = False

    def _mutate(doc: dict[str, Any]) -> dict[str, Any]:
        nonlocal wallet_orphaned
        doc["connections"] = [r for r in doc["connections"] if r["id"] != connection_id]
        still_referenced = any(r["wallet_id"] == wallet_id for r in doc["connections"])
        if not still_referenced:
            doc["wallets"] = [w for w in doc["wallets"] if w["id"] != wallet_id]
            wallet_orphaned = True
        return doc

    await local_store.update_connections_doc(_mutate)
    if wallet_orphaned:
        # 해제본·자격 일괄 제거 (security.md §2.4)
        shutil.rmtree(local_store.wallets_dir() / wallet_id, ignore_errors=True)
