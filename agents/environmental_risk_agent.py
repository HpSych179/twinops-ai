"""
TwinOps AI - Environmental Risk Agent
=======================================
Assesses climate and environmental wear factors for the coach's route.
"""

from __future__ import annotations

import json
from loguru import logger

from models.digital_twin import DigitalTwin, EnvironmentalRisk
from tools.environment_tool import EnvironmentalContextTool
from prompts.agent_prompts import ENVIRONMENTAL_RISK_SYSTEM_PROMPT
from .base_agent import BaseAgent


class EnvironmentalRiskAgent(BaseAgent):
    """
    Agent 3: Evaluates environmental and climatic wear factors.

    Combines route context lookup with Gemini analysis.
    """

    agent_name = "Environmental Risk Agent"
    system_prompt = ENVIRONMENTAL_RISK_SYSTEM_PROMPT

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._env_tool = EnvironmentalContextTool()

    def run(self, twin: DigitalTwin) -> DigitalTwin:
        """Populate the environmental_risk section of the Digital Twin."""
        route = twin.coach_info.assigned_route
        logger.info(f"[{self.agent_name}] Assessing environmental risk for route: {route}")

        # --- Step 1: Get route environmental context (deterministic tool) ---
        route_context = self._env_tool.get_route_context(route)
        humidity_risk = self._env_tool.humidity_risk_label(
            twin.sensor_readings.humidity_percent, route_context
        )

        # --- Step 2: Use Gemini for contextual risk assessment ---
        env_analysis = self._analyze_with_llm(twin, route_context, humidity_risk)

        # --- Step 3: Populate Digital Twin ---
        twin.environmental_risk = EnvironmentalRisk(
            humidity_risk=env_analysis.get("humidity_risk", humidity_risk),
            climate_exposure_factor=env_analysis.get(
                "climate_exposure_factor", route_context.get("wear_multiplier", 1.0)
            ),
            environmental_observations=env_analysis.get(
                "environmental_observations",
                route_context.get("observations", []),
            ),
            additional_wear_estimate_percent=env_analysis.get(
                "additional_wear_estimate_percent",
                route_context.get("additional_wear_estimate_percent", 0),
            ),
        )

        wear_factor = twin.environmental_risk.climate_exposure_factor
        twin.log_agent(
            self.agent_name,
            "completed",
            f"Humidity risk: {twin.environmental_risk.humidity_risk}. "
            f"Wear multiplier: ×{wear_factor:.2f}. "
            f"Corrosion risk: {route_context.get('corrosion_risk', 'unknown')}.",
        )

        return twin

    def _analyze_with_llm(
        self, twin: DigitalTwin, route_context: dict, humidity_risk: str
    ) -> dict:
        """Use Gemini to provide contextual environmental risk assessment."""

        prompt = f"""Assess the environmental wear risk for railway coach {twin.coach_info.coach_id}.

COACH INFORMATION:
- Type: {twin.coach_info.coach_type}
- Assigned Route: {twin.coach_info.assigned_route or 'Unknown'}
- Manufacture Year: {twin.coach_info.manufacture_year or 'Unknown'}
- Total Lifetime Hours: {twin.coach_info.total_lifetime_hours or 'Unknown'}

CURRENT SENSOR READINGS:
- Humidity: {twin.sensor_readings.humidity_percent}% RH
- Temperature: {twin.sensor_readings.temperature_celsius}°C
- Runtime Since Maintenance: {twin.sensor_readings.runtime_hours} hours

ROUTE ENVIRONMENTAL PROFILE:
- Climate Zones: {route_context.get('climate_zones', ['Unknown'])}
- Average Humidity: {route_context.get('avg_humidity_percent', 'N/A')}%
- Average Temperature: {route_context.get('avg_temp_celsius', 'N/A')}°C
- Dust Exposure: {route_context.get('dust_exposure', 'medium')}
- Corrosion Risk: {route_context.get('corrosion_risk', 'medium')}
- Wear Multiplier: ×{route_context.get('wear_multiplier', 1.0)}
- Route Notes: {route_context.get('notes', 'N/A')}

Humidity Risk Classification: {humidity_risk}

Provide environmental risk assessment as JSON:
{{
  "humidity_risk": "low/medium/high/very_high",
  "climate_exposure_factor": 1.XX,
  "additional_wear_estimate_percent": N,
  "corrosion_risk": "low/medium/high/very_high",
  "dust_exposure": "low/medium/high",
  "environmental_observations": [
    "Specific observation about how this environment affects this coach",
    "Component-level impact observation",
    "Recommendation based on environmental risk"
  ],
  "most_at_risk_components": ["component1", "component2"],
  "agent_summary": "One sentence environmental risk summary"
}}

Be specific to this coach type and route. Reference actual values."""

        try:
            response_text = self._call_llm(prompt)
            return self._extract_json(response_text)
        except Exception as e:
            logger.warning(f"[{self.agent_name}] LLM analysis failed: {e}")
            # Fallback to tool data
            return {
                "humidity_risk": humidity_risk,
                "climate_exposure_factor": route_context.get("wear_multiplier", 1.0),
                "additional_wear_estimate_percent": route_context.get("additional_wear_estimate_percent", 0),
                "environmental_observations": route_context.get("observations", []),
            }

    def _mock_response(self) -> str:
        return json.dumps({
            "humidity_risk": "medium",
            "climate_exposure_factor": 1.15,
            "additional_wear_estimate_percent": 15,
            "environmental_observations": ["Standard environmental conditions on route."],
            "agent_summary": "Mock environmental risk assessment.",
            "mock": True,
        })
