from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ROBUST = [
    {"index": 0, "lower": "1", "upper": "2"},
    {"index": 1, "lower": "2", "upper": "3"},
    {"index": 2, "lower": "2", "upper": "4"},
    {"index": 3, "lower": "1", "upper": "1.5"},
]

# Same family but a0 upper = 2.5 and a1 lower = 0.5:
# K3 = 2.5 + 0.5 s + 2 s^2 + 1.5 s^3 has Δ2 = 2*0.5 - 2.5*1.5 = -11/4.
FRAGILE = [
    {"index": 0, "lower": "1", "upper": "2.5"},
    {"index": 1, "lower": "0.5", "upper": "3"},
    {"index": 2, "lower": "2", "upper": "4"},
    {"index": 3, "lower": "1", "upper": "1.5"},
]


def audit(coefficients):
    return client.post("/api/audit", json={"coefficients": coefficients})


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_robust_family():
    resp = audit(ROBUST)
    assert resp.status_code == 200
    data = resp.json()
    assert data["degree"] == 3
    assert data["robust"] is True
    assert data["firstFailure"] is None
    assert [v["name"] for v in data["vertices"]] == ["K1", "K2", "K3", "K4"]
    assert all(v["stable"] for v in data["vertices"])
    # K1 = 1 + 2s + 4s^2 + 3/2 s^3: Δ = 4, 13/2, 13/2 (exact fractions)
    k1 = data["vertices"][0]
    assert [m["value"] for m in k1["minors"]] == ["4", "13/2", "13/2"]
    # K1 pattern --++ uses the upper bound of a3 -> rendered as exact 3/2
    assert k1["coefficients"][3]["value"] == "3/2"
    assert k1["coefficients"][3]["bound"] == "upper"
    # K2 pattern ++-- uses the lower bound of a3
    k2 = data["vertices"][1]
    assert k2["coefficients"][3]["value"] == "1"
    assert k2["coefficients"][3]["bound"] == "lower"


def test_fragile_family_locates_first_failure():
    resp = audit(FRAGILE)
    assert resp.status_code == 200
    data = resp.json()
    assert data["robust"] is False
    failure = data["firstFailure"]
    assert failure["vertexId"] == 3
    assert failure["minorOrder"] == 2
    assert failure["value"] == "-11/4"
    k3 = data["vertices"][2]
    assert k3["stable"] is False
    assert k3["firstNonPositive"] == 2
    assert k3["minors"][1]["positive"] is False
    # K1, K2, K4 remain stable in this family
    assert [v["stable"] for v in data["vertices"]] == [True, True, False, True]


def test_exact_decimal_conversion():
    coeffs = [
        {"index": 0, "lower": "0.1", "upper": "0.2"},
        {"index": 1, "lower": "2", "upper": "3"},
        {"index": 2, "lower": "2", "upper": "4"},
        {"index": 3, "lower": "1", "upper": "1.5"},
    ]
    data = audit(coeffs).json()
    k1 = data["vertices"][0]
    assert k1["coefficients"][0]["value"] == "1/10"
    k2 = data["vertices"][1]
    assert k2["coefficients"][0]["value"] == "1/5"


def test_exponent_notation_is_finite_decimal():
    coeffs = [
        {"index": 0, "lower": "1e-3", "upper": "2"},
        {"index": 1, "lower": "2", "upper": "3"},
        {"index": 2, "lower": "2", "upper": "4"},
        {"index": 3, "lower": "1", "upper": "1.5"},
    ]
    resp = audit(coeffs)
    assert resp.status_code == 200
    assert resp.json()["vertices"][0]["coefficients"][0]["value"] == "1/1000"


def test_reject_nonpositive_top_lower():
    coeffs = [dict(c) for c in ROBUST]
    coeffs[3]["lower"] = "0"
    resp = audit(coeffs)
    assert resp.status_code == 422
    assert "最高次项" in resp.json()["detail"]


def test_reject_lower_above_upper():
    coeffs = [dict(c) for c in ROBUST]
    coeffs[1]["lower"] = "5"
    resp = audit(coeffs)
    assert resp.status_code == 422
    assert "下界大于上界" in resp.json()["detail"]


def test_reject_bad_decimal():
    coeffs = [dict(c) for c in ROBUST]
    coeffs[0]["lower"] = "abc"
    resp = audit(coeffs)
    assert resp.status_code == 422


def test_reject_degree_out_of_range():
    too_small = ROBUST[:2]
    assert audit(too_small).status_code == 422
    too_big = [
        {"index": i, "lower": "1", "upper": "2"} for i in range(42)
    ]
    assert audit(too_big).status_code == 422


def test_degree_40_accepted():
    # (s+1)^40-like stable family: all coefficients fixed at binomial values
    # would be heavy; use p(s) = sum s^i scaled — instead use a simple
    # stable-ish family: c_i in [1, 1] for all i is NOT stable, so use
    # c_i = C(40, i) exactly (binomial => (s+1)^40, stable).
    from math import comb

    coeffs = [
        {"index": i, "lower": str(comb(40, i)), "upper": str(comb(40, i))}
        for i in range(41)
    ]
    resp = audit(coeffs)
    assert resp.status_code == 200
    data = resp.json()
    assert data["degree"] == 40
    assert data["robust"] is True
    assert len(data["vertices"][0]["minors"]) == 40
