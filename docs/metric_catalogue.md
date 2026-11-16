# Centralised KPI Catalogue & Metric Governance Layer

**Product:** E-COMMERCE INTELLIGENCE OS — AI-Powered Business Intelligence & Decision Platform  
**Source Module:** `src/analytics/metric_catalogue.py`  
**Currency:** Brazilian Real (`BRL` / `R$`)  
**Governance Rules Enforced:** `D-1` (Revenue Proxy vs Item Price), `D-2` (Jan 2017 – Aug 2018 Trend Window), `D-3` (Latest Review Deduplication), `D-4` (74-Category Mapping), `D-5` (Multi-Day Repeat Customer Rule)

---

## 1. Summary Table of Canonical KPIs

| KPI ID | Metric Name | Category | Canonical Value | Window Value (Jan 17–Aug 18) | Unit | Grain |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `KPI-001` | **Total Orders (All Statuses)** | Executive & Volume | **99,441** | 99,092 | Count | Order (order_id) |
| `KPI-002` | **Delivered Orders** | Executive & Volume | **96,478** | 96,211 | Count | Order (order_id) |
| `KPI-003` | **Delivery Completion Rate** | Executive & Volume | **97.02%** | 97.09 | Percentage (%) | Order (order_id) |
| `KPI-004` | **Delivered Order Value (Revenue Proxy)** | Revenue & Financials | **R$ 15,422,461.77** | R$ 15,375,875.44 | BRL (R$) | Order (order_id) |
| `KPI-005` | **Delivered Item Merchandise Revenue** | Revenue & Financials | **R$ 13,221,498.11** | R$ 13,181,027.13 | BRL (R$) | Order Item / Order |
| `KPI-006` | **Delivered Freight Value** | Revenue & Financials | **R$ 2,198,275.64** | R$ 2,192,092.88 | BRL (R$) | Order Item / Order |
| `KPI-007` | **Gross Payment Value (All Statuses)** | Revenue & Financials | **R$ 16,008,872.12** | Full Dataset | BRL (R$) | Payment Installment / Order |
| `KPI-008` | **Mean Order Value (AOV Proxy)** | Revenue & Financials | **R$ 159.86** | R$ 159.81 | BRL (R$) | Order (order_id) |
| `KPI-009` | **Median Order Value & IQR** | Revenue & Financials | **R$ 105.28 (IQR: R$ 114.45)** | R$ 105.28 | BRL (R$) | Order (order_id) |
| `KPI-010` | **Unique Customers (Delivered vs All Statuses)** | Customer & Retention | **93,358** | 93,104 | Count | Customer (customer_unique_id) |
| `KPI-011` | **True Repeat Customer Rate (Governance Rule D-5)** | Customer & Retention | **2.16% (2,015 customers)** | 2.15 | Percentage (%) | Customer (customer_unique_id) |
| `KPI-012` | **Repeat Customer Revenue Share (D-5)** | Customer & Retention | **4.19% (R$ 646,454.25)** | Full Dataset | Percentage (%) | Customer (customer_unique_id) |
| `KPI-013` | **Average & Median Delivery Days** | Logistics & Satisfaction | **12.56 days (Median: 10.22d)** | 12.5 | Days | Order (order_id) |
| `KPI-014` | **Late Delivery Rate (Timestamp vs Calendar Date)** | Logistics & Satisfaction | **8.11% (Calendar: 6.77%)** | 8.12 | Percentage (%) | Order (order_id) |
| `KPI-015` | **Average Customer Review Score (Delivered)** | Logistics & Satisfaction | **4.16 / 5.00** | 4.16 | Stars (1–5) | Order (order_id) |
| `KPI-016` | **Late Delivery Review Score Drop** | Logistics & Satisfaction | **-1.73 stars (4.29 vs 2.57)** | 1.73 | Stars (1–5) | Order (order_id) |
| `KPI-017` | **Top Product Category Item Revenue (health_beauty)** | Product & Seller | **R$ 1,233,131.72 (9.33% share)** | Full Dataset | BRL (R$) | Order Item |
| `KPI-018` | **Top 10% Seller Revenue Concentration (Decile 1)** | Product & Seller | **67.11% (R$ 8,873,076.37)** | Full Dataset | Percentage (%) | Seller Decile (seller_id) |

---

## 2. Detailed KPI Specifications

