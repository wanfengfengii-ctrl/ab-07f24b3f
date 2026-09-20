"""FastAPI application: exact Kharitonov robust-stability auditing."""

from __future__ import annotations

from fractions import Fraction

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .kharitonov import PATTERNS, build_vertices, hurwitz_minors
from .schemas import AuditRequest, InputError, validate_request

app = FastAPI(title="Kharitonov 区间多项式稳健性审计", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def fraction_str(value: Fraction) -> str:
    """Exact decimal-string form: integers plain, otherwise ``p/q``."""
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def decimal_str(value: Fraction) -> str:
    """Approximate decimal for display only (never used for the verdict)."""
    try:
        return f"{float(value):.6g}"
    except OverflowError:
        return "超出浮点表示范围"


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/audit")
def audit(req: AuditRequest) -> dict:
    try:
        bounds = validate_request(req)
    except InputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    degree = len(bounds) - 1
    vertices = build_vertices(bounds)

    vertex_reports = []
    first_failure = None
    for vertex in vertices:
        coeffs = [c["value"] for c in vertex["coefficients"]]
        minors = hurwitz_minors(coeffs)

        minor_reports = []
        first_non_positive = None
        for order, minor in enumerate(minors, start=1):
            positive = minor > 0
            if not positive and first_non_positive is None:
                first_non_positive = order
            minor_reports.append(
                {
                    "order": order,
                    "value": fraction_str(minor),
                    "decimal": decimal_str(minor),
                    "positive": positive,
                }
            )

        stable = first_non_positive is None
        if not stable and first_failure is None:
            bad = minor_reports[first_non_positive - 1]
            first_failure = {
                "vertexId": vertex["id"],
                "minorOrder": first_non_positive,
                "value": bad["value"],
                "decimal": bad["decimal"],
            }

        vertex_reports.append(
            {
                "id": vertex["id"],
                "name": f"K{vertex['id']}",
                "pattern": vertex["pattern"],
                "patternLabel": "".join(
                    "−" if ch == "L" else "+" for ch in PATTERNS[vertex["id"]]
                ),
                "coefficients": [
                    {
                        "index": c["index"],
                        "value": fraction_str(c["value"]),
                        "decimal": decimal_str(c["value"]),
                        "bound": c["bound"],
                    }
                    for c in vertex["coefficients"]
                ],
                "minors": minor_reports,
                "stable": stable,
                "firstNonPositive": first_non_positive,
            }
        )

    robust = all(v["stable"] for v in vertex_reports)
    return {
        "degree": degree,
        "robust": robust,
        "vertices": vertex_reports,
        "firstFailure": first_failure,
    }
