#!/usr/bin/env python3
"""
Longitudinal Growth Tracking for BMI Z-Score WHO Calculator.
Tracks patient growth velocity over time to detect faltering growth,
obesity trends, and growth plateaus requiring intervention.
"""

import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class GrowthMeasurement:
    """Single growth measurement point."""
    date: str
    age_months: float
    weight_kg: float
    height_cm: float
    bmi: float
    bmi_z_score: float
    sex: str = "M"


def compute_growth_velocity(measurements: List[GrowthMeasurement]) -> Dict[str, Any]:
    """Compute growth velocity metrics from sequential measurements."""
    if len(measurements) < 2:
        return {"velocity_available": False, "reason": "Insufficient measurements"}

    sorted_pts = sorted(measurements, key=lambda m: m.age_months)
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
    all_bmi_z = [m.bmi_z_score for m in sorted_pts]
    trend_slope = 0.0
    if len(sorted_pts) > 2 and total_span_months > 0:
        x_vals = [(m.age_months - sorted_pts[0].age_months) for m in sorted_pts]
        y_vals = all_bmi_z
        n = len(x_vals)
        sum_x = sum(x_vals)
        sum_y = sum(y_vals)
        sum_xy = sum(x * y for x, y in zip(x_vals, y_vals))
        sum_x2 = sum(x * x for x in x_vals)
        denom = n * sum_x2 - sum_x * sum_x
        if denom != 0:
            trend_slope = (n * sum_xy - sum_x * sum_y) / denom

    return {
        "velocity_available": True,
        "weight_velocity_kg_per_year": round(weight_velocity, 2),
        "height_velocity_cm_per_year": round(height_velocity, 2),
        "bmi_change_per_interval": round(bmi_change, 2),
        "bmi_z_score_change": round(bmi_z_change, 3),
        "bmi_z_trend_slope": round(trend_slope, 4),
        "measurement_count": len(sorted_pts),
        "follow_up_months": round(total_span_months, 1),
    }


def classify_growth_pattern(velocity: Dict[str, Any]) -> Dict[str, Any]:
    """Classify growth pattern based on velocity metrics."""
    pattern = "NORMAL"
    alerts = []

    if not velocity.get("velocity_available"):
        return {"pattern": "INSUFFICIENT_DATA", "alerts": []}

    z_change = velocity["bmi_z_score_change"]
    slope = velocity["bmi_z_trend_slope"]

    if z_change > 0.5 or slope > 0.1:
        pattern = "RAPID_BMI_GAIN"
        alerts.append({
            "type": "RAPID_BMI_INCREASE",
            "severity": "WARNING" if z_change <= 1.0 else "CRITICAL",
            "message": f"BMI z-score increased by {z_change:+.3f}. Trend slope: {slope:+.4f}/month.",
            "recommendation": "Assess dietary intake, activity level, and screen for endocrine causes."
        })
    elif z_change < -0.5 or slope < -0.1:
        pattern = "FALTERING_GROWTH"
        alerts.append({
            "type": "BMI_DECLINE",
            "severity": "WARNING" if z_change >= -1.0 else "CRITICAL",
            "message": f"BMI z-score decreased by {z_change:+.3f}. Growth faltering suspected.",
            "recommendation": "Investigate malnutrition, chronic illness, or eating disorder. Refer to dietitian."
        })
    elif velocity["weight_velocity_kg_per_year"] < 0:
        pattern = "WEIGHT_LOSS"
        alerts.append({
            "type": "NEGATIVE_WEIGHT_VELOCITY",
            "severity": "WARNING",
            "message": f"Negative weight velocity: {velocity['weight_velocity_kg_per_year']:+.2f} kg/year.",
            "recommendation": "Evaluate for underlying pathology. Consider nutritional supplementation."
        })
    else:
        pattern = "STABLE"
        if abs(z_change) < 0.2:
            alerts.append({
                "type": "STABLE_GROWTH",
                "severity": "INFO",
                "message": "Growth pattern stable with minimal BMI z-score variation.",
                "recommendation": "Continue routine monitoring per standard schedule."
            })

    return {"pattern": pattern, "alerts": alerts}


class LongitudinalGrowthAgent:
    """Sub-agent for longitudinal growth velocity tracking."""

    def __init__(self):
        self.agent_name = "LongitudinalGrowthAgent"

    def evaluate(self, measurements: List[GrowthMeasurement]) -> Dict[str, Any]:
        """Evaluate longitudinal growth pattern."""
        velocity = compute_growth_velocity(measurements)
        classification = classify_growth_pattern(velocity)

        return {
            "velocity": velocity,
            "pattern": classification["pattern"],
            "alerts": classification["alerts"],
            "measurement_count": len(measurements),
            "latest_bmi_z": measurements[-1].bmi_z_score if measurements else None,
        }