### KPI-001 — Total Orders (All Statuses)
- **Domain Category:** Executive & Volume
- **Canonical Verified Value:** `99,441` (Raw: `99441`)
- **Business Definition:** Total number of distinct customer checkout orders recorded across all 8 marketplace lifecycle statuses (delivered, shipped, canceled, unavailable, invoiced, processing, created, approved).
- **SQL Formula:** `SELECT COUNT(DISTINCT order_id) FROM orders_clean;`
- **Python Formula:** `int(order_master['order_id'].nunique())`
- **Source Tables:** `orders_clean, order_level_analytics`
- **Filters (Inclusions / Exclusions):** None (Full Dataset across all 8 order_status values).
- **Aggregation Grain:** Order (order_id)
- **Unit / Currency:** Count
- **Analysis Window:** Full Dataset (Sep 2016 – Oct 2018); Window (Jan 2017 – Aug 2018): 99,092
- **Null-Handling Rule:** Primary key order_id is non-null and 100% unique (99,441 rows).
- **Known Limitations & Caveats:** Includes 2,963 non-delivered orders (1,107 shipped, 625 canceled, 609 unavailable, etc.) that must be excluded from realized revenue reporting.

### KPI-002 — Delivered Orders
- **Domain Category:** Executive & Volume
- **Canonical Verified Value:** `96,478` (Raw: `96478`)
- **Business Definition:** Total number of completed orders that reached 'delivered' lifecycle status and form the primary denominator for order-level financial and operational KPIs.
- **SQL Formula:** `SELECT COUNT(*) FROM order_level_analytics WHERE is_delivered = 1;`
- **Python Formula:** `int((order_master['is_delivered'] == True).sum())`
- **Source Tables:** `orders_clean, order_level_analytics`
- **Filters (Inclusions / Exclusions):** order_status = 'delivered' (is_delivered = 1)
- **Aggregation Grain:** Order (order_id)
- **Unit / Currency:** Count
- **Analysis Window:** Full Dataset: 96,478 | Primary Window (Jan 2017 – Aug 2018, D-2): 96,211
- **Null-Handling Rule:** 8 delivered orders lack order_delivered_customer_date and are flagged via flag_missing_delivery_date but retained in delivered order counts.
- **Known Limitations & Caveats:** Excludes 1,107 in-flight 'shipped' orders near the dataset cutoff date.

### KPI-003 — Delivery Completion Rate
- **Domain Category:** Executive & Volume
- **Canonical Verified Value:** `97.02%` (Raw: `97.02`)
- **Business Definition:** Percentage of all marketplace orders that successfully reached 'delivered' status.
- **SQL Formula:** `ROUND(100.0 * SUM(CASE WHEN is_delivered = 1 THEN 1 ELSE 0 END) / COUNT(*), 2)`
- **Python Formula:** `round(delivered_orders / total_orders * 100, 2)`
- **Source Tables:** `order_level_analytics`
- **Filters (Inclusions / Exclusions):** Numerator: is_delivered = 1; Denominator: all orders.
- **Aggregation Grain:** Order (order_id)
- **Unit / Currency:** Percentage (%)
- **Analysis Window:** Full Dataset (Sep 2016 – Oct 2018)
- **Null-Handling Rule:** order_status has 0 nulls.
- **Known Limitations & Caveats:** Right-censored orders placed in late August–October 2018 slightly depress completion rate at the tail.

### KPI-004 — Delivered Order Value (Revenue Proxy)
- **Domain Category:** Revenue & Financials
- **Canonical Verified Value:** `R$ 15,422,461.77` (Raw: `15422461.77`)
- **Business Definition:** Total customer transaction value paid across all delivered orders, including merchandise price, freight charges, and installment financing adjustments (Governance Rule D-1).
- **SQL Formula:** `SELECT ROUND(SUM(payment_value), 2) FROM order_level_analytics WHERE is_delivered = 1;`
- **Python Formula:** `round(float(delivered['payment_value'].sum()), 2)`
- **Source Tables:** `order_payments_agg, order_level_analytics`
- **Filters (Inclusions / Exclusions):** is_delivered = 1 (Governance Rule D-1)
- **Aggregation Grain:** Order (order_id)
- **Unit / Currency:** BRL (R$)
- **Analysis Window:** Full Dataset: R$ 15,422,461.77 | Primary Window (Jan 2017 – Aug 2018, D-2): R$ 15,375,875.44
- **Null-Handling Rule:** 1 delivered order (bfbd0f9bdef84302105ad712db648a6c) has missing payment row (R$ 0.00 payment_value, R$ 143.46 item total) and is flagged via flag_missing_payment.
- **Known Limitations & Caveats:** Represents gross customer transaction value (GMV proxy), NOT net Olist take-rate commission revenue.

