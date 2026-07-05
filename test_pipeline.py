"""
TwinOps AI - Pipeline smoke test
Run: py -3 test_pipeline.py
"""
import sys
sys.path.insert(0, '.')

from agents.supervisor_agent import SupervisorAgent
from models.digital_twin import HealthStatus, SafetyStatus

def test_pipeline(coach_id, temp, vib, runtime, humidity, load, label):
    print(f"\n{'='*60}")
    print(f"SCENARIO: {label}  |  Coach: {coach_id}")
    print(f"  Sensors: temp={temp}°C  vib={vib}mm/s  runtime={runtime}h  hum={humidity}%  load={load}%")
    print(f"{'='*60}")

    steps_done = []
    def on_progress(name, status, step, total):
        if status == "completed":
            steps_done.append(name)
            print(f"  [{step}/{total}] ✓ {name}")
        elif status == "error":
            print(f"  [{step}/{total}] ✗ {name} — ERROR")

    from utils.config import load_config
    cfg = load_config()
    supervisor = SupervisorAgent(api_key=cfg.google_api_key if cfg.has_api_key else None)
    twin = supervisor.run(
        coach_id=coach_id,
        temperature_celsius=temp,
        vibration_mm_s=vib,
        runtime_hours=float(runtime),
        humidity_percent=float(humidity),
        passenger_load_percent=float(load),
        progress_callback=on_progress,
    )

    print(f"\nRESULTS:")
    print(f"  Health Score  : {twin.overall_health_score:.1f}/100")
    print(f"  Risk Score    : {twin.overall_risk_score:.1f}/100")
    print(f"  Health Status : {twin.health_status.value.upper()}")
    print(f"  Safety Status : {twin.safety_assessment.safety_status.value.upper()}")
    print(f"  Op. Decision  : {twin.safety_assessment.operational_decision.value.upper()}")
    print(f"  Maint Priority: {twin.predictive_maintenance.maintenance_priority.value.upper()}")
    rul = twin.predictive_maintenance.remaining_useful_life_hours
    print(f"  RUL Estimate  : {rul:.0f}h" if rul else "  RUL Estimate  : N/A")
    print(f"  Coach Type    : {twin.coach_info.coach_type}")
    print(f"  Maint Records : {twin.total_maintenance_events}")
    print(f"  Fault Records : {len(twin.fault_history)}")
    print(f"  Open Faults   : {sum(1 for f in twin.fault_history if not f.resolved)}")
    print(f"  Agents ran    : {len(steps_done)}/6")
    print(f"  Report length : {len(twin.final_report or '')} chars")
    print(f"  Pipeline status: {twin.pipeline_status}")
    assert twin.pipeline_status == "completed", "Pipeline did not complete!"
    assert twin.overall_health_score >= 0
    assert twin.final_report, "No report generated!"
    print(f"  ✅ All assertions passed")
    return twin

if __name__ == "__main__":
    # Scenario 1 — Healthy coach
    test_pipeline("RC-1001", 35.0, 2.1, 400, 45, 80, "🟢 Healthy — All Nominal")

    # Scenario 2 — Warning
    test_pipeline("RC-1003", 48.0, 5.5, 750, 65, 105, "🟡 Warning — Approaching Maintenance")

    # Scenario 3 — Critical
    test_pipeline("RC-1007", 63.0, 8.9, 1050, 78, 125, "🔴 Critical — Multiple Anomalies")

    # Scenario 4 — Unknown coach (not in DB)
    test_pipeline("RC-9999", 72.0, 11.0, 1300, 85, 135, "🚨 Emergency — Unknown Coach")

    print(f"\n{'='*60}")
    print("ALL SCENARIOS PASSED ✅")
    print(f"{'='*60}")
