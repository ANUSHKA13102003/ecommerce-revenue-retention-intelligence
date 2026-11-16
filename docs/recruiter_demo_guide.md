# 3-Minute Recruiter & Hiring Manager Live Demonstration Guide

**Product:** **E-COMMERCE INTELLIGENCE OS** — *AI-Powered Business Intelligence & Decision Platform*  
**Dataset:** Olist Brazilian E-Commerce Public Dataset (`99,441` orders, `1,550,922` raw rows, `BRL / R$`)  
**Launch Command:** `streamlit run app/streamlit_app.py`

---

## Minute 1: Executive Pitch & Cross-Platform Metric Governance (0:00 – 1:00)

1. **Open `Executive Intelligence Dashboard` (Page 1):**
   - **What to say:**
     > *"I built E-COMMERCE INTELLIGENCE OS to transform 1.55 million raw Brazilian e-commerce records from Olist into an enterprise decision platform. Instead of building disconnected charts, I engineered a single centralized KPI layer (`src/analytics/metric_catalogue.py`) and an automated cross-platform reconciliation engine (`src/analytics/reconciliation_engine.py`) that verifies all 18 headline KPIs match to the cent across MySQL, Python, a 10-sheet Excel workbook, Power BI exports, and this Streamlit UI."*
2. **Highlight the Headline KPIs & Governance Rules (`D-1` to `D-5`):**
   - Point to the top KPI row and status pills (`Scope: Full Dataset / Jan 2017 – Aug 2018`, `Currency: BRL (R$)`, `18/18 KPIs Reconciled`):
     - **Delivered Order Value Proxy (`Rule D-1`):** `R$ 15,422,461.77` across `96,478` delivered orders (`97.02%` completion), strictly separated from **Delivered Item Merchandise Revenue** (`R$ 13,221,498.11`) and **Freight** (`R$ 2,198,275.64`) so multi-item joins never inflate revenue.
     - **Mean vs Median Basket Size:** Mean AOV is `R$ 159.86`, paired with Median AOV (`R$ 105.28`, IQR `R$ 114.45`) to account for right-skewed electronics baskets.
     - **Decision Intelligence Centre:** Point to the two executive decision cards at the bottom quantifying the `+R$ 200K–R$ 275K` retention opportunity and the `-1.73★` late-delivery review cliff.

---

## Minute 2: Deep-Dive Customer Retention, Seller Pareto & Logistics SLA (1:00 – 2:00)

1. **Click `Customer Intelligence` (Page 3) & `RFM Segmentation` (Page 4):**
   - **What to say:**
     > *"A common trap on the Olist dataset is using `customer_id`, which is generated per checkout and falsely shows 0% repeat buyers. By tracking `customer_unique_id` and applying Governance Rule D-5—requiring 2+ delivered orders on 2+ distinct calendar dates so same-day split checkouts (`786` buyers) aren't miscounted—we uncover that true repeat rate is `2.16%` (`2,015` of `93,358` delivered buyers). Yet those repeaters generate `2.0x` higher historical CLV (`R$ 320.82` vs `R$ 160.76`)."*
   - Show the **7 Validated RFM Segments** (`37,219 Recent Customers` worth `R$ 6.27M` who are prime candidates for 30-day replenishment campaigns before slipping into `Needs Attention` or `Lost`).
2. **Click `Product & Seller Intelligence` (Page 6) & `Delivery & Customer Satisfaction` (Page 7):**
   - **What to say:**
     > *"On the supply side, NTILE(10) seller decile analysis proves that the Top 10% of active sellers (`297` of `2,970` merchants) generate `67.11%` (`R$ 8,873,076.37`) of item revenue. On the operations side, a Mann-Whitney U test across `95,824` reviewed orders confirms that crossing the promised delivery date (`8.11%` late rate) causes average review ratings to plunge from `4.29★` to `2.57★` (`-1.73★` drop, `p < 0.0001`), with `69.87%` 1-star reviews when delayed 8+ days."*

---

## Minute 3: Live AI Business Copilot & Guardrail Demonstration (2:00 – 3:00)

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

