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


def test_attribute_meta_implemented(client: TestClient) -> None:
    """GET /profiles/attribute-meta — 구현 완료: 검증 21속성(엔트리 22) + defaults (api-spec §4.1).

    (스캐폴딩 시점의 501 스텁 검사를 구현 계약 검사로 대체)
    """
    res = client.get("/api/v1/profiles/attribute-meta")
    assert res.status_code == 200
    body = res.json()
    attrs = body["data"]["verified_attributes"]
    assert len(attrs) == 22  # azure_resource_name/azure_deployment_name 쌍 포함
    names = {a["name"] for a in attrs}
    assert {"provider", "comments", "model", "object_list", "enforce_object_list"} <= names
    assert body["data"]["defaults"]["provider"] == "oci"
    assert body["data"]["defaults"]["model"] == "meta.llama-3.3-70b-instruct"
    assert body["executed_sql"] == []
