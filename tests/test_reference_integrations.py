"""Tests for WHO references and auxiliary integration modules."""

import math

from alert_escalation import evaluate_escalation_rules
from fhir_bmi_integration import compute_z_from_bundle
from longitudinal_growth import GrowthMeasurement, LongitudinalGrowthAgent
from patient_stratification import stratify_patient
from simulator import run_simulation
from who_lms_tables import cutoffs_at, evaluate_child, lms_lookup
from who_reference import adjusted_lms_z, raw_lms_z, reference_for_age


def test_who_2006_source_value_is_loaded_exactly():
    ref = reference_for_age(0, "M", age_days=0)
    assert ref.L == -0.3053
    assert ref.M == 13.4069
    assert ref.S == 0.0956
    assert ref.standard == "WHO Child Growth Standards 2006"


def test_who_2007_source_value_is_loaded_exactly():
    ref = reference_for_age(60, "M")
    assert ref.L == -0.7151
    assert ref.M == 15.2679
    assert ref.S == 0.08366
    assert ref.standard == "WHO Growth Reference 2007"


def test_who_2007_fractional_month_interpolation():
    low = reference_for_age(120, "F")
    high = reference_for_age(121, "F")
    mid = reference_for_age(120.5, "F")
    assert math.isclose(mid.M, (low.M + high.M) / 2, abs_tol=1e-12)


def test_adjusted_lms_extreme_score_is_linear_beyond_three_sd():
    ref = reference_for_age(120, "M")
    value = 40.0
    raw = raw_lms_z(value, ref.L, ref.M, ref.S)
    adjusted = adjusted_lms_z(value, ref.L, ref.M, ref.S)
    assert raw > 3
    assert adjusted > 3
    assert not math.isclose(raw, adjusted)


def test_compatibility_who_2007_helpers_run_without_name_error():
    ref = lms_lookup(120, "M")
    assert ref.M == 16.4433
    result = evaluate_child(31.0, 140.0, 120, "M")
    assert "z" in result
    cutoffs = cutoffs_at(120, "F")
    assert cutoffs["overweight_gt"] < cutoffs["obesity_gt"]


def _observations():
    return [
        {
            "resourceType": "Observation",
            "code": {"coding": [{"system": "http://loinc.org", "code": "8302-2"}]},
            "valueQuantity": {"value": 140, "unit": "cm"},
            "effectiveDateTime": "2026-03-14T10:00:00Z",
        },
        {
            "resourceType": "Observation",
            "code": {"coding": [{"system": "http://loinc.org", "code": "29463-7"}]},
            "valueQuantity": {"value": 31, "unit": "kg"},
            "effectiveDateTime": "2026-03-14T10:00:00Z",
        },
    ]


def test_fhir_pipeline_is_deterministic_with_observation_date():
    patient = {
        "resourceType": "Patient",
        "gender": "male",
        "birthDate": "2016-03-14",
    }
    result = compute_z_from_bundle(patient, _observations())
    assert result["status"] == "ok"
    assert result["reference_standard"] == "WHO Growth Reference 2007"
    assert result["sex"] == "M"
    assert result["bmi"] == round(31 / (1.4**2), 2)


def test_fhir_missing_gender_is_an_error_not_female_default():
    patient = {"resourceType": "Patient", "birthDate": "2016-03-14"}
    result = compute_z_from_bundle(patient, _observations())
    assert result["status"] == "error"
    assert "gender" in result["reason"]


def test_stratification_normal_case_stays_normal():
    result = stratify_patient(0.0, age_months=120)
    assert result["base_risk_level"] == "NORMAL"
    assert result["adjusted_risk_level"] == "NORMAL"


def test_stratification_recognizes_type_1_diabetes_key():
    result = stratify_patient(
        0.0,
        age_months=120,
        comorbidities=["Type 1 diabetes"],
    )
    assert result["comorbidities"] == ["Type 1 diabetes"]
    assert result["risk_multiplier"] == 1.3


def test_longitudinal_agent_uses_latest_age_not_input_order():
    points = [
        GrowthMeasurement("later", 24, 12, 85, 16.6, 0.2),
        GrowthMeasurement("earlier", 12, 9, 75, 16.0, -0.1),
    ]
    result = LongitudinalGrowthAgent().evaluate(points)
    assert result["latest_bmi_z"] == 0.2


def test_example_alert_rules_never_return_automatic_orders():
    items = evaluate_escalation_rules(-3.5)
    assert items
    assert all(item["auto_action"] is None for item in items)


def test_simulator_runs_against_current_core():
    summary = run_simulation(20, seed=7)
    assert summary["iterations"] == 20
    assert summary["pediatric"] + summary["adult"] == 20
