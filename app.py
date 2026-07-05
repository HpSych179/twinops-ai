"""
TwinOps AI - Main Streamlit Application
=========================================
Industrial Digital Twin Copilot for Railway Rolling Stock Maintenance.

This is the main entry point for the Streamlit UI.
Run with: streamlit run app.py

Architecture:
    - The UI collects operator inputs
    - Passes them to the SupervisorAgent
    - The Supervisor orchestrates 6 specialist AI agents
    - Each agent enriches the shared Digital Twin
    - Results are displayed as an industrial dashboard
"""

import os
import sys
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Path setup — ensure src packages are importable
# ---------------------------------------------------------------------------
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

# Load environment variables
load_dotenv(ROOT_DIR / ".env")

# ---------------------------------------------------------------------------
# Page configuration — MUST be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="TwinOps AI",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get Help": "https://github.com/twinops-ai",
        "About": "TwinOps AI — Digital Twin Copilot for Railway Rolling Stock",
    },
)

# ---------------------------------------------------------------------------
# Imports (after path setup)
# ---------------------------------------------------------------------------
from agents.supervisor_agent import SupervisorAgent
from tools.csv_reader import CoachCSVReader
from ui.components import (
    render_header,
    render_health_score_gauge,
    render_status_badges,
    render_sensor_readings,
    render_agent_timeline,
    render_digital_twin_state,
    render_safety_concerns,
)
from ui.styles import MAIN_CSS
from utils.config import load_config

