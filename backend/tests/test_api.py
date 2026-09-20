"""API-level tests for the audit endpoints."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_audit_robust_payload():
    payload = {
        "coeffs": [
            {"lower": "5.8", "upper": "6.2"},
            {"lower": "10.5", "upper": "11.5"},
            {"lower": "5.7", "upper": "6.3"},
            {"lower": "1", "upper": "1"},
        ]
    }
    response = client.post("/api/audit", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["degree"] == 3
    assert body["robust"] is True
    assert [v["vertex"] for v in body["vertices"]] == ["K1", "K2", "K3", "K4"]
    assert body["failure"] is None
    # Every vertex reports every degree criterion with exact fraction text.
    for vertex in body["vertices"]:
        assert len(vertex["minor_checks"]) == 3
        assert all(c["value"] for c in vertex["minor_checks"])


def test_audit_rejects_illegal_payload_with_400():
    payload = {
        "coeffs": [
            {"lower": "1", "upper": "1"},
            {"lower": "1", "upper": "1"},
            {"lower": "0", "upper": "1"},  # leading lower bound not positive
        ]
    }
    response = client.post("/api/audit", json=payload)
    assert response.status_code == 400
    assert "最高次项" in response.json()["detail"]


def test_audit_unstable_locates_failure():
    payload = {
        "coeffs": [
            {"lower": "1", "upper": "1"},
            {"lower": "-1", "upper": "-1"},
            {"lower": "1", "upper": "1"},
        ]
    }
    response = client.post("/api/audit", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["robust"] is False
    assert body["failure"] == {"vertex": "K1", "first_failed_minor": 1}
