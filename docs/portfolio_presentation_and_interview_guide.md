# CommerceLens AI — Portfolio Presentation & Interview Guide

**Product:** **CommerceLens AI** — *AI-Powered E-Commerce Intelligence Platform*  
**Tagline:** *Turning E-Commerce Data into Intelligent Business Decisions.*  
**Repository:** `ecommerce-revenue-retention-intelligence`  
**Dataset:** Olist Brazilian E-Commerce Public Dataset (`9` raw CSVs, `1,550,922` rows, `99,441` orders)

---

## 1. 14-Slide Executive Presentation Deck Outline

### Slide 1 — Title & Executive Value Proposition
- **Headline:** CommerceLens AI: AI-Powered E-Commerce Intelligence Platform (SQL, Python, Power BI, Streamlit & Agentic AI)
- **Sub-headline:** Transforming `1.55M` raw marketplace records (`99,441` orders, `R$ 15.42M` delivered order value) into audited revenue, retention, and logistics decisions.

### Slide 2 — Business Context & 6 Governance Rules (D-1 to D-6)
- **Key Message:** Analytical integrity starts with strict metric definitions before writing a single line of SQL.
- **Visual:** Governance table showing:
  - **Rule D-1:** `SUM(payment_value)` (`R$ 15,422,461.77`) = Delivered Order Value Proxy vs. `SUM(price)` (`R$ 13,221,498.11`) = Delivered Item Revenue vs. `SUM(freight_value)` (`R$ 2,198,275.64`).
  - **Rule D-2:** Primary 20-month window (`Jan 2017 – Aug 2018`, `96,211` delivered orders).
  - **Rule D-5:** True Repeat Customer = `customer_unique_id` with $\ge 2$ delivered orders on $\ge 2$ distinct dates.

### Slide 3 — Data Architecture & Pre-Join Grain Reconciliation
- **Key Message:** Direct joins across raw `order_items` (`112,650`), `payments` (`103,886`), and `reviews` (`99,224`) cause Cartesian fan-out inflation.
- **Visual:** Architecture flow showing pre-aggregated `1:1` order summaries (`order_item_summary`, `order_payment_summary`, `order_review_summary`) feeding `order_level` (`99,441` rows) in MySQL 8 & DuckDB.

### Slide 4 — Data Quality Audit & Non-Destructive Flagging
- **Key Message:** `100%` of raw rows preserved (`0` silent deletions); `34` quality checks logged.
- **Metrics:** `2,965` orders missing delivery dates (`99.7%` explained by non-delivered statuses), `610` uncategorized products mapped to `Unknown`, `2` manual category translations documented, `1` unlinked order (`bfbd0f9bdef84302105ad712db648a6c`) flagged.

### Slide 5 — Marketplace Growth & Seasonality (Jan 2017 – Aug 2018)
- **Chart:** `reports/charts/01_monthly_revenue_and_orders_trend.png`
- **Finding:** Monthly delivered order value expanded **8.0x** from `R$ 127.5K` (`750` orders in Jan 2017) to `R$ 985.4K–R$ 1.12M`/month in 2018. Nov 2017 Black Friday hit **`R$ 1,153,528.05`** (`7,289` orders) but pushed late deliveries to **`14.31%`**.

### Slide 6 — Product Category Concentration & Pricing Dynamics
- **Chart:** `reports/charts/02_top_categories_item_revenue.png`
- **Finding:** Out of `74` categories (`R$ 13.22M` item revenue), the **top 5 categories generate `39.83%`** (`R$ 5.27M`): `health_beauty` (`R$ 1.23M`), `watches_gifts` (`R$ 1.17M`, high `R$ 199` avg price), `bed_bath_table` (`R$ 1.02M`, `10,953` units), `sports_leisure` (`R$ 0.95M`), and `computers_accessories` (`R$ 0.89M`).

### Slide 7 — Seller Pareto Concentration
- **Chart:** `reports/charts/08_seller_pareto_concentration.png`
- **Finding:** Across `2,970` active sellers with delivered orders, the **top `10%` (`297` sellers) generate `67.11%`** (`R$ 8.87M`) of item revenue, and the top `20%` (`594` sellers) generate **`82.29%`**.

### Slide 8 — Customer Retention & The Same-Day Split-Basket Discovery
- **Key Message:** Why naive SQL overstates repeat buyers by `39%`.
- **Finding:** Among `93,358` delivered customers, `2,801` (`3.00%`) have `2+` delivered `order_id`s, but **`786` (`0.84%`) placed those orders on the exact same calendar day** (multi-seller cart splits). True multi-day repeat customers total **`2,015` (`2.16%`)**, with a **2.0x higher Historical CLV Proxy** (`R$ 320.82` vs. `R$ 160.76`).

