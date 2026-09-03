#!/usr/bin/env python3
"""
BMI Calculator with WHO Classification and Z-Scores
=====================================================

Implements:
  - BMI = weight_kg / (height_m)^2
  - WHO Adult classification (Underweight through Obese III)
  - WHO Child BMI-for-age Z-scores using LMS method with reference tables
  - Percentile calculation from Z-score

Stdlib only. Usage: python bmi_zscore.py --help
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# BMI Calculation
# ---------------------------------------------------------------------------


def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """Calculate BMI = weight / height²."""
    if height_m <= 0:
        raise ValueError(f"Height must be positive, got {height_m}")
    if weight_kg <= 0:
        raise ValueError(f"Weight must be positive, got {weight_kg}")
    return weight_kg / (height_m ** 2)


# ---------------------------------------------------------------------------
# WHO Adult BMI Classification
# ---------------------------------------------------------------------------

ADULT_BMI_CATEGORIES = [
    (0, 16.0, "Severe Thinness"),
    (16.0, 17.0, "Moderate Thinness"),
    (17.0, 18.5, "Mild Thinness"),
    (18.5, 25.0, "Normal"),
    (25.0, 30.0, "Overweight"),
    (30.0, 35.0, "Obese Class I"),
    (35.0, 40.0, "Obese Class II"),
    (40.0, float("inf"), "Obese Class III"),
]


def classify_adult_bmi(bmi: float) -> str:
    """Classify adult BMI per WHO categories."""
    for low, high, category in ADULT_BMI_CATEGORIES:
        if low <= bmi < high:
            return category
    return "Obese Class III"


# ---------------------------------------------------------------------------
# Z-score / Percentile utilities
# ---------------------------------------------------------------------------


def zscore_to_percentile(z: float) -> float:
    """Convert Z-score to percentile using the normal CDF (erf)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0))) * 100.0


def percentile_to_zscore(percentile: float) -> float:
    """Convert percentile (0-100) to Z-score using rational approximation.

    Uses the Abramowitz and Stegun approximation for the inverse normal CDF.
    """
    if percentile <= 0:
        return -float("inf")
    if percentile >= 100:
        return float("inf")

    p = percentile / 100.0
    if p < 0.5:
        t = math.sqrt(-2.0 * math.log(p))
    else:
        t = math.sqrt(-2.0 * math.log(1.0 - p))

    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308

    z = t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t)
    if p < 0.5:
        return -z
    return z


# ---------------------------------------------------------------------------
# WHO Child BMI-for-age Z-scores (LMS method)
# ---------------------------------------------------------------------------
#
# The LMS method: Z = ((X/M)^L - 1) / (L * S)  when L != 0
#                 Z = log(X/M) / S               when L == 0
#
# Simplified WHO reference tables (selected ages, both sexes).
# Full WHO tables have monthly data from 0-60 months and bimonthly 61-228 months.
# These are representative LMS values from the WHO 2007 growth standards.

# Age in months -> (L, M, S) for BMI-for-age
# Male reference data
WHO_BMI_LMS_MALE = {
    0: (-0.2, 13.4, 0.094),
    3: (-0.4, 15.1, 0.089),
    6: (-0.6, 16.3, 0.085),
    9: (-0.7, 16.6, 0.083),
    12: (-0.8, 16.4, 0.082),
    18: (-0.9, 16.0, 0.080),
    24: (-1.0, 15.7, 0.079),
    36: (-1.1, 15.4, 0.078),
    48: (-1.2, 15.3, 0.079),
    60: (-1.3, 15.3, 0.080),
    72: (-1.4, 15.4, 0.082),
    84: (-1.5, 15.6, 0.085),
    96: (-1.6, 15.9, 0.089),
    108: (-1.6, 16.3, 0.094),
    120: (-1.5, 16.8, 0.099),
    132: (-1.4, 17.3, 0.105),
    144: (-1.2, 17.9, 0.111),
    156: (-1.0, 18.5, 0.116),
    168: (-0.8, 19.2, 0.121),
    180: (-0.6, 19.9, 0.124),
    192: (-0.4, 20.6, 0.126),
    204: (-0.3, 21.2, 0.127),
    216: (-0.2, 21.7, 0.126),
    228: (-0.1, 22.2, 0.124),
}

