"""FastAPI application: exact Kharitonov robust-stability audit service."""

from __future__ import annotations

from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .kharitonov import ValidationError, audit_box

app = FastAPI(
    title="Kharitonov 区间多项式稳健稳定性审计台",
    version="1.0.0",
)

# In Docker the browser talks to the same origin through the nginx proxy;
# permissive CORS additionally allows the Vite dev server during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class CoefficientBound(BaseModel):
    lower: str
    upper: str


class AuditRequest(BaseModel):
    coeffs: List[CoefficientBound]


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/audit")
def audit(request: AuditRequest) -> JSONResponse:
    raw = [item.model_dump() for item in request.coeffs]
    try:
        report = audit_box(raw)
    except ValidationError as exc:
        # 400 with an explicit, Chinese, user-actionable message.
        return JSONResponse(status_code=400, content={"detail": str(exc)})
    return JSONResponse(report)
