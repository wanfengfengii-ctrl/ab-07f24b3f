"""Request parsing and validation for the audit API.

Decimal bounds arrive as JSON strings (or numbers) and are converted to
exact rationals via ``decimal.Decimal`` -> ``fractions.Fraction``.  Only
finite decimals are accepted.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from fractions import Fraction
from typing import Any

from pydantic import BaseModel

MIN_DEGREE = 2
MAX_DEGREE = 40


class CoefficientBound(BaseModel):
    index: int
    lower: Any
    upper: Any


class AuditRequest(BaseModel):
    coefficients: list[CoefficientBound]


class InputError(ValueError):
    """Raised for any user-input validation problem (mapped to HTTP 422)."""


def parse_decimal(value: Any, label: str) -> Fraction:
    """Convert a finite decimal (string/int/float) to an exact Fraction."""
    if isinstance(value, bool) or value is None:
        raise InputError(f"{label} 必须是有限十进制数")
    text = str(value).strip()
    if not text:
        raise InputError(f"{label} 不能为空")
    try:
        dec = Decimal(text)
    except InvalidOperation:
        raise InputError(f"{label} 不是合法的有限十进制数: {text!r}")
    if not dec.is_finite():
        raise InputError(f"{label} 必须是有限十进制数（禁止 NaN/Inf）")
    return Fraction(dec)


def validate_request(req: AuditRequest) -> list[tuple[Fraction, Fraction]]:
    """Validate the request and return exact ``(lower, upper)`` bounds."""
    items = req.coefficients
    if not items:
        raise InputError("系数列表不能为空")

    degree = len(items) - 1
    if degree < MIN_DEGREE or degree > MAX_DEGREE:
        raise InputError(
            f"阶数必须在 {MIN_DEGREE}..{MAX_DEGREE} 之间（收到 {degree} 阶）"
        )

    bounds: list[tuple[Fraction, Fraction]] = []
    for pos, item in enumerate(items):
        if item.index != pos:
            raise InputError(
                f"系数编号必须从常数项 0 开始连续递增：位置 {pos} 收到编号 {item.index}"
            )
        lo = parse_decimal(item.lower, f"系数 a{item.index} 下界")
        hi = parse_decimal(item.upper, f"系数 a{item.index} 上界")
        if lo > hi:
            raise InputError(f"系数 a{item.index} 下界大于上界（{lo} > {hi}）")
        bounds.append((lo, hi))

    top_lo = bounds[-1][0]
    if top_lo <= 0:
        raise InputError(
            f"最高次项 a{degree} 的下界必须为正（收到 {top_lo}）"
        )
    return bounds