### KPI-005 — Delivered Item Merchandise Revenue
- **Domain Category:** Revenue & Financials
- **Canonical Verified Value:** `R$ 13,221,498.11` (Raw: `13221498.11`)
- **Business Definition:** Total product merchandise price across all delivered orders, excluding shipping freight and credit card installment interest (Governance Rule D-1).
- **SQL Formula:** `SELECT ROUND(SUM(price), 2) FROM order_level_analytics WHERE is_delivered = 1;`
- **Python Formula:** `round(float(delivered['price'].sum()), 2)`
- **Source Tables:** `order_items_clean, order_items_agg, order_level_analytics`
- **Filters (Inclusions / Exclusions):** is_delivered = 1 (Governance Rule D-1)
- **Aggregation Grain:** Order Item / Order
- **Unit / Currency:** BRL (R$)
- **Analysis Window:** Full Dataset: R$ 13,221,498.11 | Primary Window (Jan 2017 – Aug 2018): R$ 13,181,027.13
- **Null-Handling Rule:** 0 missing item rows among delivered orders.
- **Known Limitations & Caveats:** Does not include shipping fee (R$ 2,198,275.64) or net financing spread (R$ 2,688.02).

### KPI-006 — Delivered Freight Value
- **Domain Category:** Revenue & Financials
- **Canonical Verified Value:** `R$ 2,198,275.64` (Raw: `2198275.64`)
- **Business Definition:** Total shipping and carrier freight charges billed on delivered orders (Governance Rule D-1).
- **SQL Formula:** `SELECT ROUND(SUM(freight_value), 2) FROM order_level_analytics WHERE is_delivered = 1;`
- **Python Formula:** `round(float(delivered['freight_value'].sum()), 2)`
- **Source Tables:** `order_items_clean, order_items_agg, order_level_analytics`
- **Filters (Inclusions / Exclusions):** is_delivered = 1
- **Aggregation Grain:** Order Item / Order
- **Unit / Currency:** BRL (R$)
- **Analysis Window:** Full Dataset: R$ 2,198,275.64 | Primary Window (Jan 2017 – Aug 2018): R$ 2,192,092.88
- **Null-Handling Rule:** 383 promotional free-shipping items have R$ 0.00 freight_value and are flagged as valid zero-freight promotions.
- **Known Limitations & Caveats:** Pass-through logistics charge collected from customers; rises to 24%–29% of order value in North/Northeast states.

### KPI-007 — Gross Payment Value (All Statuses)
- **Domain Category:** Revenue & Financials
- **Canonical Verified Value:** `R$ 16,008,872.12` (Raw: `16008872.12`)
- **Business Definition:** Total payment transaction value recorded across all order statuses in order_payments_clean, prior to filtering for completed delivery.
- **SQL Formula:** `SELECT ROUND(SUM(payment_value), 2) FROM order_payments_clean;`
- **Python Formula:** `round(float(order_master['payment_value'].sum()), 2)`
- **Source Tables:** `order_payments_clean, order_level_analytics`
- **Filters (Inclusions / Exclusions):** All order statuses.
- **Aggregation Grain:** Payment Installment / Order
- **Unit / Currency:** BRL (R$)
- **Analysis Window:** Full Dataset (Sep 2016 – Oct 2018)
- **Null-Handling Rule:** 9 rows with R$ 0.00 payment_value (6 voucher + 3 canceled not_defined) are flagged.
- **Known Limitations & Caveats:** Includes R$ 586,410.35 from canceled, unavailable, and unfulfilled orders; never report as realized revenue.

### KPI-008 — Mean Order Value (AOV Proxy)
- **Domain Category:** Revenue & Financials
- **Canonical Verified Value:** `R$ 159.86` (Raw: `159.86`)
- **Business Definition:** Arithmetic mean of Delivered Order Value (payment_value) per delivered order.
- **SQL Formula:** `SELECT ROUND(AVG(payment_value), 2) FROM order_level_analytics WHERE is_delivered = 1;`
- **Python Formula:** `round(float(delivered['payment_value'].mean()), 2)`
- **Source Tables:** `order_level_analytics`
- **Filters (Inclusions / Exclusions):** is_delivered = 1
- **Aggregation Grain:** Order (order_id)
- **Unit / Currency:** BRL (R$)
- **Analysis Window:** Full Dataset: R$ 159.86 | Primary Window (Jan 2017 – Aug 2018): R$ 159.81
- **Null-Handling Rule:** Includes 1 delivered order with R$ 0.00 recorded payment_value.
- **Known Limitations & Caveats:** Right-skewed by high-ticket electronics/IT orders (max R$ 13,664.08); always pair with Median Order Value (R$ 105.28) and IQR (R$ 114.45).

