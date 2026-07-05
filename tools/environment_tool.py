"""
TwinOps AI - Environmental Context Tool
========================================
Looks up environmental and climate context for a coach's assigned route.
Returns wear multipliers, corrosion risk levels, and climate observations.
"""

import json
from pathlib import Path
from typing import Optional
from loguru import logger

_DATA_DIR = Path(__file__).parent.parent / "data"


class EnvironmentalContextTool:
    """Tool: Provides environmental risk context based on route assignment."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or _DATA_DIR
        self.env_file = self.data_dir / "environmental_context.json"
        self._data: dict = {}
        self._load()

    def _load(self) -> None:
        if not self.env_file.exists():
            logger.error(f"Environmental context file not found: {self.env_file}")
            return
        with open(self.env_file, encoding="utf-8") as f:
            self._data = json.load(f).get("routes", {})
        logger.debug(f"Loaded environmental context for {len(self._data)} routes")

    def get_route_context(self, route: Optional[str]) -> dict:
        """
        Return environmental context for a given route.

        Args:
            route: Route name as stored in coaches.csv (e.g., "Mumbai-Delhi Express")

        Returns:
            Environmental context dictionary with wear factors and observations
        """
        if not route or route not in self._data:
            logger.info(f"Route '{route}' not found — using default profile")
            context = self._data.get("default", {})
        else:
            context = self._data[route]

        return self._enrich(context, route)

    def _enrich(self, context: dict, route: Optional[str]) -> dict:
        """Add computed fields to the context."""
        result = dict(context)
        result["route"] = route or "Unknown"

        # Compute additional wear estimate
        multiplier = context.get("wear_multiplier", 1.0)
        extra_wear_percent = round((multiplier - 1.0) * 100, 1)
        result["additional_wear_estimate_percent"] = extra_wear_percent

        # Human-readable risk observations
        observations = []
        corrosion = context.get("corrosion_risk", "medium")
        dust = context.get("dust_exposure", "medium")

        if corrosion in ("high", "very_high"):
            observations.append(
                f"High corrosion risk ({corrosion}) on this route. "
                f"Accelerated degradation of metal components expected."
            )
        if dust in ("high",):
            observations.append(
                "High dust exposure on route. Axle box and bogie contamination risk elevated."
            )
        if multiplier >= 1.3:
            observations.append(
                f"Environmental wear factor {multiplier}× above baseline. "
                f"Components age approximately {extra_wear_percent:.0f}% faster than standard."
            )
        if not observations:
            observations.append(
                f"Moderate environmental conditions on this route. "
                f"Standard wear rates expected (×{multiplier})."
            )

        result["observations"] = observations
        return result

    def humidity_risk_label(self, humidity_percent: float, route_context: dict) -> str:
        """Classify humidity risk combining sensor reading with route context."""
        route_avg = route_context.get("avg_humidity_percent", 60)
        effective = (humidity_percent + route_avg) / 2  # blended reading

        if effective >= 80:
            return "high"
        if effective >= 65:
            return "medium"
        return "low"
