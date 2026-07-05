"""
TwinOps AI - Report Formatter Tool
=====================================
Generates professional engineering maintenance reports from the Digital Twin.
Produces structured Markdown output suitable for display in the Streamlit UI.
"""

from datetime import datetime
from typing import Optional
import pytz

from models.digital_twin import (
    DigitalTwin,
    HealthStatus,
    MaintenancePriority,
    SafetyStatus,
    OperationalDecision,
)


# Status icons for visual clarity in Markdown
STATUS_ICONS = {
    HealthStatus.GOOD: "🟢",
    HealthStatus.WARNING: "🟡",
    HealthStatus.CRITICAL: "🔴",
    HealthStatus.UNKNOWN: "⚪",
}

PRIORITY_ICONS = {
    MaintenancePriority.NONE: "⚪",
    MaintenancePriority.LOW: "🔵",
    MaintenancePriority.MEDIUM: "🟡",
    MaintenancePriority.HIGH: "🟠",
    MaintenancePriority.IMMEDIATE: "🔴",
}

SAFETY_ICONS = {
    SafetyStatus.SAFE: "✅",
    SafetyStatus.WARNING: "⚠️",
    SafetyStatus.CRITICAL: "🚨",
}

DECISION_ICONS = {
    OperationalDecision.CONTINUE: "▶️",
    OperationalDecision.MONITOR: "👁️",
    OperationalDecision.RESTRICT: "⚠️",
    OperationalDecision.STOP: "🛑",
}