# Female reference data
WHO_BMI_LMS_FEMALE = {
    0: (-0.1, 13.3, 0.095),
    3: (-0.3, 14.6, 0.092),
    6: (-0.5, 15.8, 0.088),
    9: (-0.6, 16.2, 0.086),
    12: (-0.7, 16.1, 0.084),
    18: (-0.8, 15.7, 0.082),
    24: (-0.9, 15.4, 0.081),
    36: (-1.0, 15.2, 0.080),
    48: (-1.1, 15.1, 0.081),
    60: (-1.2, 15.2, 0.083),
    72: (-1.3, 15.3, 0.086),
    84: (-1.4, 15.6, 0.090),
    96: (-1.4, 16.0, 0.095),
    108: (-1.3, 16.5, 0.101),
    120: (-1.2, 17.1, 0.107),
    132: (-1.0, 17.7, 0.113),
    144: (-0.8, 18.4, 0.118),
    156: (-0.6, 19.1, 0.122),
    168: (-0.4, 19.7, 0.124),
    180: (-0.3, 20.3, 0.125),
    192: (-0.2, 20.8, 0.124),
    204: (-0.1, 21.2, 0.122),
    216: (0.0, 21.5, 0.119),
    228: (0.0, 21.8, 0.116),
}


def _interpolate_lms(age_months: float, table: dict) -> tuple[float, float, float]:
    """Interpolate L, M, S values from the reference table for a given age."""
    ages = sorted(table.keys())

    # Clamp to table range
    if age_months <= ages[0]:
        return table[ages[0]]
    if age_months >= ages[-1]:
        return table[ages[-1]]

    # Find bracketing ages
    lower = ages[0]
    upper = ages[-1]
    for a in ages:
        if a <= age_months:
            lower = a
        if a >= age_months and upper == ages[-1]:
            upper = a
            break

    if lower == upper:
        return table[lower]

    # Linear interpolation
    frac = (age_months - lower) / (upper - lower)
    L = table[lower][0] + frac * (table[upper][0] - table[lower][0])
    M = table[lower][1] + frac * (table[upper][1] - table[lower][1])
    S = table[lower][2] + frac * (table[upper][2] - table[lower][2])
    return (L, M, S)


def bmi_zscore_child(bmi: float, age_months: float, sex: str) -> float:
    """Calculate BMI-for-age Z-score using WHO LMS method.

    Z = ((BMI/M)^L - 1) / (L * S)  when L != 0
    Z = log(BMI/M) / S              when L == 0
    """
    sex = sex.upper()
    if sex == "M":
        table = WHO_BMI_LMS_MALE
    elif sex == "F":
        table = WHO_BMI_LMS_FEMALE
    else:
        raise ValueError(f"sex must be 'M' or 'F', got {sex!r}")

    L, M, S = _interpolate_lms(age_months, table)

    if abs(L) < 1e-6:
        z = math.log(bmi / M) / S
    else:
        z = ((bmi / M) ** L - 1.0) / (L * S)

    return z


def classify_child_zscore(z: float) -> str:
    """Classify child BMI Z-score per WHO categories."""
    if z < -3:
        return "Severe wasting"
    elif z < -2:
        return "Wasting"
    elif z < -1:
        return "Risk of overweight/thin"
    elif z <= 1:
        return "Normal"
    elif z <= 2:
        return "Overweight risk"
    elif z <= 3:
        return "Overweight/Obese"
    else:
        return "Severe obesity"


# ---------------------------------------------------------------------------
# Patient result
# ---------------------------------------------------------------------------


@dataclass
class BMIResult:
    patient_id: str
    weight_kg: float
    height_m: float
    age_months: Optional[float] = None
    sex: Optional[str] = None
    bmi: Optional[float] = None
    adult_category: Optional[str] = None
    z_score: Optional[float] = None
    percentile: Optional[float] = None
    child_category: Optional[str] = None
    is_child: bool = False
    warnings: list[str] = field(default_factory=list)


def calculate_patient(
    patient_id: str,
    weight_kg: float,
    height_m: float,
    age_months: Optional[float] = None,
    sex: Optional[str] = None,
) -> BMIResult:
    """Calculate BMI with WHO classification for one patient."""
    warnings: list[str] = []

    if weight_kg <= 0:
        warnings.append(f"Weight {weight_kg} must be positive.")
    if height_m <= 0:
        warnings.append(f"Height {height_m} must be positive.")

    result = BMIResult(
        patient_id=patient_id, weight_kg=weight_kg, height_m=height_m,
        age_months=age_months, sex=sex, warnings=warnings,
    )

    if weight_kg <= 0 or height_m <= 0:
        return result

    result.bmi = round(calculate_bmi(weight_kg, height_m), 2)

    # Determine if child or adult
    is_child = age_months is not None and age_months < 228  # < 19 years
    result.is_child = is_child

    if is_child and sex is not None:
        # Child: compute Z-score and percentile
        result.z_score = round(bmi_zscore_child(result.bmi, age_months, sex.upper()), 2)
        result.percentile = round(zscore_to_percentile(result.z_score), 1)
        result.child_category = classify_child_zscore(result.z_score)
    else:
        # Adult (or age/sex not provided): use adult classification
        result.adult_category = classify_adult_bmi(result.bmi)
        # Also provide Z-score relative to normal adult range
        # Using midpoint 22 and SD ~4 as rough reference
        result.z_score = round((result.bmi - 22.0) / 4.0, 2)
        result.percentile = round(zscore_to_percentile(result.z_score), 1)

    return result


