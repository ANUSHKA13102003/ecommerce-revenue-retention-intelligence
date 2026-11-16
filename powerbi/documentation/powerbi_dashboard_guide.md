# Power BI Data Model, Star Schema & Dashboard Implementation Guide

**Project:** E-Commerce Revenue & Customer Retention Intelligence  
**Currency:** Brazilian Real (`BRL` — Format String: `"R$" #,##0.00`)  
**Source Options:** MySQL 8.0 (`ecommerce_analytics`) OR Pre-Reconciled CSV Exports (`powerbi/data_exports/` & `data/processed/`)

> **Compiled Workbook & Verification Note:**  
> The compiled workbook [`powerbi/Ecommerce_Intelligence_OS.pbix`](../Ecommerce_Intelligence_OS.pbix) (`34.89 MB`) and its PBIP source [`powerbi/Ecommerce_Intelligence_OS.pbip`](../Ecommerce_Intelligence_OS.pbip) are both included, built from `19` tables (`dim_date`, `7` granular tables including `payments_clean`, `11` analytical summary marts), `10` single-direction relationships, `39` weighted DAX measures (`powerbi/dax/olist_dax_measures.dax`), and `5` pages (`Executive Overview`, `Revenue Intelligence`, `Customer Intelligence`, `Product and Seller Performance`, `Retention Analysis`) with synced dropdown slicers (`Year`, `Analysis Window`, `Customer State`, `Product Category`, plus `Payment Method` on Page 2).

---

## 1. Step-by-Step Instructions to Connect CSVs & Build Relationships in Power BI Desktop

### Option A — Fast-Track Executive Dashboard (Using `powerbi/data_exports/*.csv`)
1. Open **Power BI Desktop** -> **File -> Options and settings -> Options -> Regional Settings -> Data Load** and set Locale for import to **English (United States)** (so `.` decimal separators and `YYYY-MM-DD` ISO dates parse deterministically).
2. Click **Home -> Get Data -> Text/CSV** and import the 12 CSV files from `powerbi/data_exports/`:
   - `dim_date.csv` (`1,096` rows, `2016-01-01` to `2018-12-31`, PK: `date_key`)
   - `pbi_monthly_kpis.csv` (`20` rows, `2017-01` to `2018-08`, FK: `month_start_date`)
   - `pbi_category_performance.csv` (`74` rows, PK: `category_name_en`)
   - `pbi_seller_performance.csv` (`2,970` rows, PK: `seller_id`)
   - `pbi_rfm_segments_summary.csv` (`7` rows, PK: `customer_segment`)
   - `pbi_state_performance.csv` (`27` rows, PK: `customer_state`)
   - `pbi_payment_methods.csv` (`4` rows, PK: `payment_type`)
   - `pbi_order_status_summary.csv` (`8` rows, PK: `order_status`)
   - `pbi_cohort_retention_long.csv` (`210` cohort-month pairs, FK: `cohort_start_date`)
   - `pbi_cohort_retention_matrix.csv` (`20` cohorts × `M0..M12`, FK: `cohort_start_date`)
   - `pbi_delivery_delay_buckets.csv` (`6` delivery timing buckets, PK: `delivery_timing_bucket`)
   - `pbi_customer_clv_groups.csv` (`3` repeat behaviour groups, PK: `customer_behaviour_group`)
3. In **Table View**, select `dim_date` -> click **Table tools -> Mark as date table** -> choose `date_key`. Set `month_short` to **Sort by column** `year_month`.
4. In **Model View**, drag and create the following **Single-Direction (`1 -> *`)** relationships:
   - `dim_date[date_key]` (`1`) $\longrightarrow$ `pbi_monthly_kpis[month_start_date]` (`*`)
   - `dim_date[date_key]` (`1`) $\longrightarrow$ `pbi_cohort_retention_long[cohort_start_date]` (`*`)
   - `dim_date[date_key]` (`1`) $\longrightarrow$ `pbi_cohort_retention_matrix[cohort_start_date]` (`*`)

### Option B — Full Granular Star Schema (Using `data/processed/*.csv` or MySQL `ecommerce_analytics`)
If importing the row-level tables (`order_level.csv`, `order_items_clean.csv`, `products_clean.csv`, `sellers_clean.csv`, `customers_clean.csv`, `customer_rfm.csv`) alongside `powerbi/data_exports/dim_date.csv`:

