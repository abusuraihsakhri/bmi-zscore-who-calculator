#!/usr/bin/env python3
"""
FHIR R4 integration for the WHO BMI z-score calculator.

Reads a minimal bundle of FHIR resources:
  - Patient            : gender + birthDate -> age in months
  - Observation        : LOINC 8302-2 (body height), 29463-7 (body weight)

and emits a derived FHIR Observation carrying the computed BMI
(LOINC 39156-5) together with the WHO BMI-for-age z-score and percentile.
Unit conversion handles cm/m/inch and kg/lb. Stdlib only.
"""

import datetime
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from who_lms_tables import evaluate_child

LOINC_HEIGHT = "8302-2"
LOINC_WEIGHT = "29463-7"
LOINC_BMI = "39156-5"

_CM_PER_INCH = 2.54
_LB_PER_KG = 2.20462262185


@dataclass
class VitalExtraction:
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    issues: List[str] = None

    def __post_init__(self):
        if self.issues is None:
            self.issues = []


def _to_cm(quantity: Dict[str, Any], issues: List[str]) -> Optional[float]:
    val, unit = quantity.get("value"), str(quantity.get("unit", "")).lower()
    if val is None:
        issues.append("observation missing valueQuantity.value")
        return None
    if unit.startswith("cm"):
        return float(val)
    if unit.startswith("m") and not unit.startswith("mm"):
        return float(val) * 100.0
    if unit.startswith("in"):
        return float(val) * _CM_PER_INCH
    issues.append(f"unsupported height unit '{unit}'")
    return None


def _to_kg(quantity: Dict[str, Any], issues: List[str]) -> Optional[float]:
    val, unit = quantity.get("value"), str(quantity.get("unit", "")).lower()
    if val is None:
        issues.append("observation missing valueQuantity.value")
        return None
    if unit.startswith("kg"):
        return float(val)
    if unit.startswith("g") and not unit.startswith("kg"):
        return float(val) / 1000.0
    if unit.startswith("lb"):
        return float(val) / _LB_PER_KG
    issues.append(f"unsupported weight unit '{unit}'")
    return None


def _loinc_codes(observation: Dict[str, Any]) -> List[str]:
    codes = []
    for coding in observation.get("code", {}).get("coding", []):
        if str(coding.get("system", "")).endswith("loinc.org"):
            codes.append(str(coding.get("code")))
    return codes


def age_months_from_patient(patient: Dict[str, Any],
                            reference_date: Optional[str] = None) -> int:
    """Completed months of age from a FHIR Patient.birthDate (YYYY-MM-DD)."""
    birth = datetime.date.fromisoformat(patient["birthDate"])
    ref = (datetime.date.fromisoformat(reference_date) if reference_date
           else datetime.date.today())
    months = (ref.year - birth.year) * 12 + (ref.month - birth.month)
    if ref.day < birth.day:
        months -= 1
    return months


def extract_vitals(resources: List[Dict[str, Any]]) -> VitalExtraction:
    """Pull height and weight Observations out of a resource list."""
    extraction = VitalExtraction()
    for res in resources:
        if res.get("resourceType") != "Observation":
            continue
        codes = _loinc_codes(res)
        qty = res.get("valueQuantity", {})
        if LOINC_HEIGHT in codes and extraction.height_cm is None:
            extraction.height_cm = _to_cm(qty, extraction.issues)
        elif LOINC_WEIGHT in codes and extraction.weight_kg is None:
            extraction.weight_kg = _to_kg(qty, extraction.issues)
    return extraction


def compute_z_from_bundle(patient: Dict[str, Any],
                          observations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Full pipeline: Patient + Observations -> WHO z-score evaluation."""
    vitals = extract_vitals([{"resourceType": "Observation", **o} for o in observations])
    out: Dict[str, Any] = {"issues": vitals.issues}
    if vitals.height_cm is None or vitals.weight_kg is None:
        out["status"] = "error"
        out["reason"] = "missing height or weight observation"
        return out
    try:
        months = age_months_from_patient(patient)
    except KeyError:
        out["status"] = "error"
        out["reason"] = "Patient.birthDate required"
        return out
    sex = "F" if str(patient.get("gender", "female")).lower().startswith("f") else "M"
    try:
        result = evaluate_child(vitals.weight_kg, vitals.height_cm, months, sex)
    except ValueError as exc:
        out["status"] = "error"
        out["reason"] = str(exc)
        return out
    out.update({"status": "ok", "patient_age_months": months,
                "height_cm": round(vitals.height_cm, 1),
                "weight_kg": round(vitals.weight_kg, 2)})
    out.update(result)
    return out


def build_derived_observation(evaluation: Dict[str, Any],
                              patient_ref: str = "Patient/example") -> Dict[str, Any]:
    """Render the evaluation back as a FHIR BMI Observation resource."""
    return {
        "resourceType": "Observation",
        "status": "final",
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category",
                                  "code": "vital-signs"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": LOINC_BMI,
                             "display": "Body mass index (BMI) [Ratio]"}]},
        "subject": {"reference": patient_ref},
        "effectiveDateTime": datetime.datetime.now(datetime.timezone.utc)
                             .isoformat().replace("+00:00", "Z"),
        "valueQuantity": {"value": evaluation.get("bmi"), "unit": "kg/m2",
                          "system": "http://unitsofmeasure.org", "code": "kg/m2"},
        "component": [
            {"code": {"text": "WHO BMI-for-age z-score"},
             "valueQuantity": {"value": evaluation.get("z")}},
            {"code": {"text": "WHO BMI-for-age percentile"},
             "valueQuantity": {"value": evaluation.get("percentile"), "unit": "%"}},
            {"code": {"text": "WHO weight-status category"},
             "valueCodeableConcept": {"text": evaluation.get("category")}},
        ],
    }


if __name__ == "__main__":
    patient = {"resourceType": "Patient", "gender": "female",
               "birthDate": "2016-03-14"}
    observations = [
        {"resourceType": "Observation",
         "code": {"coding": [{"system": "http://loinc.org", "code": LOINC_HEIGHT}]},
         "valueQuantity": {"value": 128.5, "unit": "cm"}},
        {"resourceType": "Observation",
         "code": {"coding": [{"system": "http://loinc.org", "code": LOINC_WEIGHT}]},
         "valueQuantity": {"value": 33.4, "unit": "kg"}},
    ]
    eval_result = compute_z_from_bundle(patient, observations)
    print(json.dumps(eval_result, indent=2))
    if eval_result["status"] == "ok":
        print("\nDerived FHIR Observation:")
        print(json.dumps(build_derived_observation(eval_result), indent=2))
