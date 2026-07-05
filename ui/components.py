"""
TwinOps AI - UI Components
============================
Reusable Streamlit UI components for the industrial dashboard.
"""

import streamlit as st
from typing import Optional
from models.digital_twin import DigitalTwin, HealthStatus, SafetyStatus, OperationalDecision
from .styles import HEALTH_COLORS, STATUS_COLORS, PRIORITY_COLORS


def render_header():
    """Render the TwinOps AI branded header."""
    st.markdown(
        """
        <div class="twinops-header">
            <div class="twinops-logo">⚙️ TwinOps AI</div>
            <div class="twinops-tagline">
                Industry 4.0 Digital Twin Copilot &nbsp;·&nbsp; 
                Railway Rolling Stock Maintenance Intelligence &nbsp;·&nbsp;
                Powered by Collaborative AI Agents
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_health_score_gauge(health_score: float, risk_score: float):
    """Render health and risk score gauges."""
    health_color = _score_to_color(health_score, invert=False)
    risk_color = _score_to_color(risk_score, invert=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {health_color};">
                    {health_score:.0f}<span style="font-size:1rem;color:#8b949e;">/100</span>
                </div>
                <div class="metric-label">Health Score</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-value" style="color: {risk_color};">
                    {risk_score:.0f}<span style="font-size:1rem;color:#8b949e;">/100</span>
                </div>
                <div class="metric-label">Risk Score</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_status_badges(twin: DigitalTwin):
    """Render the key status badges row."""
    safety_status = twin.safety_assessment.safety_status
    operational_decision = twin.safety_assessment.operational_decision
    priority = twin.predictive_maintenance.maintenance_priority
    health_status = twin.health_status

    # Safety decision banner
    if operational_decision == OperationalDecision.STOP:
        st.markdown(
            '<div class="alert-critical">🛑 <strong>IMMEDIATE ACTION: WITHDRAW COACH FROM SERVICE</strong> — '
            "Critical conditions detected. Coach must not operate until inspection and clearance.</div>",
            unsafe_allow_html=True,
        )
    elif operational_decision == OperationalDecision.RESTRICT:
        st.markdown(
            '<div class="alert-warning">⚠️ <strong>RESTRICTED OPERATION</strong> — '
            "Apply speed/load restrictions. Expedited maintenance required.</div>",
            unsafe_allow_html=True,
        )
    elif operational_decision == OperationalDecision.MONITOR:
        st.markdown(
            '<div class="alert-warning">👁️ <strong>ENHANCED MONITORING</strong> — '
            "Continue operation with increased inspection frequency.</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div class="alert-safe">✅ <strong>CONTINUE OPERATION</strong> — '
            "All parameters within acceptable limits. Standard monitoring applies.</div>",
            unsafe_allow_html=True,
        )

    # Status row
    cols = st.columns(4)
    with cols[0]:
        _status_metric("🏥 Health Status", health_status.value.upper(),
                       HEALTH_COLORS.get(health_status.value, "#8b949e"))
    with cols[1]:
        _status_metric("🛡️ Safety Status", safety_status.value.upper(),
                       _safety_color(safety_status))
    with cols[2]:
        _status_metric("⚙️ Operational", operational_decision.value.upper(),
                       _decision_color(operational_decision))
    with cols[3]:
        _status_metric("🔧 Maint. Priority", priority.value.upper(),
                       PRIORITY_COLORS.get(priority.value, "#8b949e"))


def render_sensor_readings(twin: DigitalTwin):
    """Render the sensor readings panel with status indicators."""
    st.markdown('<div class="section-header">Live Sensor Readings</div>', unsafe_allow_html=True)

    sensors = twin.sensor_readings
    analysis = twin.sensor_analysis

    sensor_data = [
        ("🌡️ Temperature", f"{sensors.temperature_celsius:.1f} °C", analysis.temperature_status),
        ("📳 Vibration", f"{sensors.vibration_mm_s:.2f} mm/s", analysis.vibration_status),
        ("⏱️ Runtime", f"{sensors.runtime_hours:.0f} hrs", analysis.runtime_status),
        ("💧 Humidity", f"{sensors.humidity_percent:.0f} %RH", "normal"),
        ("👥 Passenger Load", f"{sensors.passenger_load_percent:.0f} %", "normal"),
    ]

    cols = st.columns(len(sensor_data))
    for col, (label, value, status) in zip(cols, sensor_data):
        color = STATUS_COLORS.get(status, "#8b949e")
        icon = "🔴" if status == "critical" else "🟡" if status == "warning" else "🟢"
        col.markdown(
            f"""
            <div class="metric-card">
                <div style="font-size:0.7rem;color:#8b949e;margin-bottom:0.3rem;">{label}</div>
                <div style="font-size:1.3rem;font-weight:700;color:{color};">{value}</div>
                <div style="font-size:0.7rem;margin-top:0.2rem;">{icon} {status.upper()}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_agent_timeline(twin: DigitalTwin):
    """Render the agent execution timeline."""
    st.markdown('<div class="section-header">Agent Execution Log</div>', unsafe_allow_html=True)

    if not twin.agent_observations:
        st.caption("No agent observations recorded.")
        return

    for obs in twin.agent_observations:
        icon = {"completed": "✅", "started": "⏳", "error": "❌"}.get(obs.status, "•")
        color = {"completed": "#3fb950", "started": "#58a6ff", "error": "#f85149"}.get(
            obs.status, "#8b949e"
        )
        st.markdown(
            f"""
            <div style="padding:0.5rem 0; border-bottom:1px solid #21262d;">
                <span style="color:{color};font-weight:600;">{icon} {obs.agent_name}</span>
                <span style="color:#8b949e;font-size:0.8rem;margin-left:0.5rem;">{obs.status}</span>
                <div style="color:#c9d1d9;font-size:0.85rem;margin-top:0.2rem;">{obs.summary}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if obs.details:
            with st.expander("Details", expanded=False):
                st.text(obs.details)


def render_digital_twin_state(twin: DigitalTwin):
    """Render the current Digital Twin state overview."""
    st.markdown('<div class="section-header">Digital Twin State</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Coach Identity**")
        info = twin.coach_info
        st.markdown(f"- ID: `{info.coach_id}`")
        st.markdown(f"- Type: {info.coach_type}")
        st.markdown(f"- Route: {info.assigned_route or 'N/A'}")
        st.markdown(f"- Last Overhaul: {info.last_overhaul or 'N/A'}")
        st.markdown(f"- Lifetime Hours: {info.total_lifetime_hours or 'N/A'}")

        st.markdown("**Maintenance History**")
        st.markdown(f"- Total Events: {twin.total_maintenance_events}")
        st.markdown(f"- Fault Records: {len(twin.fault_history)}")
        open_faults = sum(1 for f in twin.fault_history if not f.resolved)
        open_color = "#f85149" if open_faults > 0 else "#3fb950"
        st.markdown(f"- Open Faults: <span style='color:{open_color};font-weight:700;'>{open_faults}</span>",
                    unsafe_allow_html=True)
        st.markdown(f"- Last Inspection: {twin.last_inspection_date or 'N/A'}")

    with col2:
        st.markdown("**Environmental Risk**")
        er = twin.environmental_risk
        st.markdown(f"- Humidity Risk: {er.humidity_risk}")
        st.markdown(f"- Wear Multiplier: ×{er.climate_exposure_factor:.2f}")
        st.markdown(f"- Additional Wear: +{er.additional_wear_estimate_percent:.0f}%")

        st.markdown("**Predictive Maintenance**")
        pm = twin.predictive_maintenance
        rul = f"~{pm.remaining_useful_life_hours:.0f}h" if pm.remaining_useful_life_hours else "N/A"
        st.markdown(f"- RUL Estimate: {rul}")
        st.markdown(f"- Inspection Urgency: {pm.inspection_urgency}")
        if pm.next_recommended_action:
            st.markdown(f"- Next Action: _{pm.next_recommended_action[:80]}..._" 
                       if len(pm.next_recommended_action) > 80 
                       else f"- Next Action: _{pm.next_recommended_action}_")


def render_safety_concerns(twin: DigitalTwin):
    """Render safety concerns panel."""
    concerns = twin.safety_assessment.safety_concerns
    if not concerns:
        st.success("✅ No safety concerns identified.")
        return

    st.markdown('<div class="section-header">Safety Concerns</div>', unsafe_allow_html=True)
    for concern in concerns:
        if "CRITICAL" in concern.upper() or "OPEN FAULT" in concern.upper():
            st.error(f"🚨 {concern}")
        elif "WARNING" in concern.upper():
            st.warning(f"⚠️ {concern}")
        else:
            st.info(f"ℹ️ {concern}")

    reasoning = twin.safety_assessment.safety_reasoning
    if reasoning:
        st.markdown(f"**Safety Reasoning:** {reasoning}")


# -----------------------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------------------

def _score_to_color(score: float, invert: bool = False) -> str:
    """Map a 0–100 score to a color. Invert=True for risk (higher=redder)."""
    if not invert:
        if score >= 70:
            return "#3fb950"
        elif score >= 40:
            return "#d29922"
        else:
            return "#f85149"
    else:
        if score <= 30:
            return "#3fb950"
        elif score <= 60:
            return "#d29922"
        else:
            return "#f85149"


def _status_metric(label: str, value: str, color: str):
    st.markdown(
        f"""
        <div class="metric-card">
            <div style="font-size:0.7rem;color:#8b949e;margin-bottom:0.4rem;">{label}</div>
            <div style="font-size:1rem;font-weight:700;color:{color};">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _safety_color(status: SafetyStatus) -> str:
    return {
        SafetyStatus.SAFE: "#3fb950",
        SafetyStatus.WARNING: "#d29922",
        SafetyStatus.CRITICAL: "#f85149",
    }.get(status, "#8b949e")


def _decision_color(decision: OperationalDecision) -> str:
    return {
        OperationalDecision.CONTINUE: "#3fb950",
        OperationalDecision.MONITOR: "#58a6ff",
        OperationalDecision.RESTRICT: "#d29922",
        OperationalDecision.STOP: "#f85149",
    }.get(decision, "#8b949e")
