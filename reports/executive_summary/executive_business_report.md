# Executive Business Intelligence Report — E-Commerce Revenue & Customer Retention

**Dataset:** Olist Brazilian E-Commerce Public Dataset (`99,441` orders, `1,550,922` raw records)  
**Currency:** Brazilian Real (`BRL`)  
**Primary Analysis Window (Rule D-2):** January 2017 – August 2018 (`in_analysis_window = 1`)  

---

## 1. Executive Summary & Verified Headline KPIs (Facts)

| Metric | Full Dataset (Sep 2016 – Oct 2018) | Analysis Window (Jan 2017 – Aug 2018) | Methodological Note |
|---|---:|---:|---|
| **Total Orders (All Statuses)** | `99,441` | `99,092` | 1 row per `order_id` |
| **Delivered Orders** | `96,478` (`97.02%`) | `96,211` | `order_status = 'delivered'` |
| **Unique Delivered Customers** | `93,358` | `93,104` | Distinct `customer_unique_id` |
| **Delivered Order Value Proxy (BRL)** | `R$ 15,422,461.77` | `R$ 15,375,875.44` | Rule D-1: `SUM(payment_value)` (Revenue proxy) |
| **Delivered Item Revenue (BRL)** | `R$ 13,221,498.11` | `R$ 13,181,027.13` | Rule D-1: `SUM(price)` for Product/Category/Seller |
| **Delivered Freight Value (BRL)** | `R$ 2,198,275.64` | `R$ 2,192,092.88` | Reported separately from item price |
| **Average Order Value Proxy (BRL)** | `R$ 159.86` | `R$ 159.81` | Median: `R$ 105.28` |
| **True Repeat Customers (Rule D-5)** | `2,015` (`2.16%`) | `2,005` (`2.15%`) | `2+` delivered orders on `2+` calendar dates |
| **Average Delivery Time** | `12.56 days` | — | Median: `10.22 days` |
| **Late Delivery Rate** | `8.11%` | — | `7,826` of `96,470` delivered orders with date |
| **Average Review Score** | `4.16 / 5.00` | — | On-Time `4.29` vs Late `2.57` |

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
