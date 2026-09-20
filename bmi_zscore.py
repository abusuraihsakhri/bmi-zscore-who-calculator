#!/usr/bin/env python3
"""BMI calculator with WHO BMI-for-age z-scores.

Core features:
- BMI from weight and height.
- WHO adult BMI categories.
- WHO Child Growth Standards 2006 BMI-for-age (birth to <60 months).
- WHO Growth Reference 2007 BMI-for-age (60 to <229 months).
- Standard-normal percentile conversion.
- Single-patient and CSV command-line workflows.

Pediatric calculations use the local WHO reference tables via who_reference.py.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from dataclasses import dataclass, field
from typing import Optional

from who_reference import (
    DAYS_PER_MONTH,
    WHO_2007_MAX_EXCLUSIVE_MONTHS,
    bmi_for_age_z as _who_bmi_for_age_z,
    classify_bmi_for_age,
    normalize_sex,
    reference_for_age,
    zscore_to_percentile as _reference_percentile,
)


def calculate_bmi(weight_kg: float, height_m: float) -> float:
    """Calculate BMI in kg/m²."""
    weight_kg = float(weight_kg)
    height_m = float(height_m)
    if not math.isfinite(weight_kg) or weight_kg <= 0:
        raise ValueError(f"Weight must be a finite positive number, got {weight_kg}")
    if not math.isfinite(height_m) or height_m <= 0:
        raise ValueError(f"Height must be a finite positive number, got {height_m}")
    return weight_kg / (height_m ** 2)


ADULT_BMI_CATEGORIES = [
    (0.0, 16.0, "Severe Thinness"),
    (16.0, 17.0, "Moderate Thinness"),
    (17.0, 18.5, "Mild Thinness"),
    (18.5, 25.0, "Normal"),
    (25.0, 30.0, "Overweight"),
    (30.0, 35.0, "Obese Class I"),
    (35.0, 40.0, "Obese Class II"),
    (40.0, float("inf"), "Obese Class III"),
]


def classify_adult_bmi(bmi: float) -> str:
    """Classify adult BMI using WHO category thresholds."""
    bmi = float(bmi)
    if not math.isfinite(bmi) or bmi <= 0:
        raise ValueError("BMI must be a finite positive number")
    for low, high, category in ADULT_BMI_CATEGORIES:
        if low <= bmi < high:
            return category
    raise RuntimeError("unreachable BMI category")


def zscore_to_percentile(z: float) -> float:
    """Convert z-score to standard-normal percentile."""
    return _reference_percentile(z)


def percentile_to_zscore(percentile: float) -> float:
    """Convert percentile (0-100) to z-score using a rational approximation."""
    percentile = float(percentile)
    if not math.isfinite(percentile):
        raise ValueError("percentile must be finite")
    if percentile <= 0:
        return -float("inf")
    if percentile >= 100:
        return float("inf")

    p = percentile / 100.0
    t = math.sqrt(-2.0 * math.log(p if p < 0.5 else 1.0 - p))
    c0, c1, c2 = 2.515517, 0.802853, 0.010328
    d1, d2, d3 = 1.432788, 0.189269, 0.001308
    z = t - (c0 + c1 * t + c2 * t * t) / (
        1.0 + d1 * t + d2 * t * t + d3 * t * t * t
    )
    return -z if p < 0.5 else z


def bmi_zscore_child(
    bmi: float,
    age_months: Optional[float],
    sex: str,
    *,
    age_days: Optional[float] = None,
) -> float:
    """Calculate WHO BMI-for-age adjusted z-score."""
    z, _ = _who_bmi_for_age_z(bmi, age_months, sex, age_days=age_days)
    return z


def classify_child_zscore(z: float, age_months: float = 60.0) -> str:
    """Classify pediatric BMI-for-age z-score for the supplied age."""
    return classify_bmi_for_age(z, age_months)


@dataclass
class BMIResult:
    patient_id: str
    weight_kg: float
    height_m: float
    age_months: Optional[float] = None
    age_days: Optional[float] = None
    sex: Optional[str] = None
    bmi: Optional[float] = None
    adult_category: Optional[str] = None
    z_score: Optional[float] = None
    percentile: Optional[float] = None
    child_category: Optional[str] = None
    reference_standard: Optional[str] = None
    is_child: bool = False
    warnings: list[str] = field(default_factory=list)


def calculate_patient(
    patient_id: str,
    weight_kg: float,
    height_m: float,
    age_months: Optional[float] = None,
    sex: Optional[str] = None,
    age_days: Optional[float] = None,
) -> BMIResult:
    """Calculate BMI and, when applicable, WHO BMI-for-age z-score."""
    warnings: list[str] = []
    result = BMIResult(
        patient_id=patient_id,
        weight_kg=weight_kg,
        height_m=height_m,
        age_months=age_months,
        age_days=age_days,
        sex=sex,
        warnings=warnings,
    )

    try:
        result.bmi = round(calculate_bmi(weight_kg, height_m), 2)
    except (TypeError, ValueError) as exc:
        warnings.append(str(exc))
        return result

    if age_days is not None:
        try:
            age_days_value = float(age_days)
            if not math.isfinite(age_days_value) or age_days_value < 0:
                raise ValueError("age_days must be a finite non-negative number")
            derived_months = age_days_value / DAYS_PER_MONTH
            if derived_months < 60.0:
                if (
                    age_months is not None
                    and abs(float(age_months) - derived_months) > 0.55
                ):
                    warnings.append(
                        "age_months and age_days differ materially; exact age_days "
                        "was used for the under-5 WHO reference."
                    )
                age_months = derived_months
                result.age_months = age_months
            elif age_months is None:
                age_months = derived_months
                result.age_months = age_months
        except (TypeError, ValueError) as exc:
            warnings.append(str(exc))
            return result

    if age_months is not None:
        try:
            age_months = float(age_months)
            if not math.isfinite(age_months) or age_months < 0:
                raise ValueError("age_months must be a finite non-negative number")
            result.age_months = age_months
        except (TypeError, ValueError) as exc:
            warnings.append(str(exc))
            return result

    if age_months is not None and age_months < WHO_2007_MAX_EXCLUSIVE_MONTHS:
        result.is_child = True
        if not sex:
            warnings.append("Sex is required for WHO pediatric BMI-for-age z-score calculation.")
            return result
        try:
            result.sex = normalize_sex(sex)
            z, ref = _who_bmi_for_age_z(
                result.bmi,
                age_months,
                result.sex,
                age_days=age_days,
            )
            result.z_score = round(z, 2)
            result.percentile = round(zscore_to_percentile(z), 1)
            result.child_category = classify_bmi_for_age(z, age_months)
            result.reference_standard = ref.standard
            if age_months < 60 and age_days is None:
                warnings.append(
                    "Under-5 age was supplied in months; day-level WHO reference age "
                    "was approximated using 365.25/12 days per month."
                )
        except (TypeError, ValueError) as exc:
            warnings.append(str(exc))
        return result

    result.adult_category = classify_adult_bmi(result.bmi)
    return result


CSV_OUTPUT_FIELDS = [
    "patient_id",
    "weight_kg",
    "height_m",
    "age_months",
    "sex",
    "bmi",
    "adult_category",
    "z_score",
    "percentile",
    "child_category",
    "warnings",
]


def _parse_float(value: Optional[str]) -> Optional[float]:
    if value is None or not str(value).strip():
        return None
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def process_csv(input_path: str, output_path: str) -> list[BMIResult]:
    """Read patient rows from CSV, compute BMI, and write a results CSV."""
    results: list[BMIResult] = []

    with open(input_path, "r", newline="", encoding="utf-8-sig") as f_in:
        reader = csv.DictReader(f_in)
        fieldnames = [fn.strip() for fn in (reader.fieldnames or [])]
        field_map = {fn.lower().replace(" ", "_"): fn for fn in fieldnames}

        has_weight = "weight_kg" in field_map or "weight" in field_map
        has_height = any(
            key in field_map for key in ("height_m", "height_cm", "height", "length_cm")
        )
        if not has_weight or not has_height:
            missing = []
            if not has_weight:
                missing.append("weight_kg")
            if not has_height:
                missing.append("height_m (or height_cm)")
            raise ValueError(f"Input CSV is missing required columns: {missing}")
        rows_data = list(reader)

    has_rich_columns = any(
        key in field_map
        for key in (
            "height_cm",
            "age_days",
            "l_param",
            "m_param",
            "s_param",
            "nutritional_classification",
        )
    )

    for row_num, row in enumerate(rows_data, start=2):
        r = {k.lower().strip().replace(" ", "_"): v for k, v in row.items() if k}
        patient_id = (r.get("patient_id") or r.get("id") or "").strip() or f"row{row_num}"
        row_warnings: list[str] = []

        weight_kg_val = _parse_float(r.get("weight_kg") or r.get("weight"))

        height_m_val = _parse_float(r.get("height_m"))
        if height_m_val is None:
            height_cm_val = _parse_float(r.get("height_cm") or r.get("length_cm"))
            if height_cm_val is not None:
                height_m_val = height_cm_val / 100.0
        if height_m_val is None:
            generic_height = _parse_float(r.get("height"))
            if generic_height is not None:
                height_m_val = generic_height / 100.0 if generic_height > 3.0 else generic_height

        if weight_kg_val is None or height_m_val is None:
            row_warnings.append("Could not parse required fields: weight/height")
            results.append(
                BMIResult(
                    patient_id=patient_id,
                    weight_kg=weight_kg_val or 0.0,
                    height_m=height_m_val or 0.0,
                    warnings=row_warnings,
                )
            )
            continue

        age_months = _parse_float(r.get("age_months") or r.get("age"))
        age_days = _parse_float(r.get("age_days"))
        if age_months is None and age_days is not None:
            age_months = age_days / DAYS_PER_MONTH

        sex_val = (r.get("sex") or r.get("gender") or "").strip() or None

        result = calculate_patient(
            patient_id=patient_id,
            weight_kg=weight_kg_val,
            height_m=height_m_val,
            age_months=age_months,
            age_days=age_days,
            sex=sex_val,
        )
        result.warnings = row_warnings + result.warnings
        results.append(result)

    if has_rich_columns:
        output_fields = [
            "patient_id",
            "age_months",
            "age_days",
            "sex",
            "height_cm",
            "weight_kg",
            "bmi",
            "l_param",
            "m_param",
            "s_param",
            "z_score",
            "percentile",
            "nutritional_classification",
            "warnings",
        ]
        with open(output_path, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=output_fields)
            writer.writeheader()
            for result, original in zip(results, rows_data):
                original_row = {
                    k.lower().strip().replace(" ", "_"): v
                    for k, v in original.items()
                    if k
                }
                height_cm = (
                    f"{result.height_m * 100.0:.1f}"
                    if result.height_m
                    else original_row.get("height_cm", "")
                )
                age_day_value = original_row.get("age_days", "")
                if not age_day_value and result.age_months is not None:
                    age_day_value = str(int(math.floor(result.age_months * DAYS_PER_MONTH + 0.5)))

                l_str = m_str = s_str = ""
                if result.is_child and result.z_score is not None and result.sex:
                    try:
                        ref = reference_for_age(
                            result.age_months,
                            result.sex,
                            age_days=result.age_days,
                        )
                        l_str = f"{ref.L:.4f}"
                        m_str = f"{ref.M:.4f}"
                        s_str = f"{ref.S:.5f}"
                    except ValueError:
                        pass

                writer.writerow(
                    {
                        "patient_id": result.patient_id,
                        "age_months": _fmt(result.age_months),
                        "age_days": age_day_value,
                        "sex": result.sex or "",
                        "height_cm": height_cm,
                        "weight_kg": _fmt(result.weight_kg),
                        "bmi": _fmt(result.bmi),
                        "l_param": l_str,
                        "m_param": m_str,
                        "s_param": s_str,
                        "z_score": _fmt(result.z_score),
                        "percentile": _fmt(result.percentile),
                        "nutritional_classification": (
                            result.child_category or result.adult_category or ""
                        ),
                        "warnings": " | ".join(result.warnings),
                    }
                )
    else:
        with open(output_path, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=CSV_OUTPUT_FIELDS)
            writer.writeheader()
            for result in results:
                writer.writerow(
                    {
                        "patient_id": result.patient_id,
                        "weight_kg": result.weight_kg,
                        "height_m": result.height_m,
                        "age_months": (
                            result.age_months if result.age_months is not None else ""
                        ),
                        "sex": result.sex or "",
                        "bmi": _fmt(result.bmi),
                        "adult_category": result.adult_category or "",
                        "z_score": _fmt(result.z_score),
                        "percentile": _fmt(result.percentile),
                        "child_category": result.child_category or "",
                        "warnings": " | ".join(result.warnings),
                    }
                )

    return results


def _fmt(value: Optional[float]) -> str:
    return "" if value is None else f"{value:.2f}"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bmi_zscore",
        description="BMI calculator with WHO pediatric BMI-for-age z-scores.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("single", help="Calculate BMI for one person")
    single.add_argument("--id", dest="patient_id", default="patient", help="Identifier")
    single.add_argument("--weight", type=float, required=True, help="Weight in kg")
    single.add_argument("--height", type=float, required=True, help="Height in metres")
    single.add_argument("--age-months", type=float, default=None, help="Age in months")
    single.add_argument(
        "--age-days",
        type=float,
        default=None,
        help="Exact age in days for under-5 WHO calculations",
    )
    single.add_argument(
        "--sex",
        default=None,
        choices=["M", "F", "m", "f"],
        help="Sex used by the WHO reference (M/F)",
    )

    batch = subparsers.add_parser("batch", help="Batch CSV processing")
    batch.add_argument("-i", "--input", required=True, help="Input CSV path")
    batch.add_argument("-o", "--output", required=True, help="Output CSV path")
    return parser


def _print_single_result(result: BMIResult) -> None:
    print(f"Patient: {result.patient_id}")
    print(f"  Weight: {result.weight_kg:.1f} kg  Height: {result.height_m:.2f} m")
    if result.age_months is not None:
        print(
            f"  Age: {result.age_months:.1f} months "
            f"({result.age_months / 12.0:.1f} years)"
        )
    if result.sex:
        print(f"  Sex: {result.sex}")

    if result.bmi is not None:
        print(f"\n  BMI: {result.bmi:.2f} kg/m²")

    if result.is_child and result.child_category:
        print(f"  Z-score: {result.z_score:.2f}")
        print(f"  Percentile: {result.percentile:.1f}%")
        print(f"  WHO category: {result.child_category}")
        if result.reference_standard:
            print(f"  Reference: {result.reference_standard}")
    elif result.adult_category:
        print(f"  WHO category: {result.adult_category}")

    if result.warnings:
        print("\n  Warnings:")
        for warning in result.warnings:
            print(f"    - {warning}")


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.command == "single":
        result = calculate_patient(
            patient_id=args.patient_id,
            weight_kg=args.weight,
            height_m=args.height,
            age_months=args.age_months,
            age_days=args.age_days,
            sex=args.sex,
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