```
                   ┌──────────────────────────┐
                   │        dim_date          │
                   │  PK: date_key (1,096 d)  │
                   └────────────┬─────────────┘
                                │ 1 : * (PurchaseDate = Date.From(order_purchase_timestamp))
                                ▼
┌──────────────────────┐   ┌──────────────────────────┐   ┌──────────────────────────┐
│     customer_rfm     │1:*│       order_level        │1:*│    order_items_clean     │
│PK: customer_unique_id├──►│   PK: order_id (99,441)  ├──►│ PK: (order_id, item_id)  │
│  (93,358 delivered)  │   │  payment_value, is_late  │   │ price, freight (112,650) │
└──────────────────────┘   └──────────────────────────┘   └──────┬────────────┬──────┘
                                                                 │ * : 1      │ * : 1
                                                                 ▼            ▼
                                                   ┌──────────────────┐  ┌──────────────────┐
                                                   │  products_clean  │  │  sellers_clean   │
                                                   │  PK: product_id  │  │  PK: seller_id   │
                                                   └──────────────────┘  └──────────────────┘
```

1. In **Power Query Editor** on `order_level`, duplicate `order_purchase_timestamp`, rename it `purchase_date`, and change its type from **Date/Time** to **Date** (`YYYY-MM-DD`).
2. Configure **Single-Direction (`1 -> *`)** relationships in **Model View** (never use Bi-Directional cross-filtering between `order_level` and `order_items_clean`, so `SUM(order_level[payment_value])` is never multiplied by line items):
   - `dim_date[date_key]` (`1`) $\longrightarrow$ `order_level[purchase_date]` (`*`, Single)
   - `order_level[order_id]` (`1`) $\longrightarrow$ `order_items_clean[order_id]` (`*`, Single)
   - `products_clean[product_id]` (`1`) $\longrightarrow$ `order_items_clean[product_id]` (`*`, Single)
   - `sellers_clean[seller_id]` (`1`) $\longrightarrow$ `order_items_clean[seller_id]` (`*`, Single)
   - `customers_clean[customer_id]` (`1`) $\longrightarrow$ `order_level[customer_id]` (`1`, Single)
   - `customer_rfm[customer_unique_id]` (`1`) $\longrightarrow$ `order_level[customer_unique_id]` (`*`, Single)

---

## 2. Reconciled 4-Page Dashboard Layout & Exact Target Values

### Page 1 — Executive Revenue & Sales Overview
- **Top KPI Cards (Reconciled Values):**
  - **Delivered Order Value Proxy (BRL):** **`R$ 15,422,461.77`** (Full Dataset) / **`R$ 15,375,875.44`** (Jan 2017 – Aug 2018 Window)
  - **Delivered Merchandise Revenue (BRL):** **`R$ 13,221,498.11`** (Full) / **`R$ 13,181,027.13`** (Window)
  - **Delivered Orders:** **`96,478`** (`96.48%` of `99,441` orders; `96,211` in Window)
  - **Average Order Value (BRL):** **`R$ 159.86`** (Median **`R$ 105.28`**)
  - **Unique Delivered Customers:** **`93,358`** (`93,104` in Window)
  - **True Repeat Customer Rate (Rule D-5):** **`2.16%`** (`2,015` customers; `2.15%` / `2,005` in Window)
  - **On-Time Delivery Rate:** **`91.89%`** (`8.11%` late by timestamp; `6.77%` late by calendar day)
