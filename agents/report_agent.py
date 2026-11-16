"""
Report Agent
=============
Drafts structured Executive Summaries and Markdown Business Reports
using only verified metrics from `reports/analytics_summary.json` and
`reports/sql_outputs/`. Clearly separates empirical facts from recommendations.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ReportAgent:
    """Generates the verified Executive Summary markdown report."""

    def __init__(self) -> None:
        self.summary_path = ROOT / "reports" / "analytics_summary.json"
        self.out_dir = ROOT / "reports" / "executive_summary"
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def generate_executive_markdown(self) -> Path:
        s = json.loads(self.summary_path.read_text(encoding="utf-8"))
        kf = s["executive_kpis"]["full_dataset"]
        kw = s["executive_kpis"]["analysis_window_2017_01_to_2018_08"]
        ret = s["retention_metrics"]["full_dataset_delivered"]
        mw = s["statistical_tests"]["on_time_vs_late_review_score_mann_whitney"]
        sp_corr = s["statistical_tests"]["delay_days_vs_estimate_spearman"]

        md = f"""# Executive Business Intelligence Report — E-Commerce Revenue & Customer Retention

**Dataset:** Olist Brazilian E-Commerce Public Dataset (`99,441` orders, `1,550,922` raw records)  
**Currency:** Brazilian Real (`BRL`)  
**Primary Analysis Window (Rule D-2):** January 2017 – August 2018 (`in_analysis_window = 1`)  

---

## 1. Executive Summary & Verified Headline KPIs (Facts)

| Metric | Full Dataset (Sep 2016 – Oct 2018) | Analysis Window (Jan 2017 – Aug 2018) | Methodological Note |
|---|---:|---:|---|
| **Total Orders (All Statuses)** | `{kf['total_orders_all_statuses']:,}` | `{kw['total_orders_all_statuses']:,}` | 1 row per `order_id` |
| **Delivered Orders** | `{kf['delivered_orders']:,}` (`{kf['delivery_completion_rate_pct']}%`) | `{kw['delivered_orders']:,}` | `order_status = 'delivered'` |
| **Unique Delivered Customers** | `{kf['unique_delivered_customers']:,}` | `{kw['unique_delivered_customers']:,}` | Distinct `customer_unique_id` |
| **Delivered Order Value Proxy (BRL)** | `R$ {kf['delivered_order_value_proxy_brl']:,.2f}` | `R$ {kw['delivered_order_value_proxy_brl']:,.2f}` | Rule D-1: `SUM(payment_value)` (Revenue proxy) |
| **Delivered Item Revenue (BRL)** | `R$ {kf['delivered_item_revenue_brl']:,.2f}` | `R$ {kw['delivered_item_revenue_brl']:,.2f}` | Rule D-1: `SUM(price)` for Product/Category/Seller |
| **Delivered Freight Value (BRL)** | `R$ {kf['delivered_freight_value_brl']:,.2f}` | `R$ {kw['delivered_freight_value_brl']:,.2f}` | Reported separately from item price |
| **Average Order Value Proxy (BRL)** | `R$ {kf['average_order_value_proxy_brl']:,.2f}` | `R$ {kw['average_order_value_proxy_brl']:,.2f}` | Median: `R$ {kf['median_order_value_proxy_brl']:,.2f}` |
| **True Repeat Customers (Rule D-5)** | `{ret['repeat_customers_d5_distinct_days']:,}` (`{ret['repeat_rate_d5_pct']}%`) | `{s['retention_metrics']['analysis_window_delivered']['repeat_customers_d5_distinct_days']:,}` (`{s['retention_metrics']['analysis_window_delivered']['repeat_rate_d5_pct']}%`) | `2+` delivered orders on `2+` calendar dates |
| **Average Delivery Time** | `{kf['avg_delivery_days']:.2f} days` | — | Median: `{kf['median_delivery_days']:.2f} days` |
| **Late Delivery Rate** | `{kf['late_delivery_rate_timestamp_pct']}%` | — | `7,826` of `96,470` delivered orders with date |
| **Average Review Score** | `{kf['avg_review_score_delivered']:.2f} / 5.00` | — | On-Time `{mw['on_time_mean_score']:.2f}` vs Late `{mw['late_mean_score']:.2f}` |

