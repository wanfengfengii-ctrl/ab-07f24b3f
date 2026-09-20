"""Exact Kharitonov interval-polynomial stability audit.

All arithmetic is done with :mod:`fractions` (exact rationals).  No floating
point arithmetic and no polynomial root finding is used anywhere in the
stability decision: coefficient bounds supplied as finite decimal strings are
converted to exact ``Fraction`` instances, the four Kharitonov vertex
polynomials are built with the standard cyclic four-term selection pattern,
and every vertex is adjudicated with the Routh-Hurwitz criterion by checking
that every leading principal minor of its Hurwitz matrix is strictly positive.
"""

from __future__ import annotations

from fractions import Fraction
from typing import List, Sequence

# Coefficient index modulo 4 for each of the four Kharitonov vertices.
#
# Coefficients are indexed from the constant term a_0.  The standard four
# Kharitonov polynomials are
#
#   K1: a_0^+ + a_1^+ s + a_2^- s^2 + a_3^- s^3 + a_4^+ s^4 + a_5^+ s^5 + ...
#   K2: a_0^+ + a_1^- s + a_2^- s^2 + a_3^+ s^3 + a_4^+ s^4 + a_5^- s^5 + ...
#   K3: a_0^- + a_1^- s + a_2^+ s^2 + a_3^+ s^3 + a_4^- s^4 + a_5^- s^5 + ...
#   K4: a_0^- + a_1^+ s + a_2^+ s^2 + a_3^- s^3 + a_4^- s^4 + a_5^+ s^5 + ...
#
# i.e. the bound selection repeats with period four.  The tables below record,
# for index ``i mod 4``, which bound is selected (0 = lower, 1 = upper).
_VERTEX_PATTERNS = (
    (1, 1, 0, 0),  # K1: upper, upper, lower, lower
    (1, 0, 0, 1),  # K2: upper, lower, lower, upper
    (0, 0, 1, 1),  # K3: lower, lower, upper, upper
    (0, 1, 1, 0),  # K4: lower, upper, upper, lower
)

VERTEX_NAMES = ("K1", "K2", "K3", "K4")


class ValidationError(ValueError):
    """Raised when the submitted coefficient box is not a valid audit input."""


def decimal_to_fraction(text: str) -> Fraction:
    """Convert a finite decimal string to an exact :class:`Fraction`.

    A leading ``+`` is accepted, as is an exponent (``1.2e-3`` etc.).  The
    conversion is purely lexical, so values like ``0.1`` become ``1/10``
    rather than the nearest binary float.
    """
    s = text.strip()
    if not s:
        raise ValidationError("空的系数值")
    sign = 1
    if s[0] in "+-":
        if s[0] == "-":
            sign = -1
        s = s[1:]
    if not s:
        raise ValidationError(f"非法十进制数: {text!r}")
    # Normalise exponent: split mantissa and exponent, then shift the decimal
    # point exactly (integer arithmetic only).
    exp = 0
    if "e" in s or "E" in s:
        mantissa, _, exp_text = s.replace("E", "e").partition("e")
        s = mantissa
        if not s or exp_text.strip() in ("", "+", "-"):
            raise ValidationError(f"非法十进制数: {text!r}")
        try:
            exp = int(exp_text)
        except ValueError as exc:
            raise ValidationError(f"非法十进制数: {text!r}") from exc
    if "." in s:
        int_part, _, frac_part = s.partition(".")
    else:
        int_part, frac_part = s, ""
    if not int_part and not frac_part:
        raise ValidationError(f"非法十进制数: {text!r}")
    if int_part and not int_part.isdigit():
        raise ValidationError(f"非法十进制数: {text!r}")
    if frac_part and not frac_part.isdigit():
        raise ValidationError(f"非法十进制数: {text!r}")
    digits = (int_part or "0") + frac_part
    exp -= len(frac_part)
    value = Fraction(sign * int(digits or "0"), 1)
    if exp >= 0:
        value *= 10 ** exp
    else:
        value /= 10 ** (-exp)
    return value


