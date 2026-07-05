"""
TwinOps AI - UI Styles
=======================
CSS and styling constants for the Streamlit industrial dashboard.
"""

# Main application CSS
MAIN_CSS = """
<style>
/* ---- Global ---- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background-color: #0d1117;
    color: #c9d1d9;
}

/* ---- Header ---- */
.twinops-header {
    background: linear-gradient(135deg, #1a1f2e 0%, #0d1117 100%);
    border-bottom: 2px solid #21262d;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    border-radius: 0 0 12px 12px;
}

.twinops-logo {
    font-size: 1.8rem;
    font-weight: 700;
    color: #58a6ff;
    letter-spacing: -0.5px;
}

.twinops-tagline {
    font-size: 0.85rem;
    color: #8b949e;
    margin-top: 0.25rem;
}

/* ---- Metric Cards ---- */
.metric-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 1.25rem;
    text-align: center;
    transition: border-color 0.2s;
}

.metric-card:hover {
    border-color: #58a6ff;
}

.metric-value {
    font-size: 2.2rem;
    font-weight: 700;
    line-height: 1;
}

.metric-label {
    font-size: 0.75rem;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 0.4rem;
}

/* ---- Status Badges ---- */
.badge {
    display: inline-block;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.badge-good { background: rgba(63, 185, 80, 0.15); color: #3fb950; border: 1px solid #3fb950; }
.badge-warning { background: rgba(210, 153, 34, 0.15); color: #d29922; border: 1px solid #d29922; }
.badge-critical { background: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid #f85149; }
.badge-safe { background: rgba(63, 185, 80, 0.15); color: #3fb950; border: 1px solid #3fb950; }
.badge-stop { background: rgba(248, 81, 73, 0.15); color: #f85149; border: 1px solid #f85149; }
.badge-unknown { background: rgba(139, 148, 158, 0.15); color: #8b949e; border: 1px solid #8b949e; }

/* ---- Section Headers ---- */
.section-header {
    font-size: 0.9rem;
    font-weight: 600;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 1px;
    border-bottom: 1px solid #21262d;
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
    margin-top: 1.5rem;
}

/* ---- Agent Timeline ---- */
.agent-step {
    display: flex;
    align-items: flex-start;
    padding: 0.75rem 0;
    border-bottom: 1px solid #21262d;
}

.agent-step-icon {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    margin-right: 0.75rem;
    flex-shrink: 0;
}

.agent-step-running { background: rgba(88, 166, 255, 0.2); border: 1px solid #58a6ff; }
.agent-step-completed { background: rgba(63, 185, 80, 0.2); border: 1px solid #3fb950; }
.agent-step-error { background: rgba(248, 81, 73, 0.2); border: 1px solid #f85149; }
.agent-step-pending { background: rgba(139, 148, 158, 0.1); border: 1px solid #30363d; }

/* ---- Risk Score Bar ---- */
.risk-bar-container {
    background: #21262d;
    border-radius: 6px;
    height: 12px;
    overflow: hidden;
}

.risk-bar {
    height: 100%;
    border-radius: 6px;
    transition: width 0.5s ease;
}

/* ---- Digital Twin Panel ---- */
.twin-panel {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 1.25rem;
}

/* ---- Report Area ---- */
.report-container {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 1.5rem;
    max-height: 70vh;
    overflow-y: auto;
}

/* ---- Input Form ---- */
.form-container {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 1.5rem;
}

/* ---- Streamlit Overrides ---- */
.stButton > button {
    background: linear-gradient(135deg, #1f6feb, #388bfd);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    padding: 0.6rem 1.5rem;
    transition: all 0.2s;
    width: 100%;
}

.stButton > button:hover {
    background: linear-gradient(135deg, #388bfd, #58a6ff);
    transform: translateY(-1px);
}

.stSlider > div > div > div {
    background-color: #58a6ff !important;
}

.stNumberInput > div > div > input,
.stTextInput > div > div > input {
    background-color: #0d1117;
    border: 1px solid #30363d;
    color: #c9d1d9;
    border-radius: 6px;
}

/* Hide Streamlit default header/footer */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header { visibility: hidden; }

/* ---- Alert Boxes ---- */
.alert-critical {
    background: rgba(248, 81, 73, 0.1);
    border: 1px solid #f85149;
    border-left: 4px solid #f85149;
    border-radius: 6px;
    padding: 1rem;
    margin: 0.75rem 0;
}

.alert-warning {
    background: rgba(210, 153, 34, 0.1);
    border: 1px solid #d29922;
    border-left: 4px solid #d29922;
    border-radius: 6px;
    padding: 1rem;
    margin: 0.75rem 0;
}

.alert-safe {
    background: rgba(63, 185, 80, 0.1);
    border: 1px solid #3fb950;
    border-left: 4px solid #3fb950;
    border-radius: 6px;
    padding: 1rem;
    margin: 0.75rem 0;
}
</style>
"""

# Color maps
HEALTH_COLORS = {
    "good": "#3fb950",
    "warning": "#d29922",
    "critical": "#f85149",
    "unknown": "#8b949e",
}

STATUS_COLORS = {
    "normal": "#3fb950",
    "warning": "#d29922",
    "critical": "#f85149",
}

PRIORITY_COLORS = {
    "none": "#8b949e",
    "low": "#58a6ff",
    "medium": "#d29922",
    "high": "#f0883e",
    "immediate": "#f85149",
}
