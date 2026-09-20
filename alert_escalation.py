#!/usr/bin/env python3
"""Configurable alert-routing examples for BMI z-score workflows.

These rules are workflow examples, not WHO clinical recommendations. They
perform no automatic clinical orders or external notifications.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EscalationRule:
    rule_id: str
    trigger_condition: str
    severity: str
    escalate_to: str
    time_limit_hours: int
    requires_acknowledgment: bool = True
    auto_action: Optional[str] = None


ESCALATION_RULES = [
    EscalationRule("ESCAL-001", "bmi_z_score < -3.0", "REVIEW", "configured_clinical_reviewer", 4),
    EscalationRule("ESCAL-002", "bmi_z_score > 3.5", "REVIEW", "configured_clinical_reviewer", 24),
    EscalationRule("ESCAL-003", "bmi_z_score_change > 1.0 in 3 months", "REVIEW", "configured_clinical_reviewer", 48),
    EscalationRule("ESCAL-004", "bmi_z_score_change < -1.0 in 3 months", "REVIEW", "configured_clinical_reviewer", 24),
    EscalationRule("ESCAL-005", "weight_loss > 5% in 1 month", "REVIEW", "configured_clinical_reviewer", 2),
    EscalationRule("ESCAL-006", "bmi_z_score < -2.0 AND comorbidity_present", "REVIEW", "configured_clinical_reviewer", 12),
]


def evaluate_escalation_rules(
    bmi_z_score: float,
    bmi_z_change: float = 0.0,
    weight_change_pct: float = 0.0,
    comorbidities: Optional[List[str]] = None,
    interval_months: float = 3.0,
) -> List[Dict[str, Any]]:
    """Evaluate configured example rules and return triggered review items."""
    comorbidities = comorbidities or []
    triggered: List[Dict[str, Any]] = []

    for rule in ESCALATION_RULES:
        should_trigger = False
        if rule.rule_id == "ESCAL-001" and bmi_z_score < -3.0:
            should_trigger = True
        elif rule.rule_id == "ESCAL-002" and bmi_z_score > 3.5:
            should_trigger = True
        elif rule.rule_id == "ESCAL-003" and bmi_z_change > 1.0 and interval_months <= 3:
            should_trigger = True
        elif rule.rule_id == "ESCAL-004" and bmi_z_change < -1.0 and interval_months <= 3:
            should_trigger = True
        elif rule.rule_id == "ESCAL-005" and weight_change_pct < -5.0 and interval_months <= 1:
            should_trigger = True
        elif rule.rule_id == "ESCAL-006" and bmi_z_score < -2.0 and comorbidities:
            should_trigger = True

        if should_trigger:
            triggered.append(
                {
                    "rule_id": rule.rule_id,
                    "trigger_condition": rule.trigger_condition,
                    "severity": rule.severity,
                    "escalate_to": rule.escalate_to,
                    "time_limit_hours": rule.time_limit_hours,
                    "requires_acknowledgment": rule.requires_acknowledgment,
                    "auto_action": None,
                    "escalation_id": str(uuid.uuid4())[:8],
                    "escalation_time": datetime.datetime.now(
                        datetime.timezone.utc
                    ).isoformat(),
                    "model_status": "example_rule_not_clinically_validated",
                }
            )
    return triggered


class AlertEscalationAgent:
    """In-memory wrapper around configured workflow rules."""

    def __init__(self) -> None:
        self.agent_name = "AlertEscalationAgent"
        self.escalation_log: List[Dict[str, Any]] = []

    def evaluate(
        self,
        bmi_z_score: float,
        bmi_z_change: float = 0.0,
        weight_change_pct: float = 0.0,
        comorbidities: Optional[List[str]] = None,
        interval_months: float = 3.0,
    ) -> Dict[str, Any]:
        triggered = evaluate_escalation_rules(
            bmi_z_score,
            bmi_z_change,
            weight_change_pct,
            comorbidities,
            interval_months,
        )
        self.escalation_log.extend(triggered)
        return {
            "escalations": triggered,
            "review_count": len(triggered),
            "escalation_status": "REVIEW" if triggered else "ROUTINE",
            "log_entries": len(self.escalation_log),
        }
