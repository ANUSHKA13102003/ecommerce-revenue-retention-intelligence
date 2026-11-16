# AI / Agentic Analytics System Design

## 1. Overview & Architecture

The AI Agentic Analytics subsystem (`agents/`) implements a **deterministic, tool-using multi-agent architecture** that answers natural-language business questions, enforces read-only SQL execution, and generates structured executive reports without fabricating numbers or requiring paid LLM API keys.

```
User Question / CLI / Streamlit UI
                │
                ▼
┌────────────────────────────────────────────────────────────────┐
│ AnalyticsOrchestrator (agents/orchestrator.py)                 │
│ Routes intents, coordinates agents, writes agent_audit_log.json│
└───┬───────────┬───────────────┬───────────────┬────────────┬───┘
    │           │               │               │            │
    ▼           ▼               ▼               ▼            ▼
┌─────────┐ ┌─────────┐ ┌──────────────┐ ┌───────────┐ ┌──────────┐
│Data     │ │Data     │ │SQLAnalyst    │ │Customer   │ │Business  │
│Profiler │ │Quality  │ │Agent         │ │Analytics  │ │Insight & │
│Agent    │ │Agent    │ │      │       │ │Agent      │ │Report    │
└─────────┘ └─────────┘ │      ▼       │ └───────────┘ │Agents    │
                        │ SQLSafety    │               └──────────┘
                        │ Validator    │
                        │ (Allow-List) │
                        │      │       │
                        │      ▼       │
                        │ AnalyticsDB  │
                        │ Engine       │
                        └──────────────┘
```

---

## 2. Specialized Agent Roster

| Agent Class | Module | Responsibility |
|---|---|---|
| **`AnalyticsOrchestrator`** | `agents/orchestrator.py` | Central coordinator providing CLI (`--demo`, `--question`) and Python API (`ask()`, `run_full_pipeline_audit()`), audit logging (`reports/agent_audit_log.json`), and execution routing. |
| **`DataProfilerAgent`** | `agents/data_profiler_agent.py` | Inspects the `9` raw datasets (`1,550,922` rows) and `14` cleaned datasets (`1,067,181` rows), returning verified row counts, date bounds, and schema summaries. |
| **`DataQualityAgent`** | `agents/data_quality_agent.py` | Summarizes non-destructive quality flags from `reports/data_quality/cleaning_log.json` and `phase3_quality_results.json` (`2,965` missing delivery dates, `610` missing categories, `8` zero-payment rows). |
| **`SQLAnalystAgent`** | `agents/sql_analyst_agent.py` | Matches natural-language business questions to verified SQL templates (or accepts custom SQL), validates queries through `validate_sql_query()`, executes against `AnalyticsDBEngine`, and attaches table lineage and chart recommendations. |
| **`CustomerAnalyticsAgent`** | `agents/customer_analytics_agent.py` | Synthesizes Rule D-5 repeat purchase diagnostics (`2,015` / `2.16%`), RFM segment distributions (`93,358` customers), and cohort decay metrics. |
| **`BusinessInsightAgent`** | `agents/insight_agent.py` | Converts executed pandas DataFrames into structured `AgentQueryResponse` payloads containing `factual_summary`, `business_interpretation`, `recommended_actions`, and `limitations`. |
| **`ReportAgent`** | `agents/report_agent.py` | Generates the consulting-grade Markdown executive report (`reports/executive_summary/executive_business_report.md`) from verified KPI outputs. |

---

## 3. SQL Safety Validator (`agents/tools/sql_safety_validator.py`)

Every query processed by `SQLAnalystAgent` is inspected by `validate_sql_query(sql: str) -> SQLValidationResult` before touching the database:

1. **Comment & Multi-Statement Stripping:** Removes `--` and `/* ... */` comments and rejects any query containing embedded `;` statement separators.
2. **Read-Only Prefix Enforcement:** Requires the statement to start with `SELECT` or `WITH`.
3. **Destructive Keyword Blocklist:** Rejects `DROP`, `DELETE`, `UPDATE`, `INSERT`, `TRUNCATE`, `ALTER`, `CREATE`, `REPLACE`, `GRANT`, `REVOKE`, `CALL`, `EXEC`, `EXECUTE`, `OUTFILE`, `DUMPFILE`, `LOAD_FILE`, `INTO`, `ATTACH`, `DETACH`, `COPY`, and `PRAGMA`.
4. **Schema Allow-List Verification:** Extracts all `FROM` and `JOIN` identifiers, subtracts query-local CTE aliases defined in `WITH ... AS (...)`, and verifies that every referenced table/view belongs to the `23` approved tables and views in `ecommerce_analytics`.

---

## 4. Local Deterministic Mode vs. Optional LLM Adapter

- **Default Mode (`deterministic_local`):** Requires zero external API keys (`LLM_PROVIDER=none`). All intent matching, SQL generation, execution, and insight synthesis run 100% locally.
- **Optional External LLM Mode (`llm_assisted`):** If `LLM_PROVIDER`, `LLM_API_KEY`, and `LLM_MODEL` are configured in `.env`, the orchestrator flags `execution_mode = "llm_assisted"` while still enforcing the exact same `validate_sql_query()` read-only gate and factual number verification.
