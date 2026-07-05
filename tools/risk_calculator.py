"""
TwinOps AI - Risk Score Calculator Tool
=========================================
Computes a composite risk score (0–100) and health score (0–100)
by combining sensor anomalies, runtime status, environmental risk,
and historical fault patterns.

Score interpretation:
    Health Score: 100 = perfect condition, 0 = total failure
    Risk Score:   0 = no risk, 100 = maximum risk
"""

from loguru import logger
from models.digital_twin import HealthStatus, MaintenancePriority


# Weights for risk calculation (must sum to 1.0)
WEIGHTS = {
    "sensor": 0.35,       # Sensor anomaly contribution
    "runtime": 0.25,      # Runtime / maintenance overdue contribution
    "environment": 0.20,  # Environmental wear contribution
    "history": 0.20,      # Historical fault / maintenance patterns
}


class RiskScoreCalculator:
    """Tool: Computes composite health and risk scores for a digital twin."""

    def calculate(
        self,
        sensor_health_score: float,         # 0–100 from sensor agent
        runtime_cycle_percent: float,       # % of maintenance interval used
        environmental_wear_percent: float,  # % additional wear from environment
        fault_count: int,                   # total historical faults
        critical_fault_count: int,          # historical critical faults
        open_fault_count: int,              # currently open/unresolved faults
        maintenance_event_count: int,       # total maintenance events
    ) -> dict:
        """
        Calculate composite risk and health scores.

        Returns:
            dict with risk_score, health_score, health_status,
            maintenance_priority, and contributing factors.
        """
        # --- Sensor sub-score (higher anomaly = higher risk) ---
        sensor_risk = max(0.0, 100.0 - sensor_health_score)

        # --- Runtime sub-score ---
        # 0–100%: 0 risk; 100–120%: linear 0–50; >120%: linear 50–100
        if runtime_cycle_percent <= 100:
            runtime_risk = runtime_cycle_percent * 0.3  # Low risk until overdue
        elif runtime_cycle_percent <= 150:
            runtime_risk = 30 + (runtime_cycle_percent - 100) * 1.4
        else:
            runtime_risk = min(100, 100 + (runtime_cycle_percent - 150) * 0.5)

        # --- Environmental sub-score ---
        env_risk = min(100, environmental_wear_percent * 2.5)

        # --- History sub-score ---
        history_risk = min(
            100,
            (critical_fault_count * 15)
            + (fault_count * 3)
            + (open_fault_count * 20),
        )

        # --- Composite risk score (weighted) ---
        risk_score = (
            WEIGHTS["sensor"] * sensor_risk
            + WEIGHTS["runtime"] * runtime_risk
            + WEIGHTS["environment"] * env_risk
            + WEIGHTS["history"] * history_risk
        )
        risk_score = round(min(100.0, max(0.0, risk_score)), 1)
        health_score = round(100.0 - risk_score, 1)

        # --- Classify health status ---
        health_status = self._classify_health(risk_score, open_fault_count, critical_fault_count)
        maintenance_priority = self._classify_priority(risk_score, runtime_cycle_percent, open_fault_count)

        return {
            "risk_score": risk_score,
            "health_score": health_score,
            "health_status": health_status,
            "maintenance_priority": maintenance_priority,
            "contributing_factors": {
                "sensor_risk": round(sensor_risk, 1),
                "runtime_risk": round(runtime_risk, 1),
                "environmental_risk": round(env_risk, 1),
                "history_risk": round(history_risk, 1),
            },
            "weights_applied": WEIGHTS,
        }

    def _classify_health(
        self,
        risk_score: float,
        open_faults: int,
        critical_faults: int,
    ) -> HealthStatus:
        # Open faults always elevate status
        if open_faults > 0 or critical_faults > 3 or risk_score >= 70:
            return HealthStatus.CRITICAL
        if risk_score >= 45:
            return HealthStatus.WARNING
        if risk_score >= 20:
            return HealthStatus.GOOD
        return HealthStatus.GOOD

    def _classify_priority(
        self,
        risk_score: float,
        runtime_cycle_percent: float,
        open_faults: int,
    ) -> MaintenancePriority:
        if open_faults > 0 or risk_score >= 75:
            return MaintenancePriority.IMMEDIATE
        if risk_score >= 55 or runtime_cycle_percent >= 130:
            return MaintenancePriority.HIGH
        if risk_score >= 35 or runtime_cycle_percent >= 100:
            return MaintenancePriority.MEDIUM
        if risk_score >= 15:
            return MaintenancePriority.LOW
        return MaintenancePriority.NONE
