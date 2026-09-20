"""Tests for the BMI calculator core."""

import csv
import math
import os
import tempfile

import pytest

import bmi_zscore as bmi
from who_reference import reference_for_age


def test_bmi_basic():
    assert math.isclose(bmi.calculate_bmi(70, 1.75), 22.8571, rel_tol=1e-4)


@pytest.mark.parametrize(
    ("value", "category"),
    [
        (15.0, "Severe Thinness"),
        (16.5, "Moderate Thinness"),
        (18.0, "Mild Thinness"),
        (18.5, "Normal"),
        (24.9, "Normal"),
        (25.0, "Overweight"),
        (30.0, "Obese Class I"),
        (35.0, "Obese Class II"),
        (40.0, "Obese Class III"),
    ],
)
def test_adult_categories(value, category):
    assert bmi.classify_adult_bmi(value) == category


@pytest.mark.parametrize(("weight", "height"), [(0, 1.7), (-1, 1.7), (70, 0)])
def test_bmi_rejects_invalid_anthropometrics(weight, height):
    with pytest.raises(ValueError):
        bmi.calculate_bmi(weight, height)


def test_percentile_conversions():
    assert math.isclose(bmi.zscore_to_percentile(0), 50.0, abs_tol=0.01)
    for percentile in (5, 25, 50, 75, 95):
        z = bmi.percentile_to_zscore(percentile)
        assert math.isclose(
            bmi.zscore_to_percentile(z), percentile, abs_tol=0.5
        )


def test_official_who_2007_medians_give_zero_z():
    assert abs(bmi.bmi_zscore_child(16.4433, 120, "M")) < 1e-10
    assert abs(bmi.bmi_zscore_child(16.6133, 120, "F")) < 1e-10


def test_official_who_2006_day_level_median_gives_zero_z():
    ref = reference_for_age(365 / (365.25 / 12), "M", age_days=365)
    assert abs(
        bmi.bmi_zscore_child(ref.M, ref.age_months, "M", age_days=365)
    ) < 1e-10


def test_reference_range_includes_228_but_not_229_months():
    result = bmi.calculate_patient(
        "edge", 70, 1.75, age_months=228, sex="M"
    )
    assert result.is_child is True
    assert result.z_score is not None

    with pytest.raises(ValueError):
        bmi.bmi_zscore_child(22.0, 229, "M")


@pytest.mark.parametrize(
    ("z", "age", "category"),
    [
        (-3.1, 120, "Severe thinness"),
        (-2.5, 120, "Thinness"),
        (0.0, 120, "Normal"),
        (1.5, 120, "Overweight"),
        (2.5, 120, "Obesity"),
        (-3.1, 36, "Very low BMI-for-age"),
        (-2.5, 36, "Low BMI-for-age"),
        (1.5, 36, "Risk of overweight"),
        (2.5, 36, "Overweight"),
        (3.5, 36, "Obesity"),
    ],
)
def test_age_specific_pediatric_classification(z, age, category):
    assert bmi.classify_child_zscore(z, age) == category


def test_child_without_sex_does_not_fall_back_to_adult_classification():
    result = bmi.calculate_patient("P", 20, 1.10, age_months=60)
    assert result.is_child is True
    assert result.adult_category is None
    assert result.z_score is None
    assert any("Sex is required" in warning for warning in result.warnings)


def test_adult_result_has_no_pseudo_zscore():
    result = bmi.calculate_patient("A", 70, 1.75)
    assert result.is_child is False
    assert result.adult_category == "Normal"
    assert result.z_score is None
    assert result.percentile is None


def test_under_five_month_only_age_warns_about_day_approximation():
    result = bmi.calculate_patient("C", 16.5, 0.96, age_months=36, sex="M")
    assert result.z_score is not None
    assert any("day-level" in warning for warning in result.warnings)


def test_negative_age_is_rejected_without_adult_fallback():
    result = bmi.calculate_patient("bad-age", 70, 1.75, age_months=-1, sex="M")
    assert result.adult_category is None
    assert result.z_score is None
    assert result.warnings


def test_exact_age_days_override_materially_inconsistent_under_five_months():
    result = bmi.calculate_patient(
        "exact-age",
        9.6,
        0.76,
        age_months=24,
        age_days=365,
        sex="M",
    )
    assert math.isclose(result.age_months, 365 / (365.25 / 12), abs_tol=1e-12)
    assert any("exact age_days was used" in warning for warning in result.warnings)


def test_batch_csv_standard_format():
    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "in.csv")
        target = os.path.join(tmp, "out.csv")
        with open(source, "w", newline="", encoding="utf-8") as handle:
            handle.write("patient_id,weight_kg,height_m,age_months,sex\n")
            handle.write("A1,70,1.75,,\n")
            handle.write("A2,20,1.10,60,M\n")
        results = bmi.process_csv(source, target)
        assert len(results) == 2
        assert results[0].adult_category == "Normal"
        assert results[1].child_category is not None
        with open(target, newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        assert len(rows) == 2
        assert rows[1]["z_score"]


def test_batch_csv_uses_exact_age_days_when_available():
    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "in.csv")
        target = os.path.join(tmp, "out.csv")
        with open(source, "w", newline="", encoding="utf-8") as handle:
            handle.write("patient_id,age_days,sex,height_cm,weight_kg\n")
            handle.write("P1,365,M,76,9.6\n")
        results = bmi.process_csv(source, target)
        assert results[0].age_days == 365
        assert not any("approximated" in item for item in results[0].warnings)


def test_cli_single_and_batch():
    assert (
        bmi.main(
            [
                "single",
                "--weight",
                "20",
                "--height",
                "1.10",
                "--age-months",
                "60",
                "--sex",
                "M",
            ]
        )
        == 0
    )
    with tempfile.TemporaryDirectory() as tmp:
        source = os.path.join(tmp, "in.csv")
        target = os.path.join(tmp, "out.csv")
        with open(source, "w", encoding="utf-8") as handle:
            handle.write("patient_id,weight_kg,height_m\nA,70,1.75\n")
        assert bmi.main(["batch", "-i", source, "-o", target]) == 0
        assert os.path.exists(target)
