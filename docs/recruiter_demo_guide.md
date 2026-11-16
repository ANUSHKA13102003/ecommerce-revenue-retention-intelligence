# 3-Minute Recruiter & Hiring Manager Live Demonstration Guide

**Product:** **CommerceLens AI** — *AI-Powered E-Commerce Intelligence Platform*  
**Tagline:** *Turning E-Commerce Data into Intelligent Business Decisions.*  
**Dataset:** Olist Brazilian E-Commerce Public Dataset (`99,441` orders, `1,550,922` raw rows, `BRL / R$`)  
**Launch Command:** `streamlit run app/streamlit_app.py`

---

## Minute 1: Business Problem, Architecture & Power BI PBIX Walkthrough (0:00 – 1:15)

1. **Introduce Business Problem, Dataset & Architecture (`README.md` / `docs/architecture.md`):**
   - > *"CommerceLens AI turns 1.55 million raw Olist marketplace records (`99,441` orders) into reconciled revenue, retention, and logistics decisions. I engineered pre-join 1:1 order aggregations so multi-item/multi-payment joins never inflate revenue, backed by a 15-table MySQL 8.0 / DuckDB warehouse, a centralized 18-KPI catalogue, and automated cross-platform reconciliation."*
2. **Open Power BI Desktop (`powerbi/Ecommerce_Intelligence_OS.pbix`):**
   - Walk through the 5 pages (`Executive Overview`, `Revenue Intelligence`, `Customer Intelligence`, `Product and Seller Performance`, `Retention Analysis`).
   - **Test Synced Slicers Live:** Filter **`Year = 2018`** (`Orders = 52,783`, `Order Value Proxy = R$ 8,452,975.20`), **`Product Category = health_beauty`** (`Item Revenue = R$ 1,233,131.72` while `order_level` order counts remain preserved under single-direction star filtering), and **`Payment Method = credit_card`** on Page 2 (`R$ 12,101,094.88`), then clear slicers to restore `96,478` delivered orders / `R$ 15,422,461.77`.
3. **Highlight Three Key Empirical Findings:**
   - **D-5 True Repeat Discovery:** Separating `786` same-day split-basket buyers (`0.84%`) leaves **`2,015` true multi-day repeat customers (`2.16%`)**, who deliver **`2.0x` higher CLV** (`R$ 320.82` vs. `R$ 160.76`).
   - **Top-Decile Seller Pareto:** Top `10%` of sellers (`297` of `2,970`) drive **`67.11%`** (`R$ 8,873,076.37`) of merchandise revenue.
   - **Delivery Satisfaction Cliff:** Crossing the estimated delivery date (`8.11%` late rate) drops average review ratings from **`4.29★` to `2.57★`** (`-1.72★` penalty, Mann-Whitney $U$ $p < 0.0001$).

---

## Minute 2: Interactive 8-Page Streamlit Walkthrough & Deep-Dive Analytics (1:15 – 2:15)

1. **Open `Executive Intelligence Dashboard` & `Revenue Intelligence` (`streamlit run app/streamlit_app.py`):**
   - Toggle `Full Dataset` (`96,478` / `R$ 15,422,461.77`) vs `Window D-2` (`96,211` / `R$ 15,375,875.44`, Rule D-1 `SUM(price)` = `R$ 13,221,498.11`, Freight = `R$ 2,198,275.64`).
2. **Click `Customer Intelligence` (Page 3) & `RFM Segmentation` (Page 4):**
   - Highlight all 7 RFM segments (`37,219 Recent Customers` = `R$ 6.27M` priority retention cohort) and the 20-month cohort heatmap (`0.184%–0.716%` M+1 retention).
3. **Click `Product & Seller Intelligence` (Page 6) & `Delivery & Customer Satisfaction` (Page 7):**
   - Point out `SP` (`5.89%` late) vs `RJ` (`13.47%` late) and `AL`/`MA` (`23.93%`/`19.67%` late), plus Excel (`10` sheets) and PDF (`3` pages) deliverables.

---

## Minute 3: AI Business Copilot, Limitations & Recommendations (2:15 – 3:00)

1. **Click `AI Business Copilot` (Page 8):**
   - **Select Question 2:** *"Why did order value decline in June 2018?"*
     - Show how the Copilot decomposes the `-10.34%` MoM drop (`R$ 1,128,836.69` in May 2018 $\rightarrow$ `R$ 1,012,090.68` in June 2018) into a `-9.63%` order volume drop (`6,749` $\rightarrow$ `6,099` orders) following the late-May 2018 Brazilian truckers' strike while AOV held steady (`R$ 167.26` $\rightarrow$ `R$ 165.94`).
   - **Select Question 8:** *"What business actions should management consider?"*
     - Show the 4 quantified management actions grounded in SQL lineage, alongside the expandable **Read-Only SQL Inspector** and **SQL Safety Gate (`PASS`)**.
   - **Type an Out-of-Scope Question:** *"What is our net profit margin after marketing CAC?"*
     - Show how the **Scope Guardrail** refuses to hallucinate unmeasured metrics (COGS/CAC) and explains the exact dataset boundaries.

---

## Key Technical Questions & Ready Answers for Interviewers

- **Q: How did you prevent row-multiplication fan-out when joining orders, items, payments, and reviews?**
  - **A:** In `src/cleaning/clean_pipeline.py` and `sql/02_business_analysis/`, `order_items` (`112,650` rows), `order_payments` (`103,886` rows), and `order_reviews` (`99,224` rows) are pre-aggregated to exact `1:1` `order_id` grain (`order_items_agg`, `order_payments_agg`, `order_reviews_agg`) before joining to `orders_clean` (`99,441` rows). Automated tests in `tests/test_analytics_pipeline.py` assert zero row inflation and cent-for-cent financial conservation.
- **Q: Why do `SUM(payment_value)` (`R$ 15,422,461.77`) and `SUM(price + freight_value)` (`R$ 15,419,773.75`) differ by `R$ 2,688.02` on delivered orders?**
  - **A:** Because multi-installment credit card checkouts in Brazil include issuer financing interest in `payment_value` (and 1 delivered order `bfbd0f9bdef84302105ad712db648a6c` has `R$ 143.46` in item/freight value but zero recorded rows in `order_payments`). Under Governance Rule `D-1`, we report `payment_value` as `Delivered Order Value Proxy` at the order level and `SUM(price)` (`R$ 13,221,498.11`) for product, category, and seller analysis.

