# TwinOps AI — Architecture Document

## System Architecture Diagram

```mermaid
graph TB
    subgraph UI ["🖥️ Streamlit UI Layer"]
        INPUT[Coach Input Form\nSensor Sliders + Coach ID]
        DASH[Industrial Dashboard\nHealth Score · Risk · Status]
        REPORT[Engineering Report\nMarkdown · Downloadable]
        LOG[Agent Execution Log\nTimeline View]
    end

    subgraph ORCHESTRATION ["🎯 Orchestration Layer"]
        SUP[Supervisor Agent\nPipeline Coordinator]
    end

    subgraph AGENTS ["🤖 Agent Layer — Specialist AI Agents"]
        A1[Identity & History Agent\n──────────────────\n• Fleet DB Lookup\n• History Pattern Analysis\n• Open Fault Detection]
        A2[Sensor Analysis Agent\n──────────────────\n• ISO 10816-3 Evaluation\n• Anomaly Detection\n• Health Score Calculation]
        A3[Environmental Risk Agent\n──────────────────\n• Route Climate Context\n• Corrosion Risk\n• Wear Multiplier]
        A4[Predictive Maintenance Agent\n──────────────────\n• RUL Estimation\n• Risk Score Synthesis\n• Priority Assignment]
        A5[Safety Agent\n──────────────────\n• Hard Safety Triggers\n• Go/No-Go Decision\n• Passenger Risk]
        A6[Report Agent\n──────────────────\n• Executive Narrative\n• Structured Markdown\n• Download-ready]
    end

    subgraph TOOLS ["🔧 Tools Layer — Reusable Deterministic Functions"]
        T1[CoachCSVReader\nFleet Master Data]
        T2[MaintenanceHistoryLookup\nMaintenance + Fault Records]
        T3[SensorThresholdChecker\nEngineering Thresholds]
        T4[RuntimeCalculator\nCycle Metrics + RUL]
        T5[EnvironmentalContextTool\nRoute Climate Profiles]
        T6[RiskScoreCalculator\nComposite Scoring]
        T7[ReportFormatter\nMarkdown Generation]
    end

    subgraph DATA ["💾 Data Layer"]
        D1[(coaches.csv\n10 railway coaches)]
        D2[(maintenance_history.csv\n40+ records)]
        D3[(fault_history.csv\n25+ records)]
        D4[(sensor_thresholds.json\nISO standards)]
        D5[(environmental_context.json\n9 route profiles)]
    end

    subgraph SHARED ["🔄 Shared State"]
        DT[Digital Twin\nPydantic Model\n─────────────\ncoach_info\nsensor_readings\nmaintenance_history\nfault_history\nsensor_analysis\nenvironmental_risk\npredictive_maintenance\nsafety_assessment\nagent_observations\nfinal_report]
    end

    subgraph LLM ["🧠 Gemini AI Layer"]
        G[Gemini 2.0 Flash\nPattern Analysis\nNarrative Generation\nReasoning]
    end

    INPUT --> SUP
    SUP --> A1 --> A2 --> A3 --> A4 --> A5 --> A6
    A6 --> DASH
    A6 --> REPORT
    A6 --> LOG

    A1 --> T1 & T2
    A2 --> T3
    A3 --> T5
    A4 --> T4 & T6
    A6 --> T7

    T1 --> D1
    T2 --> D2 & D3
    T3 --> D4
    T5 --> D5

    A1 & A2 & A3 & A4 & A5 & A6 --> DT
    DT --> A1 & A2 & A3 & A4 & A5 & A6

    A1 & A2 & A3 & A4 & A5 & A6 --> G

    style DT fill:#1a1f2e,stroke:#58a6ff,color:#c9d1d9
    style G fill:#1f3a1f,stroke:#3fb950,color:#c9d1d9
```

---

## Digital Twin Data Flow