### Slide 9 — Monthly Cohort Retention Decay (Jan 2017 – Aug 2018)
- **Chart:** `reports/charts/03_cohort_retention_heatmap.png`
- **Finding:** Across `20` monthly acquisition cohorts (`93,104` customers), M+1 repeat retention stays between **`0.184%` and `0.716%`**, proving that one-and-done purchasing is a structural platform issue requiring lifecycle CRM intervention.

### Slide 10 — RFM Customer Segmentation (`93,358` Delivered Customers)
- **Chart:** `reports/charts/04_rfm_customer_segments.png`
- **Finding:** `Recent Customers` (`37,219` / `39.87%`) drive **`R$ 6.27M` (`40.65%`)** of order value, while `Lost Customers` (`37,358` / `40.02%`) represent **`R$ 6.17M` (`39.99%`)**. High-frequency tiers (`Potential Loyalists` `449`, `At Risk` `31`, `Champions` `23`, `Loyal` `6`) total `509` high-value buyers (`R$ 331–R$ 693` avg spend).

### Slide 11 — Delivery Delay vs. Customer Review Score (Statistical Proof)
- **Chart:** `reports/charts/05_delivery_delay_vs_review_score.png`
- **Finding:** On-time orders (`91.89%`) average **`4.29 ★`** (`8.94%` 1-star rate), whereas late orders (`8.11%`, `7,826` orders) plunge to **`2.57 ★`** (`46.46%` 1-star rate) — a **`-1.72 ★` drop** (Welch's $t = 96.49, p < 0.0001$; Mann-Whitney $U, p < 0.0001$). At `8+` days late (`2,862` orders), `69.87%` of reviews are 1-star (`1.70 ★` mean).

### Slide 12 — Geographic Logistics Bottlenecks & Payment Behavior
- **Charts:** `06_state_revenue_and_late_rate.png` & `07_payment_method_distribution.png`
- **Finding:** `SP` (`42%` of orders) has a `5.89%` late rate (`8.76` days, `4.25 ★`), while `RJ` (`12,350` orders) hits **`13.47%` late** (`15.31` days, `3.97 ★`) and Northeast states hit **`14%–24%` late**. Credit cards represent **`78.46%`** of delivered payment value (`R$ 12.10M`, avg `3.51` installments, `R$ 163.08` avg transaction) vs. Boleto (`17.96%`, `R$ 144.66`).

### Slide 13 — AI Multi-Agent System, Interactive Streamlit App & BI Suite
- **Showcase:**
  - `AnalyticsOrchestrator` (`6` specialized agents + Read-Only SQL Allow-List Gate blocking `DROP`/`DELETE`/multi-statement SQL).
  - `8`-page Streamlit application (`app/streamlit_app.py`), `10`-tab Executive Excel Workbook (`.xlsx`), `3`-page Executive PDF, and Power BI Project (`powerbi/Ecommerce_Intelligence_OS.pbip`: `19` tables, `10` relationships, `39` DAX measures).

### Slide 14 — Quantified Strategic Roadmap
- **Action 1 (Logistics SLA & Regional 3PL):** Cut late rate in RJ & Northeast by `50%` (~`3,913` orders) -> prevent **`~1,468` 1-star reviews** and lift marketplace rating from `4.16 ★` to `4.22 ★`.
- **Action 2 (30–60 Day Replenishment Trigger):** Convert `+1.84%` of `Recent Customers` into repeat buyers (`2.16% -> 4.00%`) -> generate **`~R$ 275,000+`** in incremental order value.
- **Action 3 (Top-Decile Seller Governance):** Enforce SLA & packaging standards on the `297` sellers driving `67.11%` (`R$ 8.87M`) of item sales.

---

## 2. Spoken Presentation Scripts

### 2.1 Two-Minute Elevator Pitch
> "I built an end-to-end E-Commerce Revenue and Customer Retention Intelligence platform on the real Olist Brazilian E-Commerce dataset — 1.55 million raw rows across 9 tables and 99,441 orders totaling R$ 15.42 million in delivered order value.
>
> Instead of jumping straight into charts, I first solved three classic marketplace data traps: first, pre-aggregating line items, payments, and reviews to the order grain before joining so multi-item and multi-payment orders never inflate revenue; second, separating buyer checkout payment value from actual merchandise item price (`R$ 13.22M`) and freight (`R$ 2.20M`); and third, discovering that out of 2,801 multi-order customers, 786 actually placed split-cart orders on the exact same day — meaning the true multi-day repeat purchase rate is 2.16% (`2,015` customers), and those repeat customers spend twice as much (`R$ 320.82` vs. `R$ 160.76`).
>
> Using SQL, Python hypothesis testing, and RFM segmentation across 93,358 customers, I proved that the #1 operational killer of customer satisfaction is late delivery: crossing the estimated delivery date causes average reviews to plunge by 1.72 stars — from 4.29 stars to 2.57 stars ($p < 0.0001$), with 70% 1-star reviews when orders are 8+ days late, heavily concentrated in Rio de Janeiro (`13.47%` late) and Northeast Brazil.
>
> Finally, I packaged the entire warehouse into 8 reusable SQL views, an 8-tab Executive Excel Workbook, a 12-table Power BI star-schema package with 22 DAX measures, an 8-page Streamlit web app, and a 6-agent AI SQL assistant protected by a read-only SQL safety gate — all backed by 12 automated pytest tests."

### 2.2 Five-Minute Technical Walkthrough Script
1. **Minute 1 — Problem Framing & Data Engineering (`data/raw/` -> `data/processed/`):**
   - Explain the 9 raw CSV files (`1,550,922` rows) and why raw immutability (SHA-256 verification) + non-destructive quality flagging (`cleaning_log.json`) was used instead of dropping rows.
   - Highlight the grain reconciliation architecture: aggregating `order_items_clean` (`112,650` rows), `payments_clean` (`103,886` rows), and `reviews_clean` (`99,224` rows) into `1:1` order summaries before building `order_level` (`99,441` rows).
2. **Minute 2 — Relational Warehouse & Advanced SQL (`sql/`):**
   - Walk through the dual-engine design (`MySQL 8` + `DuckDB` fallback in `src/database/db_engine.py`) and the 14 SQL scripts + 8 analytical views (`sql/05_views/01_analytical_views.sql`).
   - Explain why standard `NTILE(5)` fails on Olist RFM Frequency (since `97.84%` of customers have `frequency = 1`), and show how combining explicit frequency tiers (`1 -> 1, 2 -> 3, 3 -> 4, 4+ -> 5`) with `CUME_DIST()` quintiles for Recency and Monetary produces the exact 7-segment distribution (`93,358` customers).
3. **Minute 3 — Statistical Analysis & Cohort Retention (`src/analytics/` & `notebooks/`):**
   - Walk through the Jan 2017 – Aug 2018 (`20`-month) cohort retention matrix (`M+1` retention `< 0.72%`) and Rule D-5 sensitivity checks (`2.16%` multi-day vs. `3.00%` any-day delivered).
   - Present the Welch's t-test ($t = 96.49, p < 0.0001$) and Mann-Whitney U test proving the `-1.72 ★` satisfaction cliff on late deliveries.
4. **Minute 4 — Multi-Agent AI System & SQL Safety Gate (`agents/`):**
   - Demonstrate `AnalyticsOrchestrator` coordinating `DataProfilerAgent`, `DataQualityAgent`, `SQLAnalystAgent`, `CustomerAnalyticsAgent`, `BusinessInsightAgent`, and `ReportAgent`.
   - Show how `validate_sql_query()` strips comments/literals, blocks DDL/DML (`DROP`, `DELETE`, `;`), resolves query-local CTEs, and enforces the `23`-table allow-list before execution.
5. **Minute 5 — Executive Delivery & Quantified Impact (`app/`, `powerbi/`, `reports/`):**
   - Walk through the 8-page Streamlit app, 8-tab Excel workbook, and Power BI star schema.
   - Conclude with the two headline quantified recommendations: cutting late deliveries by `50%` saves `~1,468` 1-star reviews, and lifting repeat rate from `2.16%` to `4.00%` unlocks `~R$ 275,000+` in incremental order value.

---

## 3. Resume Bullet Points & GitHub Metadata

### GitHub Repository Description (1-Line)
> End-to-End E-Commerce Revenue & Retention Intelligence Platform (Olist 1.55M rows): MySQL/DuckDB Warehouse, 14 SQL Analyses & 8 Views, Python Hypothesis Testing, RFM & Cohort Modeling, Power BI Star Schema, Excel Automation, 8-Page Streamlit App & Read-Only Agentic AI SQL Assistant (`12/12` pytest).

### Resume Bullet Points (Copy-Ready)
- **Data Analytics & SQL Engineering:** Architected a grain-reconciled e-commerce data warehouse (`1.55M` raw records, `99,441` orders, `R$ 15.42M` order value) across MySQL 8 and DuckDB with `14` production SQL scripts and `8` analytical views, eliminating multi-item/payment join fan-out to achieve `100%` cent-level financial reconciliation.
- **Customer Retention, RFM & Statistical Modeling:** Engineered a custom `CUME_DIST()` + rule-based RFM segmentation and 20-month cohort pipeline across `93,358` customers, isolating `786` same-day checkout cart splits from `2,015` true repeat buyers (`2.16%` repeat rate, `2.0x` CLV multiplier) and proving via Mann-Whitney U / Welch's t-tests ($p < 0.0001$) that delivery delays reduce review ratings by `1.72` stars (`4.29 ★` to `2.57 ★`).
- **Agentic AI & BI Delivery:** Built a 6-agent AI analytics orchestrator with a deterministic read-only SQL allow-list validator (`0` hallucinations, blocks DDL/DML injection), alongside an 8-page Streamlit web app, automated 8-tab `openpyxl` Executive Workbook, and 12-table Power BI star-schema package (`22` DAX measures) verified by `12` automated `pytest` tests.

---

## 4. Technical & Business Interview Q&A

### Q1 (Technical — SQL & Data Modeling): Why can't you join `orders`, `order_items`, and `order_payments` directly in a single SQL query to calculate both category revenue and total payment value?
- **Answer:** Because `order_items` (`112,650` rows) and `order_payments` (`103,886` rows) both have `1-to-many` relationships with `orders` (`99,441` rows) along independent dimensions. If an order has `3` items and `2` payment methods (e.g., credit card + voucher), a direct join produces `3 × 2 = 6` rows for that single order, multiplying `SUM(price)` by `2x` and `SUM(payment_value)` by `3x`. In this project, we pre-aggregate items to `order_item_summary` (`1` row per `order_id`), payments to `order_payment_summary` (`1` row per `order_id`), and reviews to `order_review_summary` (`1` row per `order_id`) before joining to `order_level`, or join `order_items_clean` directly to `order_level` when analyzing category-level `SUM(price)`.

### Q2 (Technical — Customer Identity): What is the difference between `customer_id` and `customer_unique_id` in Olist?
- **Answer:** In Olist, `customer_id` (`99,441` unique values) is a **per-order session/transaction key** that has a `1:1` relationship with `order_id`. If you group by `customer_id`, the repeat purchase rate appears to be `0.00%`. True customer identity is stored in `customer_unique_id` (`96,096` unique customers overall; `93,358` with delivered orders).

### Q3 (Technical — RFM Scoring): Why did you use `CUME_DIST()` for Recency/Monetary and explicit rules for Frequency instead of `NTILE(5)` across all three dimensions?
- **Answer:** Because `97.84%` of delivered customers (`91,343` out of `93,358`) purchased on exactly `1` calendar day. If you apply `NTILE(5) OVER (ORDER BY purchase_days)` to a column where `97.84%` of rows are tied at `1`, SQL arbitrarily assigns Frequency scores of `1, 2, 3, 4, and 5` to single-purchase customers based on physical row order! Instead, we assign deterministic Frequency scores (`1 day -> 1`, `2 days -> 3`, `3 days -> 4`, `4+ days -> 5`) and use `CUME_DIST()` quintile thresholds (`0.20, 0.40, 0.60, 0.80`) on Recency and Monetary so tied values always receive the exact same score.

### Q4 (Technical — AI Engineering): How do you prevent your AI SQL Analyst Agent from hallucinating numbers or running destructive SQL?
- **Answer:** Two architectural guardrails:
  1. **Read-Only SQL Safety Gate (`validate_sql_query`):** Before any SQL string reaches `AnalyticsDBEngine`, our regex AST validator strips comments and string literals, verifies a single statement (blocking `;`), enforces a `SELECT` or `WITH` prefix, blocks `21` destructive/write keywords (`DROP`, `DELETE`, `UPDATE`, `COPY`, `ATTACH`, etc.), and checks every `FROM`/`JOIN` table against the `23` approved tables/views (excluding query-local CTEs).
  2. **Deterministic Grounded Synthesis:** `BusinessInsightAgent` never invents numbers from an LLM prompt; it interpolates statistics directly from the executed pandas DataFrame and logs the SQL, row count, and output to `reports/agent_audit_log.json`.

### Q5 (Business Insight): Why did you define a Repeat Customer as having `2+` delivered orders on `2+` distinct dates (Rule D-5), and what business insight came from that distinction?
- **Answer:** When inspecting the `2,801` customers with `2+` delivered `order_id`s (`3.00%`), we found that `786` of them (`28%` of multi-order buyers) placed all of their orders on the **exact same calendar date** (often within the same minute) because Olist splits multi-seller carts into separate `order_id`s at checkout. Counting split carts as "customer retention" overstates true repeat behavior by `39%`. Separating them reveals two distinct business opportunities: (1) a lifecycle retention program for the `2,015` true multi-day repeat buyers (`2.16%`) who spend `2.0x` more (`R$ 320.82` vs `R$ 160.76`), and (2) checkout UX optimization for the `786` multi-seller cart buyers.