# ---------------------------------------------------------------------------
# CSV batch processing
# ---------------------------------------------------------------------------

CSV_INPUT_FIELDS = ["patient_id", "weight_kg", "height_m", "age_months", "sex"]

CSV_OUTPUT_FIELDS = [
    "patient_id", "weight_kg", "height_m", "age_months", "sex",
    "bmi", "adult_category", "z_score", "percentile", "child_category", "warnings",
]


def process_csv(input_path: str, output_path: str) -> list[BMIResult]:
    """Read patient rows from CSV, compute BMI for each, write results CSV."""
    results: list[BMIResult] = []

    with open(input_path, "r", newline="", encoding="utf-8-sig") as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = [fn.strip() for fn in (reader.fieldnames or [])]
        field_map = {fn.lower().replace(" ", "_"): fn for fn in fieldnames}

        # Check required fields with flexible naming
        has_weight = "weight_kg" in field_map or "weight" in field_map
        has_height = "height_m" in field_map or "height_cm" in field_map or "height" in field_map or "length_cm" in field_map

        if not has_weight or not has_height:
            missing = []
            if not has_weight:
                missing.append("weight_kg")
            if not has_height:
                missing.append("height_m (or height_cm)")
            raise ValueError(f"Input CSV is missing required columns: {missing}")

        rows_data = list(reader)

    # Check if input had custom/rich pediatric columns to preserve or enhance
    has_rich_columns = any(k in field_map for k in ["height_cm", "age_days", "l_param", "m_param", "s_param", "nutritional_classification"])

    for row_num, row in enumerate(rows_data, start=2):
        # Normalize key access
        r = {k.lower().strip().replace(" ", "_"): v for k, v in row.items() if k}

        patient_id = (r.get("patient_id") or r.get("id") or "").strip() or f"row{row_num}"
        row_warnings: list[str] = []

        # Parse weight
        weight_kg_val = None
        for w_key in ["weight_kg", "weight"]:
            if w_key in r and r[w_key].strip():
                try:
                    weight_kg_val = float(r[w_key])
                    break
                except ValueError:
                    pass

        # Parse height
        height_m_val = None
        if "height_m" in r and r["height_m"].strip():
            try:
                height_m_val = float(r["height_m"])
            except ValueError:
                pass
        elif "height_cm" in r and r["height_cm"].strip():
            try:
                height_m_val = float(r["height_cm"]) / 100.0
            except ValueError:
                pass
        elif "length_cm" in r and r["length_cm"].strip():
            try:
                height_m_val = float(r["length_cm"]) / 100.0
            except ValueError:
                pass
        elif "height" in r and r["height"].strip():
            try:
                val = float(r["height"])
                height_m_val = val / 100.0 if val > 3.0 else val
            except ValueError:
                pass

        if weight_kg_val is None or height_m_val is None:
            row_warnings.append("Could not parse required fields: weight/height")
            results.append(BMIResult(patient_id=patient_id, weight_kg=0, height_m=0, warnings=row_warnings))
            continue

        # Parse age
        age_months = None
        if "age_months" in r and r["age_months"].strip():
            try:
                age_months = float(r["age_months"])
            except ValueError:
                pass
        elif "age_days" in r and r["age_days"].strip():
            try:
                age_months = round(float(r["age_days"]) / 30.4375, 2)
            except ValueError:
                pass
        elif "age" in r and r["age"].strip():
            try:
                age_months = float(r["age"])
            except ValueError:
                pass

        sex_val = (r.get("sex") or r.get("gender") or "").strip().upper() or None
        if sex_val:
            if sex_val.startswith("M"):
                sex_val = "M"
            elif sex_val.startswith("F"):
                sex_val = "F"

        result = calculate_patient(
            patient_id=patient_id, weight_kg=weight_kg_val, height_m=height_m_val,
            age_months=age_months, sex=sex_val,
        )
        result.warnings = row_warnings + result.warnings
        results.append(result)

    # Determine output columns: standard or extended based on input format
    if has_rich_columns:
        output_fields = [
            "patient_id", "age_months", "age_days", "sex", "height_cm", "weight_kg",
            "bmi", "l_param", "m_param", "s_param", "z_score", "percentile",
            "nutritional_classification", "warnings",
        ]
        with open(output_path, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=output_fields)
            writer.writeheader()
            for r, orig_row in zip(results, rows_data):
                orig_r = {k.lower().strip().replace(" ", "_"): v for k, v in orig_row.items() if k}
                h_cm = f"{r.height_m * 100.0:.1f}" if r.height_m else orig_r.get("height_cm", "")
                age_d = orig_r.get("age_days", "")
                if not age_d and r.age_months is not None:
                    age_d = str(int(round(r.age_months * 30.4375)))

                # LMS lookup if child
                l_str, m_str, s_str = "", "", ""
                if r.is_child and r.age_months is not None and r.sex:
                    tbl = WHO_BMI_LMS_MALE if r.sex == "M" else WHO_BMI_LMS_FEMALE
                    L, M, S = _interpolate_lms(r.age_months, tbl)
                    l_str, m_str, s_str = f"{L:.2f}", f"{M:.2f}", f"{S:.4f}"

                # Classification label
                class_label = ""
                if r.z_score is not None and r.is_child:
                    if r.z_score < -3.0:
                        class_label = "severe wasting"
                    elif r.z_score < -2.0:
                        class_label = "wasted"
                    elif r.z_score <= 1.0:
                        class_label = "normal"
                    elif r.z_score <= 2.0:
                        class_label = "risk of overweight"
                    elif r.z_score <= 3.0:
                        class_label = "overweight"
                    else:
                        class_label = "obese"
                elif r.adult_category:
                    class_label = r.adult_category

                writer.writerow({
                    "patient_id": r.patient_id,
                    "age_months": f"{r.age_months:.1f}" if r.age_months is not None else "",
                    "age_days": age_d,
                    "sex": r.sex or "",
                    "height_cm": h_cm,
                    "weight_kg": f"{r.weight_kg:.1f}" if r.weight_kg else "",
                    "bmi": _fmt(r.bmi),
                    "l_param": l_str,
                    "m_param": m_str,
                    "s_param": s_str,
                    "z_score": _fmt(r.z_score),
                    "percentile": _fmt(r.percentile),
                    "nutritional_classification": class_label,
                    "warnings": " | ".join(r.warnings),
                })
    else:
        with open(output_path, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=CSV_OUTPUT_FIELDS)
            writer.writeheader()
            for r in results:
                writer.writerow({
                    "patient_id": r.patient_id,
                    "weight_kg": r.weight_kg,
                    "height_m": r.height_m,
                    "age_months": r.age_months if r.age_months is not None else "",
                    "sex": r.sex or "",
                    "bmi": _fmt(r.bmi),
                    "adult_category": r.adult_category or "",
                    "z_score": _fmt(r.z_score),
                    "percentile": _fmt(r.percentile),
                    "child_category": r.child_category or "",
                    "warnings": " | ".join(r.warnings),
                })

    return results


