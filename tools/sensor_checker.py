"""
TwinOps AI - Sensor Threshold Checker Tool
==========================================
Evaluates sensor readings against engineering thresholds.
Returns structured status labels and anomaly flags for each sensor.
"""

import json
from pathlib import Path
from typing import Optional
from loguru import logger

_DATA_DIR = Path(__file__).parent.parent / "data"


class SensorStatus:
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


class SensorThresholdChecker:
    """Tool: Compares sensor readings to defined safe operating thresholds."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or _DATA_DIR
        self.thresholds_file = self.data_dir / "sensor_thresholds.json"
        self._thresholds: dict = {}
        self._load()

    def _load(self) -> None:
        if not self.thresholds_file.exists():
            logger.error(f"Thresholds file not found: {self.thresholds_file}")
            return
        with open(self.thresholds_file, encoding="utf-8") as f:
            self._thresholds = json.load(f)
        logger.debug(f"Loaded thresholds for {list(self._thresholds.keys())}")

    def _classify(self, value: float, key: str) -> str:
        """Classify a single value as normal / warning / critical."""
        t = self._thresholds.get(key, {})
        if not t:
            return SensorStatus.NORMAL
        if value >= t.get("critical_max", float("inf")):
            return SensorStatus.CRITICAL
        if value >= t.get("warning_max", float("inf")):
            return SensorStatus.WARNING
        return SensorStatus.NORMAL

    def check_temperature(self, value: float) -> dict:
        status = self._classify(value, "temperature")
        t = self._thresholds.get("temperature", {})
        return {
            "value": value,
            "unit": t.get("unit", "°C"),
            "status": status,
            "normal_max": t.get("normal_max"),
            "warning_max": t.get("warning_max"),
            "critical_max": t.get("critical_max"),
            "observation": self._temp_observation(value, status, t),
        }

    def _temp_observation(self, v: float, status: str, t: dict) -> str:
        if status == SensorStatus.CRITICAL:
            return (
                f"CRITICAL: Temperature {v}°C exceeds critical limit "
                f"({t.get('critical_max')}°C). Risk of component thermal damage."
            )
        if status == SensorStatus.WARNING:
            return (
                f"WARNING: Temperature {v}°C above normal operating range "
                f"({t.get('normal_max')}°C). Monitor closely."
            )
        return f"Normal: Temperature {v}°C within safe operating range."

    def check_vibration(self, value: float) -> dict:
        status = self._classify(value, "vibration")
        t = self._thresholds.get("vibration", {})
        return {
            "value": value,
            "unit": t.get("unit", "mm/s RMS"),
            "status": status,
            "normal_max": t.get("normal_max"),
            "warning_max": t.get("warning_max"),
            "critical_max": t.get("critical_max"),
            "standard": t.get("standard", "ISO 10816-3"),
            "observation": self._vib_observation(value, status, t),
        }

    def _vib_observation(self, v: float, status: str, t: dict) -> str:
        if status == SensorStatus.CRITICAL:
            return (
                f"CRITICAL: Vibration {v} mm/s exceeds critical threshold "
                f"({t.get('critical_max')} mm/s per ISO 10816-3). Structural risk."
            )
        if status == SensorStatus.WARNING:
            return (
                f"WARNING: Vibration {v} mm/s elevated above normal "
                f"({t.get('normal_max')} mm/s). Inspect bogie and wheel condition."
            )
        return f"Normal: Vibration {v} mm/s within ISO 10816-3 Class III limits."

    def check_runtime(self, value: float) -> dict:
        status = self._classify(value, "runtime_hours")
        t = self._thresholds.get("runtime_hours", {})
        return {
            "value": value,
            "unit": t.get("unit", "hours"),
            "status": status,
            "normal_max": t.get("normal_max"),
            "warning_max": t.get("warning_max"),
            "critical_max": t.get("critical_max"),
            "observation": self._runtime_observation(value, status, t),
        }

    def _runtime_observation(self, v: float, status: str, t: dict) -> str:
        if status == SensorStatus.CRITICAL:
            return (
                f"CRITICAL: Runtime {v} hours significantly exceeds maintenance "
                f"interval ({t.get('normal_max')} hours). Immediate inspection required."
            )
        if status == SensorStatus.WARNING:
            return (
                f"WARNING: Runtime {v} hours approaching overdue status "
                f"(threshold: {t.get('warning_max')} hours). Schedule maintenance."
            )
        remaining = t.get("normal_max", 720) - v
        return f"Normal: {v} hours in service. Approximately {remaining:.0f} hours remaining in maintenance cycle."

    def check_humidity(self, value: float) -> dict:
        status = self._classify(value, "humidity")
        t = self._thresholds.get("humidity", {})
        return {
            "value": value,
            "unit": t.get("unit", "%RH"),
            "status": status,
            "normal_max": t.get("normal_max"),
            "warning_max": t.get("warning_max"),
            "critical_max": t.get("critical_max"),
            "observation": self._humidity_observation(value, status, t),
        }

    def _humidity_observation(self, v: float, status: str, t: dict) -> str:
        if status == SensorStatus.CRITICAL:
            return (
                f"CRITICAL: Humidity {v}%RH at critical level. Accelerated corrosion "
                f"and electrical insulation degradation risk."
            )
        if status == SensorStatus.WARNING:
            return (
                f"WARNING: Humidity {v}%RH above comfort threshold. "
                f"Increased corrosion risk on metal components."
            )
        return f"Normal: Humidity {v}%RH within acceptable range."

    def check_passenger_load(self, value: float) -> dict:
        status = self._classify(value, "passenger_load")
        t = self._thresholds.get("passenger_load", {})
        return {
            "value": value,
            "unit": t.get("unit", "%"),
            "status": status,
            "normal_max": t.get("normal_max"),
            "warning_max": t.get("warning_max"),
            "critical_max": t.get("critical_max"),
            "observation": self._load_observation(value, status, t),
        }

    def _load_observation(self, v: float, status: str, t: dict) -> str:
        if status == SensorStatus.CRITICAL:
            return (
                f"CRITICAL: Passenger load {v}% severely overcrowded "
                f"(limit: {t.get('critical_max')}%). Suspension and bogie overload risk."
            )
        if status == SensorStatus.WARNING:
            return (
                f"WARNING: Passenger load {v}% over rated capacity. "
                f"Increased wear on suspension components."
            )
        return f"Normal: Passenger load {v}% within rated capacity."

    def check_all(
        self,
        temperature: float,
        vibration: float,
        runtime_hours: float,
        humidity: float,
        passenger_load: float,
    ) -> dict:
        """Run all sensor checks and return a consolidated result."""
        results = {
            "temperature": self.check_temperature(temperature),
            "vibration": self.check_vibration(vibration),
            "runtime_hours": self.check_runtime(runtime_hours),
            "humidity": self.check_humidity(humidity),
            "passenger_load": self.check_passenger_load(passenger_load),
        }
        anomalies = [k for k, v in results.items() if v["status"] != SensorStatus.NORMAL]
        critical_count = sum(1 for v in results.values() if v["status"] == SensorStatus.CRITICAL)
        warning_count = sum(1 for v in results.values() if v["status"] == SensorStatus.WARNING)
        results["summary"] = {
            "anomaly_count": len(anomalies),
            "critical_count": critical_count,
            "warning_count": warning_count,
            "anomalous_sensors": anomalies,
        }
        return results