### KPI-009 — Median Order Value & IQR
- **Domain Category:** Revenue & Financials
- **Canonical Verified Value:** `R$ 105.28 (IQR: R$ 114.45)` (Raw: `105.28`)
- **Business Definition:** 50th percentile (median) and interquartile range (P75 - P25) of Delivered Order Value across delivered orders, providing a skew-resistant measure of typical basket size.
- **SQL Formula:** `PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY payment_value) WHERE is_delivered = 1`
- **Python Formula:** `round(float(delivered['payment_value'].median()), 2)`
- **Source Tables:** `order_level_analytics`
- **Filters (Inclusions / Exclusions):** is_delivered = 1
- **Aggregation Grain:** Order (order_id)
- **Unit / Currency:** BRL (R$)
- **Analysis Window:** Full Dataset: Median R$ 105.28 (IQR R$ 114.45) | Primary Window: Median R$ 105.28
- **Null-Handling Rule:** Standard non-parametric quantile calculation.
- **Known Limitations & Caveats:** P25 = R$ 61.85, P75 = R$ 176.30, IQR = R$ 114.45.

### KPI-010 — Unique Customers (Delivered vs All Statuses)
- **Domain Category:** Customer & Retention
- **Canonical Verified Value:** `93,358` (Raw: `93358`)
- **Business Definition:** Count of distinct real-world buyers identified by customer_unique_id (never session-level customer_id).
- **SQL Formula:** `SELECT COUNT(DISTINCT customer_unique_id) FROM order_level_analytics WHERE is_delivered = 1;`
- **Python Formula:** `int(delivered['customer_unique_id'].nunique())`
- **Source Tables:** `customers_clean, order_level_analytics, customer_rfm`
- **Filters (Inclusions / Exclusions):** Delivered: is_delivered = 1 (93,358); All Statuses: none (96,096).
- **Aggregation Grain:** Customer (customer_unique_id)
- **Unit / Currency:** Count
- **Analysis Window:** Full Dataset: 93,358 delivered (96,096 all statuses) | Window (Jan 2017 – Aug 2018): 93,104
- **Null-Handling Rule:** customer_unique_id is 100% populated.
- **Known Limitations & Caveats:** Using customer_id instead of customer_unique_id would falsely report 0% repeat purchase rate because customer_id is generated per checkout.

### KPI-011 — True Repeat Customer Rate (Governance Rule D-5)
- **Domain Category:** Customer & Retention
- **Canonical Verified Value:** `2.16% (2,015 customers)` (Raw: `2.16`)
- **Business Definition:** Percentage of delivered unique customers who placed at least 2 distinct delivered orders on at least 2 distinct calendar dates (Governance Rule D-5 Option b).
- **SQL Formula:** `ROUND(100.0 * COUNT(CASE WHEN distinct_purchase_days >= 2 THEN 1 END) / COUNT(*), 2)`
- **Python Formula:** `round(2015 / 93358 * 100, 2)`
- **Source Tables:** `customer_rfm, order_level_analytics`
- **Filters (Inclusions / Exclusions):** is_delivered = 1; repeat defined as distinct_purchase_days >= 2 (D-5).
- **Aggregation Grain:** Customer (customer_unique_id)
- **Unit / Currency:** Percentage (%)
- **Analysis Window:** Full Dataset: 2.16% (2,015 customers) | Any-Day Sensitivity (Option a): 3.00% (2,801 customers; 786 same-day split checkouts)
- **Null-Handling Rule:** 0 nulls.
- **Known Limitations & Caveats:** Excludes 786 customers who only had multiple order_ids on the exact same calendar day (multi-seller checkout splits).