def _fmt(value: Optional[float]) -> str:
    return "" if value is None else f"{value:.2f}"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bmi_zscore",
        description="BMI Calculator with WHO Classification and Z-scores.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("single", help="Calculate BMI for one patient")
    single.add_argument("--id", dest="patient_id", default="patient", help="Patient identifier")
    single.add_argument("--weight", type=float, required=True, help="Weight in kg")
    single.add_argument("--height", type=float, required=True, help="Height in meters")
    single.add_argument("--age-months", type=float, default=None, help="Age in months (for child Z-score)")
    single.add_argument("--sex", default=None, choices=["M", "F", "m", "f"], help="Sex (for child Z-score)")

    batch = subparsers.add_parser("batch", help="Batch CSV processing")
    batch.add_argument("-i", "--input", required=True, help="Input CSV path")
    batch.add_argument("-o", "--output", required=True, help="Output CSV path")

    return parser


def _print_single_result(result: BMIResult) -> None:
    print(f"Patient: {result.patient_id}")
    print(f"  Weight: {result.weight_kg:.1f} kg  Height: {result.height_m:.2f} m")
    if result.age_months:
        years = result.age_months / 12.0
        print(f"  Age: {result.age_months:.0f} months ({years:.1f} years)")
    if result.sex:
        print(f"  Sex: {result.sex}")

    print(f"\n  BMI: {result.bmi:.2f} kg/m²")

    if result.is_child and result.child_category:
        print(f"  Z-score: {result.z_score:.2f}")
        print(f"  Percentile: {result.percentile:.1f}%")
        print(f"  WHO Category: {result.child_category}")
    else:
        if result.adult_category:
            print(f"  WHO Category: {result.adult_category}")
        if result.z_score is not None:
            print(f"  Z-score (vs adult ref): {result.z_score:.2f}")
            print(f"  Percentile (approx): {result.percentile:.1f}%")

    if result.warnings:
        print("\n  Warnings:")
        for w in result.warnings:
            print(f"    - {w}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "single":
        result = calculate_patient(
            patient_id=args.patient_id, weight_kg=args.weight, height_m=args.height,
            age_months=args.age_months, sex=args.sex,
        )
        _print_single_result(result)
        return 0

    if args.command == "batch":
        results = process_csv(args.input, args.output)
        print(f"Processed {len(results)} patients -> {args.output}")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
