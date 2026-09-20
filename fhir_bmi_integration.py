#!/usr/bin/env python3
"""Minimal FHIR R4 integration for the WHO BMI-for-age calculator.

Reads:
- Patient.gender and Patient.birthDate
- Observation 8302-2 (body height)
- Observation 29463-7 (body weight)

Returns a derived BMI Observation with the WHO BMI-for-age z-score and
percentile. The module is intentionally dependency-free and does not transmit
FHIR data anywhere.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from bmi_zscore import calculate_bmi
from who_reference import (
    DAYS_PER_MONTH,
    bmi_for_age_z,
    classify_bmi_for_age,
    normalize_sex,
    zscore_to_percentile,
)

LOINC_HEIGHT = "8302-2"
LOINC_WEIGHT = "29463-7"
LOINC_BMI = "39156-5"

_CM_PER_INCH = 2.54
_LB_PER_KG = 2.20462262185


@dataclass
class VitalExtraction:
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    issues: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.issues is None:
            self.issues = []


def _to_cm(quantity: Dict[str, Any], issues: List[str]) -> Optional[float]:
    val = quantity.get("value")
    unit = str(quantity.get("unit", "")).strip().lower()
    if val is None:
        issues.append("observation missing valueQuantity.value")
        return None
    try:
        numeric = float(val)
    except (TypeError, ValueError):
        issues.append("height value is not numeric")
        return None
    if numeric <= 0:
        issues.append("height must be positive")
        return None
    if unit.startswith("cm"):
        return numeric
    if unit == "m" or unit.startswith("meter") or unit.startswith("metre"):
        return numeric * 100.0
    if unit.startswith("in"):
        return numeric * _CM_PER_INCH
    issues.append(f"unsupported height unit '{unit}'")
    return None


def _to_kg(quantity: Dict[str, Any], issues: List[str]) -> Optional[float]:
    val = quantity.get("value")
    unit = str(quantity.get("unit", "")).strip().lower()
    if val is None:
        issues.append("observation missing valueQuantity.value")
        return None
    try:
        numeric = float(val)
    except (TypeError, ValueError):
        issues.append("weight value is not numeric")
        return None
    if numeric <= 0:
        issues.append("weight must be positive")
        return None
    if unit.startswith("kg"):
        return numeric
    if unit == "g" or unit.startswith("gram"):
        return numeric / 1000.0
    if unit.startswith("lb"):
        return numeric / _LB_PER_KG
    issues.append(f"unsupported weight unit '{unit}'")
    return None


def _loinc_codes(observation: Dict[str, Any]) -> List[str]:
    codes: List[str] = []
    for coding in observation.get("code", {}).get("coding", []):
        if str(coding.get("system", "")).rstrip("/").endswith("loinc.org"):
            codes.append(str(coding.get("code", "")))
    return codes


def _parse_reference_date(reference_date: Optional[str]) -> datetime.date:
    if reference_date is None:
        return datetime.date.today()
    return datetime.date.fromisoformat(str(reference_date)[:10])


def age_days_from_patient(
    patient: Dict[str, Any],
    reference_date: Optional[str] = None,
) -> int:
    """Age in whole days from Patient.birthDate."""
    if not patient.get("birthDate"):
        raise ValueError("Patient.birthDate required")
    birth = datetime.date.fromisoformat(str(patient["birthDate"])[:10])
    ref = _parse_reference_date(reference_date)
    days = (ref - birth).days
    if days < 0:
        raise ValueError("Patient.birthDate is after the reference date")
    return days


def age_months_from_patient(
    patient: Dict[str, Any],
    reference_date: Optional[str] = None,
) -> float:
    """Age in months using 365.25/12 days per month."""
    return age_days_from_patient(patient, reference_date) / DAYS_PER_MONTH


def extract_vitals(resources: List[Dict[str, Any]]) -> VitalExtraction:
    """Extract first valid height and weight observations."""
    extraction = VitalExtraction()
    assert extraction.issues is not None
    for resource in resources:
        if resource.get("resourceType") != "Observation":
            continue
        codes = _loinc_codes(resource)
        quantity = resource.get("valueQuantity", {})
        if LOINC_HEIGHT in codes and extraction.height_cm is None:
            extraction.height_cm = _to_cm(quantity, extraction.issues)
        if LOINC_WEIGHT in codes and extraction.weight_kg is None:
            extraction.weight_kg = _to_kg(quantity, extraction.issues)
    return extraction


def _reference_date_from_observations(
    observations: List[Dict[str, Any]],
) -> Optional[str]:
    dates: List[str] = []
    for observation in observations:
        raw = observation.get("effectiveDateTime")
        if raw:
            dates.append(str(raw)[:10])
    return max(dates) if dates else None


def compute_z_from_bundle(
    patient: Dict[str, Any],
    observations: List[Dict[str, Any]],
    reference_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Patient plus height/weight observations to WHO BMI-for-age result."""
    vitals = extract_vitals(
        [{"resourceType": "Observation", **observation} for observation in observations]
    )
    out: Dict[str, Any] = {"issues": vitals.issues or []}
    if vitals.height_cm is None or vitals.weight_kg is None:
        out.update(status="error", reason="missing valid height or weight observation")
        return out

    if reference_date is None:
        reference_date = _reference_date_from_observations(observations)

    try:
        age_days = age_days_from_patient(patient, reference_date)
        age_months = age_days / DAYS_PER_MONTH
        gender = patient.get("gender")
        if not gender:
            raise ValueError("Patient.gender required (male or female)")
        sex = normalize_sex(str(gender))
        bmi = calculate_bmi(vitals.weight_kg, vitals.height_cm / 100.0)
        z, ref = bmi_for_age_z(
            bmi,
            age_months,
            sex,
            age_days=age_days if age_months < 60 else None,
        )
    except (TypeError, ValueError) as exc:
        out.update(status="error", reason=str(exc))
        return out

    out.update(
        {
            "status": "ok",
            "patient_age_days": age_days,
            "patient_age_months": round(age_months, 3),
            "height_cm": round(vitals.height_cm, 2),
            "weight_kg": round(vitals.weight_kg, 3),
            "bmi": round(bmi, 2),
            "z": round(z, 3),
            "percentile": round(zscore_to_percentile(z), 2),
            "category": classify_bmi_for_age(z, age_months),
            "reference_standard": ref.standard,
            "sex": sex,
        }
    )
    return out


