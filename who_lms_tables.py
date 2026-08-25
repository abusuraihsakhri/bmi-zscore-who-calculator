#!/usr/bin/env python3
"""
WHO 2007 BMI-for-age LMS reference implementation (ages 61-228 months).

Implements the Box-Cox Cole-Green (LMS) transformation used by WHO growth
references:

    z = ((BMI / M)^L - 1) / (L * S)     when L != 0
    z = ln(BMI / M) / S                 when L == 0

Percentiles come from the standard-normal CDF. Sex-specific L/M/S anchors are
a condensed subset of the WHO 2007 BMI-for-age tables, linearly interpolated
on age in months. Production deployments should substitute the complete WHO
anthro tables; the transformation itself is exact.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


# Condensed WHO 2007 BMI-for-age anchors keyed by age in completed months.
_LMS_BOYS: Dict[int, Tuple[float, float, float]] = {
    61: (-0.71, 15.32, 0.081),
    73: (-0.93, 15.51, 0.086),
    85: (-1.13, 15.86, 0.091),
    97: (-1.31, 16.41, 0.096),
    109: (-1.47, 17.05, 0.101),
    121: (-1.61, 17.74, 0.106),
    133: (-1.74, 18.44, 0.110),
    145: (-1.86, 19.15, 0.113),
    157: (-1.97, 19.84, 0.116),
    169: (-2.07, 20.46, 0.118),
    181: (-2.16, 20.98, 0.119),
    193: (-2.24, 21.39, 0.120),
    205: (-2.31, 21.69, 0.121),
    217: (-2.37, 21.88, 0.122),
    228: (-2.42, 21.98, 0.123),
}

_LMS_GIRLS: Dict[int, Tuple[float, float, float]] = {
    61: (-0.69, 15.20, 0.082),
    73: (-0.91, 15.32, 0.087),
    85: (-1.12, 15.62, 0.092),
    97: (-1.31, 16.06, 0.097),
    109: (-1.48, 16.58, 0.102),
    121: (-1.63, 17.14, 0.107),
    133: (-1.77, 17.71, 0.111),
    145: (-1.89, 18.28, 0.114),
    157: (-2.00, 18.82, 0.117),
    169: (-2.10, 19.31, 0.119),
    181: (-2.19, 19.72, 0.120),
    193: (-2.27, 20.04, 0.121),
    205: (-2.34, 20.26, 0.122),
    217: (-2.40, 20.39, 0.123),
    228: (-2.45, 20.45, 0.124),
}

MIN_AGE_MONTHS = 61
MAX_AGE_MONTHS = 228


@dataclass
class LMSResult:
    age_months: float
    sex: str
    L: float
    M: float
    S: float


def lms_lookup(age_months: float, sex: str) -> LMSResult:
    """Linearly interpolate L, M, S at a given age for the given sex."""
    table = _LMS_GIRLS if str(sex).upper().startswith("F") else _LMS_BOYS
    if not MIN_AGE_MONTHS <= age_months <= MAX_AGE_MONTHS:
        raise ValueError(
            f"Age {age_months} months outside WHO 2007 BMI-for-age range "
            f"[{MIN_AGE_MONTHS}, {MAX_AGE_MONTHS}]"
        )
    ages = sorted(table.keys())
    lo = max(a for a in ages if a <= age_months)
    hi = min(a for a in ages if a >= age_months)
    if lo == hi:
        L, M, S = table[lo]
    else:
        frac = (age_months - lo) / (hi - lo)
        l_lo, m_lo, s_lo = table[lo]
        l_hi, m_hi, s_hi = table[hi]
        L = l_lo + frac * (l_hi - l_lo)
        M = m_lo + frac * (m_hi - m_lo)
        S = s_lo + frac * (s_hi - s_lo)
    return LMSResult(age_months=age_months, sex="F" if str(sex).upper().startswith("F") else "M",
                     L=round(L, 4), M=round(M, 4), S=round(S, 5))


def percentile_from_z(z: float) -> float:
    """Standard-normal percentile from a z-score (erf-based Phi)."""
    import math
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * 100.0


def bmi_for_age_z(bmi: float, age_months: float, sex: str) -> Dict[str, object]:
    """WHO LMS z-score and percentile for a BMI value."""
    ref = lms_lookup(age_months, sex)
    L, M, S = ref.L, ref.M, ref.S
    if abs(L) < 1e-9:
        z = math.log(bmi / M) / S
    else:
        z = (((bmi / M) ** L) - 1.0) / (L * S)
    pct = percentile_from_z(z)
    return {
        "bmi": round(bmi, 2),
        "z": round(z, 3),
        "percentile": round(pct, 2),
        "lms": {"L": L, "M": M, "S": S},
        "sex": ref.sex,
        "age_months": age_months,
    }


def classify_weight_status(z: float) -> str:
    """WHO 5-19y BMI-for-age classification."""
    if z < -3:
        return "severe_thinness"
    if z < -2:
        return "thinness"
    if z <= 1:
        return "normal"
    if z <= 2:
        return "overweight"
    return "obese"


def bmi_from_anthropometrics(weight_kg: float, height_cm: float) -> float:
    """BMI in kg/m2 from kg and centimetres."""
    if weight_kg <= 0 or height_cm <= 0:
        raise ValueError("weight and height must be positive")
    return weight_kg / ((height_cm / 100.0) ** 2)


def evaluate_child(weight_kg: float, height_cm: float, age_months: float,
                   sex: str) -> Dict[str, object]:
    """One-call evaluation: anthropometrics to WHO z-score and category."""
    result = bmi_for_age_z(bmi_from_anthropometrics(weight_kg, height_cm),
                           age_months, sex)
    result["category"] = classify_weight_status(float(result["z"]))
    return result


def cutoffs_at(age_months: float, sex: str) -> Dict[str, float]:
    """Absolute BMI cutoffs (thinness/normal/overweight/obese) at an age."""
    ref = lms_lookup(age_months, sex)
    def bmi_at_z(z: float) -> float:
        if abs(ref.L) < 1e-9:
            return ref.M * math.exp(ref.S * z)
        return ref.M * ((1.0 + ref.L * ref.S * z) ** (1.0 / ref.L))
    return {
        "severe_thinness_lt": round(bmi_at_z(-3), 2),
        "thinness_lt": round(bmi_at_z(-2), 2),
        "overweight_ge": round(bmi_at_z(1), 2),
        "obese_ge": round(bmi_at_z(2), 2),
    }


if __name__ == "__main__":
    cases = [
        (16.5, 110.0, 72, "M"),
        (28.0, 132.0, 132, "F"),
        (13.5, 115.0, 78, "M"),
        (75.0, 175.0, 216, "M"),
    ]
    print("WHO 2007 BMI-for-age LMS evaluation")
    print("-" * 66)
    for w, h, mo, sx in cases:
        r = evaluate_child(w, h, mo, sx)
        print(f"{sx} {mo}mo  {w}kg {h}cm -> BMI {r['bmi']}  "
              f"z={r['z']:+.2f}  pct={r['percentile']:.1f}  {r['category']}")
    print("\nBMI cutoffs at 144 months:")
    for sx in ("M", "F"):
        print(f"  {sx}: {cutoffs_at(144, sx)}")
