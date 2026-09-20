#!/usr/bin/env python3
"""Longitudinal BMI-for-age tracking helpers.

The alert thresholds in this module are configurable heuristics for workflow
testing; they are not WHO diagnostic criteria and do not replace clinical
assessment.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class GrowthMeasurement:
    date: str
    age_months: float
    weight_kg: float
    height_cm: float
    bmi: float
    bmi_z_score: float
    sex: str = "M"


def compute_growth_velocity(measurements: List[GrowthMeasurement]) -> Dict[str, Any]:
    """Compute simple annualized changes from sequential measurements."""
    if len(measurements) < 2:
        return {"velocity_available": False, "reason": "Insufficient measurements"}

    for measurement in measurements:
        values = (
            measurement.age_months,
            measurement.weight_kg,
            measurement.height_cm,
            measurement.bmi,
            measurement.bmi_z_score,
        )
        if not all(math.isfinite(float(value)) for value in values):
            return {"velocity_available": False, "reason": "Non-finite measurement"}
        if measurement.age_months < 0 or measurement.weight_kg <= 0 or measurement.height_cm <= 0:
            return {"velocity_available": False, "reason": "Invalid anthropometric measurement"}

    sorted_pts = sorted(measurements, key=lambda item: item.age_months)
    latest = sorted_pts[-1]
    previous = sorted_pts[-2]
    age_diff_months = latest.age_months - previous.age_months
    if age_diff_months <= 0:
        return {"velocity_available": False, "reason": "Invalid age interval"}

    weight_velocity = (latest.weight_kg - previous.weight_kg) / age_diff_months * 12
    height_velocity = (latest.height_cm - previous.height_cm) / age_diff_months * 12
    bmi_change = latest.bmi - previous.bmi
    bmi_z_change = latest.bmi_z_score - previous.bmi_z_score

    total_span_months = sorted_pts[-1].age_months - sorted_pts[0].age_months
    trend_slope = 0.0
    if len(sorted_pts) > 2 and total_span_months > 0:
        x_vals = [item.age_months - sorted_pts[0].age_months for item in sorted_pts]
        y_vals = [item.bmi_z_score for item in sorted_pts]
        n = len(x_vals)
        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
        sum_x2 = sum(x * x for x in x_vals)
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator:
            trend_slope = (n * sum_xy - sum_x * sum_y) / denominator

    return {
        "velocity_available": True,
        "weight_velocity_kg_per_year": round(weight_velocity, 2),
        "height_velocity_cm_per_year": round(height_velocity, 2),
        "bmi_change_per_interval": round(bmi_change, 2),
        "bmi_z_score_change": round(bmi_z_change, 3),
        "bmi_z_trend_slope": round(trend_slope, 4),
        "measurement_count": len(sorted_pts),
        "follow_up_months": round(total_span_months, 1),
        "latest_age_months": latest.age_months,
        "latest_bmi_z": latest.bmi_z_score,
    }


def classify_growth_pattern(
    velocity: Dict[str, Any],
    *,
    z_change_threshold: float = 0.5,
    slope_threshold: float = 0.1,
) -> Dict[str, Any]:
    """Classify serial change using configurable non-diagnostic thresholds."""
    if not velocity.get("velocity_available"):
        return {"pattern": "INSUFFICIENT_DATA", "alerts": []}

    z_change = float(velocity["bmi_z_score_change"])
    slope = float(velocity["bmi_z_trend_slope"])
    alerts: List[Dict[str, str]] = []

    if z_change > z_change_threshold or slope > slope_threshold:
        pattern = "RAPID_BMI_GAIN"
        alerts.append(
            {
                "type": "BMI_Z_INCREASE",
                "severity": "REVIEW",
                "message": f"BMI z-score changed by {z_change:+.3f}; slope {slope:+.4f}/month.",
                "recommendation": "Review serial measurements, data quality, and clinical context.",
            }
        )
    elif z_change < -z_change_threshold or slope < -slope_threshold:
        pattern = "BMI_DECLINE"
        alerts.append(
            {
                "type": "BMI_Z_DECREASE",
                "severity": "REVIEW",
                "message": f"BMI z-score changed by {z_change:+.3f}; slope {slope:+.4f}/month.",
                "recommendation": "Review serial measurements, data quality, and clinical context.",
            }
        )
    elif float(velocity["weight_velocity_kg_per_year"]) < 0:
        pattern = "WEIGHT_LOSS"
        alerts.append(
            {
                "type": "NEGATIVE_WEIGHT_VELOCITY",
                "severity": "REVIEW",
                "message": (
                    f"Negative weight velocity: "
                    f"{velocity['weight_velocity_kg_per_year']:+.2f} kg/year."
                ),
                "recommendation": "Confirm measurements and assess in the appropriate clinical context.",
            }
        )
    else:
        pattern = "STABLE"
        alerts.append(
            {
                "type": "STABLE_GROWTH",
                "severity": "INFO",
                "message": "No configured longitudinal threshold was crossed.",
                "recommendation": "Continue monitoring according to the applicable care plan.",
            }
        )

    return {"pattern": pattern, "alerts": alerts}


class LongitudinalGrowthAgent:
    """Wrapper for longitudinal growth calculations."""

    def __init__(self) -> None:
        self.agent_name = "LongitudinalGrowthAgent"

    def evaluate(self, measurements: List[GrowthMeasurement]) -> Dict[str, Any]:
        velocity = compute_growth_velocity(measurements)
        classification = classify_growth_pattern(velocity)
        return {
            "velocity": velocity,
            "pattern": classification["pattern"],
            "alerts": classification["alerts"],
            "measurement_count": len(measurements),
            "latest_bmi_z": velocity.get("latest_bmi_z"),
        }
