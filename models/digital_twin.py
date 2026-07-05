"""
TwinOps AI - Shared Digital Twin State Model
============================================
The Digital Twin is the central data structure shared across all agents.
Every agent reads from and writes to this object, enabling collaborative
reasoning without passing disconnected text between agents.

Architecture Decision:
    Using Pydantic BaseModel for type safety and easy serialization.
    The twin passes through each agent which enriches it progressively.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
import pytz


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class HealthStatus(str, Enum):
    UNKNOWN = "unknown"
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"


class MaintenancePriority(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    IMMEDIATE = "immediate"


class SafetyStatus(str, Enum):
    SAFE = "safe"
    WARNING = "warning"
    CRITICAL = "critical"


class OperationalDecision(str, Enum):
    CONTINUE = "continue"
    MONITOR = "monitor"
    RESTRICT = "restrict"
    STOP = "stop"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class CoachInfo(BaseModel):
    """Basic identity and specification of the railway coach."""
    coach_id: str
    coach_type: str = "Unknown"
    manufacture_year: Optional[int] = None
    last_overhaul: Optional[str] = None
    assigned_route: Optional[str] = None
    total_lifetime_hours: Optional[float] = None


class SensorReadings(BaseModel):
    """Current sensor values submitted by the operator."""
    temperature_celsius: float
    vibration_mm_s: float          # vibration in mm/s RMS
    runtime_hours: float           # hours since last maintenance
    humidity_percent: float
    passenger_load_percent: float  # 0–100%
    timestamp: str = Field(
        default_factory=lambda: datetime.now(pytz.UTC).isoformat()
    )


class MaintenanceRecord(BaseModel):
    """Single historical maintenance or inspection record."""
    date: str
    type: str          # e.g., "Scheduled", "Corrective", "Inspection"
    component: str
    description: str
    technician: Optional[str] = None


class FaultRecord(BaseModel):
    """Single historical fault or failure record."""
    date: str
    fault_code: str
    description: str
    severity: str      # Low / Medium / High
    resolved: bool = True


class SensorAnalysis(BaseModel):
    """Output from the Sensor Analysis Agent."""
    temperature_status: str = "not_analyzed"
    vibration_status: str = "not_analyzed"
    runtime_status: str = "not_analyzed"
    anomalies_detected: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    sensor_health_score: float = 0.0  # 0–100


class EnvironmentalRisk(BaseModel):
    """Output from the Environmental Risk Agent."""
    humidity_risk: str = "not_analyzed"
    climate_exposure_factor: float = 1.0  # multiplier, >1 = more wear
    environmental_observations: list[str] = Field(default_factory=list)
    additional_wear_estimate_percent: float = 0.0


class PredictiveMaintenance(BaseModel):
    """Output from the Predictive Maintenance Agent."""
    remaining_useful_life_hours: Optional[float] = None
    maintenance_priority: MaintenancePriority = MaintenancePriority.NONE
    inspection_urgency: str = "not_analyzed"
    next_recommended_action: str = ""
    reasoning: list[str] = Field(default_factory=list)


class SafetyAssessment(BaseModel):
    """Output from the Safety Agent."""
    safety_status: SafetyStatus = SafetyStatus.SAFE
    operational_decision: OperationalDecision = OperationalDecision.CONTINUE
    safety_concerns: list[str] = Field(default_factory=list)
    passenger_risk_level: str = "not_analyzed"
    safety_reasoning: str = ""


class AgentObservation(BaseModel):
    """Log entry from any agent during processing."""
    agent_name: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(pytz.UTC).isoformat()
    )
    status: str  # "started" | "completed" | "error"
    summary: str
    details: Optional[str] = None


# ---------------------------------------------------------------------------
# Main Digital Twin
# ---------------------------------------------------------------------------

class DigitalTwin(BaseModel):
    """
    Shared Digital Twin state object.

    This is the single source of truth that flows through all agents.
    Each agent enriches specific sections without overwriting others.
    The twin represents the complete knowledge state of one railway coach.
    """

    # Identity (set at intake)
    coach_info: CoachInfo

    # Current sensor data (set at intake)
    sensor_readings: SensorReadings

    # Historical data (populated by Identity & History Agent)
    maintenance_history: list[MaintenanceRecord] = Field(default_factory=list)
    fault_history: list[FaultRecord] = Field(default_factory=list)
    last_inspection_date: Optional[str] = None
    total_maintenance_events: int = 0

    # Analysis outputs (each agent fills its section)
    sensor_analysis: SensorAnalysis = Field(default_factory=SensorAnalysis)
    environmental_risk: EnvironmentalRisk = Field(default_factory=EnvironmentalRisk)
    predictive_maintenance: PredictiveMaintenance = Field(
        default_factory=PredictiveMaintenance
    )
    safety_assessment: SafetyAssessment = Field(default_factory=SafetyAssessment)

    # Computed scores
    overall_health_score: float = 0.0          # 0–100
    overall_risk_score: float = 0.0            # 0–100
    health_status: HealthStatus = HealthStatus.UNKNOWN

    # Final report text (generated by Report Agent)
    final_report: Optional[str] = None
    report_generated_at: Optional[str] = None

    # Agent execution log
    agent_observations: list[AgentObservation] = Field(default_factory=list)

    # Pipeline metadata
    pipeline_started_at: str = Field(
        default_factory=lambda: datetime.now(pytz.UTC).isoformat()
    )
    pipeline_completed_at: Optional[str] = None
    pipeline_status: str = "pending"  # pending | running | completed | error

    # ---------------------------------------------------------------------------
    # Helper methods
    # ---------------------------------------------------------------------------

    def log_agent(
        self,
        agent_name: str,
        status: str,
        summary: str,
        details: Optional[str] = None,
    ) -> None:
        """Append an observation to the agent execution log."""
        self.agent_observations.append(
            AgentObservation(
                agent_name=agent_name,
                status=status,
                summary=summary,
                details=details,
            )
        )

    def to_context_dict(self) -> dict[str, Any]:
        """
        Serialize the twin to a concise dict for passing to LLM agents.
        Omits raw history lists to keep prompt sizes manageable.
        """
        return {
            "coach_id": self.coach_info.coach_id,
            "coach_type": self.coach_info.coach_type,
            "last_overhaul": self.coach_info.last_overhaul,
            "sensors": self.sensor_readings.model_dump(
                exclude={"timestamp"}
            ),
            "maintenance_history_count": len(self.maintenance_history),
            "fault_history_count": len(self.fault_history),
            "last_inspection": self.last_inspection_date,
            "sensor_analysis": self.sensor_analysis.model_dump(),
            "environmental_risk": self.environmental_risk.model_dump(),
            "predictive_maintenance": self.predictive_maintenance.model_dump(),
            "safety_assessment": self.safety_assessment.model_dump(),
            "overall_health_score": self.overall_health_score,
            "overall_risk_score": self.overall_risk_score,
            "health_status": self.health_status,
        }

    def to_history_summary(self) -> str:
        """Return a concise text summary of maintenance and fault history."""
        lines = []
        if self.maintenance_history:
            lines.append("=== Recent Maintenance (last 5) ===")
            for r in self.maintenance_history[-5:]:
                lines.append(f"  [{r.date}] {r.type} — {r.component}: {r.description}")
        if self.fault_history:
            lines.append("=== Recent Faults (last 5) ===")
            for f in self.fault_history[-5:]:
                resolved = "RESOLVED" if f.resolved else "OPEN"
                lines.append(
                    f"  [{f.date}] {f.fault_code} ({f.severity}) [{resolved}]: {f.description}"
                )
        return "\n".join(lines) if lines else "No history available."
