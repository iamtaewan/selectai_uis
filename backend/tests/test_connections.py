"""커넥션/DB 인프라 단위 테스트 — local_store·crypto·connection_service·라우터.

실제 ADB에 접속하지 않는다 — _validate_connect/OCI CLI는 monkeypatch (architecture.md §6.1).
"""
from __future__ import annotations

import io
import json
import stat
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.db import local_store
from app.errors import AppError
from app.security import crypto
from app.services import connection_service

TNSNAMES = """\
demoadb_high = (description=(address=(protocol=tcps)(port=1522)(host=adb.example.com))(connect_data=(service_name=xx_demoadb_high.adb.oraclecloud.com)))
demoadb_low = (description=(address=(protocol=tcps)(port=1522)(host=adb.example.com))(connect_data=(service_name=xx_demoadb_low.adb.oraclecloud.com)))
"""


def make_wallet_zip(*, include_tns: bool = True, include_pem: bool = True) -> bytes:
    """테스트용 wallet zip 바이트 생성."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        if include_tns:
            zf.writestr("tnsnames.ora", TNSNAMES)
        if include_pem:
            zf.writestr("ewallet.pem", "-----BEGIN ...-----")
        zf.writestr("sqlnet.ora", "WALLET_LOCATION=...")
    return buf.getvalue()


def upload_wallet(client: TestClient) -> dict:
    """wallet 업로드 헬퍼 — data 페이로드 반환."""
    res = client.post(
        "/api/v1/connections/wallet",
        files={"file": ("wallet.zip", make_wallet_zip(), "application/zip")},
    )
    assert res.status_code == 200, res.text
    return res.json()["data"]


@pytest.fixture
def fake_validate(monkeypatch):
    """_validate_connect를 성공 응답으로 대체 (DB 미접속)."""

    async def _fake(**kwargs):
        recorder = kwargs.get("recorder")
        if recorder is not None:
            recorder.record(connection_service.SQL_DB_VERSION)
            recorder.record(connection_service.SQL_INSTANCE_META)
        return "Oracle AI Database 26ai", "DEMOADB"

    monkeypatch.setattr(connection_service, "_validate_connect", _fake)
    return _fake


def create_connection(client: TestClient, name: str = "데모 ADB") -> dict:
    """wallet 업로드 + 커넥션 생성 헬퍼 — data 페이로드 반환."""
    wallet = upload_wallet(client)
    res = client.post(
        "/api/v1/connections",
        json={
            "name": name,
            "wallet_id": wallet["wallet_id"],
            "tns_alias": "demoadb_high",
            "username": "admin",
            "password": "Secret#123",
            "validate": True,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["data"]


# ---------------------------------------------------------------- local_store


async def test_local_store_atomic_write_and_permissions(tmp_app_data_dir):
    """원자적 쓰기 + 파일 0600/디렉토리 0700 보장."""
    await local_store.write_json(local_store.SETTINGS_FILE, {"k": "v"})
    path = tmp_app_data_dir / local_store.SETTINGS_FILE
    assert json.loads(path.read_text()) == {"k": "v"}
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert stat.S_IMODE(tmp_app_data_dir.stat().st_mode) == 0o700
    # 임시 파일 잔존물 없음
    assert not list(tmp_app_data_dir.glob("*.tmp"))


async def test_local_store_defaults_and_default_arg(tmp_app_data_dir):
    """파일 없을 때 — 파일별 기본 구조 / 호출자 지정 default 지원."""
    doc = await local_store.load_connections_doc()
    assert doc == {"connections": [], "wallets": []}
    assert await local_store.read_json("settings.json", {"x": 1}) == {"x": 1}
    assert await local_store.read_json(local_store.RESOURCES_FILE) == []


# ---------------------------------------------------------------- crypto


def test_crypto_roundtrip_and_keyfile(tmp_app_data_dir):
    """Fernet 암복호화 + secret.key 자동 생성(0600)."""
    token = crypto.encrypt_secret("p@ssw0rd")
    assert token != "p@ssw0rd"
    assert crypto.decrypt_secret(token) == "p@ssw0rd"
    key_path = tmp_app_data_dir / "secret.key"
    assert key_path.exists()
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600


def test_crypto_decrypt_mismatch_is_app_error(tmp_app_data_dir):
    """키 불일치 토큰 → SECRET_KEY_MISMATCH AppError (평문 폴백 금지)."""
    with pytest.raises(AppError) as exc_info:
        crypto.decrypt_secret("gAAAAA" + "x" * 60)
    assert exc_info.value.app_code == "SECRET_KEY_MISMATCH"


@pytest.mark.parametrize(
    "text",
    [
        "oci db autonomous-database generate-wallet --password Hunter2!",
        '{"password": "Hunter2!"}',
        "wallet_password => 'Hunter2!'",
        "private_key=Hunter2!",
        "api_token: Hunter2!",
    ],
)
def test_mask_secrets_patterns(text):
    """비밀 키 이름/--password/Fernet 토큰 마스킹 (security.md §2.3)."""
    masked = crypto.mask_secrets(text)
    assert "Hunter2!" not in masked
    assert crypto.MASK in masked


def test_mask_secrets_fernet_token(tmp_app_data_dir):
    token = crypto.encrypt_secret("secret")
    assert token not in crypto.mask_secrets(f"saved enc {token}")


# ---------------------------------------------------------------- wallet 업로드


def test_upload_wallet_ok(client: TestClient, tmp_app_data_dir):
    data = upload_wallet(client)
    assert data["tns_aliases"] == ["demoadb_high", "demoadb_low"]
    assert "tnsnames.ora" in data["files_found"]
    wallet_dir = tmp_app_data_dir / "wallets" / data["wallet_id"]
    assert (wallet_dir / "tnsnames.ora").exists()
    assert stat.S_IMODE(wallet_dir.stat().st_mode) == 0o700


def test_upload_wallet_not_a_zip(client: TestClient, tmp_app_data_dir):
    res = client.post(
        "/api/v1/connections/wallet",
        files={"file": ("wallet.zip", b"not-a-zip", "application/zip")},
    )
    assert res.status_code == 400
    assert res.json()["error"]["app_code"] == "WALLET_INVALID"


def test_upload_wallet_missing_tnsnames(client: TestClient, tmp_app_data_dir):
    res = client.post(
        "/api/v1/connections/wallet",
        files={"file": ("wallet.zip", make_wallet_zip(include_tns=False), "application/zip")},
    )
    assert res.status_code == 400
    assert res.json()["error"]["app_code"] == "WALLET_INVALID"
    # 실패 잔존물 없음
    assert list((tmp_app_data_dir / "wallets").glob("wlt_*")) == []


def test_upload_wallet_too_large(client: TestClient, tmp_app_data_dir):
    res = client.post(
        "/api/v1/connections/wallet",
        files={"file": ("wallet.zip", b"0" * (5 * 1024 * 1024 + 1), "application/zip")},
    )
    assert res.status_code == 413
    assert res.json()["error"]["app_code"] == "FILE_TOO_LARGE"


# ---------------------------------------------------------------- wallet 자동 다운로드


def test_generate_wallet_cli_not_found(client: TestClient, tmp_app_data_dir, monkeypatch):
    """OCI CLI 미설치 → 424 OCI_CLI_NOT_FOUND (api-spec §2.7)."""
    monkeypatch.setattr(connection_service.shutil, "which", lambda _: None)
    res = client.post(
        "/api/v1/connections/wallet/generate",
        json={"adb_name": "DEMOADB", "wallet_password": "Wpw#12345"},
    )
    assert res.status_code == 424
    assert res.json()["error"]["app_code"] == "OCI_CLI_NOT_FOUND"


def test_display_cmd_masks_password():
    """CLI 명령 표시 문자열의 --password 값 마스킹 (R5)."""
    cmd = connection_service._display_cmd(
        ["oci", "db", "autonomous-database", "generate-wallet", "--password", "Wpw#12345"]
    )
    assert "Wpw#12345" not in cmd
    assert "***MASKED***" in cmd


# ---------------------------------------------------------------- 커넥션 CRUD


def test_create_connection_ok(client: TestClient, tmp_app_data_dir, fake_validate):
    body = None
    wallet = upload_wallet(client)
    res = client.post(
        "/api/v1/connections",
        json={
            "name": "데모 ADB",
            "wallet_id": wallet["wallet_id"],
            "tns_alias": "demoadb_high",
            "username": "admin",
            "password": "Secret#123",
            "validate": True,
        },
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["data"]["status"] == "VALID"
    assert body["data"]["db_name"] == "DEMOADB"
    assert body["data"]["username"] == "ADMIN"
    # envelope — 검증 SQL 노출 + elapsed_ms (api-spec §1.3)
    assert connection_service.SQL_DB_VERSION in body["executed_sql"][0]
    assert "elapsed_ms" in body
    # 응답·저장 파일 어디에도 평문 비밀번호 금지 (R5)
    assert "Secret#123" not in res.text
    stored = (tmp_app_data_dir / "connections.json").read_text()
    assert "Secret#123" not in stored
    assert json.loads(stored)["connections"][0]["password_enc"].startswith("gAAAA")


def test_create_connection_duplicate_name(client: TestClient, tmp_app_data_dir, fake_validate):
    created = create_connection(client, name="중복")
    wallet_id = json.loads((tmp_app_data_dir / "connections.json").read_text())[
        "connections"
    ][0]["wallet_id"]
    res = client.post(
        "/api/v1/connections",
        json={
            "name": "중복",
            "wallet_id": wallet_id,
            "tns_alias": "demoadb_high",
            "password": "Secret#123",
        },
    )
    assert created["name"] == "중복"
    assert res.status_code == 409
    assert res.json()["error"]["app_code"] == "CONNECTION_NAME_EXISTS"


def test_create_connection_bad_alias(client: TestClient, tmp_app_data_dir, fake_validate):
    wallet = upload_wallet(client)
    res = client.post(
        "/api/v1/connections",
        json={
            "name": "잘못된 alias",
            "wallet_id": wallet["wallet_id"],
            "tns_alias": "nope_high",
            "password": "Secret#123",
        },
    )
    assert res.status_code == 400
    assert res.json()["error"]["app_code"] == "TNS_ALIAS_INVALID"


def test_list_connections(client: TestClient, tmp_app_data_dir, fake_validate):
    create_connection(client, name="첫째")
    res = client.get("/api/v1/connections")
    assert res.status_code == 200
    data = res.json()["data"]
    assert [c["name"] for c in data] == ["첫째"]
    assert "password" not in res.text and "password_enc" not in res.text


def test_test_connection_failure_returns_200(
    client: TestClient, tmp_app_data_dir, fake_validate, monkeypatch
):
    """§2.4 — 접속 실패도 200 + ok=false 진단 (테스트 행위 자체는 성공)."""
    created = create_connection(client)

    async def _fail(**kwargs):
        import oracledb

        raise oracledb.OperationalError("DPY-6005: cannot connect to database")

    monkeypatch.setattr(connection_service, "_validate_connect", _fail)
    res = client.post(f"/api/v1/connections/{created['id']}/test")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["ok"] is False
    assert data["app_code"] == "DB_UNREACHABLE"
    # 상태가 INVALID로 갱신
    assert client.get("/api/v1/connections").json()["data"][0]["status"] == "INVALID"


def test_test_connection_ok(client: TestClient, tmp_app_data_dir, fake_validate):
    created = create_connection(client)
    res = client.post(f"/api/v1/connections/{created['id']}/test")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["ok"] is True
    assert data["db_version"] == "Oracle AI Database 26ai"
    assert data["latency_ms"] is not None


def test_test_connection_not_found(client: TestClient, tmp_app_data_dir):
    res = client.post("/api/v1/connections/conn_none/test")
    assert res.status_code == 404
    assert res.json()["error"]["app_code"] == "CONNECTION_NOT_FOUND"


def test_update_connection_rename(client: TestClient, tmp_app_data_dir, fake_validate):
    created = create_connection(client, name="이전 이름")
    res = client.patch(
        f"/api/v1/connections/{created['id']}", json={"name": "새 이름"}
    )
    assert res.status_code == 200
    assert res.json()["data"]["name"] == "새 이름"
    # 이름만 변경 — 재검증 SQL 없음
    assert res.json()["executed_sql"] == []


def test_update_connection_password_revalidates(
    client: TestClient, tmp_app_data_dir, fake_validate
):
    created = create_connection(client)
    res = client.patch(
        f"/api/v1/connections/{created['id']}", json={"password": "NewSecret#456"}
    )
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "VALID"
    assert len(res.json()["executed_sql"]) == 2  # 재검증 SQL 2건
    assert "NewSecret#456" not in (tmp_app_data_dir / "connections.json").read_text()


def test_delete_connection_removes_orphan_wallet(
    client: TestClient, tmp_app_data_dir, fake_validate
):
    created = create_connection(client)
    doc = json.loads((tmp_app_data_dir / "connections.json").read_text())
    wallet_id = doc["connections"][0]["wallet_id"]
    res = client.delete(f"/api/v1/connections/{created['id']}")
    assert res.status_code == 204
    doc = json.loads((tmp_app_data_dir / "connections.json").read_text())
    assert doc["connections"] == [] and doc["wallets"] == []
    assert not (tmp_app_data_dir / "wallets" / wallet_id).exists()
    # 재삭제 → 404
    assert client.delete(f"/api/v1/connections/{created['id']}").status_code == 404