class ReportFormatter:
    """Tool: Renders a DigitalTwin into a structured engineering report."""

    def generate(self, twin: DigitalTwin) -> str:
        """
        Generate a full Markdown engineering report from a completed Digital Twin.

        Args:
            twin: A fully populated DigitalTwin object

        Returns:
            Markdown string containing the formatted report
        """
        timestamp = datetime.now(pytz.UTC).strftime("%Y-%m-%d %H:%M UTC")
        sections = [
            self._header(twin, timestamp),
            self._executive_summary(twin),
            self._asset_information(twin),
            self._sensor_findings(twin),
            self._environmental_findings(twin),
            self._maintenance_assessment(twin),
            self._safety_assessment(twin),
            self._maintenance_history_summary(twin),
            self._recommended_actions(twin),
            self._footer(timestamp),
        ]
        return "\n\n".join(s for s in sections if s)

    # -----------------------------------------------------------------------
    # Section builders
    # -----------------------------------------------------------------------

    def _header(self, twin: DigitalTwin, timestamp: str) -> str:
        status_icon = STATUS_ICONS.get(twin.health_status, "⚪")
        return f"""# {status_icon} TwinOps AI — Engineering Maintenance Report

**Coach ID:** `{twin.coach_info.coach_id}`  
**Report Generated:** {timestamp}  
**Pipeline Status:** {twin.pipeline_status.upper()}

---"""

    def _executive_summary(self, twin: DigitalTwin) -> str:
        health_icon = STATUS_ICONS.get(twin.health_status, "⚪")
        priority_icon = PRIORITY_ICONS.get(twin.predictive_maintenance.maintenance_priority, "⚪")
        safety_icon = SAFETY_ICONS.get(twin.safety_assessment.safety_status, "✅")
        decision_icon = DECISION_ICONS.get(twin.safety_assessment.operational_decision, "▶️")

        return f"""## Executive Summary

| Parameter | Value |
|-----------|-------|
| {health_icon} **Overall Health Score** | **{twin.overall_health_score:.0f} / 100** |
| ⚠️ **Risk Score** | **{twin.overall_risk_score:.0f} / 100** |
| {priority_icon} **Maintenance Priority** | **{twin.predictive_maintenance.maintenance_priority.value.upper()}** |
| {safety_icon} **Safety Status** | **{twin.safety_assessment.safety_status.value.upper()}** |
| {decision_icon} **Operational Decision** | **{twin.safety_assessment.operational_decision.value.upper()}** |"""

    def _asset_information(self, twin: DigitalTwin) -> str:
        info = twin.coach_info
        sensors = twin.sensor_readings
        return f"""## Asset Information

| Field | Value |
|-------|-------|
| **Coach ID** | {info.coach_id} |
| **Type** | {info.coach_type} |
| **Manufacture Year** | {info.manufacture_year or "N/A"} |
| **Assigned Route** | {info.assigned_route or "N/A"} |
| **Last Overhaul** | {info.last_overhaul or "N/A"} |
| **Total Lifetime Hours** | {info.total_lifetime_hours or "N/A"} |
| **Last Inspection** | {twin.last_inspection_date or "N/A"} |
| **Maintenance Events on Record** | {twin.total_maintenance_events} |

### Current Sensor Readings

| Sensor | Reading |
|--------|---------|
| 🌡️ Temperature | {sensors.temperature_celsius:.1f} °C |
| 📳 Vibration | {sensors.vibration_mm_s:.2f} mm/s RMS |
| ⏱️ Runtime Since Maintenance | {sensors.runtime_hours:.0f} hours |
| 💧 Humidity | {sensors.humidity_percent:.0f} % RH |
| 👥 Passenger Load | {sensors.passenger_load_percent:.0f} % |"""

    def _sensor_findings(self, twin: DigitalTwin) -> str:
        sa = twin.sensor_analysis
        anomaly_list = "\n".join(f"- {a}" for a in sa.anomalies_detected) if sa.anomalies_detected else "- None detected"
        obs_list = "\n".join(f"- {o}" for o in sa.observations) if sa.observations else "- No observations"

        return f"""## Sensor Analysis Findings

**Sensor Health Score:** {sa.sensor_health_score:.0f}/100

**Temperature Status:** `{sa.temperature_status.upper()}`  
**Vibration Status:** `{sa.vibration_status.upper()}`  
**Runtime Status:** `{sa.runtime_status.upper()}`

### Anomalies Detected
{anomaly_list}

### Engineering Observations
{obs_list}"""

    def _environmental_findings(self, twin: DigitalTwin) -> str:
        er = twin.environmental_risk
        obs_list = "\n".join(f"- {o}" for o in er.environmental_observations) if er.environmental_observations else "- Standard conditions"

        return f"""## Environmental Risk Assessment

| Factor | Value |
|--------|-------|
| **Humidity Risk** | {er.humidity_risk.upper()} |
| **Climate Wear Multiplier** | ×{er.climate_exposure_factor:.2f} |
| **Additional Wear Estimate** | +{er.additional_wear_estimate_percent:.0f}% vs. baseline |

### Environmental Observations
{obs_list}"""

    def _maintenance_assessment(self, twin: DigitalTwin) -> str:
        pm = twin.predictive_maintenance
        priority_icon = PRIORITY_ICONS.get(pm.maintenance_priority, "⚪")
        rul = (
            f"{pm.remaining_useful_life_hours:.0f} hours (estimated)"
            if pm.remaining_useful_life_hours is not None
            else "Unable to estimate"
        )
        reasoning_list = "\n".join(f"- {r}" for r in pm.reasoning) if pm.reasoning else "- No reasoning captured"

        return f"""## Predictive Maintenance Assessment

| Parameter | Value |
|-----------|-------|
| {priority_icon} **Maintenance Priority** | {pm.maintenance_priority.value.upper()} |
| **Remaining Useful Life** | {rul} |
| **Inspection Urgency** | {pm.inspection_urgency} |
| **Next Recommended Action** | {pm.next_recommended_action or "N/A"} |

### Assessment Reasoning
{reasoning_list}"""

    def _safety_assessment(self, twin: DigitalTwin) -> str:
        sa = twin.safety_assessment
        safety_icon = SAFETY_ICONS.get(sa.safety_status, "✅")
        decision_icon = DECISION_ICONS.get(sa.operational_decision, "▶️")
        concerns_list = (
            "\n".join(f"- {c}" for c in sa.safety_concerns)
            if sa.safety_concerns
            else "- No safety concerns identified"
        )

        return f"""## Safety Assessment

| Parameter | Value |
|-----------|-------|
| {safety_icon} **Safety Status** | **{sa.safety_status.value.upper()}** |
| {decision_icon} **Operational Decision** | **{sa.operational_decision.value.upper()}** |
| **Passenger Risk Level** | {sa.passenger_risk_level.upper()} |

### Safety Concerns
{concerns_list}

### Safety Reasoning
{sa.safety_reasoning or "N/A"}"""

    def _maintenance_history_summary(self, twin: DigitalTwin) -> str:
        if not twin.maintenance_history and not twin.fault_history:
            return "## Maintenance History\n\nNo records found in database."

        lines = ["## Maintenance History\n"]

        if twin.maintenance_history:
            lines.append("### Recent Maintenance Events\n")
            lines.append("| Date | Type | Component | Description |")
            lines.append("|------|------|-----------|-------------|")
            for r in twin.maintenance_history[-5:]:
                lines.append(f"| {r.date} | {r.type} | {r.component} | {r.description} |")

        if twin.fault_history:
            lines.append("\n### Fault History\n")
            lines.append("| Date | Code | Severity | Description | Status |")
            lines.append("|------|------|----------|-------------|--------|")
            for f in twin.fault_history[-5:]:
                status = "✅ Resolved" if f.resolved else "🔴 Open"
                lines.append(f"| {f.date} | {f.fault_code} | {f.severity} | {f.description} | {status} |")

        return "\n".join(lines)

    def _recommended_actions(self, twin: DigitalTwin) -> str:
        pm = twin.predictive_maintenance
        sa = twin.safety_assessment

        lines = ["## Recommended Actions\n"]

        # Operational decision banner
        decision = sa.operational_decision
        if decision == OperationalDecision.STOP:
            lines.append("> 🛑 **IMMEDIATE ACTION REQUIRED: WITHDRAW COACH FROM SERVICE**\n")
        elif decision == OperationalDecision.RESTRICT:
            lines.append("> ⚠️ **RESTRICTED OPERATION: Apply speed/load restrictions immediately.**\n")
        elif decision == OperationalDecision.MONITOR:
            lines.append("> 👁️ **ENHANCED MONITORING: Increase inspection frequency.**\n")
        else:
            lines.append("> ▶️ **CONTINUE OPERATION: Proceed with standard monitoring.**\n")

        # Primary recommendation
        if pm.next_recommended_action:
            lines.append(f"**Primary Recommendation:** {pm.next_recommended_action}\n")

        # Compiled action list from agents
        all_actions = list(sa.safety_concerns)
        if pm.reasoning:
            all_actions.extend(pm.reasoning[-3:])

        if all_actions:
            lines.append("### Action Items\n")
            for i, action in enumerate(all_actions[:8], 1):
                lines.append(f"{i}. {action}")

        return "\n".join(lines)

    def _footer(self, timestamp: str) -> str:
        return f"""---

*Report generated by TwinOps AI — Digital Twin Copilot for Railway Rolling Stock*  
*This report is generated by AI agents for engineering decision support. All recommendations should be reviewed by qualified maintenance personnel before operational decisions are made.*  
*Generated: {timestamp}*"""
