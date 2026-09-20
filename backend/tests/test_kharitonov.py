"""Permanent regression tests for the exact Kharitonov audit core."""

import pytest

from fractions import Fraction

from app.kharitonov import (
    ValidationError,
    audit_box,
    build_vertices,
    decimal_to_fraction,
    fraction_to_decimal_string,
    hurwitz_leading_minors,
    parse_box,
)


def test_decimal_conversion_is_exact():
    assert decimal_to_fraction("0.1") == Fraction(1, 10)
    assert decimal_to_fraction("1.2e-3") == Fraction(12, 10000)
    assert decimal_to_fraction("-3") == Fraction(-3)
    assert decimal_to_fraction("+2.50") == Fraction(250, 100)


@pytest.mark.parametrize("text", ["", "abc", "1.2.3", "nan", "inf", "1e", "0x1"])
def test_decimal_rejects_non_finite_decimals(text):
    with pytest.raises(ValidationError):
        decimal_to_fraction(text)


def test_fraction_display_contains_decimal_and_exact_fraction():
    s = fraction_to_decimal_string(Fraction(1, 10))
    assert s == "0.1 (1/10)"
    assert fraction_to_decimal_string(Fraction(-3, 4)) == "-0.75 (-3/4)"
    assert fraction_to_decimal_string(Fraction(7)) == "7 (7/1)"


def test_hurwitz_minors_known_cubic():
    # (s+1)(s+2)(s+3): a0..a3 = 6,11,6,1 ; minors 6, 60, 360
    minors = hurwitz_leading_minors(
        [Fraction(6), Fraction(11), Fraction(6), Fraction(1)]
    )
    assert minors == [Fraction(6), Fraction(60), Fraction(360)]


def test_hurwitz_minors_quadratic():
    assert hurwitz_leading_minors(
        [Fraction(2), Fraction(3), Fraction(1)]
    ) == [Fraction(3), Fraction(6)]
    # s^2 - s + 1 is unstable: Delta_1 < 0
    assert hurwitz_leading_minors(
        [Fraction(1), Fraction(-1), Fraction(1)]
    )[0] == -1


def test_vertex_patterns_are_four_term_cyclic():
    box = [(Fraction(i * 10), Fraction(i * 10 + 9)) for i in range(1, 5)]
    d = dict(build_vertices(box))
    assert d["K1"] == [19, 29, 30, 40]
    assert d["K2"] == [19, 20, 30, 49]
    assert d["K3"] == [10, 20, 39, 49]
    assert d["K4"] == [10, 29, 39, 40]
    # Periodicity continues past the first block of four coefficients.
    box6 = [(Fraction(i * 10), Fraction(i * 10 + 9)) for i in range(1, 7)]
    d6 = dict(build_vertices(box6))
    assert d6["K1"] == [19, 29, 30, 40, 59, 69]
    assert d6["K3"] == [10, 20, 39, 49, 50, 60]


def test_parse_validation_rules():
    good = [
        {"lower": "1", "upper": "2"},
        {"lower": "1", "upper": "2"},
        {"lower": "0.5", "upper": "1"},
    ]
    assert len(parse_box(good)) == 3
    with pytest.raises(ValidationError):
        parse_box([{"lower": "0", "upper": "1"}] * 2)  # degree 1
    with pytest.raises(ValidationError):
        parse_box([{"lower": "1", "upper": "1"}] * 42)  # degree 41
    with pytest.raises(ValidationError):
        parse_box(
            [{"lower": "2", "upper": "1"}] + [{"lower": "1", "upper": "1"}] * 2
        )
    with pytest.raises(ValidationError):
        parse_box(
            [{"lower": "1", "upper": "1"}] * 2
            + [{"lower": "0", "upper": "1"}]
        )
    with pytest.raises(ValidationError):
        parse_box(
            [{"lower": "1", "upper": "1"}] * 2
            + [{"lower": "-0.1", "upper": "1"}]
        )


def test_robust_cubic_box_all_vertices_stable():
    box = [
        {"lower": "5.8", "upper": "6.2"},
        {"lower": "10.5", "upper": "11.5"},
        {"lower": "5.7", "upper": "6.3"},
        {"lower": "1", "upper": "1"},
    ]
    report = audit_box(box)
    assert report["robust"] is True
    assert report["failure"] is None
    assert all(v["stable"] for v in report["vertices"])


def test_unstable_box_locates_smallest_vertex_and_first_minor():
    box = [
        {"lower": "1", "upper": "1"},
        {"lower": "-1", "upper": "-1"},
        {"lower": "1", "upper": "1"},
    ]
    report = audit_box(box)
    assert report["robust"] is False
    assert report["failure"] == {"vertex": "K1", "first_failed_minor": 1}
    for v in report["vertices"]:
        assert v["stable"] is False
        assert v["minor_checks"][0]["positive"] is False


def test_reports_carry_exact_fraction_strings():
    report = audit_box([
        {"lower": "0.1", "upper": "0.1"},
        {"lower": "3", "upper": "3"},
        {"lower": "1", "upper": "1"},
    ])
    k1 = report["vertices"][0]
    assert any("(1/10)" in c["value"] for c in k1["coefficients"])
