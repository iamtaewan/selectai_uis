"""JSON 파일 저장소 — ~/.selectai/{connections,settings,resources}.json.

architecture.md §3.3: 임시 파일 작성 후 os.replace 원자적 교체 + 파일별
asyncio.Lock. 디렉토리 0700, 파일 0600. SQLite 미사용 — JSON 파일 저장소만.

파일 포맷:
- connections.json: {"connections": [...], "wallets": [...]}  (커넥션 메타 + wallet 메타)
- settings.json:    {...}                                      (앱 설정 dict)
- resources.json:   [...]                                      (생성 리소스 ledger 배열, §3.3.1)
"""
from __future__ import annotations

import asyncio
import copy
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable

from app.config import get_settings

CONNECTIONS_FILE = "connections.json"
SETTINGS_FILE = "settings.json"
RESOURCES_FILE = "resources.json"

# 파일별 기본값 — 파일이 없을 때 read가 돌려주는 초기 구조
_DEFAULTS: dict[str, Any] = {
    CONNECTIONS_FILE: {"connections": [], "wallets": []},
    SETTINGS_FILE: {},
    RESOURCES_FILE: [],
}

# 파일별 asyncio.Lock — Lock은 이벤트 루프에 바인딩되므로 (loop id, 파일명)으로 키잉
# (TestClient처럼 요청마다 루프가 바뀌는 환경에서도 안전)
_locks: dict[tuple[int, str], asyncio.Lock] = {}


def _lock_for(filename: str) -> asyncio.Lock:
    """현재 이벤트 루프 기준 파일별 Lock을 반환한다 (lazy 생성)."""
    loop_id = id(asyncio.get_running_loop())
    key = (loop_id, filename)
    lock = _locks.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _locks[key] = lock
    return lock


def ensure_data_dir() -> Path:
    """앱 데이터 디렉토리(0700)와 wallets/ 하위 디렉토리(0700)를 보장한다."""
    data_dir = get_settings().data_dir
    data_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(data_dir, 0o700)
    wallets_dir = data_dir / "wallets"
    wallets_dir.mkdir(mode=0o700, exist_ok=True)
    os.chmod(wallets_dir, 0o700)
    return data_dir


def wallets_dir() -> Path:
    """wallet 해제본 보관 루트 — ~/.selectai/wallets/."""
    return ensure_data_dir() / "wallets"


def _file_path(filename: str) -> Path:
    return ensure_data_dir() / filename


def _read_sync(filename: str, default: Any = None) -> Any:
    """파일을 읽어 JSON 파싱. 없으면 default(미지정 시 파일별 기본 구조)의 깊은 복사본."""
    path = _file_path(filename)
    if not path.exists():
        if default is not None:
            return copy.deepcopy(default)
        return copy.deepcopy(_DEFAULTS.get(filename))
    with open(path, encoding="utf-8") as fp:
        return json.load(fp)


def _write_sync(filename: str, data: Any) -> None:
    """임시 파일 작성 → fsync → os.replace 원자적 교체. 파일 권한 0600."""
    path = _file_path(filename)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{filename}.", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fp:
            json.dump(data, fp, ensure_ascii=False, indent=2, default=str)
            fp.flush()
            os.fsync(fp.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, path)
    except BaseException:
        # 교체 실패 시 임시 파일 잔존 방지
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise


async def read_json(filename: str, default: Any = None) -> Any:
    """파일별 Lock 하에 JSON 읽기 — 파일 없으면 default(또는 파일별 기본 구조)."""
    async with _lock_for(filename):
        return _read_sync(filename, default)


async def write_json(filename: str, data: Any) -> None:
    """파일별 Lock 하에 원자적 JSON 쓰기."""
    async with _lock_for(filename):
        _write_sync(filename, data)


async def update_json(filename: str, mutator: Callable[[Any], Any]) -> Any:
    """Lock 하에 read-modify-write 원자 수행. mutator가 반환한 값을 저장·반환한다."""
    async with _lock_for(filename):
        data = _read_sync(filename)
        updated = mutator(data)
        _write_sync(filename, updated)
        return updated


# ---------------------------------------------------------------- 파일별 CRUD 헬퍼


async def load_connections_doc() -> dict[str, Any]:
    """connections.json 문서 전체 — {"connections": [...], "wallets": [...]}."""
    doc = await read_json(CONNECTIONS_FILE)
    doc.setdefault("connections", [])
    doc.setdefault("wallets", [])
    return doc


async def save_connections_doc(doc: dict[str, Any]) -> None:
    await write_json(CONNECTIONS_FILE, doc)


async def get_connection_record(connection_id: str) -> dict[str, Any] | None:
    """커넥션 레코드 단건 조회 (없으면 None)."""
    doc = await load_connections_doc()
    for record in doc["connections"]:
        if record.get("id") == connection_id:
            return record
    return None


async def get_wallet_record(wallet_id: str) -> dict[str, Any] | None:
    """wallet 메타 레코드 단건 조회 (없으면 None)."""
    doc = await load_connections_doc()
    for record in doc["wallets"]:
        if record.get("id") == wallet_id:
            return record
    return None


async def update_connections_doc(
    mutator: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    """connections.json 원자적 read-modify-write."""

    def _wrapped(doc: Any) -> Any:
        doc.setdefault("connections", [])
        doc.setdefault("wallets", [])
        return mutator(doc)

    return await update_json(CONNECTIONS_FILE, _wrapped)


async def load_settings() -> dict[str, Any]:
    """settings.json — 앱 설정 dict (기본 프로파일 등)."""
    return await read_json(SETTINGS_FILE)


async def save_settings(data: dict[str, Any]) -> None:
    await write_json(SETTINGS_FILE, data)


async def load_resources() -> list[dict[str, Any]]:
    """resources.json — 생성 리소스 ledger 배열 (architecture.md §3.3.1)."""
    return await read_json(RESOURCES_FILE)


async def save_resources(items: list[dict[str, Any]]) -> None:
    await write_json(RESOURCES_FILE, items)


async def append_resource(entry: dict[str, Any]) -> dict[str, Any]:
    """ledger 항목 추가 — 생성/변경 작업 성공 직후 호출한다 (FR-10)."""

    def _append(items: Any) -> Any:
        items.append(entry)
        return items

    await update_json(RESOURCES_FILE, _append)
    return entry


async def update_resource(
    resource_id: str, mutator: Callable[[dict[str, Any]], None]
) -> dict[str, Any] | None:
    """ledger 항목 단건 변경 (정리 상태 갱신 등). 없으면 None."""
    found: dict[str, Any] | None = None

    def _update(items: Any) -> Any:
        nonlocal found
        for item in items:
            if item.get("id") == resource_id:
                mutator(item)
                found = item
                break
        return items

    await update_json(RESOURCES_FILE, _update)
    return found
