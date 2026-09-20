#!/usr/bin/env python3
"""WHO BMI-for-age reference utilities.

The reference data files are copied from the World Health Organization's
official anthro (0-5 years) and anthroplus (5-19 years) repositories.
The implementation follows the LMS/Box-Cox transformation and WHO's adjusted
z-score extrapolation beyond +/-3 SD.

This module has no third-party runtime dependencies.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

DATA_DIR = Path(__file__).resolve().parent / "data"
WHO_2006_BMI_PATH = DATA_DIR / "who_bmi_0_5.tsv"
WHO_2007_BMI_PATH = DATA_DIR / "who_bmi_5_19.tsv"

DAYS_PER_MONTH = 365.25 / 12.0
WHO_2006_MAX_MONTHS = 60.0
WHO_2007_MIN_MONTHS = 60.0
WHO_2007_MAX_EXCLUSIVE_MONTHS = 229.0


@dataclass(frozen=True)
class LMSReference:
    """Sex- and age-specific LMS parameters used for BMI-for-age."""

    sex: str
    age_months: float
    L: float
    M: float
    S: float
    standard: str
    age_days: Optional[int] = None
    measurement_mode: Optional[str] = None


def normalize_sex(sex: str) -> str:
    """Normalize supported sex labels to M or F."""
    value = str(sex).strip().upper()
    if value in {"M", "MALE", "1"}:
        return "M"
    if value in {"F", "FEMALE", "2"}:
        return "F"
    raise ValueError("sex must be M/male/1 or F/female/2")


def _sex_code(sex: str) -> int:
    return 1 if normalize_sex(sex) == "M" else 2


@lru_cache(maxsize=1)
def _load_who_2006() -> dict[tuple[int, int], tuple[float, float, float, str]]:
    """Load day-level WHO Child Growth Standards BMI-for-age parameters."""
    rows: dict[tuple[int, int], tuple[float, float, float, str]] = {}
    with WHO_2006_BMI_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            key = (int(row["sex"]), int(row["age"]))
            rows[key] = (
                float(row["l"]),
                float(row["m"]),
                float(row["s"]),
                row.get("loh", ""),
            )
    if not rows:
        raise RuntimeError(f"WHO reference table is empty: {WHO_2006_BMI_PATH}")
    return rows


@lru_cache(maxsize=1)
def _load_who_2007() -> dict[tuple[int, int], tuple[float, float, float]]:
    """Load monthly WHO 2007 BMI-for-age reference parameters."""
    rows: dict[tuple[int, int], tuple[float, float, float]] = {}
    with WHO_2007_BMI_PATH.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            key = (int(row["sex"]), int(row["age"]))
            rows[key] = (float(row["l"]), float(row["m"]), float(row["s"]))
    if not rows:
        raise RuntimeError(f"WHO reference table is empty: {WHO_2007_BMI_PATH}")
    return rows


def _round_half_up(value: float) -> int:
    return int(math.floor(value + 0.5))


def reference_for_age(
    age_months: Optional[float],
    sex: str,
    *,
    age_days: Optional[float] = None,
) -> LMSReference:
    """Return WHO BMI-for-age LMS parameters for a child or adolescent.

    For ages below 60 months, WHO 2006 uses day-level reference data. If
    age_days is omitted, it is approximated from age_months using 365.25/12
    days per month. For ages 60 to <229 months, WHO 2007 monthly parameters
    are linearly interpolated for fractional months, matching AnthroPlus.
    """
    sx = normalize_sex(sex)
    code = _sex_code(sx)

    if age_months is None:
        if age_days is None:
            raise ValueError("age_months or age_days is required")
        if not math.isfinite(float(age_days)) or float(age_days) < 0:
            raise ValueError("age_days must be a finite non-negative number")
        age_months = float(age_days) / DAYS_PER_MONTH

    age_months = float(age_months)
    if not math.isfinite(age_months) or age_months < 0:
        raise ValueError("age_months must be a finite non-negative number")

    if age_months < WHO_2006_MAX_MONTHS:
        if age_days is None:
            day = _round_half_up(age_months * DAYS_PER_MONTH)
        else:
            if not math.isfinite(float(age_days)) or float(age_days) < 0:
                raise ValueError("age_days must be a finite non-negative number")
            day = _round_half_up(float(age_days))

        table = _load_who_2006()
        key = (code, day)
        if key not in table:
            raise ValueError(
                f"age {age_months:.3f} months ({day} days) is outside the "
                "WHO 2006 BMI-for-age reference range"
            )
        L, M, S, loh = table[key]
        return LMSReference(
            sex=sx,
            age_months=age_months,
            age_days=day,
            L=L,
            M=M,
            S=S,
            standard="WHO Child Growth Standards 2006",
            measurement_mode=loh or None,
        )

    if WHO_2007_MIN_MONTHS <= age_months < WHO_2007_MAX_EXCLUSIVE_MONTHS:
        table = _load_who_2007()
        low = int(math.floor(age_months))
        high = int(math.ceil(age_months))
        low_key = (code, low)
        high_key = (code, high)
        if low_key not in table or high_key not in table:
            raise ValueError(
                f"age {age_months:.3f} months is outside the WHO 2007 "
                "BMI-for-age reference range"
            )

        l0, m0, s0 = table[low_key]
        if low == high:
            L, M, S = l0, m0, s0
        else:
            l1, m1, s1 = table[high_key]
            fraction = age_months - low
            L = l0 + fraction * (l1 - l0)
            M = m0 + fraction * (m1 - m0)
            S = s0 + fraction * (s1 - s0)

        return LMSReference(
            sex=sx,
            age_months=age_months,
            L=L,
            M=M,
            S=S,
            standard="WHO Growth Reference 2007",
        )

    raise ValueError(
        "WHO BMI-for-age reference is available from birth to <229 months"
    )


def _measure_at_z(z: float, L: float, M: float, S: float) -> float:
    if abs(L) < 1e-12:
        return M * math.exp(S * z)
    base = 1.0 + L * S * z
    if base <= 0:
        raise ValueError("LMS parameters produce an invalid transformed value")
    return M * (base ** (1.0 / L))


def raw_lms_z(value: float, L: float, M: float, S: float) -> float:
    """Compute the unadjusted LMS z-score."""
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("BMI must be a finite positive number")
    if M <= 0 or S <= 0:
        raise ValueError("invalid LMS reference parameters")
    if abs(L) < 1e-12:
        return math.log(value / M) / S
    return ((value / M) ** L - 1.0) / (L * S)


def adjusted_lms_z(value: float, L: float, M: float, S: float) -> float:
    """Compute WHO's adjusted LMS z-score, including extrapolation beyond +/-3 SD."""
    z = raw_lms_z(value, L, M, S)
    if z > 3.0:
        sd3 = _measure_at_z(3.0, L, M, S)
        sd2 = _measure_at_z(2.0, L, M, S)
        return 3.0 + (value - sd3) / (sd3 - sd2)
    if z < -3.0:
        sd_neg3 = _measure_at_z(-3.0, L, M, S)
        sd_neg2 = _measure_at_z(-2.0, L, M, S)
        return -3.0 + (value - sd_neg3) / (sd_neg2 - sd_neg3)
    return z


