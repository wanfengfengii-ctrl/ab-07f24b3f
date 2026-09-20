from fractions import Fraction

from app.kharitonov import PATTERNS, build_vertices, hurwitz_minors


def F(text):
    return Fraction(text)


class TestPatterns:
    def test_four_term_cycle(self):
        assert PATTERNS[1] == "LLUU"
        assert PATTERNS[2] == "UULL"
        assert PATTERNS[3] == "ULLU"
        assert PATTERNS[4] == "LUUL"

    def test_vertex_selection_degree_5(self):
        bounds = [(F(i * 10 + 1), F(i * 10 + 2)) for i in range(6)]
        vertices = build_vertices(bounds)
        picked = {
            v["id"]: [c["value"] for c in v["coefficients"]] for v in vertices
        }
        # K1: --++--  (residues 0,1 lower; 2,3 upper; cycle repeats)
        assert picked[1] == [F(1), F(11), F(22), F(32), F(41), F(51)]
        # K2: ++--++
        assert picked[2] == [F(2), F(12), F(21), F(31), F(42), F(52)]
        # K3: +--++-
        assert picked[3] == [F(2), F(11), F(21), F(32), F(42), F(51)]
        # K4: -++--+
        assert picked[4] == [F(1), F(12), F(22), F(31), F(41), F(52)]

    def test_bound_tags(self):
        bounds = [(F(1), F(2)), (F(3), F(4)), (F(5), F(6))]
        v1 = build_vertices(bounds)[0]
        assert [c["bound"] for c in v1["coefficients"]] == [
            "lower",
            "lower",
            "upper",
        ]


class TestHurwitzMinors:
    def test_cubic_known_values(self):
        # (s+1)^3 = 1 + 3s + 3s^2 + s^3 -> Δ = 3, 8, 8
        assert hurwitz_minors([F(1), F(3), F(3), F(1)]) == [
            F(3),
            F(8),
            F(8),
        ]

    def test_quadratic(self):
        # 2 + 3s + 4s^2 -> Δ1 = 3, Δ2 = 6
        assert hurwitz_minors([F(2), F(3), F(4)]) == [F(3), F(6)]

    def test_zero_minor_is_detected(self):
        # 1 + 0s + 1s^2 (purely imaginary roots) -> Δ1 = 0, Δ2 = 0
        assert hurwitz_minors([F(1), F(0), F(1)]) == [F(0), F(0)]

    def test_unstable_cubic(self):
        # 1 + s + s^2 + s^3 = (s+1)(s^2+1): Δ2 = 0 -> not strictly stable
        minors = hurwitz_minors([F(1), F(1), F(1), F(1)])
        assert minors[0] == 1
        assert minors[1] == 0
        assert minors[2] == 0

    def test_exact_fractions_preserved(self):
        # 1 + 1/2 s + 2 s^2 + 3/2 s^3 -> Δ2 = 2*(1/2) - 1*(3/2) = -1/2
        minors = hurwitz_minors([F(1), F("1/2"), F(2), F("3/2")])
        assert minors[0] == 2
        assert minors[1] == F("-1/2")
        assert minors[2] == F("-1/2")

    def test_last_minor_is_c0_times_previous(self):
        coeffs = [F("5/2"), F("7/3"), F("11/5"), F("13/7"), F(2)]
        minors = hurwitz_minors(coeffs)
        assert minors[-1] == coeffs[0] * minors[-2]
