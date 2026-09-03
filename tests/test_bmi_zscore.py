"""Tests for bmi_zscore.py -- plain assert statements, stdlib only.

Run with: python test_bmi_zscore.py
"""

import csv
import math
import os
import tempfile

import bmi_zscore as bmi


# ---------------------------------------------------------------------------
# BMI Calculation
# ---------------------------------------------------------------------------

def test_bmi_basic():
    """70kg / (1.75m)^2 = 70 / 3.0625 = 22.86."""
    result = bmi.calculate_bmi(70, 1.75)
    assert math.isclose(result, 22.86, abs_tol=0.01), result


def test_bmi_known_value():
    """80kg / (1.80m)^2 = 80 / 3.24 = 24.69."""
    result = bmi.calculate_bmi(80, 1.80)
    assert math.isclose(result, 24.69, abs_tol=0.01), result


def test_bmi_child():
    """20kg / (1.10m)^2 = 20 / 1.21 = 16.53."""
    result = bmi.calculate_bmi(20, 1.10)
    assert math.isclose(result, 16.53, abs_tol=0.01), result


def test_bmi_invalid_height():
    try:
        bmi.calculate_bmi(70, 0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_bmi_invalid_weight():
    try:
        bmi.calculate_bmi(0, 1.70)
        assert False, "expected ValueError"
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# WHO Adult BMI Classification
# ---------------------------------------------------------------------------

def test_adult_underweight_severe():
    assert bmi.classify_adult_bmi(15.0) == "Severe Thinness"


def test_adult_underweight_moderate():
    assert bmi.classify_adult_bmi(16.5) == "Moderate Thinness"


def test_adult_underweight_mild():
    assert bmi.classify_adult_bmi(18.0) == "Mild Thinness"


def test_adult_normal():
    assert bmi.classify_adult_bmi(22.0) == "Normal"
    assert bmi.classify_adult_bmi(18.5) == "Normal"
    assert bmi.classify_adult_bmi(24.9) == "Normal"


def test_adult_overweight():
    assert bmi.classify_adult_bmi(27.0) == "Overweight"
    assert bmi.classify_adult_bmi(25.0) == "Overweight"


def test_adult_obese_i():
    assert bmi.classify_adult_bmi(32.0) == "Obese Class I"
    assert bmi.classify_adult_bmi(30.0) == "Obese Class I"


def test_adult_obese_ii():
    assert bmi.classify_adult_bmi(37.0) == "Obese Class II"
    assert bmi.classify_adult_bmi(35.0) == "Obese Class II"


def test_adult_obese_iii():
    assert bmi.classify_adult_bmi(42.0) == "Obese Class III"
    assert bmi.classify_adult_bmi(40.0) == "Obese Class III"


# ---------------------------------------------------------------------------
# Z-score / Percentile conversion
# ---------------------------------------------------------------------------

def test_zscore_to_percentile_50():
    """Z=0 should give 50th percentile."""
    result = bmi.zscore_to_percentile(0.0)
    assert math.isclose(result, 50.0, abs_tol=0.1), result


def test_zscore_to_percentile_97_7():
    """Z=2 should give ~97.7th percentile."""
    result = bmi.zscore_to_percentile(2.0)
    assert math.isclose(result, 97.72, abs_tol=0.1), result


def test_zscore_to_percentile_2_3():
    """Z=-2 should give ~2.3rd percentile."""
    result = bmi.zscore_to_percentile(-2.0)
    assert math.isclose(result, 2.28, abs_tol=0.1), result


def test_percentile_to_zscore_roundtrip():
    """Converting percentile->zscore->percentile should roundtrip."""
    for pct in [5, 25, 50, 75, 95]:
        z = bmi.percentile_to_zscore(pct)
        back = bmi.zscore_to_percentile(z)
        assert math.isclose(back, pct, abs_tol=0.5), (pct, z, back)


def test_percentile_to_zscore_50():
    """50th percentile should give Z=0."""
    result = bmi.percentile_to_zscore(50.0)
    assert math.isclose(result, 0.0, abs_tol=0.01), result


# ---------------------------------------------------------------------------
# Child Z-score (LMS method)
# ---------------------------------------------------------------------------

def test_child_zscore_male_5y_normal():
    """5-year-old male, BMI ~15.3 (M value at 60mo) -> Z ≈ 0."""
    result = bmi.bmi_zscore_child(15.3, 60, "M")
    assert abs(result) < 0.5, result


def test_child_zscore_female_5y_normal():
    """5-year-old female, BMI ~15.2 (M value at 60mo) -> Z ≈ 0."""
    result = bmi.bmi_zscore_child(15.2, 60, "F")
    assert abs(result) < 0.5, result


def test_child_zscore_high_bmi():
    """High BMI should give positive Z-score."""
    result = bmi.bmi_zscore_child(20.0, 60, "M")
    assert result > 1.0, result


def test_child_zscore_low_bmi():
    """Low BMI should give negative Z-score."""
    result = bmi.bmi_zscore_child(12.0, 60, "M")
    assert result < -1.0, result


def test_child_zscore_invalid_sex():
    try:
        bmi.bmi_zscore_child(15.0, 60, "X")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_child_classification_wasting():
    assert bmi.classify_child_zscore(-2.5) == "Wasting"


def test_child_classification_normal():
    assert bmi.classify_child_zscore(0.0) == "Normal"


def test_child_classification_overweight():
    assert bmi.classify_child_zscore(1.5) == "Overweight risk"


def test_child_classification_obese():
    assert bmi.classify_child_zscore(2.5) == "Overweight/Obese"


# ---------------------------------------------------------------------------
# Patient workflow
# ---------------------------------------------------------------------------

def test_calculate_patient_adult():
    result = bmi.calculate_patient("P1", 70, 1.75)
    assert result.bmi is not None
    assert result.adult_category == "Normal"
    assert result.is_child is False


def test_calculate_patient_child():
    result = bmi.calculate_patient("P2", 20, 1.10, age_months=60, sex="M")
    assert result.bmi is not None
    assert result.is_child is True
    assert result.z_score is not None
    assert result.percentile is not None
    assert result.child_category is not None


def test_calculate_patient_adult_obese():
    result = bmi.calculate_patient("P3", 120, 1.70)
    assert result.adult_category in ("Obese Class I", "Obese Class II", "Obese Class III")


# ---------------------------------------------------------------------------
# CSV batch processing
# ---------------------------------------------------------------------------

def test_batch_csv():
    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "in.csv")
        out = os.path.join(tmp, "out.csv")
        with open(inp, "w", newline="") as f:
            f.write("patient_id,weight_kg,height_m,age_months,sex\n")
            f.write("A1,70,1.75,,\n")
            f.write("A2,20,1.10,60,M\n")
        results = bmi.process_csv(inp, out)
        assert len(results) == 2
        assert results[0].adult_category is not None
        assert results[1].child_category is not None
        assert os.path.exists(out)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def test_cli_single_adult():
    rc = bmi.main(["single", "--weight", "70", "--height", "1.75"])
    assert rc == 0


def test_cli_single_child():
    rc = bmi.main(["single", "--weight", "20", "--height", "1.10", "--age-months", "60", "--sex", "M"])
    assert rc == 0


def test_cli_batch():
    with tempfile.TemporaryDirectory() as tmp:
        inp = os.path.join(tmp, "in.csv")
        out = os.path.join(tmp, "out.csv")
        with open(inp, "w", newline="") as f:
            f.write("patient_id,weight_kg,height_m,age_months,sex\n")
            f.write("T1,70,1.75,,\n")
        rc = bmi.main(["batch", "--input", inp, "--output", out])
        assert rc == 0
        assert os.path.exists(out)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all():
    tests = [obj for name, obj in globals().items() if name.startswith("test_") and callable(obj)]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  PASS: {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"  FAIL: {t.__name__} -- {e}")
    print(f"\n{passed}/{passed + failed} tests passed.")
    return failed


if __name__ == "__main__":
    import sys
    sys.exit(run_all())