def build_derived_observation(
    evaluation: Dict[str, Any],
    patient_ref: str = "Patient/example",
) -> Dict[str, Any]:
    """Render a successful evaluation as a FHIR BMI Observation."""
    if evaluation.get("status") != "ok":
        raise ValueError("evaluation must have status='ok'")
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                    }
                ]
            }
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": LOINC_BMI,
                    "display": "Body mass index (BMI) [Ratio]",
                }
            ]
        },
        "subject": {"reference": patient_ref},
        "effectiveDateTime": datetime.datetime.now(datetime.timezone.utc)
        .isoformat()
        .replace("+00:00", "Z"),
        "valueQuantity": {
            "value": evaluation["bmi"],
            "unit": "kg/m2",
            "system": "http://unitsofmeasure.org",
            "code": "kg/m2",
        },
        "component": [
            {
                "code": {"text": "WHO BMI-for-age z-score"},
                "valueQuantity": {"value": evaluation["z"]},
            },
            {
                "code": {"text": "WHO BMI-for-age percentile"},
                "valueQuantity": {"value": evaluation["percentile"], "unit": "%"},
            },
            {
                "code": {"text": "WHO BMI-for-age category"},
                "valueCodeableConcept": {"text": evaluation["category"]},
            },
        ],
    }


if __name__ == "__main__":
    patient = {
        "resourceType": "Patient",
        "gender": "female",
        "birthDate": "2016-03-14",
    }
    observations = [
        {
            "resourceType": "Observation",
            "code": {"coding": [{"system": "http://loinc.org", "code": LOINC_HEIGHT}]},
            "valueQuantity": {"value": 128.5, "unit": "cm"},
            "effectiveDateTime": "2026-03-14T10:00:00Z",
        },
        {
            "resourceType": "Observation",
            "code": {"coding": [{"system": "http://loinc.org", "code": LOINC_WEIGHT}]},
            "valueQuantity": {"value": 33.4, "unit": "kg"},
            "effectiveDateTime": "2026-03-14T10:00:00Z",
        },
    ]
    result = compute_z_from_bundle(patient, observations)
    print(json.dumps(result, indent=2))
