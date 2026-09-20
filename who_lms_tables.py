#!/usr/bin/env python3
"""Compatibility helpers for the WHO 2007 BMI-for-age reference.

This module preserves the original public helper API while delegating to the
verified reference engine in who_reference.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict

from who_reference import (
    adjusted_lms_z,
    normalize_sex,
    reference_for_age,
    zscore_to_percentile,
)

MIN_AGE_MONTHS = 60
MAX_AGE_MONTHS = 228


@dataclass(frozen=True)
class LMSResult:
    age_months: float
    sex: str
    L: float
    M: float
    S: float


def lms_lookup(age_months: float, sex: str) -> LMSResult:
    """Return interpolated WHO 2007 LMS parameters for age 60-228 months."""
    age_months = float(age_months)
    if not MIN_AGE_MONTHS <= age_months <= MAX_AGE_MONTHS:
        raise ValueError(
            f"Age {age_months} months outside WHO 2007 BMI-for-age range "
            f"[{MIN_AGE_MONTHS}, {MAX_AGE_MONTHS}]"
        )
    ref = reference_for_age(age_months, normalize_sex(sex))
    return LMSResult(
        age_months=age_months,
        sex=ref.sex,
        L=ref.L,
        M=ref.M,
        S=ref.S,
    )


def percentile_from_z(z: float) -> float:
    """Standard-normal percentile from a z-score."""
    return zscore_to_percentile(z)


def bmi_for_age_z(bmi: float, age_months: float, sex: str) -> Dict[str, object]:
    """WHO adjusted BMI-for-age z-score and percentile for ages 5-19."""
    ref = lms_lookup(age_months, sex)
    z = adjusted_lms_z(float(bmi), ref.L, ref.M, ref.S)
    return {
        "bmi": round(float(bmi), 2),
        "z": round(z, 3),
        "percentile": round(percentile_from_z(z), 2),
        "lms": {"L": ref.L, "M": ref.M, "S": ref.S},
        "sex": ref.sex,
        "age_months": age_months,
    }


def classify_weight_status(z: float) -> str:
    """WHO 5-19 BMI-for-age classification."""
    z = float(z)
    if z < -3:
        return "severe_thinness"
    if z < -2:
        return "thinness"
    if z > 2:
        return "obesity"
    if z > 1:
        return "overweight"
    return "normal"


def bmi_from_anthropometrics(weight_kg: float, height_cm: float) -> float:
    """BMI in kg/m² from kg and centimetres."""
    weight_kg = float(weight_kg)
    height_cm = float(height_cm)
    if (
        not math.isfinite(weight_kg)
        or not math.isfinite(height_cm)
        or weight_kg <= 0
        or height_cm <= 0
    ):
        raise ValueError("weight and height must be finite positive numbers")
    return weight_kg / ((height_cm / 100.0) ** 2)


def evaluate_child(
    weight_kg: float,
    height_cm: float,
    age_months: float,
    sex: str,
) -> Dict[str, object]:
    """Evaluate BMI, WHO z-score, percentile, and 5-19 classification."""
    result = bmi_for_age_z(
        bmi_from_anthropometrics(weight_kg, height_cm),
        age_months,
        sex,
    )
    result["category"] = classify_weight_status(float(result["z"]))
    return result


def cutoffs_at(age_months: float, sex: str) -> Dict[str, float]:
    """Absolute BMI values corresponding to WHO 5-19 z-score cut-offs."""
    ref = lms_lookup(age_months, sex)

    def bmi_at_z(z: float) -> float:
        if abs(ref.L) < 1e-12:
            return ref.M * math.exp(ref.S * z)
        base = 1.0 + ref.L * ref.S * z
        if base <= 0:
            raise ValueError("LMS parameters produce an invalid cut-off")
        return ref.M * (base ** (1.0 / ref.L))

    return {
        "severe_thinness_lt": round(bmi_at_z(-3), 2),
        "thinness_lt": round(bmi_at_z(-2), 2),
        "overweight_gt": round(bmi_at_z(1), 2),
        "obesity_gt": round(bmi_at_z(2), 2),
    }


if __name__ == "__main__":
    for sx in ("M", "F"):
        print(sx, evaluate_child(28.0, 132.0, 132, sx))
