"""
TwinOps AI - Identity & History Agent
=======================================
Validates coach identity against the fleet database and retrieves all
historical maintenance and fault records.

This agent uses deterministic tools (CSV lookup) rather than LLM reasoning
for the core data retrieval, then uses Gemini to summarize patterns.
"""

from __future__ import annotations

import json
from loguru import logger

from models.digital_twin import CoachInfo, DigitalTwin
from tools.csv_reader import CoachCSVReader
from tools.history_lookup import MaintenanceHistoryLookup
from prompts.agent_prompts import IDENTITY_HISTORY_SYSTEM_PROMPT
from .base_agent import BaseAgent


class IdentityHistoryAgent(BaseAgent):
    """
    Agent 1: Validates coach identity and retrieves maintenance history.

    Uses deterministic CSV lookup tools + Gemini for pattern analysis.
    """

    agent_name = "Identity & History Agent"
    system_prompt = IDENTITY_HISTORY_SYSTEM_PROMPT

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._csv_reader = CoachCSVReader()
        self._history_lookup = MaintenanceHistoryLookup()

    def run(self, twin: DigitalTwin) -> DigitalTwin:
        """
        Populate the Digital Twin with coach identity and historical records.
        """
        coach_id = twin.coach_info.coach_id
        logger.info(f"[{self.agent_name}] Processing coach: {coach_id}")

        # --- Step 1: Look up coach in database (deterministic tool) ---
        coach_data = self._csv_reader.get_coach(coach_id)
        coach_exists = coach_data is not None

        if coach_exists:
            # Enrich the CoachInfo from database
            twin.coach_info = CoachInfo(
                coach_id=coach_id,
                coach_type=coach_data.get("coach_type", "Unknown"),
                manufacture_year=int(coach_data["manufacture_year"])
                if coach_data.get("manufacture_year")
                else None,
                last_overhaul=coach_data.get("last_overhaul"),
                assigned_route=coach_data.get("assigned_route"),
                total_lifetime_hours=float(coach_data["total_lifetime_hours"])
                if coach_data.get("total_lifetime_hours")
                else None,
            )
            logger.info(f"[{self.agent_name}] Coach found: {twin.coach_info.coach_type}")
        else:
            logger.warning(f"[{self.agent_name}] Coach {coach_id} not found in database")

        # --- Step 2: Retrieve maintenance history (deterministic tool) ---
        maintenance_records = self._history_lookup.get_maintenance_history(coach_id)
        fault_records = self._history_lookup.get_fault_history(coach_id)
        last_inspection = self._history_lookup.get_last_inspection_date(coach_id)
        open_faults = self._history_lookup.count_open_faults(coach_id)
        has_critical = self._history_lookup.has_critical_history(coach_id)

        twin.maintenance_history = maintenance_records
        twin.fault_history = fault_records
        twin.last_inspection_date = last_inspection
        twin.total_maintenance_events = len(maintenance_records)

        logger.info(
            f"[{self.agent_name}] Found {len(maintenance_records)} maintenance records, "
            f"{len(fault_records)} fault records, {open_faults} open faults"
        )

        # --- Step 3: Use Gemini to analyze history patterns ---
        history_observations = self._analyze_history_with_llm(
            coach_id=coach_id,
            coach_exists=coach_exists,
            maintenance_records=maintenance_records,
            fault_records=fault_records,
            open_faults=open_faults,
            has_critical=has_critical,
        )

        # Log the agent's findings
        twin.log_agent(
            self.agent_name,
            "completed",
            f"Coach {'found' if coach_exists else 'not in database'}. "
            f"{len(maintenance_records)} maintenance records, {len(fault_records)} faults, "
            f"{open_faults} open.",
            details="\n".join(history_observations),
        )

        return twin

    def _analyze_history_with_llm(
        self,
        coach_id: str,
        coach_exists: bool,
        maintenance_records: list,
        fault_records: list,
        open_faults: int,
        has_critical: bool,
    ) -> list[str]:
        """Use Gemini to identify patterns in maintenance/fault history."""

        if not maintenance_records and not fault_records:
            return [f"No historical records found for {coach_id}. Operating with unknown history."]

        # Build history summary for LLM
        maintenance_summary = "\n".join(
            f"- [{r.date}] {r.type} — {r.component}: {r.description}"
            for r in maintenance_records[-8:]
        )
        fault_summary = "\n".join(
            f"- [{f.date}] {f.fault_code} ({f.severity}): {f.description} [{'RESOLVED' if f.resolved else 'OPEN'}]"
            for f in fault_records[-8:]
        )

        prompt = f"""Analyze the maintenance and fault history for railway coach {coach_id}.

MAINTENANCE RECORDS (most recent first):
{maintenance_summary or 'None'}

FAULT RECORDS (most recent first):
{fault_summary or 'None'}

Open faults: {open_faults}
Has critical history: {has_critical}

Provide your analysis as a JSON object:
{{
  "history_observations": [
    "Observation 1 — be specific and technical",
    "Observation 2",
    "Observation 3 (max 5 observations)"
  ],
  "recurring_components": ["component1", "component2"],
  "risk_pattern": "low/medium/high — brief explanation",
  "agent_summary": "One sentence technical summary"
}}

Focus on: recurring failure patterns, escalating severity trends, components frequently maintained, 
time between failures for repeated components."""

        try:
            response_text = self._call_llm(prompt)
            parsed = self._extract_json(response_text)
            observations = parsed.get("history_observations", [])
            if parsed.get("agent_summary"):
                observations.insert(0, f"Pattern Analysis: {parsed['agent_summary']}")
            return observations
        except Exception as e:
            logger.warning(f"[{self.agent_name}] LLM history analysis failed: {e}")
            # Fallback to rule-based observations
            obs = []
            if open_faults > 0:
                obs.append(f"⚠️ {open_faults} unresolved fault(s) still open — requires immediate attention.")
            if has_critical:
                obs.append("History contains critical-severity faults — elevated risk profile.")
            if len(fault_records) > 5:
                obs.append(f"High fault frequency: {len(fault_records)} recorded faults.")
            return obs or ["History retrieved. No significant patterns identified."]

    def _mock_response(self) -> str:
        return json.dumps({
            "history_observations": [
                "Maintenance records retrieved from fleet database.",
                "Standard maintenance patterns observed.",
            ],
            "agent_summary": "Mock history analysis complete.",
            "mock": True,
        })
