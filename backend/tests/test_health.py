"""스캐폴딩 스모크 테스트 — 앱 import/health/스텁 501 응답 확인."""
from fastapi.testclient import TestClient


def test_health_ok(client: TestClient) -> None:
    """GET /api/v1/health — envelope 형태(data/executed_sql/elapsed_ms) 확인."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["data"]["status"] == "ok"
    assert body["executed_sql"] == []
    assert "elapsed_ms" in body


def test_stub_returns_501_envelope(client: TestClient) -> None:
    """스텁 엔드포인트 — 501 + §1.4 오류 envelope."""
    res = client.get("/api/v1/profiles/attribute-meta")
    assert res.status_code == 501
    assert res.json()["error"]["app_code"] == "NOT_IMPLEMENTED"