### KPI-012 — Repeat Customer Revenue Share (D-5)
- **Domain Category:** Customer & Retention
- **Canonical Verified Value:** `4.19% (R$ 646,454.25)` (Raw: `4.19`)
- **Business Definition:** Percentage of total Delivered Order Value generated by true multi-day repeat customers (2,015 customers with distinct_purchase_days >= 2).
- **SQL Formula:** `SELECT ROUND(100.0 * SUM(CASE WHEN is_repeat_customer_d5 = 1 THEN total_order_value_brl ELSE 0 END) / SUM(total_order_value_brl), 2) FROM customer_rfm;`
- **Python Formula:** `round(repeat_revenue_d5 / total_delivered_order_value * 100, 2)`
- **Source Tables:** `customer_rfm`
- **Filters (Inclusions / Exclusions):** is_delivered = 1, is_repeat_customer_d5 = 1
- **Aggregation Grain:** Customer (customer_unique_id)
- **Unit / Currency:** Percentage (%)
- **Analysis Window:** Full Dataset (Sep 2016 – Oct 2018)
- **Null-Handling Rule:** 0 nulls.
- **Known Limitations & Caveats:** 95.81% of marketplace order value depends on one-time buyers.

### KPI-013 — Average & Median Delivery Days
- **Domain Category:** Logistics & Satisfaction
- **Canonical Verified Value:** `12.56 days (Median: 10.22d)` (Raw: `12.56`)
- **Business Definition:** Elapsed calendar days from order_purchase_timestamp to order_delivered_customer_date for delivered orders.
- **SQL Formula:** `SELECT ROUND(AVG(delivery_days), 2) FROM order_level_analytics WHERE is_delivered = 1 AND delivery_days IS NOT NULL;`
- **Python Formula:** `round(float(delivered['delivery_days'].dropna().mean()), 2)`
- **Source Tables:** `order_level_analytics`
- **Filters (Inclusions / Exclusions):** is_delivered = 1 AND delivery_days IS NOT NULL (96,470 orders)
- **Aggregation Grain:** Order (order_id)
- **Unit / Currency:** Days
- **Analysis Window:** Full Dataset (96,470 delivered orders with valid delivery timestamp)
- **Null-Handling Rule:** 8 delivered orders with NULL order_delivered_customer_date are excluded from duration calculation.
- **Known Limitations & Caveats:** Mean (12.56 days) exceeds median (10.22 days) due to long-tail interstate shipments to North/Northeast Brazil.

### KPI-014 — Late Delivery Rate (Timestamp vs Calendar Date)
- **Domain Category:** Logistics & Satisfaction
- **Canonical Verified Value:** `8.11% (Calendar: 6.77%)` (Raw: `8.11`)
- **Business Definition:** Percentage of delivered orders where actual customer delivery timestamp exceeded the promised order_estimated_delivery_date timestamp.
- **SQL Formula:** `SELECT ROUND(100.0 * AVG(CASE WHEN is_late_delivery = 1 THEN 1.0 ELSE 0.0 END), 2) FROM order_level_analytics WHERE is_delivered = 1 AND delivery_days IS NOT NULL;`
- **Python Formula:** `round(float(delivered.dropna(subset=['delivery_days'])['is_late_delivery'].mean() * 100), 2)`
- **Source Tables:** `order_level_analytics`
- **Filters (Inclusions / Exclusions):** is_delivered = 1 AND delivery_days IS NOT NULL
- **Aggregation Grain:** Order (order_id)
- **Unit / Currency:** Percentage (%)
- **Analysis Window:** Full Dataset (96,470 delivered orders with delivery dates)
- **Null-Handling Rule:** Excludes 8 delivered orders missing delivery date.
- **Known Limitations & Caveats:** Exact timestamp comparison yields 8.11% (7,826 orders); strict calendar-date comparison (> 0 calendar days after estimated date) yields 6.77% (6,534 orders).

### KPI-015 — Average Customer Review Score (Delivered)
- **Domain Category:** Logistics & Satisfaction
- **Canonical Verified Value:** `4.16 / 5.00` (Raw: `4.16`)
- **Business Definition:** Mean customer satisfaction score (1 to 5 stars) on delivered orders after deduplicating multi-review orders to the most recent review (Governance Rule D-3).
- **SQL Formula:** `SELECT ROUND(AVG(latest_review_score), 2) FROM order_level_analytics WHERE is_delivered = 1 AND latest_review_score IS NOT NULL;`
- **Python Formula:** `round(float(delivered['latest_review_score'].dropna().mean()), 2)`
- **Source Tables:** `order_reviews_clean, order_reviews_agg, order_level_analytics`
- **Filters (Inclusions / Exclusions):** is_delivered = 1 AND latest_review_score IS NOT NULL (95,832 orders; D-3 latest review per order)
- **Aggregation Grain:** Order (order_id)
- **Unit / Currency:** Stars (1–5)
- **Analysis Window:** Full Dataset (95,832 reviewed delivered orders)
- **Null-Handling Rule:** 646 delivered orders without a submitted review are excluded from the average.
- **Known Limitations & Caveats:** Sensitivity check using mean score per order yields an identical 4.16 stars.