- **Visuals:**
  1. **Combo Line & Clustered Column Chart:** `sales_month` (`2017-01` to `2018-08`), `order_value_proxy_brl` (bars, peaking in Nov 2017 at `R$ 1,153,528.05`) and `delivered_orders` (line, peaking at `7,289`).
  2. **Horizontal Bar Chart:** Top 10 Categories by `item_revenue_brl` (`health_beauty` #1 at `R$ 1,233,131.72`, `watches_gifts` #2 at `R$ 1,166,176.98`, `bed_bath_table` #3 at `R$ 1,023,434.76`).
  3. **Donut Chart:** Payment Value Share by Payment Method (`credit_card` `78.46%` / `R$ 12,101,094.88`, `boleto` `17.96%` / `R$ 2,769,932.58`, `voucher` `2.23%`, `debit_card` `1.35%`).
  4. **Stacked Bar Chart:** Order Funnel Status (`delivered` `96,478`, `shipped` `1,107`, `canceled` `625`, `unavailable` `609`, `invoiced` `314`, `processing` `301`, `created` `5`, `approved` `2`).

### Page 2 — Customer Retention, RFM & CLV Intelligence
- **Visuals & Exact Reconciled Figures:**
  1. **Clustered Bar Chart (RFM Segments — `93,358` Customers, `R$ 15,422,461.77` Total):**
     - `Lost Customers`: **`37,358`** (`40.02%` customers | **`R$ 6,167,951.88`** | `39.99%` value)
     - `Recent Customers`: **`37,219`** (`39.87%` customers | **`R$ 6,269,299.23`** | `40.65%` value)
     - `Needs Attention`: **`18,272`** (`19.57%` customers | **`R$ 2,798,239.09`** | `18.14%` value)
     - `Potential Loyalists`: **`449`** (`0.48%` customers | **`R$ 147,286.12`** | `0.96%` value | avg `R$ 328.03`)
     - `Champions`: **`23`** (`0.02%` customers | **`R$ 19,684.50`** | `0.13%` value | avg `R$ 855.85`)
     - `At Risk`: **`31`** (`0.03%` customers | **`R$ 15,067.94`** | `0.10%` value | avg `R$ 486.06`)
     - `Loyal Customers`: **`6`** (`0.01%` customers | **`R$ 4,933.01`** | `0.03%` value | avg `R$ 822.17`)
  2. **Matrix Heatmap (Cohort Retention):** `cohort_month` (`2017-01` to `2018-08`) on rows, `m1_pct` through `m12_pct` on columns (`M+1` peaks at `0.72%` in `2017-10`).
  3. **Comparison Table (CLV Proxy by Repeat Tier):**
     - `1. True Repeat Customer (D-5: 2+ Orders, 2+ Days)`: `2,015` customers (`2.16%`), **`R$ 320.82`** avg historical CLV (`R$ 646,454.25` total).
     - `2. Same-Day Multi-Order (Split Basket: 2+ Orders, 1 Day)`: `786` customers (`0.84%`), **`R$ 277.23`** avg historical CLV (`R$ 217,902.96` total).
     - `3. Single-Order Customer (1 Delivered Order)`: `90,557` customers (`97.00%`), **`R$ 160.76`** avg historical CLV (`R$ 14,558,104.56` total).

### Page 3 — Product, Category & Seller Performance
- **Visuals:**
  1. **Pareto Combo Chart:** Category `item_revenue_brl` (`SUM(price)`) and cumulative % share (Top 5 categories = `39.83%`; Top 18 of 74 categories = `81.30%`).
  2. **Seller Decile Concentration Chart:** Top 10% of active sellers (`297` of `2,970` sellers, Decile 1) generate **`67.11%`** (`R$ 8,873,076.37`) of delivered merchandise revenue; Top 20% (`594` sellers, Deciles 1–2) generate **`82.29%`** (`R$ 10,879,659.64`).
  3. **Top Sellers Matrix Table:** `seller_id`, `seller_state`, `delivered_orders`, `item_revenue_brl`, `late_delivery_rate_pct`, `avg_review_score`.

### Page 4 — Delivery Logistics & Customer Experience
- **Top KPI Cards:**
  - **Average Delivery Time:** **`12.56 days`** (On-Time: `10.88 days` vs Late: `31.52 days`)
  - **On-Time Delivery Rate:** **`91.89%`** (`88,644` orders) vs **Late Rate:** **`8.11%`** (`7,826` orders)
  - **Average Review Score:** **`4.16 ★`** overall (On-Time **`4.29 ★`** vs Late **`2.57 ★`**, `-1.72 ★` drop, $p < 0.0001$)
- **Visuals:**
  1. **Delivery Timing Bucket vs Review Score & 1-Star Share Chart:** Shows sharp satisfaction cliff from `4.32 ★` (`8+ days early`, `6.47%` 1-star) down to `1.70 ★` (`8+ days late`, where **`69.87%`** of reviews are 1-star).
  2. **State Logistics Comparison:** `SP` (`40,501` orders, `5.89%` late, `8.76` days, `4.25 ★`) vs `RJ` (`12,350` orders, `13.47%` late, `15.31` days, `3.97 ★`), `BA` (`14.04%` late, `3.86 ★`), `AL` (`23.93%` late, `3.85 ★`), and `MA` (`19.67%` late, `3.83 ★`).
