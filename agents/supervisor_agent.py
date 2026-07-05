"""
TwinOps AI - Supervisor Agent
==============================
The orchestrator. Coordinates all specialized agents in sequence,
passes the enriched Digital Twin through the pipeline, and surfaces
the final result.

Architecture Decision:
    The Supervisor implements the ADK-style multi-agent coordination pattern:
    sequential delegation with shared state (the Digital Twin) flowing
    through each agent. Each agent enriches its section and passes the
    twin to the next agent. The Supervisor never does the specialist work.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

import pytz
from loguru import logger

from models.digital_twin import (
    CoachInfo,
    DigitalTwin,
    SensorReadings,
)
from .identity_history_agent import IdentityHistoryAgent
from .sensor_analysis_agent import SensorAnalysisAgent
from .environmental_risk_agent import EnvironmentalRiskAgent
from .predictive_maintenance_agent import PredictiveMaintenanceAgent
from .safety_agent import SafetyAgent
from .report_agent import ReportAgent


# Type for progress callbacks (used by UI to show agent status)
ProgressCallback = Callable[[str, str, int, int], None]


class SupervisorAgent:
    """
    TwinOps AI Supervisor — Multi-Agent Pipeline Orchestrator.

    Implements ADK-style agent delegation pattern:
    1. Initialize Digital Twin with input data
    2. Delegate to each specialist agent in sequence
    3. Each agent enriches the shared Digital Twin
    4. Surface the completed twin with final report

    The supervisor decides the pipeline order and handles errors,
    but never performs the specialist reasoning itself.
    """

    PIPELINE = [
        ("identity_history", "Identity & History Agent"),
        ("sensor_analysis", "Sensor Analysis Agent"),
        ("environmental_risk", "Environmental Risk Agent"),
        ("predictive_maintenance", "Predictive Maintenance Agent"),
        ("safety", "Safety Agent"),
        ("report", "Report Agent"),
    ]

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        """
        Initialize all agents in the pipeline.

        Args:
            model: Gemini model name override
            api_key: Gemini API key override
        """
        agent_kwargs = {"model": model, "api_key": api_key}

        self._agents = {
            "identity_history": IdentityHistoryAgent(**agent_kwargs),
            "sensor_analysis": SensorAnalysisAgent(**agent_kwargs),
            "environmental_risk": EnvironmentalRiskAgent(**agent_kwargs),
            "predictive_maintenance": PredictiveMaintenanceAgent(**agent_kwargs),
            "safety": SafetyAgent(**agent_kwargs),
            "report": ReportAgent(**agent_kwargs),
        }

        logger.info(
            f"[Supervisor] Initialized pipeline with {len(self._agents)} agents: "
            + ", ".join(k for k in self._agents.keys())
        )

    def run(
        self,
        coach_id: str,
        temperature_celsius: float,
        vibration_mm_s: float,
        runtime_hours: float,
        humidity_percent: float,
        passenger_load_percent: float,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> DigitalTwin:
        """
        Run the complete multi-agent assessment pipeline.

        Args:
            coach_id: Railway coach identifier
            temperature_celsius: Current temperature reading
            vibration_mm_s: Vibration level in mm/s RMS
            runtime_hours: Hours since last maintenance
            humidity_percent: Relative humidity
            passenger_load_percent: Passenger load as % of rated capacity
            progress_callback: Optional callback(agent_name, status, step, total)
                               for real-time UI updates

        Returns:
            Fully populated DigitalTwin with report
        """
        total_steps = len(self.PIPELINE)
        logger.info(
            f"[Supervisor] Starting pipeline for coach {coach_id}. "
            f"Steps: {total_steps}."
        )

        # --- Initialize the Digital Twin ---
        twin = DigitalTwin(
            coach_info=CoachInfo(coach_id=coach_id.strip().upper()),
            sensor_readings=SensorReadings(
                temperature_celsius=temperature_celsius,
                vibration_mm_s=vibration_mm_s,
                runtime_hours=runtime_hours,
                humidity_percent=humidity_percent,
                passenger_load_percent=passenger_load_percent,
            ),
            pipeline_status="running",
        )

        twin.log_agent(
            "Supervisor",
            "started",
            f"Pipeline started for coach {coach_id}. "
            f"Running {total_steps} specialist agents.",
        )

        # --- Execute pipeline ---
        for step, (agent_key, agent_display_name) in enumerate(self.PIPELINE, 1):
            if progress_callback:
                progress_callback(agent_display_name, "running", step, total_steps)

            logger.info(
                f"[Supervisor] Step {step}/{total_steps}: Delegating to {agent_display_name}"
            )

            agent = self._agents[agent_key]
            try:
                twin = agent.run(twin)
                if progress_callback:
                    progress_callback(agent_display_name, "completed", step, total_steps)
                logger.info(f"[Supervisor] Step {step} complete: {agent_display_name}")

            except Exception as e:
                logger.error(f"[Supervisor] Agent {agent_display_name} failed: {e}")
                twin.log_agent(
                    "Supervisor",
                    "error",
                    f"Agent {agent_display_name} failed: {str(e)[:200]}",
                )
                if progress_callback:
                    progress_callback(agent_display_name, "error", step, total_steps)
                # Continue pipeline despite individual agent failure
                # (twin retains whatever state it had before the failure)
                continue

        # --- Finalize ---
        if twin.pipeline_status != "completed":
            twin.pipeline_status = "completed"
            twin.pipeline_completed_at = datetime.now(pytz.UTC).isoformat()

        twin.log_agent(
            "Supervisor",
            "completed",
            f"Pipeline complete. Health: {twin.overall_health_score:.0f}/100. "
            f"Risk: {twin.overall_risk_score:.0f}/100. "
            f"Safety: {twin.safety_assessment.safety_status.value.upper()}. "
            f"Decision: {twin.safety_assessment.operational_decision.value.upper()}.",
        )

        logger.success(
            f"[Supervisor] Pipeline completed for {coach_id}. "
            f"Health={twin.overall_health_score:.0f}, "
            f"Risk={twin.overall_risk_score:.0f}, "
            f"Safety={twin.safety_assessment.safety_status.value}"
        )

        return twin
