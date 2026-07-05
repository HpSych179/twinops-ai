"""
TwinOps AI - Safety Agent
===========================
The final safety guardian. Determines operational safety status
and issues the go/no-go decision for the coach.

Safety principle: When in doubt, STOP.
Passenger safety always has highest priority.
"""

from __future__ import annotations

import json
from loguru import logger

from models.digital_twin import (
    DigitalTwin,
    SafetyAssessment,
    SafetyStatus,
    OperationalDecision,
)
from prompts.agent_prompts import SAFETY_SYSTEM_PROMPT
from .base_agent import BaseAgent


# Safety trigger thresholds
CRITICAL_RISK_THRESHOLD = 60.0
WARNING_RISK_THRESHOLD = 35.0
CRITICAL_HEALTH_THRESHOLD = 40.0


class SafetyAgent(BaseAgent):
    """
    Agent 5: Determines operational safety status.

    Uses both rule-based safety checks and Gemini reasoning.
    Rule-based checks always take precedence for hard safety limits.
    """

    agent_name = "Safety Agent"
    system_prompt = SAFETY_SYSTEM_PROMPT

    def run(self, twin: DigitalTwin) -> DigitalTwin:
        """Populate the safety_assessment section of the Digital Twin."""
        logger.info(
            f"[{self.agent_name}] Safety assessment for {twin.coach_info.coach_id}. "
            f"Risk={twin.overall_risk_score:.0f}, Health={twin.overall_health_score:.0f}"
        )

        # --- Step 1: Rule-based hard safety checks ---
        hard_triggers = self._check_hard_safety_triggers(twin)

        # --- Step 2: Gemini contextual safety reasoning ---
        safety_analysis = self._assess_with_llm(twin, hard_triggers)

        # --- Step 3: Determine final safety status ---
        # Hard triggers can escalate, but cannot de-escalate Gemini's assessment
        final_status, final_decision = self._determine_final_status(
            llm_status=safety_analysis.get("safety_status", "safe"),
            llm_decision=safety_analysis.get("operational_decision", "continue"),
            hard_triggers=hard_triggers,
        )

        # Merge safety concerns
        llm_concerns = safety_analysis.get("safety_concerns", [])
        all_concerns = hard_triggers + [c for c in llm_concerns if c not in hard_triggers]

        # --- Step 4: Populate Digital Twin ---
        twin.safety_assessment = SafetyAssessment(
            safety_status=SafetyStatus(final_status),
            operational_decision=OperationalDecision(final_decision),
            safety_concerns=all_concerns,
            passenger_risk_level=safety_analysis.get("passenger_risk_level", "low"),
            safety_reasoning=safety_analysis.get(
                "safety_reasoning",
                f"Safety status determined based on risk score {twin.overall_risk_score:.0f}/100.",
            ),
        )

        twin.log_agent(
            self.agent_name,
            "completed",
            f"Safety: {final_status.upper()} | Decision: {final_decision.upper()} | "
            f"Passenger risk: {twin.safety_assessment.passenger_risk_level.upper()}",
            details="\n".join(all_concerns[:5]) if all_concerns else "No safety concerns.",
        )

        return twin

    def _check_hard_safety_triggers(self, twin: DigitalTwin) -> list[str]:
        """
        Rule-based safety triggers that cannot be overridden by LLM.
        These represent absolute engineering safety limits.
        """
        triggers = []
        sensors = twin.sensor_readings
        sa = twin.sensor_analysis

        # Critical sensor readings
        if sa.temperature_status == "critical":
            triggers.append(
                f"CRITICAL: Temperature {sensors.temperature_celsius}°C exceeds safe limit. "
                f"Risk of thermal damage to electronics and passenger discomfort."
            )
        if sa.vibration_status == "critical":
            triggers.append(
                f"CRITICAL: Vibration {sensors.vibration_mm_s} mm/s exceeds ISO 10816-3 "
                f"Class C limit. Structural integrity risk."
            )
        if sa.runtime_status == "critical":
            triggers.append(
                f"CRITICAL: Runtime {sensors.runtime_hours}h significantly exceeds "
                f"maintenance interval. Mandatory inspection required."
            )

        # Open unresolved faults
        open_faults = [f for f in twin.fault_history if not f.resolved]
        if open_faults:
            for fault in open_faults:
                triggers.append(
                    f"OPEN FAULT: {fault.fault_code} — {fault.description} "
                    f"(Severity: {fault.severity})"
                )

        # Overcrowded coach
        if sensors.passenger_load_percent > 120:
            triggers.append(
                f"Passenger overload: {sensors.passenger_load_percent:.0f}% of rated capacity. "
                f"Excessive stress on suspension and bogies."
            )

        # Overall risk score
        if twin.overall_risk_score >= CRITICAL_RISK_THRESHOLD:
            triggers.append(
                f"Overall risk score {twin.overall_risk_score:.0f}/100 exceeds critical "
                f"threshold ({CRITICAL_RISK_THRESHOLD:.0f}). Multi-factor risk convergence."
            )

        return triggers

    def _assess_with_llm(self, twin: DigitalTwin, hard_triggers: list[str]) -> dict:
        """Use Gemini for contextual safety reasoning."""

        context = twin.to_context_dict()

        prompt = f"""You are the TwinOps AI Safety Agent. Make the operational safety determination 
for railway coach {twin.coach_info.coach_id}.

COMPLETE ASSESSMENT CONTEXT:
{json.dumps(context, indent=2)}

HARD SAFETY TRIGGERS ALREADY IDENTIFIED (rule-based):
{chr(10).join(f'- {t}' for t in hard_triggers) if hard_triggers else '- None'}

KEY SAFETY DATA:
- Overall Risk Score: {twin.overall_risk_score:.0f}/100
- Overall Health Score: {twin.overall_health_score:.0f}/100
- Health Status: {twin.health_status}
- Open Faults: {sum(1 for f in twin.fault_history if not f.resolved)}
- Critical Historical Faults: {sum(1 for f in twin.fault_history if f.severity.lower() == 'critical')}
- Maintenance Priority: {twin.predictive_maintenance.maintenance_priority.value}
- RUL Estimate: ~{twin.predictive_maintenance.remaining_useful_life_hours or 'N/A'} hours

HISTORY SUMMARY:
{twin.to_history_summary()}

Provide safety assessment as JSON:
{{
  "safety_status": "safe/warning/critical",
  "operational_decision": "continue/monitor/restrict/stop",
  "safety_concerns": [
    "Specific concern 1",
    "Specific concern 2"
  ],
  "passenger_risk_level": "low/medium/high/critical",
  "safety_reasoning": "Clear explanation of your safety determination (2-3 sentences)",
  "trigger_conditions": ["What specifically triggered your assessment"],
  "agent_summary": "Safety determination in one sentence"
}}

SAFETY PRINCIPLE: When in doubt, choose the more conservative option.
Passenger safety takes absolute precedence over operational convenience."""

        try:
            response_text = self._call_llm(prompt)
            return self._extract_json(response_text)
        except Exception as e:
            logger.warning(f"[{self.agent_name}] LLM safety assessment failed: {e}")
            # Conservative fallback
            return self._rule_based_fallback(twin, hard_triggers)

    def _determine_final_status(
        self,
        llm_status: str,
        llm_decision: str,
        hard_triggers: list[str],
    ) -> tuple[str, str]:
        """
        Determine final status by taking the more conservative of
        LLM assessment and rule-based triggers.
        """
        status_order = {"safe": 0, "warning": 1, "critical": 2}
        decision_order = {"continue": 0, "monitor": 1, "restrict": 2, "stop": 3}

        current_status = status_order.get(llm_status.lower(), 0)
        current_decision = decision_order.get(llm_decision.lower(), 0)

        # Hard triggers escalate status
        if hard_triggers:
            # Count severity of triggers
            critical_keywords = ["CRITICAL:", "OPEN FAULT", "exceeds"]
            critical_count = sum(
                1 for t in hard_triggers if any(kw in t for kw in critical_keywords)
            )
            if critical_count >= 2:
                current_status = max(current_status, 2)  # critical
                current_decision = max(current_decision, 3)  # stop
            elif critical_count == 1:
                current_status = max(current_status, 2)  # critical
                current_decision = max(current_decision, 2)  # restrict
            else:
                current_status = max(current_status, 1)  # warning
                current_decision = max(current_decision, 1)  # monitor

        # Map back to strings
        reverse_status = {v: k for k, v in status_order.items()}
        reverse_decision = {v: k for k, v in decision_order.items()}
        return reverse_status[current_status], reverse_decision[current_decision]

    def _rule_based_fallback(self, twin: DigitalTwin, triggers: list[str]) -> dict:
        """Conservative rule-based safety determination when LLM is unavailable."""
        risk = twin.overall_risk_score
        if triggers or risk >= CRITICAL_RISK_THRESHOLD:
            return {
                "safety_status": "critical",
                "operational_decision": "stop" if triggers else "restrict",
                "safety_concerns": triggers or [f"Risk score {risk:.0f}/100 above critical threshold."],
                "passenger_risk_level": "high",
                "safety_reasoning": "Critical conditions detected. Conservative safety determination applied.",
            }
        elif risk >= WARNING_RISK_THRESHOLD:
            return {
                "safety_status": "warning",
                "operational_decision": "monitor",
                "safety_concerns": [f"Risk score {risk:.0f}/100 above warning threshold."],
                "passenger_risk_level": "medium",
                "safety_reasoning": "Warning conditions detected. Enhanced monitoring recommended.",
            }
        return {
            "safety_status": "safe",
            "operational_decision": "continue",
            "safety_concerns": [],
            "passenger_risk_level": "low",
            "safety_reasoning": "All parameters within acceptable limits.",
        }

    def _mock_response(self) -> str:
        return json.dumps({
            "safety_status": "safe",
            "operational_decision": "continue",
            "safety_concerns": [],
            "passenger_risk_level": "low",
            "safety_reasoning": "Mock safety assessment — all nominal.",
            "agent_summary": "Mock: Coach is safe for operation.",
            "mock": True,
        })