```
Operator Input
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│  Digital Twin (Initial State)                           │
│  coach_id = "RC-1001"                                   │
│  sensors = {temp: 48.0, vib: 5.5, runtime: 750, ...}   │
│  [all other fields empty / default]                     │
└─────────────────────────────────────────────────────────┘
      │
      ▼ Identity & History Agent
┌─────────────────────────────────────────────────────────┐
│  Digital Twin (+ Identity + History)                    │
│  coach_info = {type: "AC Sleeper", route: "...", ...}   │
│  maintenance_history = [10 records]                     │
│  fault_history = [5 records]                            │
│  last_inspection_date = "2024-11-02"                    │
└─────────────────────────────────────────────────────────┘
      │
      ▼ Sensor Analysis Agent
┌─────────────────────────────────────────────────────────┐
│  Digital Twin (+ Sensor Analysis)                       │
│  sensor_analysis = {                                    │
│    temperature_status: "warning",                       │
│    vibration_status: "warning",                         │
│    anomalies: ["Temp elevated...", "Vib above..."],     │
│    sensor_health_score: 76                              │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
      │
      ▼ Environmental Risk Agent
┌─────────────────────────────────────────────────────────┐
│  Digital Twin (+ Environmental Risk)                    │
│  environmental_risk = {                                 │
│    humidity_risk: "medium",                             │
│    climate_exposure_factor: 1.25,                       │
│    additional_wear_percent: 25                          │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
      │
      ▼ Predictive Maintenance Agent
┌─────────────────────────────────────────────────────────┐
│  Digital Twin (+ Risk Scores + Maintenance Plan)        │
│  overall_health_score = 58                              │
│  overall_risk_score = 42                                │
│  predictive_maintenance = {                             │
│    rul_hours: 210,                                      │
│    priority: "MEDIUM",                                  │
│    next_action: "Schedule bogie inspection"             │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
      │
      ▼ Safety Agent
┌─────────────────────────────────────────────────────────┐
│  Digital Twin (+ Safety Assessment)                     │
│  safety_assessment = {                                  │
│    safety_status: "WARNING",                            │
│    operational_decision: "MONITOR",                     │
│    passenger_risk: "medium",                            │
│    reasoning: "..."                                     │
│  }                                                      │
└─────────────────────────────────────────────────────────┘
      │
      ▼ Report Agent
┌─────────────────────────────────────────────────────────┐
│  Digital Twin (COMPLETE)                                │
│  final_report = "# TwinOps AI Report..."               │
│  pipeline_status = "completed"                          │
│  agent_observations = [12 log entries]                  │
└─────────────────────────────────────────────────────────┘
      │
      ▼
  Streamlit Dashboard
```

---

## Risk Score Calculation

The composite risk score (0–100) is computed by the Predictive Maintenance Agent using a weighted formula:

```
Risk Score = (0.35 × sensor_risk)
           + (0.25 × runtime_risk)
           + (0.20 × environmental_risk)
           + (0.20 × history_risk)

Where:
  sensor_risk       = 100 - sensor_health_score
  runtime_risk      = function of cycle_percent_used (0–100)
  environmental_risk = min(100, additional_wear_percent × 2.5)
  history_risk      = (critical_faults × 15) + (faults × 3) + (open_faults × 20)

Health Score = 100 - Risk Score
```

## Safety Decision Logic

```
Hard Triggers (rule-based, override LLM):
  ANY critical sensor → CRITICAL / STOP
  Open unresolved fault → CRITICAL / RESTRICT+
  Risk score > 60 → CRITICAL
  
LLM Assessment (Gemini reasoning):
  Contextual analysis of combined factors
  Conservative safety principle applied
  
Final = MAX(hard_trigger_level, llm_level)
```

---

## Key Design Decisions

1. **Shared Digital Twin over message passing** — Agents share a Pydantic state object rather than passing text between each other. This ensures type safety, enables structured aggregation, and makes the reasoning chain auditable.

2. **Deterministic tools + LLM narrative** — Core calculations (threshold checks, risk scores, RUL estimates) use deterministic code. Gemini is used for contextual reasoning, pattern identification, and narrative generation — the tasks where LLMs genuinely add value.

3. **Conservative safety escalation** — The Safety Agent takes the *more conservative* of its rule-based and LLM-based assessments. Safety cannot be downgraded by AI reasoning alone.

4. **Graceful degradation** — Each agent has a fallback path. If Gemini is unavailable (no API key, rate limit), tools return deterministic results and the pipeline completes with heuristic analysis.

5. **Sequential pipeline with error isolation** — Agents run sequentially (each needs the prior agent's output), but individual agent failures don't crash the pipeline. The Supervisor logs the error and continues.
