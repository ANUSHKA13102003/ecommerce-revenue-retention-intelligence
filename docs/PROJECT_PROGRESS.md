# Project Execution & Audit Progress Log

**Project:** E-Commerce Revenue & Customer Retention Intelligence  
**Dataset:** Olist Brazilian E-Commerce Public Dataset (Kaggle — `9` raw CSVs, `1,550,922` rows)  
**Currency:** Brazilian Real (`BRL` / `R$`)  
**Primary Analysis Window:** January 2017 – August 2018 (`2017-01-01` to `2018-09-01` exclusive)

---

## 1. End-to-End Verification & Final Phase Status

| Component | Status | Validation Evidence |
|---|---|---|
| **Raw Data Integrity (`data/raw/`)** | ✅ Verified | All `9` CSVs (`1,550,922` rows) present and unmodified (`raw_files_unchanged = true` in `cleaning_log.json`, SHA-256 verified, `test_01`). |
| **Cleaned Pipeline (`data/processed/`)** | ✅ Verified | `14` cleaned datasets (`1,067,181` rows) + `customer_rfm.csv` (`93,358` rows); zero silent deletions (`test_02`, `test_03`, `test_04`). |
| **SQL Warehouse & Views (`sql/`)** | ✅ Verified | `14` SQL scripts and `8` analytical views executed via `execute_and_validate_sql.py`; `31` CSV outputs in `reports/sql_outputs/` (`test_05`..`test_09`). |
| **Python Analytics & Charts (`src/analytics/`)** | ✅ Verified | `reports/analytics_summary.json`, `8` PNG charts in `reports/charts/`, and `6` populated `.ipynb` notebooks in `notebooks/` (`test_12`). |
| **Streamlit BI Application (`app/streamlit_app.py`)** | ✅ Completed & Verified | Enterprise visual redesign completed across all 8 modules with custom CSS KPI cards, `R$` formatting, interactive filters, `st.column_config` tables, and CSV downloads (`test_17` + 8-module smoke test). |
| **AI Multi-Agent System (`agents/`)** | ✅ Completed & Verified | Upgraded with `delivery_vs_reviews` intent, `ScopeGuardrail` (`unsupported_question`), CTE-aware `validate_sql_query`, and full 8-question audit (`test_10`, `test_11`, `test_13`, `test_14`). |
| **Excel Executive Workbook (`src/reporting/excel_report_builder.py`)** | ✅ Completed & Verified | Regenerated `Ecommerce_Revenue_Retention_Intelligence_Report.xlsx` (`43.1 KB`) with per-unit formatting on `Executive_KPI_Summary` and `=SUM` vs `=AVERAGE` totals (`test_15`). |
| **Power BI Package (`powerbi/`)** | ✅ Completed & Verified | `13` exports in `powerbi/data_exports/` (including `dim_date.csv`, `month_start_date`/`cohort_start_date` FKs, and `star_schema_relationships.json`), `22` DAX measures, and reconciled guide (`test_16`). |
| **Automated Test Suite (`tests/`)** | ✅ Completed & Verified | **`17/17` `pytest` tests passed** in `tests/test_analytics_pipeline.py`. |
| **Final Audit Report (`docs/FINAL_PROJECT_AUDIT.md`)** | ✅ Completed | Complete end-to-end audit report documenting all files, tests, findings, and instructions. |

---

## 2. Issues Discovered & Resolved in the Final Phase

1. **Streamlit UI & UX Redesign (`app/streamlit_app.py`) — RESOLVED:**
   - Replaced cramped 6-column default `st.metric` rows with custom HTML/CSS 4-column enterprise KPI cards (`render_kpi_card`) that never truncate titles or values.
   - Applied a unified Plotly chart theme (`apply_enterprise_chart_theme`) with anti-clipping margins, formatted hover tooltips, and dual-axis legends.
   - Configured `st.column_config` human-readable headers, `R$ %.2f` and `%.2f%%` formats, and CSV download buttons on every table across all 8 modules.
   - Added a checkbox toggle on Module 5 (`Cohort Retention`) so the heatmap defaults to `M+1..M+12` (`0.00%–0.72%`) for clear visual contrast without `M+0 = 100%` washing out the color scale.
   - Added dynamic interactive Plotly chart rendering and a Read-Only Custom SQL Sandbox to Module 8 (`AI Business Q&A Assistant`).

2. **AI Agent Intent Granularity & Scope Guardrails (`agents/`) — RESOLVED:**
   - Added `delivery_vs_reviews` intent in `agents/sql_analyst_agent.py` and `agents/insight_agent.py` so *"Does late delivery relate to lower review scores?"* queries the 6 delivery timing buckets (`Early`, `On Time`, `1–3 Days Late`, `4–7 Days Late`, `8+ Days Late`) directly from `order_level` (`Rows: 6`).
   - Added `ScopeGuardrail` (`unsupported_question`) so out-of-scope queries (e.g., net profit margin, marketing CAC, payroll, weather) safely return `0` rows with an explanation of available `ecommerce_analytics` tables.
   - Explicitly distinguished the `91,343` non-D5 customers in `vw_customer_lifecycle` (`R$ 161.76` avg CLV proxy, combining `90,557` single-order buyers at `R$ 160.76` and `786` same-day split-basket buyers at `R$ 277.23`) from the `2,015` Rule D-5 True Repeat Customers (`R$ 320.82`).

3. **Excel & Power BI Reconciliation Fixes — RESOLVED:**
   - Fixed the Jan 2017 – Aug 2018 window order value proxy total (**`R$ 15,375,875.44`** across `96,211` delivered orders) and exact RFM segment totals (`Potential Loyalists = R$ 148,840.82`, `At Risk = R$ 16,445.55`, `Champions = R$ 15,941.99`, `Loyal Customers = R$ 3,873.64`) in `powerbi/documentation/powerbi_dashboard_guide.md`.
   - Added `month_start_date` and `cohort_start_date` (`YYYY-MM-01`) foreign keys to Power BI summary CSVs and exported `powerbi/data_exports/star_schema_relationships.json`.
   - Applied unit-specific number formats (`"R$" #,##0.00`, `#,##0`, `0.00"%"`, `0.00`) on `Executive_KPI_Summary` and `=SUM` on additive share columns in `src/reporting/excel_report_builder.py`.
