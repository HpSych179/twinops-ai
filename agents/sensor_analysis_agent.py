"""
TwinOps AI - Sensor Analysis Agent
=====================================
Analyzes current sensor readings against engineering thresholds and
uses Gemini to generate expert technical observations.
"""

from __future__ import annotations

import json
from loguru import logger

from models.digital_twin import DigitalTwin, SensorAnalysis
from tools.sensor_checker import SensorThresholdChecker, SensorStatus
from prompts.agent_prompts import SENSOR_ANALYSIS_SYSTEM_PROMPT
from .base_agent import BaseAgent


class SensorAnalysisAgent(BaseAgent):
    """
    Agent 2: Analyzes sensor readings and detects anomalies.

    Uses deterministic threshold checker + Gemini for contextual observations.
    """

    agent_name = "Sensor Analysis Agent"
    system_prompt = SENSOR_ANALYSIS_SYSTEM_PROMPT

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._checker = SensorThresholdChecker()

    def run(self, twin: DigitalTwin) -> DigitalTwin:
        """Analyze sensor readings and populate sensor_analysis section."""
        sensors = twin.sensor_readings
        logger.info(
            f"[{self.agent_name}] Analyzing sensors for {twin.coach_info.coach_id}: "
            f"temp={sensors.temperature_celsius}°C, vib={sensors.vibration_mm_s}mm/s, "
            f"runtime={sensors.runtime_hours}h"
        )

        # --- Step 1: Run deterministic threshold checks ---
        check_results = self._checker.check_all(
            temperature=sensors.temperature_celsius,
            vibration=sensors.vibration_mm_s,
            runtime_hours=sensors.runtime_hours,
            humidity=sensors.humidity_percent,
            passenger_load=sensors.passenger_load_percent,
        )

        # --- Step 2: Compute sensor health score ---
        summary = check_results.get("summary", {})
        sensor_health_score = self._compute_health_score(check_results)

        # --- Step 3: Build anomaly list from threshold results ---
        anomalies = []
        for sensor_key in ["temperature", "vibration", "runtime_hours", "humidity", "passenger_load"]:
            result = check_results.get(sensor_key, {})
            if result.get("status") in (SensorStatus.WARNING, SensorStatus.CRITICAL):
                anomalies.append(result.get("observation", f"{sensor_key} anomaly detected"))

        # --- Step 4: Get Gemini's contextual analysis ---
        gemini_observations = self._get_llm_observations(
            twin=twin,
            check_results=check_results,
            anomalies=anomalies,
            sensor_health_score=sensor_health_score,
        )

        # --- Step 5: Populate Digital Twin ---
        twin.sensor_analysis = SensorAnalysis(
            temperature_status=check_results["temperature"]["status"],
            vibration_status=check_results["vibration"]["status"],
            runtime_status=check_results["runtime_hours"]["status"],
            anomalies_detected=anomalies,
            observations=gemini_observations,
            sensor_health_score=sensor_health_score,
        )

        twin.log_agent(
            self.agent_name,
            "completed",
            f"Sensor health: {sensor_health_score:.0f}/100. "
            f"Anomalies: {len(anomalies)}. "
            f"Critical sensors: {summary.get('critical_count', 0)}.",
            details="\n".join(anomalies),
        )

        return twin

    def _compute_health_score(self, check_results: dict) -> float:
        """
        Compute sensor health score.
        Start at 100, deduct for each warning/critical sensor.
        """
        score = 100.0
        for sensor_key in ["temperature", "vibration", "runtime_hours", "humidity", "passenger_load"]:
            status = check_results.get(sensor_key, {}).get("status", SensorStatus.NORMAL)
            if status == SensorStatus.CRITICAL:
                score -= 22
            elif status == SensorStatus.WARNING:
                score -= 12
        return max(0.0, score)

    def _get_llm_observations(
        self,
        twin: DigitalTwin,
        check_results: dict,
        anomalies: list[str],
        sensor_health_score: float,
    ) -> list[str]:
        """Use Gemini to generate contextual engineering observations."""

        sensor_summary = {
            "temperature_celsius": twin.sensor_readings.temperature_celsius,
            "temperature_status": check_results["temperature"]["status"],
            "vibration_mm_s": twin.sensor_readings.vibration_mm_s,
            "vibration_status": check_results["vibration"]["status"],
            "runtime_hours": twin.sensor_readings.runtime_hours,
            "runtime_status": check_results["runtime_hours"]["status"],
            "humidity_percent": twin.sensor_readings.humidity_percent,
            "humidity_status": check_results["humidity"]["status"],
            "passenger_load_percent": twin.sensor_readings.passenger_load_percent,
            "load_status": check_results["passenger_load"]["status"],
        }

        prompt = f"""Analyze these sensor readings for railway coach {twin.coach_info.coach_id} 
(Type: {twin.coach_info.coach_type}, Route: {twin.coach_info.assigned_route or 'Unknown'}).

SENSOR DATA:
{json.dumps(sensor_summary, indent=2)}

ANOMALIES DETECTED:
{chr(10).join(anomalies) if anomalies else 'None'}

SENSOR HEALTH SCORE: {sensor_health_score:.0f}/100

COACH HISTORY CONTEXT:
- Maintenance events on record: {twin.total_maintenance_events}
- Open faults: {sum(1 for f in twin.fault_history if not f.resolved)}
- Recent faults: {len(twin.fault_history)}

Provide technical engineering observations as a JSON object:
{{
  "observations": [
    "Technical observation 1 — specific, actionable, references actual values",
    "Technical observation 2",
    "Technical observation 3",
    "Technical observation 4 (max 6 observations)"
  ],
  "primary_concern": "The single most important finding",
  "agent_summary": "One sentence technical summary of sensor status"
}}

Be technically precise. Reference actual sensor values and thresholds. 
Link sensor findings to likely mechanical causes (e.g., elevated vibration → possible wheel wear or bogie issue)."""

        try:
            response_text = self._call_llm(prompt)
            parsed = self._extract_json(response_text)
            observations = parsed.get("observations", [])
            if parsed.get("primary_concern") and parsed["primary_concern"] not in observations:
                observations.insert(0, f"PRIMARY: {parsed['primary_concern']}")
            return observations
        except Exception as e:
            logger.warning(f"[{self.agent_name}] LLM observation failed: {e}")
            # Fall back to tool-generated observations
            return [
                check_results[k].get("observation", "")
                for k in ["temperature", "vibration", "runtime_hours", "humidity", "passenger_load"]
                if check_results.get(k, {}).get("observation")
            ]

    def _mock_response(self) -> str:
        return json.dumps({
            "observations": [
                "All sensor readings within normal operating parameters.",
                "No anomalies detected in current scan.",
            ],
            "primary_concern": "None identified in mock mode.",
            "agent_summary": "Mock sensor analysis — all nominal.",
            "mock": True,
        })