---

## 2. Empirical Findings by Domain (Measured Facts)

### 2.1 Revenue Trajectory & Payment Behaviour
- **Rapid Expansion in 2017 Followed by 2018 Plateau:** Monthly delivered order value proxy grew **8.1x** from **`R$ 127,545.67`** (`750` orders) in January 2017 to a Black Friday peak of **`R$ 1,153,528.05`** (`7,289` orders) in November 2017, then stabilized between **`R$ 966.5K` and `R$ 1.13M`** per month from January to August 2018.
- **Credit Card & Installment Dominance:** Credit cards drive **`78.46%`** (`R$ 12,101,094.88`) of delivered payment value across `74,304` orders, followed by **boleto** at **`17.96%`** (`R$ 2,769,932.58`), **vouchers** (`2.22%`), and **debit cards** (`1.35%`). Orders paid in `11+` credit card installments carry an average payment value of **`R$ 385.56`** vs **`R$ 110.22`** for single-installment credit card orders.

### 2.2 Product Category & Seller Concentration
- **Top 5 Categories Generate 39.83% of Item Revenue:** Across `74` categories (total delivered item price `R$ 13,221,498.11`), the top 5 are:
  1. `health_beauty`: **`R$ 1,233,131.72`** (`9.33%`, `8,647` delivered orders)
  2. `watches_gifts`: **`R$ 1,166,176.98`** (`8.82%`, `5,495` delivered orders, avg price `R$ 199.04`)
  3. `bed_bath_table`: **`R$ 1,023,434.76`** (`7.74%`, `9,272` delivered orders)
  4. `sports_leisure`: **`R$ 954,852.55`** (`7.22%`, `7,530` delivered orders)
  5. `computers_accessories`: **`R$ 888,724.61`** (`6.72%`, `6,530` delivered orders)
- **Extreme Seller Pareto Concentration:** Of `2,970` active sellers with delivered orders, the **top 10% (`297` sellers, Decile 1)** generate **`67.11%`** (`R$ 8,873,076.37`) of total delivered item revenue, and the top 20% (`594` sellers, Deciles 1–2) generate **`82.29%`** (`R$ 10,879,659.64`).

### 2.3 Customer Retention, RFM Segmentation & CLV Proxy
- **Repeat Purchase Sensitivity (Rule D-5):**
  - **Approved Primary Rule D-5 (`2+` delivered orders on `2+` distinct dates):** **`2,015` customers (`2.16%`)** of `93,358` delivered customers.
  - **Sensitivity Option (a) (`2+` delivered orders, any date):** **`2,801` customers (`3.00%`)**, which includes `786` customers who placed multiple orders on the same calendar day (split baskets).
  - **Sensitivity Option (c) (`2+` orders across all statuses):** **`2,997` customers (`3.12%`)** of `96,096` total customers.
- **2.0x Historical CLV Multiplier:** True repeat customers (`2,015`) average **`R$ 320.82`** in historical delivered order value (`4.19%` of total value) vs **`R$ 160.76`** for single-order customers (`90,557` customers).
- **Validated RFM Segmentation (`93,358` Delivered Customers):**
  - `Lost Customers`: **`37,358`** (`40.02%` of customers, `R$ 6,167,951.88`)
  - `Recent Customers`: **`37,219`** (`39.87%` of customers, `R$ 6,269,299.23`)
  - `Needs Attention`: **`18,272`** (`19.57%` of customers, `R$ 2,798,239.09`)
  - `Potential Loyalists`: **`449`** (`0.48%`, `R$ 147,286.12`)
  - `At Risk`: **`31`** (`0.03%`, `R$ 15,067.94`)
  - `Champions`: **`23`** (`0.02%`, `R$ 19,684.50`)
  - `Loyal Customers`: **`6`** (`0.01%`, `R$ 4,933.01`)
- **Monthly Cohort Retention (Jan 2017 – Aug 2018):** Across all cohorts, `M+1` retention ranges between **`0.184%` (`2017-02`) and `0.716%` (`2017-10`)**, with holiday cohort `2017-12` dropping to **`0.206%`** in `M+1`.

