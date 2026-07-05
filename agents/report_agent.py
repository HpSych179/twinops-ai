"""
TwinOps AI - Report Agent
===========================
Generates the final professional engineering maintenance report by
combining the ReportFormatter tool with Gemini's narrative generation.
"""

from __future__ import annotations

import json
from datetime import datetime
from loguru import logger
import pytz

from models.digital_twin import DigitalTwin
from tools.report_formatter import ReportFormatter
from prompts.agent_prompts import REPORT_SYSTEM_PROMPT
from .base_agent import BaseAgent


class ReportAgent(BaseAgent):
    """
    Agent 6: Generates the final engineering maintenance report.

    Combines structured Markdown (from ReportFormatter tool) with
    a Gemini-generated executive narrative.
    """

    agent_name = "Report Agent"
    system_prompt = REPORT_SYSTEM_PROMPT

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._formatter = ReportFormatter()

    def run(self, twin: DigitalTwin) -> DigitalTwin:
        """Generate the final report and finalize the Digital Twin."""
        logger.info(f"[{self.agent_name}] Generating report for {twin.coach_info.coach_id}")

        # --- Step 1: Get Gemini's executive narrative & key findings ---
        report_content = self._generate_executive_content(twin)

        # --- Step 2: Generate structured Markdown report ---
        # The formatter handles the structured sections; we inject Gemini's narrative
        structured_report = self._formatter.generate(twin)

        # --- Step 3: Prepend executive narrative if available ---
        if report_content.get("executive_narrative"):
            narrative_section = (
                "\n\n### Executive Narrative\n\n"
                f"{report_content['executive_narrative']}\n"
            )
            # Insert narrative after the executive summary table
            structured_report = structured_report.replace(
                "## Asset Information",
                f"{narrative_section}\n## Asset Information",
                1,
            )

        # --- Step 4: Finalize the Digital Twin ---
        twin.final_report = structured_report
        twin.report_generated_at = datetime.now(pytz.UTC).isoformat()
        twin.pipeline_completed_at = datetime.now(pytz.UTC).isoformat()
        twin.pipeline_status = "completed"

        twin.log_agent(
            self.agent_name,
            "completed",
            f"Report generated ({len(structured_report)} chars). Pipeline complete.",
            details=report_content.get("agent_summary", ""),
        )

        return twin

    def _generate_executive_content(self, twin: DigitalTwin) -> dict:
        """Use Gemini to generate the executive narrative and action items."""

        context = {
            "coach_id": twin.coach_info.coach_id,
            "coach_type": twin.coach_info.coach_type,
            "route": twin.coach_info.assigned_route,
            "health_score": twin.overall_health_score,
            "risk_score": twin.overall_risk_score,
            "health_status": twin.health_status.value if hasattr(twin.health_status, 'value') else str(twin.health_status),
            "safety_status": twin.safety_assessment.safety_status.value,
            "operational_decision": twin.safety_assessment.operational_decision.value,
            "maintenance_priority": twin.predictive_maintenance.maintenance_priority.value,
            "rul_hours": twin.predictive_maintenance.remaining_useful_life_hours,
            "key_anomalies": twin.sensor_analysis.anomalies_detected,
            "safety_concerns": twin.safety_assessment.safety_concerns[:3],
            "maintenance_reasoning": twin.predictive_maintenance.reasoning[:3],
            "environmental_risk": twin.environmental_risk.humidity_risk,
            "wear_multiplier": twin.environmental_risk.climate_exposure_factor,
            "open_faults": sum(1 for f in twin.fault_history if not f.resolved),
            "passenger_risk": twin.safety_assessment.passenger_risk_level,
        }

        prompt = f"""You are the TwinOps AI Report Agent. Generate executive content for a 
professional railway maintenance report.

COMPLETE ASSESSMENT:
{json.dumps(context, indent=2)}

Generate report content as JSON:
{{
  "executive_narrative": "2-3 sentence professional executive summary suitable for engineering management. Include health status, key findings, and operational impact.",
  "key_findings": [
    "Most critical finding",
    "Second most important finding", 
    "Third finding",
    "Fourth finding",
    "Fifth finding"
  ],
  "critical_alerts": ["Any items requiring IMMEDIATE attention — empty list if none"],
  "prioritized_actions": [
    "1. Most urgent action",
    "2. Second action",
    "3. Third action",
    "4. Fourth action",
    "5. Fifth action"
  ],
  "report_confidence": "Assessment of data quality and recommendation confidence",
  "agent_summary": "Report generation complete — one sentence status"
}}

Write in professional engineering language. Be specific and actionable.
Reference actual sensor values and measurements where relevant."""

        try:
            response_text = self._call_llm(prompt)
            return self._extract_json(response_text)
        except Exception as e:
            logger.warning(f"[{self.agent_name}] LLM report generation failed: {e}")
            return {
                "executive_narrative": (
                    f"Coach {twin.coach_info.coach_id} has been assessed with an overall health score of "
                    f"{twin.overall_health_score:.0f}/100 and risk score of {twin.overall_risk_score:.0f}/100. "
                    f"Safety status: {twin.safety_assessment.safety_status.value.upper()}. "
                    f"Recommended operational decision: {twin.safety_assessment.operational_decision.value.upper()}."
                ),
                "agent_summary": "Report generated with fallback content.",
            }

    def _mock_response(self) -> str:
        return json.dumps({
            "executive_narrative": "Mock executive narrative for testing purposes.",
            "key_findings": ["Mock finding 1", "Mock finding 2"],
            "prioritized_actions": ["Mock action 1", "Mock action 2"],
            "agent_summary": "Mock report generated.",
            "mock": True,
        })
