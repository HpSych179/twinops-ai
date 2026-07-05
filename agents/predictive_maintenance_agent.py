"""
TwinOps AI - Predictive Maintenance Agent
==========================================
Synthesizes all prior agent findings to estimate RUL, assign maintenance
priority, and recommend specific actions.
"""

from __future__ import annotations

import json
from loguru import logger

from models.digital_twin import DigitalTwin, PredictiveMaintenance, MaintenancePriority
from tools.runtime_calculator import RuntimeCalculator
from tools.risk_calculator import RiskScoreCalculator
from prompts.agent_prompts import PREDICTIVE_MAINTENANCE_SYSTEM_PROMPT
from .base_agent import BaseAgent


class PredictiveMaintenanceAgent(BaseAgent):
    """
    Agent 4: Estimates RUL and determines maintenance priority.

    This agent receives the fully enriched Digital Twin from prior agents
    and synthesizes all findings into maintenance recommendations.
    """

    agent_name = "Predictive Maintenance Agent"
    system_prompt = PREDICTIVE_MAINTENANCE_SYSTEM_PROMPT

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._runtime_calc = RuntimeCalculator()
        self._risk_calc = RiskScoreCalculator()

    def run(self, twin: DigitalTwin) -> DigitalTwin:
        """Populate predictive_maintenance and update health/risk scores."""
        logger.info(f"[{self.agent_name}] Synthesizing findings for {twin.coach_info.coach_id}")

        sensors = twin.sensor_readings
        sensor_analysis = twin.sensor_analysis
        env_risk = twin.environmental_risk

        # --- Step 1: Compute runtime cycle metrics ---
        cycle_metrics = self._runtime_calc.calculate_cycle_position(sensors.runtime_hours)
        runtime_cycle_percent = cycle_metrics["cycle_percent_used"]

        # --- Step 2: Compute RUL estimate ---
        rul_result = self._runtime_calc.estimate_rul(
            runtime_hours=sensors.runtime_hours,
            total_lifetime_hours=twin.coach_info.total_lifetime_hours or 30000,
            sensor_health_score=sensor_analysis.sensor_health_score,
            wear_multiplier=env_risk.climate_exposure_factor,
            fault_history_count=len(
                [f for f in twin.fault_history if f.severity.lower() in ("high", "critical")]
            ),
        )

        # --- Step 3: Compute composite risk & health scores ---
        critical_fault_count = sum(
            1 for f in twin.fault_history if f.severity.lower() == "critical"
        )
        open_fault_count = sum(1 for f in twin.fault_history if not f.resolved)

        scores = self._risk_calc.calculate(
            sensor_health_score=sensor_analysis.sensor_health_score,
            runtime_cycle_percent=runtime_cycle_percent,
            environmental_wear_percent=env_risk.additional_wear_estimate_percent,
            fault_count=len(twin.fault_history),
            critical_fault_count=critical_fault_count,
            open_fault_count=open_fault_count,
            maintenance_event_count=twin.total_maintenance_events,
        )

        # Update Digital Twin scores
        twin.overall_health_score = scores["health_score"]
        twin.overall_risk_score = scores["risk_score"]
        twin.health_status = scores["health_status"]

        # --- Step 4: Get Gemini's contextual assessment ---
        pm_analysis = self._get_llm_assessment(
            twin=twin,
            cycle_metrics=cycle_metrics,
            rul_result=rul_result,
            scores=scores,
        )

        # --- Step 5: Populate Digital Twin ---
        priority = self._parse_priority(pm_analysis.get("maintenance_priority", scores["maintenance_priority"].value))

        twin.predictive_maintenance = PredictiveMaintenance(
            remaining_useful_life_hours=pm_analysis.get(
                "remaining_useful_life_hours", rul_result["rul_hours_estimate"]
            ),
            maintenance_priority=priority,
            inspection_urgency=pm_analysis.get("inspection_urgency", cycle_metrics["cycle_status"]),
            next_recommended_action=pm_analysis.get(
                "next_recommended_action",
                "Schedule routine inspection per maintenance interval",
            ),
            reasoning=pm_analysis.get("reasoning", [cycle_metrics["observation"]]),
        )

        twin.log_agent(
            self.agent_name,
            "completed",
            f"Health: {twin.overall_health_score:.0f}/100. "
            f"Risk: {twin.overall_risk_score:.0f}/100. "
            f"Priority: {twin.predictive_maintenance.maintenance_priority.value.upper()}. "
            f"RUL: ~{twin.predictive_maintenance.remaining_useful_life_hours:.0f}h.",
        )

        return twin

    def _parse_priority(self, value: str) -> MaintenancePriority:
        """Parse string to MaintenancePriority enum, with fallback."""
        try:
            return MaintenancePriority(value.lower())
        except ValueError:
            logger.warning(f"[{self.agent_name}] Unknown priority value: {value}")
            return MaintenancePriority.MEDIUM

    def _get_llm_assessment(
        self,
        twin: DigitalTwin,
        cycle_metrics: dict,
        rul_result: dict,
        scores: dict,
    ) -> dict:
        """Use Gemini to synthesize all findings into a maintenance assessment."""

        # Build a concise context for the LLM
        context = {
            "coach_id": twin.coach_info.coach_id,
            "coach_type": twin.coach_info.coach_type,
            "route": twin.coach_info.assigned_route,
            "manufacture_year": twin.coach_info.manufacture_year,
            "total_lifetime_hours": twin.coach_info.total_lifetime_hours,
            "sensor_health_score": twin.sensor_analysis.sensor_health_score,
            "anomalies": twin.sensor_analysis.anomalies_detected,
            "sensor_observations": twin.sensor_analysis.observations[:3],
            "runtime_cycle_percent": cycle_metrics["cycle_percent_used"],
            "cycle_status": cycle_metrics["cycle_status"],
            "overdue_hours": cycle_metrics["overdue_hours"],
            "rul_estimate_hours": rul_result["rul_hours_estimate"],
            "rul_range": f"{rul_result['rul_range_low']}–{rul_result['rul_range_high']} hours",
            "rul_confidence": rul_result["confidence"],
            "environmental_wear_multiplier": twin.environmental_risk.climate_exposure_factor,
            "additional_wear_percent": twin.environmental_risk.additional_wear_estimate_percent,
            "humidity_risk": twin.environmental_risk.humidity_risk,
            "risk_score": scores["risk_score"],
            "health_score": scores["health_score"],
            "contributing_factors": scores["contributing_factors"],
            "total_fault_count": len(twin.fault_history),
            "critical_fault_count": sum(1 for f in twin.fault_history if f.severity.lower() == "critical"),
            "open_faults": sum(1 for f in twin.fault_history if not f.resolved),
            "last_maintenance": twin.maintenance_history[0].date if twin.maintenance_history else None,
            "last_overhaul": twin.coach_info.last_overhaul,
        }

        prompt = f"""You are the TwinOps AI Predictive Maintenance Agent. Synthesize these findings to 
determine maintenance priority and remaining useful life for this railway coach.

COMPLETE DIGITAL TWIN CONTEXT:
{json.dumps(context, indent=2)}

Based on ALL available data, provide your maintenance assessment as JSON:
{{
  "remaining_useful_life_hours": N (your best estimate in hours),
  "rul_range_low": N,
  "rul_range_high": N,
  "rul_confidence": "low/medium/high",
  "maintenance_priority": "none/low/medium/high/immediate",
  "inspection_urgency": "routine/scheduled/expedited/immediate",
  "next_recommended_action": "Specific, actionable single most important task",
  "reasoning": [
    "Reasoning step 1 — explain specific data points driving your assessment",
    "Reasoning step 2",
    "Reasoning step 3",
    "Reasoning step 4 (max 6 steps)"
  ],
  "agent_summary": "One sentence assessment"
}}

Remember: This is decision support for qualified engineers. Be conservative (safety-first) 
and transparent about your reasoning. Reference specific sensor values and history."""

        try:
            response_text = self._call_llm(prompt)
            return self._extract_json(response_text)
        except Exception as e:
            logger.warning(f"[{self.agent_name}] LLM assessment failed: {e}")
            return {
                "remaining_useful_life_hours": rul_result["rul_hours_estimate"],
                "maintenance_priority": scores["maintenance_priority"].value,
                "inspection_urgency": cycle_metrics["cycle_status"],
                "next_recommended_action": "Schedule inspection per maintenance interval.",
                "reasoning": [cycle_metrics["observation"]],
            }

    def _mock_response(self) -> str:
        return json.dumps({
            "remaining_useful_life_hours": 480,
            "maintenance_priority": "medium",
            "inspection_urgency": "scheduled",
            "next_recommended_action": "Schedule routine maintenance inspection.",
            "reasoning": ["Mock predictive maintenance assessment."],
            "agent_summary": "Mock assessment complete.",
            "mock": True,
        })