def bmi_for_age_z(
    bmi: float,
    age_months: Optional[float],
    sex: str,
    *,
    age_days: Optional[float] = None,
) -> tuple[float, LMSReference]:
    """Return WHO BMI-for-age adjusted z-score and the LMS reference used."""
    ref = reference_for_age(age_months, sex, age_days=age_days)
    return adjusted_lms_z(bmi, ref.L, ref.M, ref.S), ref


def zscore_to_percentile(z: float) -> float:
    """Convert a z-score to a standard-normal percentile."""
    return 0.5 * (1.0 + math.erf(float(z) / math.sqrt(2.0))) * 100.0


def classify_bmi_for_age(z: float, age_months: float) -> str:
    """Classify BMI-for-age using WHO age-specific z-score cut-offs."""
    z = float(z)
    age_months = float(age_months)
    if not math.isfinite(z) or not math.isfinite(age_months):
        raise ValueError("z-score and age_months must be finite")
    if age_months < 0 or age_months >= WHO_2007_MAX_EXCLUSIVE_MONTHS:
        raise ValueError("age is outside the WHO BMI-for-age reference range")

    if z < -3.0:
        return "Very low BMI-for-age" if age_months < 60.0 else "Severe thinness"
    if z < -2.0:
        return "Low BMI-for-age" if age_months < 60.0 else "Thinness"
    if age_months < 60.0:
        if z > 3.0:
            return "Obesity"
        if z > 2.0:
            return "Overweight"
        if z > 1.0:
            return "Risk of overweight"
        return "Normal"
    if z > 2.0:
        return "Obesity"
    if z > 1.0:
        return "Overweight"
    return "Normal"