# ---------------------------------------------------------------------------
# Load config and apply styles
# ---------------------------------------------------------------------------
config = load_config()
st.markdown(MAIN_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------
if "twin" not in st.session_state:
    st.session_state.twin = None
if "pipeline_running" not in st.session_state:
    st.session_state.pipeline_running = False
if "agent_progress" not in st.session_state:
    st.session_state.agent_progress = []


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
render_header()

# API Key warning banner
if not config.has_api_key:
    st.warning(
        "⚠️ **GOOGLE_API_KEY not configured.** "
        "Agents are running in mock mode — results are deterministic/heuristic, not AI-generated. "
        "Add your Gemini API key to `.env` to enable full AI analysis.",
        icon="🔑",
    )

# ---------------------------------------------------------------------------
# Layout: Left panel (inputs) + Right panel (results)
# ---------------------------------------------------------------------------
left_col, right_col = st.columns([1, 2], gap="large")

# ---------------------------------------------------------------------------
# LEFT PANEL — Input Form
# ---------------------------------------------------------------------------
with left_col:
    st.markdown("### 🚃 Coach Assessment Input")
    st.caption("Enter current coach data to start the AI agent pipeline")

    with st.form("coach_input_form"):
        # Coach Selection
        csv_reader = CoachCSVReader()
        known_ids = csv_reader.list_all_coach_ids()

        coach_id_input = st.text_input(
            "Coach ID",
            value="RC-1001",
            placeholder="e.g., RC-1001",
            help="Enter an ID from the fleet database. Known IDs: " + ", ".join(known_ids),
        )

        # Quick load from known coaches
        if known_ids:
            selected_preset = st.selectbox(
                "Or select from fleet",
                options=["Custom"] + known_ids,
                index=1,
            )
        else:
            selected_preset = "Custom"

        st.divider()
        st.markdown("**📊 Sensor Readings**")

        temp = st.slider(
            "🌡️ Temperature (°C)",
            min_value=10.0,
            max_value=90.0,
            value=38.0,
            step=0.5,
            help="Normal: <40°C | Warning: 40-55°C | Critical: >55°C",
        )

        vib = st.slider(
            "📳 Vibration (mm/s RMS)",
            min_value=0.0,
            max_value=15.0,
            value=3.2,
            step=0.1,
            help="ISO 10816-3 Class III | Normal: <4.5 | Warning: 4.5-7.0 | Critical: >7.0",
        )

        runtime = st.number_input(
            "⏱️ Runtime Since Maintenance (hours)",
            min_value=0,
            max_value=2000,
            value=450,
            step=10,
            help="Standard interval: 720h | Warning: >720h | Critical: >960h",
        )

        humidity = st.slider(
            "💧 Humidity (% RH)",
            min_value=10,
            max_value=100,
            value=55,
            step=1,
            help="Normal: <60% | Warning: 60-75% | Critical: >75%",
        )

        load = st.slider(
            "👥 Passenger Load (% of capacity)",
            min_value=0,
            max_value=160,
            value=85,
            step=5,
            help="Normal: <100% | Warning: 100-120% | Critical: >120%",
        )

        st.divider()

        # Scenario presets for demonstration
        st.markdown("**🎯 Demo Scenarios**")
        scenario = st.selectbox(
            "Load demo scenario",
            [
                "Custom (use sliders)",
                "🟢 Healthy Coach — All Nominal",
                "🟡 Warning — Approaching Maintenance",
                "🔴 Critical — Multiple Anomalies",
                "🚨 Emergency — Withdraw from Service",
            ],
        )

        submit = st.form_submit_button(
            "🚀 Run AI Agent Assessment",
            use_container_width=True,
            type="primary",
        )

    # Scenario descriptions
    scenario_tips = {
        "🟢 Healthy Coach — All Nominal": "Temperature: 35°C, Vibration: 2.1 mm/s, Runtime: 400h",
        "🟡 Warning — Approaching Maintenance": "Temperature: 48°C, Vibration: 5.5 mm/s, Runtime: 750h",
        "🔴 Critical — Multiple Anomalies": "Temperature: 63°C, Vibration: 8.9 mm/s, Runtime: 1050h",
        "🚨 Emergency — Withdraw from Service": "Temperature: 78°C, Vibration: 12.5 mm/s, Runtime: 1400h",
    }
    if scenario in scenario_tips:
        st.info(f"📋 {scenario_tips[scenario]}")

    # Coach database info
    with st.expander("📋 Fleet Database", expanded=False):
        st.caption(f"**{len(known_ids)} coaches** in database")
        for cid in known_ids:
            coach = csv_reader.get_coach(cid)
            if coach:
                st.caption(f"• {cid} — {coach.get('coach_type', '?')} | {coach.get('assigned_route', '?')}")

# ---------------------------------------------------------------------------
# RIGHT PANEL — Results Dashboard
# ---------------------------------------------------------------------------
with right_col:

    if not st.session_state.twin and not st.session_state.pipeline_running:
        # Welcome / idle state
        st.markdown("### 🔄 Awaiting Assessment")
        st.markdown(
            """
            <div style="background:#161b22;border:1px solid #30363d;border-radius:12px;padding:2rem;text-align:center;margin-top:1rem;">
                <div style="font-size:3rem;margin-bottom:1rem;">⚙️</div>
                <div style="font-size:1.2rem;font-weight:600;color:#58a6ff;margin-bottom:0.5rem;">
                    TwinOps AI Multi-Agent Pipeline
                </div>
                <div style="color:#8b949e;margin-bottom:1.5rem;">
                    Enter coach data and click <strong>Run AI Agent Assessment</strong> to start.<br>
                    6 specialized AI agents will collaborate to analyze the coach.
                </div>
                <div style="display:flex;justify-content:center;gap:1rem;flex-wrap:wrap;">
                    <span style="background:#21262d;border-radius:6px;padding:0.4rem 0.8rem;font-size:0.8rem;">🔍 Identity & History</span>
                    <span style="background:#21262d;border-radius:6px;padding:0.4rem 0.8rem;font-size:0.8rem;">📊 Sensor Analysis</span>
                    <span style="background:#21262d;border-radius:6px;padding:0.4rem 0.8rem;font-size:0.8rem;">🌍 Environmental Risk</span>
                    <span style="background:#21262d;border-radius:6px;padding:0.4rem 0.8rem;font-size:0.8rem;">🔮 Predictive Maintenance</span>
                    <span style="background:#21262d;border-radius:6px;padding:0.4rem 0.8rem;font-size:0.8rem;">🛡️ Safety Assessment</span>
                    <span style="background:#21262d;border-radius:6px;padding:0.4rem 0.8rem;font-size:0.8rem;">📄 Report Generation</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Handle form submission
    if submit:
        # Apply scenario presets
        preset_values = {
            "🟢 Healthy Coach — All Nominal": (35.0, 2.1, 400, 45, 80),
            "🟡 Warning — Approaching Maintenance": (48.0, 5.5, 750, 65, 105),
            "🔴 Critical — Multiple Anomalies": (63.0, 8.9, 1050, 78, 125),
            "🚨 Emergency — Withdraw from Service": (78.0, 12.5, 1400, 88, 140),
        }

        if scenario in preset_values:
            p_temp, p_vib, p_runtime, p_hum, p_load = preset_values[scenario]
        else:
            # Use slider/preset coach values
            p_temp, p_vib, p_runtime, p_hum, p_load = temp, vib, runtime, humidity, load

        # Determine coach ID
        final_coach_id = (
            selected_preset if selected_preset != "Custom" else coach_id_input.strip()
        ) or "RC-CUSTOM"

        # Run the pipeline
        st.session_state.pipeline_running = True
        progress_placeholder = st.empty()
        status_placeholder = st.empty()

        with progress_placeholder.container():
            st.markdown("### ⚡ Agent Pipeline Running...")
            progress_bar = st.progress(0)
            agent_status_area = st.empty()

        agent_log = []

        def on_progress(agent_name: str, status: str, step: int, total: int):
            """Callback for real-time UI updates during pipeline."""
            pct = int((step / total) * 100)
            progress_bar.progress(pct)
            icon = {"running": "⏳", "completed": "✅", "error": "❌"}.get(status, "•")
            agent_log.append(f"{icon} **{agent_name}** — {status}")
            agent_status_area.markdown("\n\n".join(agent_log[-3:]))

        try:
            supervisor = SupervisorAgent(
                api_key=config.google_api_key if config.has_api_key else None
            )

            start_time = time.time()
            twin = supervisor.run(
                coach_id=final_coach_id,
                temperature_celsius=p_temp,
                vibration_mm_s=p_vib,
                runtime_hours=float(p_runtime),
                humidity_percent=float(p_hum),
                passenger_load_percent=float(p_load),
                progress_callback=on_progress,
            )
            elapsed = time.time() - start_time

            st.session_state.twin = twin
            progress_bar.progress(100)
            agent_status_area.markdown(
                f"✅ **Pipeline complete in {elapsed:.1f}s** — {len(twin.agent_observations)} agent operations"
            )
            time.sleep(0.5)
            progress_placeholder.empty()

        except Exception as e:
            st.error(f"Pipeline error: {str(e)}")
            import traceback
            with st.expander("Error details"):
                st.code(traceback.format_exc())

        st.session_state.pipeline_running = False
        st.rerun()

    # Display results
    if st.session_state.twin:
        twin = st.session_state.twin

        # ---- Key metrics row ----
        render_health_score_gauge(twin.overall_health_score, twin.overall_risk_score)
        st.markdown("<br>", unsafe_allow_html=True)
        render_status_badges(twin)

        st.divider()

        # ---- Tabs for different sections ----
        tab1, tab2, tab3, tab4 = st.tabs(
            ["📊 Dashboard", "📄 Full Report", "🤖 Agent Log", "🔬 Digital Twin"]
        )

        with tab1:
            render_sensor_readings(twin)
            st.markdown("<br>", unsafe_allow_html=True)
            render_safety_concerns(twin)

            # Sensor analysis observations
            if twin.sensor_analysis.observations:
                st.markdown('<div class="section-header">Sensor Analysis Observations</div>',
                           unsafe_allow_html=True)
                for obs in twin.sensor_analysis.observations:
                    if "PRIMARY" in obs or "CRITICAL" in obs:
                        st.error(obs)
                    elif "WARNING" in obs or "Warning" in obs:
                        st.warning(obs)
                    else:
                        st.info(obs)

            # Environmental risk observations
            if twin.environmental_risk.environmental_observations:
                st.markdown('<div class="section-header">Environmental Risk Observations</div>',
                           unsafe_allow_html=True)
                for obs in twin.environmental_risk.environmental_observations:
                    st.info(f"🌍 {obs}")

            # Predictive maintenance reasoning
            if twin.predictive_maintenance.reasoning:
                st.markdown('<div class="section-header">Maintenance Assessment Reasoning</div>',
                           unsafe_allow_html=True)
                for reason in twin.predictive_maintenance.reasoning:
                    st.markdown(f"🔮 {reason}")

        with tab2:
            if twin.final_report:
                st.markdown(twin.final_report)
                # Download button
                st.download_button(
                    label="📥 Download Report (Markdown)",
                    data=twin.final_report,
                    file_name=f"twinops_report_{twin.coach_info.coach_id}_{twin.report_generated_at[:10] if twin.report_generated_at else 'now'}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            else:
                st.warning("Report not yet generated.")

        with tab3:
            render_agent_timeline(twin)

        with tab4:
            render_digital_twin_state(twin)

            # Raw Digital Twin JSON
            with st.expander("🔧 Raw Digital Twin (JSON)", expanded=False):
                import json
                st.json(json.loads(twin.model_dump_json(indent=2)))

        # Reset button
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 New Assessment", use_container_width=False):
            st.session_state.twin = None
            st.session_state.pipeline_running = False
            st.rerun()

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.markdown(
    """
    <div style="text-align:center;color:#8b949e;font-size:0.75rem;padding:2rem 0 1rem 0;
                border-top:1px solid #21262d;margin-top:2rem;">
        <strong>TwinOps AI</strong> — Kaggle × Google AI Agents Capstone Project<br>
        Multi-Agent Digital Twin Copilot for Railway Rolling Stock Maintenance<br>
        <span style="color:#444;">Built with Google ADK · Gemini 2.0 Flash · Streamlit</span>
    </div>
    """,
    unsafe_allow_html=True,
)
