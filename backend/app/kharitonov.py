"""Exact Kharitonov / Hurwitz stability auditing.

All arithmetic is exact rational arithmetic (``fractions.Fraction``).
No floating-point root finding and no interval sampling is used anywhere:
the robust-stability verdict is decided solely by the strict positivity of
all leading principal minors of the Hurwitz matrix of each of the four
Kharitonov vertex polynomials.

Polynomials are indexed ascending from the constant term:

    p(s) = c_0 + c_1 s + ... + c_n s^n      (c_n > 0)
"""

from __future__ import annotations

from fractions import Fraction
from math import lcm

# Standard four-term cyclic Kharitonov bound-selection patterns.
# For coefficient index i (counted from the constant term), the residue
# i % 4 selects one entry of the pattern; 'L' = lower bound, 'U' = upper bound.
#
#   K1: --++--++...   K2: ++--++--...   K3: +--++--+...   K4: -++--++-...
PATTERNS: dict[int, str] = {
    1: "LLUU",
    2: "UULL",
    3: "ULLU",
    4: "LUUL",
}

VERTEX_IDS = (1, 2, 3, 4)


def build_vertices(bounds: list[tuple[Fraction, Fraction]]) -> list[dict]:
    """Build the four Kharitonov vertex polynomials.

    ``bounds`` is a list of ``(lower, upper)`` exact rationals indexed from
    the constant term.  Returns one dict per vertex with its id, pattern and
    coefficient list (each coefficient tagged with the bound it came from).
    """
    vertices = []
    for vid in VERTEX_IDS:
        pattern = PATTERNS[vid]
        coeffs = []
        for i, (lo, hi) in enumerate(bounds):
            take_lower = pattern[i % 4] == "L"
            coeffs.append(
                {
                    "index": i,
                    "value": lo if take_lower else hi,
                    "bound": "lower" if take_lower else "upper",
                }
            )
        vertices.append({"id": vid, "pattern": pattern, "coefficients": coeffs})
    return vertices


def _bareiss_det(matrix: list[list[int]]) -> int:
    """Exact determinant of an integer matrix via fraction-free Bareiss
    elimination with partial pivoting."""
    n = len(matrix)
    a = [row[:] for row in matrix]
    sign = 1
    prev = 1
    for k in range(n - 1):
        if a[k][k] == 0:
            pivot = None
            for i in range(k + 1, n):
                if a[i][k] != 0:
                    pivot = i
                    break
            if pivot is None:
                return 0
            a[k], a[pivot] = a[pivot], a[k]
            sign = -sign
        pivot_val = a[k][k]
        for i in range(k + 1, n):
            for j in range(k + 1, n):
                a[i][j] = (a[i][j] * pivot_val - a[i][k] * a[k][j]) // prev
        for i in range(k + 1, n):
            a[i][k] = 0
        prev = pivot_val
    return sign * a[n - 1][n - 1]


def hurwitz_minors(coeffs: list[Fraction]) -> list[Fraction]:
    """All leading principal minors Δ_1..Δ_n of the Hurwitz matrix.

    ``coeffs`` are the exact coefficients c_0..c_n (ascending, c_n > 0).
    The Hurwitz matrix is the n×n matrix H with

        H[i][j] = c_{n - 2i + j - 1}        (0-based i, j; c_k = 0 outside [0, n])

    The polynomial is strictly Hurwitz stable iff every leading principal
    minor is strictly positive.  Computations are done on an integer-scaled
    copy of the matrix (common denominator D); the k-th minor of the scaled
    matrix is D^k times the true minor, so exactness and signs are preserved.
    """
    n = len(coeffs) - 1
    if n < 1:
        raise ValueError("degree must be at least 1")

    denom = 1
    for c in coeffs:
        denom = lcm(denom, c.denominator)
    ints = [int(c * denom) for c in coeffs]

    def ci(k: int) -> int:
        return ints[k] if 0 <= k <= n else 0

    minors: list[Fraction] = []
    for size in range(1, n + 1):
        sub = [[ci(n - 2 * i + j - 1) for j in range(size)] for i in range(size)]
        det = _bareiss_det(sub)
        minors.append(Fraction(det, denom**size))
    return minors