def fraction_to_decimal_string(value: Fraction) -> str:
    """Render an exact fraction as a finite decimal (or an exact fraction).

    Audit inputs are finite decimals and all vertex coefficients are selected
    from those bounds, so every displayed value has a finite decimal
    expansion; the exact ``p/q`` form is appended in parentheses so the UI can
    prove to the reviewer that no floating point approximation is involved.
    """
    if value.denominator == 1:
        decimal = str(value.numerator)
    else:
        # Find k such that denominator divides 10**k after reduction.
        den = value.denominator
        k = 0
        rest = den
        while rest % 2 == 0:
            rest //= 2
            k += 1
        twos = k
        k = 0
        while rest % 5 == 0:
            rest //= 5
            k += 1
        fives = k
        if rest != 1:
            # Not a finite decimal.  Inputs are decimal, so this should never
            # happen, but fall back to an exact fraction rather than rounding.
            return f"{value.numerator}/{value.denominator}"
        places = max(twos, fives)
        scaled = value.numerator * (10 ** places // den)
        if scaled < 0:
            digits = "-" + str(-scaled).zfill(places + 1)
        else:
            digits = str(scaled).zfill(places + 1)
        decimal = digits[: -places] + "." + digits[-places:]
    return f"{decimal} ({value.numerator}/{value.denominator})"


def parse_box(
    raw_coeffs: Sequence[dict[str, str]],
) -> List[tuple[Fraction, Fraction]]:
    """Validate the request payload and return exact ``(lower, upper)`` pairs.

    Coefficients are indexed from the constant term (index 0).  The order
    ``n`` must satisfy ``2 <= n <= 40``; every bound must be a finite decimal
    with ``lower <= upper``, and the leading coefficient lower bound must be
    strictly positive.
    """
    if not isinstance(raw_coeffs, Sequence) or isinstance(raw_coeffs, (str, bytes)):
        raise ValidationError("系数列表格式错误")
    n = len(raw_coeffs) - 1
    if not (2 <= n <= 40):
        raise ValidationError("阶数 n 必须满足 2 ≤ n ≤ 40")
    box: List[tuple[Fraction, Fraction]] = []
    for i, item in enumerate(raw_coeffs):
        if not isinstance(item, dict) or "lower" not in item or "upper" not in item:
            raise ValidationError(f"a_{i} 缺少 lower/upper 字段")
        low = decimal_to_fraction(str(item["lower"]))
        high = decimal_to_fraction(str(item["upper"]))
        if low > high:
            raise ValidationError(f"a_{i} 的下界大于上界")
        box.append((low, high))
    if box[-1][0] <= 0:
        raise ValidationError(f"最高次项 a_{n} 的下界必须严格为正")
    return box


def build_vertices(
    box: Sequence[tuple[Fraction, Fraction]],
) -> List[tuple[str, List[Fraction]]]:
    """Construct the four Kharitonov vertex polynomials.

    Returns ``(name, coefficients)`` pairs with coefficients indexed from the
    constant term, using the four-term cyclic bound-selection pattern.
    """
    vertices: List[tuple[str, List[Fraction]]] = []
    for name, pattern in zip(VERTEX_NAMES, _VERTEX_PATTERNS):
        coeffs = [box[i][pattern[i % 4]] for i in range(len(box))]
        vertices.append((name, coeffs))
    return vertices


def hurwitz_leading_minors(coeffs: Sequence[Fraction]) -> List[Fraction]:
    """Return the n leading principal minors Δ_1..Δ_n of the Hurwitz matrix.

    For degree ``n`` polynomial ``a_0 + a_1 s + ... + a_n s^n`` (``a_n > 0``)
    the n×n Hurwitz matrix has (0-based) entries
    ``H[i][j] = a_{n - 1 + i - 2j}`` with out-of-range coefficients treated
    as zero, i.e.

      ``a_{n-1}  a_{n-3}  a_{n-5} ...``
      ``a_n      a_{n-2}  a_{n-4} ...``
      ``0        a_{n-1}  a_{n-3} ...``
      ``...``

    Determinants are computed by exact Bareiss fraction-free elimination,
    which is dramatically faster than recursive expansion for n up to 40 and
    remains exact over the rationals.
    """
    n = len(coeffs) - 1

    def a(k: int) -> Fraction:
        return coeffs[k] if 0 <= k <= n else Fraction(0)

    matrix = [[a(n - 1 + i - 2 * j) for j in range(n)] for i in range(n)]
    return _bareiss_leading_minors(matrix)


def _bareiss_leading_minors(matrix: List[List[Fraction]]) -> List[Fraction]:
    """Exact leading principal minors via Bareiss fraction-free elimination."""
    n = len(matrix)
    minors: List[Fraction] = []
    # Work on a copy; Bareiss overwrites entries.  Formula:
    #   a'_{ij} = (a_{kk}*a_{ij} - a_{ik}*a_{kj}) / a_{k-1,k-1}
    # with the previous pivot initialised to 1.  The pivot at step k equals
    # the (k+1)-th leading principal minor of the original matrix.
    m = [row[:] for row in matrix]
    prev_pivot = Fraction(1)
    for k in range(n):
        pivot = m[k][k]
        minors.append(pivot)  # Bareiss invariant: pivot = det of leading block
        if pivot == 0:
            # A zero pivot at this stage means this and all larger leading
            # minors cannot be obtained by plain Bareiss; compute the rest
            # directly (exact).  Triggered only on genuinely non-robust
            # inputs, where speed is irrelevant.
            minors.pop()
            minors.extend(_all_leading_minors_direct(matrix, start=len(minors)))
            return minors
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                m[i][j] = (pivot * m[i][j] - m[i][k] * m[k][j]) / prev_pivot
        prev_pivot = pivot
    return minors


def _det_exact(matrix: List[List[Fraction]]) -> Fraction:
    """Exact determinant via Gaussian elimination with rational pivoting."""
    n = len(matrix)
    m = [row[:] for row in matrix]
    det = Fraction(1)
    for k in range(n):
        pivot_row = next((r for r in range(k, n) if m[r][k] != 0), None)
        if pivot_row is None:
            return Fraction(0)
        if pivot_row != k:
            m[k], m[pivot_row] = m[pivot_row], m[k]
            det = -det
        pivot = m[k][k]
        det *= pivot
        for i in range(k + 1, n):
            if m[i][k] == 0:
                continue
            factor = m[i][k] / pivot
            for j in range(k + 1, n):
                m[i][j] -= factor * m[k][j]
    return det


def _all_leading_minors_direct(
    matrix: List[List[Fraction]], start: int
) -> List[Fraction]:
    n = len(matrix)
    return [
        _det_exact([row[: size] for row in matrix[:size]])
        for size in range(start + 1, n + 1)
    ]


def audit_vertex(
    name: str, coeffs: Sequence[Fraction]
) -> dict:
    """Adjudicate one vertex: strict positivity of every Hurwitz minor.

    The Routh-Hurwitz theorem states (with ``a_n > 0``) that every root has
    strictly negative real part iff ``Δ_k > 0`` for all ``k = 1..n``.
    """
    minors = hurwitz_leading_minors(coeffs)
    checks = []
    first_failure = None
    for k, delta in enumerate(minors, start=1):
        positive = delta > 0
        checks.append(
            {
                "index": k,
                "value": fraction_to_decimal_string(delta),
                "positive": positive,
            }
        )
        if not positive and first_failure is None:
            first_failure = k
    return {
        "vertex": name,
        "stable": first_failure is None,
        "coefficients": [
            {"index": i, "value": fraction_to_decimal_string(c)}
            for i, c in enumerate(coeffs)
        ],
        "minor_checks": checks,
        "first_failed_minor": first_failure,
    }


def audit_box(raw_coeffs: Sequence[dict[str, str]]) -> dict:
    """Full audit: parse -> four vertices -> Hurwitz adjudication."""
    box = parse_box(raw_coeffs)
    degree = len(box) - 1
    vertices = [audit_vertex(name, coeffs) for name, coeffs in build_vertices(box)]
    failed = [v for v in vertices if not v["stable"]]
    robust = not failed
    report = {
        "degree": degree,
        "robust": robust,
        "vertices": vertices,
        "bounds": [
            {
                "index": i,
                "lower": fraction_to_decimal_string(lo),
                "upper": fraction_to_decimal_string(hi),
            }
            for i, (lo, hi) in enumerate(box)
        ],
    }
    if failed:
        # Locate the failing vertex with the smallest canonical number
        # (K1 < K2 < K3 < K4) and, within it, the first non-positive minor.
        order = {name: i for i, name in enumerate(VERTEX_NAMES)}
        worst = min(failed, key=lambda v: order[v["vertex"]])
        report["failure"] = {
            "vertex": worst["vertex"],
            "first_failed_minor": worst["first_failed_minor"],
        }
    else:
        report["failure"] = None
    return report
