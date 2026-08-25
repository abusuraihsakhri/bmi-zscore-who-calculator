#!/usr/bin/env python3
"""
Patient Stratification Engine for BMI Z-Score WHO Calculator.
Stratifies patients into risk categories based on BMI z-score,
comorbidities, and growth trajectory for targeted intervention.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass


# WHO BMI z-score classification thresholds (adapted for clinical use)
BMI_Z_RISK_STRATA = {
    "severe_thinness": {"z_min": float("-inf"), "z_max": -3.0, "risk_level": "HIGH", "action": "Immediate nutritional assessment"},
    "moderate_thinness": {"z_min": -3.0, "z_max": -2.0, "risk_level": "MODERATE", "action": "Nutritional counseling, monitor monthly"},
    "mild_thinness": {"z_min": -2.0, "z_max": -1.0, "risk_level": "LOW", "action": "Monitor growth velocity"},
    "normal": {"z_min": -1.0, "z_max": 1.0, "risk_level": "NORMAL", "action": "Routine monitoring"},
    "overweight": {"z_min": 1.0, "z_max": 2.0, "risk_level": "LOW", "action": "Lifestyle counseling"},
    "obese": {"z_min": 2.0, "z_max": 3.0, "risk_level": "MODERATE", "action": "Dietitian referral, activity plan"},
    "severe_obese": {"z_min": 3.0, "z_max": float("inf"), "risk_level": "HIGH", "action": "Multidisciplinary obesity team"},
}

COMORBIDITY_RISK_MULTIPLIERS = {
    "down_syndrome": 1.5,
    "prader_willi": 2.0,
    "turner_syndrome": 1.3,
    "hypothyroid": 1.4,
    "cushing_syndrome": 1.8,
    "growth_hormone_deficiency": 1.6,
    " Type 1 diabetes": 1.3,
    "cystic_fibrosis": 1.5,
    "congenital_heart_disease": 1.2,
    "cerebral_palsy": 1.4,
}


def stratify_patient(bmi_z_score: float, sex: str = "M",
                     comorbidities: Optional[List[str]] = None,
                     age_months: float = 120.0) -> Dict[str, Any]:
    """Stratify patient into risk category based on BMI z-score and factors."""
    comorbidities = comorbidities or []

    stratum = "normal"
    for category, info in BMI_Z_RISK_STRATA.items():
        if info["z_min"] <= bmi_z_score < info["z_max"]:
            stratum = category
            break

    base_risk = BMI_Z_RISK_STRATA[stratum]

    risk_multiplier = 1.0
    active_comorbidities = []
    for comorbidity in comorbidities:
        if comorbidity.lower().replace(" ", "_") in COMORBIDITY_RISK_MULTIPLIERS:
            multiplier = COMORBIDITY_RISK_MULTIPLIERS[comorbidity.lower().replace(" ", "_")]
            risk_multiplier *= multiplier
            active_comorbidities.append(comorbidity)

    if age_months < 24:
        risk_multiplier *= 1.3
    elif age_months < 60:
        risk_multiplier *= 1.1

    adjusted_risk = min(risk_multiplier, 5.0)

    if adjusted_risk >= 2.5:
        overall_risk = "HIGH"
    elif adjusted_risk >= 1.5:
        overall_risk = "MODERATE"
    elif adjusted_risk >= 1.0:
        overall_risk = "LOW"
    else:
        overall_risk = "NORMAL"

    return {
        "bmi_z_score": bmi_z_score,
        "stratum": stratum,
        "base_risk_level": base_risk["risk_level"],
        "base_action": base_risk["action"],
        "comorbidities": active_comorbidities,
        "risk_multiplier": round(risk_multiplier, 2),
        "adjusted_risk_level": overall_risk,
        "sex": sex,
        "age_months": age_months,
        "intervention_urgency": "IMMEDIATE" if overall_risk == "HIGH" else (
            "SCHEDULED" if overall_risk == "MODERATE" else "ROUTINE"
        ),
    }


class StratificationAgent:
    """Sub-agent for patient risk stratification."""

    def __init__(self):
        self.agent_name = "StratificationAgent"

    def evaluate(self, bmi_z_score: float, sex: str = "M",
                 comorbidities: Optional[List[str]] = None,
                 age_months: float = 120.0) -> Dict[str, Any]:
        """Evaluate patient stratification."""
        stratification = stratify_patient(bmi_z_score, sex, comorbidities, age_months)
        alerts = []

        if stratification["adjusted_risk_level"] == "HIGH":
            alerts.append({
                "type": "HIGH_RISK_STRATUM",
                "severity": "CRITICAL",
                "message": f"Patient stratified as HIGH RISK (z-score: {bmi_z_score:+.2f}, "
                           f"comorbidities: {len(stratification['comorbidities'])}).",
                "recommendation": f"Urgent action required: {stratification['base_action']}. "
                                  f"Risk multiplier: {stratification['risk_multiplier']:.1f}x."
            })
        elif stratification["adjusted_risk_level"] == "MODERATE":
            alerts.append({
                "type": "MODERATE_RISK_STRATUM",
                "severity": "WARNING",
                "message": f"Patient at moderate risk (z-score: {bmi_z_score:+.2f}).",
                "recommendation": f"Recommended action: {stratification['base_action']}."
            })

        for comorbidity in stratification["comorbidities"]:
            alerts.append({
                "type": "COMORBIDITY_AMPLIFIER",
                "severity": "ADVISORY",
                "message": f"Comorbidity '{comorbidity}' increases nutritional risk.",
                "recommendation": "Consider specialist referral and enhanced monitoring frequency."
            })

        return {
            "stratification": stratification,
            "alerts": alerts,
            "intervention_urgency": stratification["intervention_urgency"],
        }
