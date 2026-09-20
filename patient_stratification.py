#!/usr/bin/env python3
"""Heuristic patient stratification helpers.

This module is retained for workflow experiments. Its comorbidity multipliers
are configurable heuristics, not validated WHO risk models.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

BMI_Z_RISK_STRATA = {
    "severe_thinness": {"z_min": float("-inf"), "z_max": -3.0, "risk_level": "HIGH", "action": "Clinical review"},
    "moderate_thinness": {"z_min": -3.0, "z_max": -2.0, "risk_level": "MODERATE", "action": "Clinical review"},
    "normal": {"z_min": -2.0, "z_max": 1.0, "risk_level": "NORMAL", "action": "Routine follow-up"},
    "overweight": {"z_min": 1.0, "z_max": 2.0, "risk_level": "LOW", "action": "Review growth trajectory"},
    "obesity": {"z_min": 2.0, "z_max": float("inf"), "risk_level": "MODERATE", "action": "Clinical review"},
}

COMORBIDITY_RISK_MULTIPLIERS = {
    "down_syndrome": 1.5,
    "prader_willi": 2.0,
    "turner_syndrome": 1.3,
    "hypothyroid": 1.4,
    "cushing_syndrome": 1.8,
    "growth_hormone_deficiency": 1.6,
    "type_1_diabetes": 1.3,
    "cystic_fibrosis": 1.5,
    "congenital_heart_disease": 1.2,
    "cerebral_palsy": 1.4,
}

_RISK_RANK = {"NORMAL": 0, "LOW": 1, "MODERATE": 2, "HIGH": 3}


def _higher_risk(first: str, second: str) -> str:
    return first if _RISK_RANK[first] >= _RISK_RANK[second] else second


def stratify_patient(
    bmi_z_score: float,
    sex: str = "M",
    comorbidities: Optional[List[str]] = None,
    age_months: float = 120.0,
) -> Dict[str, Any]:
    """Apply the legacy heuristic stratification without overriding BMI risk."""
    comorbidities = comorbidities or []

    stratum = "normal"
    for category, info in BMI_Z_RISK_STRATA.items():
        if info["z_min"] <= bmi_z_score < info["z_max"]:
            stratum = category
            break

    base_risk = BMI_Z_RISK_STRATA[stratum]
    risk_multiplier = 1.0
    active_comorbidities: List[str] = []
    for comorbidity in comorbidities:
        key = comorbidity.lower().strip().replace(" ", "_")
        if key in COMORBIDITY_RISK_MULTIPLIERS:
            risk_multiplier *= COMORBIDITY_RISK_MULTIPLIERS[key]
            active_comorbidities.append(comorbidity)

    if age_months < 24:
        risk_multiplier *= 1.3
    elif age_months < 60:
        risk_multiplier *= 1.1

    risk_multiplier = min(risk_multiplier, 5.0)
    multiplier_risk = "NORMAL"
    if risk_multiplier >= 2.5:
        multiplier_risk = "HIGH"
    elif risk_multiplier >= 1.5:
        multiplier_risk = "MODERATE"
    elif risk_multiplier > 1.0:
        multiplier_risk = "LOW"

    overall_risk = _higher_risk(base_risk["risk_level"], multiplier_risk)

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
        "intervention_urgency": (
            "REVIEW" if overall_risk in {"HIGH", "MODERATE"} else "ROUTINE"
        ),
        "model_status": "heuristic_not_clinically_validated",
    }


class StratificationAgent:
    """Wrapper for the legacy heuristic stratifier."""

    def __init__(self) -> None:
        self.agent_name = "StratificationAgent"

    def evaluate(
        self,
        bmi_z_score: float,
        sex: str = "M",
        comorbidities: Optional[List[str]] = None,
        age_months: float = 120.0,
    ) -> Dict[str, Any]:
        stratification = stratify_patient(
            bmi_z_score, sex, comorbidities, age_months
        )
        alerts: List[Dict[str, str]] = []
        if stratification["adjusted_risk_level"] in {"HIGH", "MODERATE"}:
            alerts.append(
                {
                    "type": "HEURISTIC_REVIEW",
                    "severity": "REVIEW",
                    "message": (
                        "Configured heuristic indicates additional review; "
                        "this is not a diagnostic score."
                    ),
                    "recommendation": "Interpret alongside validated clinical guidance.",
                }
            )
        return {
            "stratification": stratification,
            "alerts": alerts,
            "intervention_urgency": stratification["intervention_urgency"],
        }
