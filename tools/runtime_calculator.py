"""
TwinOps AI - Runtime Calculator Tool
=====================================
Computes derived runtime metrics including maintenance cycle position,
overdue status, and wear accumulation estimates.
"""

from loguru import logger


# Standard maintenance intervals (hours)
STANDARD_MAINTENANCE_INTERVAL = 720   # ~30 days continuous operation
EXTENDED_MAINTENANCE_INTERVAL = 960   # Extended schedule (special approval)
OVERHAUL_INTERVAL = 8760             # Annual overhaul (~1 year)


class RuntimeCalculator:
    """Tool: Computes runtime metrics and maintenance cycle status."""

    def calculate_cycle_position(self, runtime_hours: float) -> dict:
        """
        Determine position in the maintenance cycle.

        Args:
            runtime_hours: Hours since last maintenance

        Returns:
            Detailed cycle position metrics
        """
        interval = STANDARD_MAINTENANCE_INTERVAL
        cycle_percent = min((runtime_hours / interval) * 100, 200)  # cap at 200%
        overdue_hours = max(0, runtime_hours - interval)
        hours_remaining = max(0, interval - runtime_hours)

        if runtime_hours >= EXTENDED_MAINTENANCE_INTERVAL:
            cycle_status = "critically_overdue"
        elif runtime_hours >= interval:
            cycle_status = "overdue"
        elif runtime_hours >= interval * 0.85:
            cycle_status = "approaching_due"
        else:
            cycle_status = "within_interval"

        return {
            "runtime_hours": runtime_hours,
            "maintenance_interval_hours": interval,
            "cycle_percent_used": round(cycle_percent, 1),
            "hours_remaining_in_cycle": round(hours_remaining, 1),
            "overdue_hours": round(overdue_hours, 1),
            "cycle_status": cycle_status,
            "observation": self._cycle_observation(runtime_hours, cycle_status, overdue_hours),
        }

    def _cycle_observation(
        self, runtime: float, status: str, overdue: float
    ) -> str:
        obs_map = {
            "critically_overdue": (
                f"Maintenance is critically overdue by {overdue:.0f} hours. "
                f"Immediate maintenance action required to prevent component failure."
            ),
            "overdue": (
                f"Maintenance overdue by {overdue:.0f} hours. "
                f"Schedule maintenance at earliest opportunity."
            ),
            "approaching_due": (
                f"Coach is approaching its {STANDARD_MAINTENANCE_INTERVAL}-hour "
                f"maintenance interval. Plan maintenance within the next few days."
            ),
            "within_interval": (
                f"Coach is within normal maintenance interval. "
                f"Next maintenance due at {STANDARD_MAINTENANCE_INTERVAL} hours."
            ),
        }
        return obs_map.get(status, "Runtime status unknown.")

    def estimate_component_wear(
        self,
        runtime_hours: float,
        total_lifetime_hours: float,
        wear_multiplier: float = 1.0,
    ) -> dict:
        """
        Estimate overall component wear based on runtime.

        Args:
            runtime_hours: Hours since last maintenance
            total_lifetime_hours: Cumulative lifetime hours on the coach
            wear_multiplier: Environmental wear factor (from env tool)

        Returns:
            Wear estimates for key component groups
        """
        # Simplified heuristic wear model (not scientifically precise)
        # Wheel wear: rated life ~500,000 km → ~5,000 hours at avg 100 km/h
        # Brake shoes: rated life ~150,000 km → ~1,500 hours
        # Suspension: rated life ~1,000,000 km → ~10,000 hours
        # Bearings: rated life ~2,000,000 km → ~20,000 hours

        component_lives = {
            "wheels": 5000,
            "brake_shoes": 1500,
            "suspension": 10000,
            "bearings": 20000,
            "hvac": 12000,
        }

        wear_estimates = {}
        for component, life in component_lives.items():
            # Combine lifetime hours with current runtime and environmental factor
            effective_hours = total_lifetime_hours * wear_multiplier
            wear_percent = min((effective_hours / life) * 100, 100)
            wear_estimates[component] = {
                "wear_percent": round(wear_percent, 1),
                "estimated_remaining_life_hours": round(
                    max(0, (life - effective_hours) / wear_multiplier), 0
                ),
                "condition": self._condition_label(wear_percent),
            }

        return {
            "component_wear": wear_estimates,
            "overall_wear_percent": round(
                sum(v["wear_percent"] for v in wear_estimates.values())
                / len(wear_estimates),
                1,
            ),
        }

    def _condition_label(self, wear_percent: float) -> str:
        if wear_percent >= 90:
            return "end_of_life"
        if wear_percent >= 75:
            return "poor"
        if wear_percent >= 50:
            return "fair"
        if wear_percent >= 25:
            return "good"
        return "excellent"

    def estimate_rul(
        self,
        runtime_hours: float,
        total_lifetime_hours: float,
        sensor_health_score: float,
        wear_multiplier: float = 1.0,
        fault_history_count: int = 0,
    ) -> dict:
        """
        Heuristic estimate of Remaining Useful Life (RUL).

        This is an explainable engineering estimate, not a scientifically
        validated predictive model. It combines multiple factors to produce
        a range rather than a single point estimate.

        Args:
            runtime_hours: Hours since last maintenance
            total_lifetime_hours: Total lifetime hours on coach
            sensor_health_score: 0–100 from sensor analysis
            wear_multiplier: Environmental wear factor
            fault_history_count: Number of historical critical/high faults

        Returns:
            RUL estimate with explanation
        """
        # Base estimate from maintenance cycle
        hours_remaining_in_cycle = max(0, STANDARD_MAINTENANCE_INTERVAL - runtime_hours)

        # Adjust for sensor health (lower health = shorter RUL)
        sensor_factor = sensor_health_score / 100.0  # 0.0–1.0
        adjusted_hours = hours_remaining_in_cycle * sensor_factor

        # Adjust for environmental wear
        adjusted_hours /= max(wear_multiplier, 1.0)

        # Penalty for fault history
        fault_penalty = min(fault_history_count * 20, 120)  # max 120 hour penalty
        adjusted_hours = max(0, adjusted_hours - fault_penalty)

        # Confidence label
        confidence = "medium"
        if sensor_health_score < 40 or fault_history_count > 5:
            confidence = "low"
        elif sensor_health_score > 80 and fault_history_count <= 2:
            confidence = "high"

        return {
            "rul_hours_estimate": round(adjusted_hours, 1),
            "rul_range_low": round(adjusted_hours * 0.7, 1),
            "rul_range_high": round(adjusted_hours * 1.3, 1),
            "confidence": confidence,
            "methodology": "Heuristic model combining maintenance cycle, sensor health, environmental wear, and fault history",
            "factors_applied": {
                "sensor_health_factor": round(sensor_factor, 2),
                "wear_multiplier": wear_multiplier,
                "fault_history_penalty_hours": fault_penalty,
            },
        }