### KPI-016 — Late Delivery Review Score Drop
- **Domain Category:** Logistics & Satisfaction
- **Canonical Verified Value:** `-1.73 stars (4.29 vs 2.57)` (Raw: `1.73`)
- **Business Definition:** Difference in mean customer review score between on-time delivered orders (4.29 stars) and late delivered orders (2.57 stars), validated via Mann-Whitney U test.
- **SQL Formula:** `ROUND(AVG(CASE WHEN is_late_delivery = 0 THEN latest_review_score END) - AVG(CASE WHEN is_late_delivery = 1 THEN latest_review_score END), 2)`
- **Python Formula:** `round(on_time_mean_score - late_mean_score, 2)`
- **Source Tables:** `order_level_analytics`
- **Filters (Inclusions / Exclusions):** is_delivered = 1 AND delivery_days IS NOT NULL AND latest_review_score IS NOT NULL (88,163 on-time vs 7,661 late)
- **Aggregation Grain:** Order (order_id)
- **Unit / Currency:** Stars (1–5)
- **Analysis Window:** Full Dataset (95,824 orders with both delivery timestamp and review score)
- **Null-Handling Rule:** Requires non-null delivery_days and latest_review_score.
- **Known Limitations & Caveats:** Mann-Whitney U = 524,647,305.0, p < 0.0001; Spearman rho = -0.2346 (delivery days vs review score).

### KPI-017 — Top Product Category Item Revenue (health_beauty)
- **Domain Category:** Product & Seller
- **Canonical Verified Value:** `R$ 1,233,131.72 (9.33% share)` (Raw: `1233131.72`)
- **Business Definition:** Delivered item merchandise revenue (SUM(price)) for the #1 revenue-generating product category (health_beauty / beleza_saude) under Governance Rule D-1 & D-4.
- **SQL Formula:** `SELECT ROUND(SUM(price), 2) FROM order_items_clean i JOIN orders_clean o ON i.order_id = o.order_id WHERE o.order_status = 'delivered' AND category = 'health_beauty';`
- **Python Formula:** `round(float(cat_perf.loc[cat_perf['category_english']=='health_beauty', 'item_revenue_brl'].iloc[0]), 2)`
- **Source Tables:** `order_items_clean, products_clean, vw_category_performance`
- **Filters (Inclusions / Exclusions):** order_status = 'delivered', category_english = 'health_beauty'
- **Aggregation Grain:** Order Item
- **Unit / Currency:** BRL (R$)
- **Analysis Window:** Full Dataset (74 categories including uncategorized and 2 manual mappings under D-4)
- **Null-Handling Rule:** 610 products without category name are mapped to 'uncategorized' (R$ 175,952.71 delivered item revenue).
- **Known Limitations & Caveats:** Evaluated using SUM(price) per D-1 to avoid order-level payment multiplication across multi-item orders.

### KPI-018 — Top 10% Seller Revenue Concentration (Decile 1)
- **Domain Category:** Product & Seller
- **Canonical Verified Value:** `67.11% (R$ 8,873,076.37)` (Raw: `67.11`)
- **Business Definition:** Percentage of total delivered item merchandise revenue (R$ 13,221,498.11) generated by the top 10% of active delivered sellers (Decile 1: 297 of 2,970 sellers).
- **SQL Formula:** `SELECT share_of_total_item_revenue_pct FROM seller_decile_summary WHERE revenue_decile = 1;`
- **Python Formula:** `round(8873076.37 / 13221498.11 * 100, 2)`
- **Source Tables:** `order_items_clean, sellers_clean, 03_seller_performance_analysis_result_2.csv`
- **Filters (Inclusions / Exclusions):** order_status = 'delivered' across 2,970 active delivered sellers (NTILE(10) by item_revenue_brl DESC).
- **Aggregation Grain:** Seller Decile (seller_id)
- **Unit / Currency:** Percentage (%)
- **Analysis Window:** Full Dataset (2,970 active delivered sellers out of 3,095 total registered sellers)
- **Null-Handling Rule:** 125 registered sellers with 0 delivered orders are excluded from active delivered seller deciles.
- **Known Limitations & Caveats:** Decile 1 (297 sellers) generates R$ 8,873,076.37 (67.11%); Top 20% (Deciles 1–2, 594 sellers) generates R$ 10,879,659.64 (82.29%).