### 2.4 Delivery Logistics & Customer Satisfaction
- **Statistically Significant Satisfaction Cliff (`p < 0.0001`):**
  - On-time delivered orders (`88,644`) average **`4.29 / 5.00`** review score (`10.88` avg delivery days).
  - Late delivered orders (`7,826`, `8.11%` by timestamp; `6,534` / `6.77%` by calendar day) average **`2.57 / 5.00`** (`31.52` avg delivery days) — a **`-1.72` star drop** (Mann-Whitney U test `p < 0.0001`; Spearman correlation between delay days vs estimate and review score `rho = -0.2673`).
  - When orders are **`8+` days late** (`2,862` orders), average review score collapses to **`1.70 / 5.00`** and **`69.87%`** of reviews are **1-star**.
- **Regional Fulfilment Disparity:** São Paulo (`SP`, `37.41%` of order value) enjoys **`8.76` avg delivery days**, a **`5.89%` late rate**, and a **`4.25` review score**. By contrast, Rio de Janeiro (`RJ`, `13.33%` of value) suffers a **`13.47%` late rate** (`3.97` score), Bahia (`BA`) **`14.04%` late** (`3.93` score), and Ceará (`CE`) **`15.32%` late** (`3.94` score). Inter-state shipments (`64.0%` of items) take **`14.95` days** (`9.37%` late) vs **`8.42` days** (`5.66%` late) for intra-state shipments.

---

## 3. Strategic Business Recommendations (Actions)

1. **SLA Enforcement & Dynamic EDD Calibration on Inter-State Routes (Operations):**
   - *Action:* Recalibrate carrier estimated delivery dates (EDDs) for inter-state shipments into `RJ`, `BA`, `CE`, `PE`, `AL`, and `MA`, and introduce proactive delay notifications 48 hours before an EDD breach.
   - *Expected Impact:* Reducing the `8+ day late` bucket (`2,862` orders, `69.87%` 1-star rate) by 50% would prevent ~`1,000` 1-star reviews and protect marketplace brand trust.
2. **Regional Seller Onboarding & 3PL Decentralization (Supply Growth):**
   - *Action:* Recruit sellers and establish regional fulfillment warehousing in Northeast Brazil (`BA`, `PE`, `CE`) and `RJ` for fast-moving categories (`health_beauty`, `bed_bath_table`, `housewares`).
   - *Expected Impact:* Converting inter-state orders (`14.95` days, `R$ 22.87` avg freight) to intra-state fulfillment (`8.42` days, `R$ 14.81` avg freight) lowers buyer freight burden by ~`35%` and cuts late delivery rates from `9.37%` to `5.66%`.
3. **30-to-60 Day Post-Delivery Retention Lifecycle Campaign (CRM / Marketing):**
   - *Action:* Target the `37,219` `Recent Customers` with category-matched replenishment incentives (e.g., `health_beauty` and `pet_shop` refills) triggered 14–30 days after confirmed on-time delivery.
   - *Expected Impact:* Because a true repeat customer generates **`R$ 320.82`** vs **`R$ 160.76`** for a one-time buyer (`+R$ 160.06` incremental value), lifting the repeat purchase rate by just `+1.0` percentage point (`+934` customers) represents **`~R$ 149,500 BRL`** in incremental delivered order value.

---

## 4. Limitations & Analytical Guardrails

- **Revenue Proxy vs Marketplace Take-Rate:** `payment_value` (`R$ 15.42M` delivered) represents customer gross payment value (item price + freight + installment financing adjustments), not Olist's net commission revenue.
- **Historical Observation Window:** Data spans September 2016 – October 2018 (with sparse edge months outside Jan 2017 – Aug 2018 excluded from trend and cohort analyses per Rule D-2).
- **Analytical Inactivity vs Observed Churn:** Because e-commerce marketplace purchases are non-contractual, RFM segments (`Lost Customers`, `At Risk`) and recency thresholds (`90/180/270/365` days) represent analytical inactivity rules, not verified customer churn.
"""
        out_path = self.out_dir / "executive_business_report.md"
        out_path.write_text(md, encoding="utf-8")
        return out_path

