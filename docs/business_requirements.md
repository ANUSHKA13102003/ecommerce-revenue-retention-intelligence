# Business Requirements & Verified Answers (13 Core Questions)

This document maps the **13 core business questions** to their verified SQL scripts, analytical views, and empirical answers (all currency values in **Brazilian Real `BRL` / `R$`**).

---

## 1. Revenue & Order Performance

### Q1. What is the total order value and monthly revenue trend?
- **Verified Answer:** Across all `96,478` delivered orders (`2016–2018`), **Delivered Order Value Proxy (`SUM(payment_value)`)** is **`R$ 15,422,461.77`**, **Delivered Item Revenue (`SUM(price)`)** is **`R$ 13,221,498.11`**, and **Delivered Freight (`SUM(freight_value)`)** is **`R$ 2,198,235.63`**. Inside the 20-month analysis window (**Jan 2017 – Aug 2018**, `96,211` delivered orders, `R$ 15,375,875.44`), monthly delivered order value grew **8.0x** from `R$ 127,545.67` (`750` orders in Jan 2017) to `R$ 985,414.28` (`6,351` orders in Aug 2018), peaking in **Nov 2017 (Black Friday)** at **`R$ 1,153,528.05`** (`7,289` orders).
- **Source SQL:** `sql/02_business_analysis/01_monthly_revenue_analysis.sql`, `vw_executive_monthly_kpis`

### Q2. Which product categories generate the most revenue?
- **Verified Answer:** Per Rule D-1 (`SUM(price)` on delivered items = `R$ 13,221,498.11`), the top 5 categories generate **`39.83%`** (`R$ 5,266,320.62`) of all item revenue:
  1. `health_beauty` (`R$ 1,233,131.72`, `8,647` delivered orders)
  2. `watches_gifts` (`R$ 1,166,176.98`, `5,495` orders)
  3. `bed_bath_table` (`R$ 1,023,434.76`, `9,272` orders)
  4. `sports_leisure` (`R$ 954,852.55`, `7,530` orders)
  5. `computers_accessories` (`R$ 888,724.61`, `6,530` orders)
- **Source SQL:** `sql/02_business_analysis/02_product_and_category_performance.sql`, `vw_category_performance`

### Q3. Which products and sellers perform best?
- **Verified Answer:** Out of `2,970` active sellers with delivered orders, the **top `10%` (`297` sellers)** generate **`67.45%`** (`R$ 8,917,843.20`) of delivered item revenue, and the top `20%` (`594` sellers) generate **`83.31%`**. The single highest-revenue seller (`4869f7a5dfa277a7dca6462dcf3b52b2`, SP) generated **`R$ 226,987.93`** across `1,124` delivered orders (`4.13 ★`). The top individual product (`bb50f2e236e5eea0100680137654686c`, `health_beauty`) generated **`R$ 63,560.00`** across `194` units sold.
- **Source SQL:** `sql/02_business_analysis/02_product_and_category_performance.sql`, `sql/02_business_analysis/03_seller_performance_analysis.sql`, `vw_seller_performance`

### Q4. What is the average order value (AOV)?
- **Verified Answer:** Across `96,478` delivered orders, **Mean AOV** is **`R$ 159.86`** (`R$ 137.04` item price + `R$ 22.78` freight) and **Median AOV** is **`R$ 105.28`** (`IQR: R$ 61.88 – R$ 176.33`, `90th percentile = R$ 305.50`, `99th percentile = R$ 1,048.55`).
- **Source SQL:** `sql/02_business_analysis/01_monthly_revenue_analysis.sql`, `sql/02_business_analysis/05_payment_and_installment_analysis.sql`

---

## 2. Customer Retention & Segmentation

### Q5 & Q6. How many customers make repeat purchases and what percentage return?
- **Verified Answer (Rule D-5):** Among **`93,358`** unique delivered customers (`customer_unique_id`), **`2,015` (`2.16%`)** are **True Repeat Customers** (`2+` delivered orders on `2+` distinct calendar dates; `2,005` / `2.15%` in the Jan 2017 – Aug 2018 window).
  - Sensitivity (a) — `2+` delivered orders regardless of date: **`2,801` (`3.00%`)** (includes `786` same-day split-basket buyers).
  - Sensitivity (c) — `2+` orders across all order statuses (`96,096` customers): **`2,997` (`3.12%`)**.
  - True Repeat Customers have a **2.0x higher Historical CLV Proxy** (**`R$ 320.82`** vs. **`R$ 160.76`** for single-order customers).
- **Source SQL:** `sql/03_customer_analytics/01_repeat_customer_analysis.sql`, `sql/03_customer_analytics/03_customer_lifetime_value_proxy.sql`

