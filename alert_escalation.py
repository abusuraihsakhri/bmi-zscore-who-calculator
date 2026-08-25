#!/usr/bin/env python3
"""
Alert Escalation for BMI Z-Score WHO Calculator.
Manages escalation workflows for critical BMI z-score findings
with configurable severity thresholds and notification routing.
"""

import datetime
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class EscalationRule:
    """Defines when and how to escalate."""
    rule_id: str
    trigger_condition: str
    severity: str
    escalate_to: str
    time_limit_hours: int
    requires_acknowledgment: bool = True
    auto_action: Optional[str] = None


ESCALATION_RULES = [
    EscalationRule(
        rule_id="ESCAL-001",
        trigger_condition="bmi_z_score < -3.0",
        severity="CRITICAL",
        escalate_to="pediatric_endocrinology",
        time_limit_hours=4,
        auto_action="order_comprehensive_nutritional_panel",
    ),
    EscalationRule(
        rule_id="ESCAL-002",
        trigger_condition="bmi_z_score > 3.5",
        severity="CRITICAL",
        escalate_to="pediatric_obesity_clinic",
        time_limit_hours=24,
        auto_action="schedule_dietitian_consult",
    ),
    EscalationRule(
        rule_id="ESCAL-003",
        trigger_condition="bmi_z_score_change > 1.0 in 3 months",
        severity="WARNING",
        escalate_to="primary_care_provider",
        time_limit_hours=48,
    ),
    EscalationRule(
        rule_id="ESCAL-004",
        trigger_condition="bmi_z_score_change < -1.0 in 3 months",
        severity="WARNING",
        escalate_to="pediatric_gastroenterology",
        time_limit_hours=24,
        auto_action="order_celiac_screen",
    ),
    EscalationRule(
        rule_id="ESCAL-005",
        trigger_condition="weight_loss > 5% in 1 month",
        severity="CRITICAL",
        escalate_to="pediatrics_inpatient",
        time_limit_hours=2,
        auto_action="initiate_refeeding_protocol_screening",
    ),
    EscalationRule(
        rule_id="ESCAL-006",
        trigger_condition="bmi_z_score < -2.0 AND comorbidity_present",
        severity="WARNING",
        escalate_to="multidisciplinary_team",
        time_limit_hours=12,
    ),
]


def evaluate_escalation_rules(bmi_z_score: float, bmi_z_change: float = 0.0,
                               weight_change_pct: float = 0.0,
                               comorbidities: Optional[List[str]] = None,
                               interval_months: float = 3.0) -> List[Dict[str, Any]]:
    """Evaluate escalation rules and return triggered escalations."""
    comorbidities = comorbidities or []
    triggered = []

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
        elif rule.rule_id == "ESCAL-005" and weight_change_pct < -5.0:
            should_trigger = True
        elif rule.rule_id == "ESCAL-006" and bmi_z_score < -2.0 and len(comorbidities) > 0:
            should_trigger = True

        if should_trigger:
            triggered.append({
                "rule_id": rule.rule_id,
                "trigger_condition": rule.trigger_condition,
                "severity": rule.severity,
                "escalate_to": rule.escalate_to,
                "time_limit_hours": rule.time_limit_hours,
                "requires_acknowledgment": rule.requires_acknowledgment,
                "auto_action": rule.auto_action,
                "escalation_id": str(uuid.uuid4())[:8],
                "escalation_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            })

    return triggered


class AlertEscalationAgent:
    """Sub-agent for alert escalation management."""

    def __init__(self):
        self.agent_name = "AlertEscalationAgent"
        self.escalation_log: List[Dict[str, Any]] = []

    def evaluate(self, bmi_z_score: float, bmi_z_change: float = 0.0,
                 weight_change_pct: float = 0.0,
                 comorbidities: Optional[List[str]] = None,
                 interval_months: float = 3.0) -> Dict[str, Any]:
        """Evaluate escalation triggers and manage escalation workflow."""
        triggered = evaluate_escalation_rules(
            bmi_z_score, bmi_z_change, weight_change_pct, comorbidities, interval_months
        )

        self.escalation_log.extend(triggered)

        critical_count = sum(1 for e in triggered if e["severity"] == "CRITICAL")
        warning_count = sum(1 for e in triggered if e["severity"] == "WARNING")

        return {
            "escalations": triggered,
            "critical_count": critical_count,
            "warning_count": warning_count,
            "total_escalations": len(triggered),
            "escalation_status": "IMMEDIATE_ACTION" if critical_count > 0 else (
                "TIME_SENSITIVE" if warning_count > 0 else "ROUTINE"
            ),
            "log_entries": len(self.escalation_log),
        }
