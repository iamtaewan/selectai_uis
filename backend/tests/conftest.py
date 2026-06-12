"""pytest 공통 픽스처 — oracledb 모킹 골격.

단위 테스트는 실제 ADB에 접속하지 않는다 (architecture.md §6.1 — oracledb만 스텁).
구현 에이전트는 여기의 픽스처를 확장하되 기존 픽스처 이름/시그니처는 유지한다.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """FastAPI 동기 테스트 클라이언트 (스텁/계약 테스트용)."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_oracle_connection() -> AsyncMock:
    """oracledb AsyncConnection 모킹 — cursor/execute/fetch 골격.

    사용 예: pool_registry를 monkeypatch해 이 커넥션을 반환하게 한다.
    """
    conn = AsyncMock(name="AsyncConnection")
    cursor = AsyncMock(name="AsyncCursor")
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = None
    cursor.description = []
    conn.cursor.return_value = cursor
    return conn


@pytest.fixture
def mock_pool(mock_oracle_connection: AsyncMock) -> MagicMock:
    """oracledb AsyncConnectionPool 모킹 — acquire()가 모킹 커넥션을 반환."""
    pool = MagicMock(name="AsyncConnectionPool")
    acquire_ctx = AsyncMock()
    acquire_ctx.__aenter__.return_value = mock_oracle_connection
    acquire_ctx.__aexit__.return_value = False
    pool.acquire.return_value = acquire_ctx
    return pool


@pytest.fixture
def tmp_app_data_dir(tmp_path, monkeypatch):
    """앱 데이터 디렉토리(~/.selectai)를 임시 경로로 격리."""
    data_dir = tmp_path / ".selectai"
    data_dir.mkdir(mode=0o700)
    monkeypatch.setenv("APP_DATA_DIR", str(data_dir))
    # config 싱글턴 캐시 무효화
    from app.config import get_settings

    get_settings.cache_clear()
    yield data_dir
    get_settings.cache_clear()