### Q7. Which acquisition-month cohorts retain customers?
- **Verified Answer:** Across the `20` monthly cohorts from `2017-01` to `2018-08` (`93,104` delivered customers), **M+1 retention** peaks in cohort **`2017-10`** (`0.716%`, `31` of `4,328` customers) and **`2017-09`** (`0.701%`, `28` of `3,995` customers), while holiday cohort **`2017-12`** (`0.206%`, `11` of `5,338`) and **`2017-02`** (`0.184%`, `3` of `1,628`) exhibit the steepest M+1 drop-off.
- **Source SQL:** `sql/04_cohort_retention/01_cohort_retention_analysis.sql`

### Q8. Which customer segments generate the most revenue?
- **Verified Answer:** In the 7-segment RFM model (`93,358` customers), **`Recent Customers`** (`37,219` customers, `39.87%`) generate **`R$ 6,269,299.23` (`40.65%`)**, and **`Lost Customers`** (`37,358` customers, `40.02%`) account for **`R$ 6,167,951.88` (`39.99%`)**, followed by **`Needs Attention`** (`18,272` customers, `R$ 2,800,108.66`, `18.16%`). High-frequency segments (`Potential Loyalists` `449`, `At Risk` `31`, `Champions` `23`, `Loyal Customers` `6`) total `509` customers (`R$ 185,102.00`, avg monetary `R$ 331–R$ 693`).
- **Source SQL:** `sql/03_customer_analytics/02_rfm_customer_segmentation.sql`, `vw_rfm_segments_summary`

### Q9. Which customers appear at risk of becoming inactive?
- **Verified Answer (Rule D-6 Analytical Inactivity Bands):** Relative to the `2018-10-17` snapshot:
  - Active (`<= 90` days): **`11,769`** (`12.61%`)
  - Cooling (`91–180` days): **`18,754`** (`20.09%`)
  - At-Risk (`181–270` days): **`19,092`** (`20.45%`)
  - High Inactivity Risk (`271–365` days): **`19,383`** (`20.76%`)
  - Long-Term Inactive (`> 365` days): **`24,360`** (`26.09%`)
- **Source SQL:** `sql/03_customer_analytics/03_customer_lifetime_value_proxy.sql`, `vw_customer_lifecycle`

---

## 3. Operations, Delivery & Strategic Recommendations

### Q10. What is the delivery delay rate?
- **Verified Answer:** Among `96,470` delivered orders with non-null delivery dates, **`7,826` orders (`8.11%`)** were delivered after the estimated delivery timestamp (`6,534` orders / **`6.77%`** when measured strictly in whole calendar days). Mean actual delivery time is **`12.56` days** vs. **`24.33` days** estimated (`11.77` days early on average).
- **Source SQL:** `sql/02_business_analysis/04_delivery_and_satisfaction_analysis.sql`

### Q11. How are delivery delays associated with review scores?
- **Verified Answer:** On-time delivered orders average **`4.29 / 5.00 ★`** (`8.94%` 1-star reviews), whereas late orders average **`2.57 / 5.00 ★`** (`46.46%` 1-star reviews) — a **`-1.72 ★` penalty** ($p < 0.0001$). Orders delayed by `8+` days (`2,862` orders) average **`1.70 ★`** with **`69.87%` 1-star reviews**.
- **Source SQL:** `sql/02_business_analysis/04_delivery_and_satisfaction_analysis.sql`

### Q12. Which regions and product categories show opportunities?
- **Verified Answer:** Southeast Brazil (`SP`, `RJ`, `MG`) generates **`67.26%`** of delivered orders, but **Rio de Janeiro (`RJ`, `12,350` orders, `R$ 2.06M`)** suffers a **`13.47%` late rate** (`3.97 ★`), and **Bahia (`BA`, `3,256` orders, `R$ 591K`)** has a **`14.04%` late rate** (`3.86 ★`). Establishing regional 3PL fulfillment hubs in RJ and Northeast Brazil (`BA/PE/CE`) reduces transit times and high freight ratios (`>24%` of item price in the Northeast vs. `12.6%` in SP).
- **Source SQL:** `sql/02_business_analysis/06_geographic_sales_performance.sql`, `vw_delivery_and_reviews_by_state`

### Q13. What business actions can improve retention and experience?
- **Verified Answer:**
  1. **Logistics SLA Buffer & Regional 3PL:** Cutting late deliveries by `50%` (~`3,913` orders) prevents ~`1,468` 1-star reviews.
  2. **30–60 Day Replenishment Trigger:** Targeting the `37,219` `Recent Customers` in high-repeat categories (`health_beauty`, `bed_bath_table`, `sports_leisure`) to lift repeat rate from `2.16%` toward `4.00%` represents ~`R$ 275,000+` in incremental order value.
  3. **Installment Merchandising:** Promoting 3–6x interest-free credit card installments on carts above `R$ 150` leverages higher credit-card AOV (`R$ 163.08` vs `R$ 144.66` boleto).
