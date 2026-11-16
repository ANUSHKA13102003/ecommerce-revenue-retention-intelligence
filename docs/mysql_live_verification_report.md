# Live MySQL 8.0 Database Connection & Reconciliation Report

**Verified Timestamp:** `2026-11-16T16:28:02.403110`  
**MySQL Server Version:** `8.0.46` (`DESKTOP-DI8S09O:3306`)  
**Database:** `ecommerce_analytics`  
**Windows Service (`MySQL80`):** `RUNNING`  
**Overall Verification Status:** **FAIL**

---

## 1. Imported Table Row Count Verification (`14` Base Tables + `customer_rfm`)

| Table Name | Live MySQL Row Count | Expected Python CSV Row Count | Difference | Status |
| :--- | ---: | ---: | ---: | :---: |
| `customers_clean` | `99,441` | `99,441` | `0` | **PASS** |
| `customers_with_geolocation` | `99,441` | `99,441` | `0` | **PASS** |
| `geolocation_zip_lookup` | `17,737` | `19,015` | `-1278` | **FAIL** |
| `order_item_summary` | `98,666` | `98,666` | `0` | **PASS** |
| `order_items_clean` | `112,650` | `112,650` | `0` | **PASS** |
| `order_level` | `99,441` | `99,441` | `0` | **PASS** |
| `order_payment_summary` | `99,440` | `99,440` | `0` | **PASS** |
| `order_review_summary` | `98,673` | `98,673` | `0` | **PASS** |
| `orders_clean` | `99,441` | `99,441` | `0` | **PASS** |
| `payments_clean` | `103,886` | `103,886` | `0` | **PASS** |
| `products_clean` | `32,951` | `32,951` | `0` | **PASS** |
| `reviews_clean` | `99,224` | `99,224` | `0` | **PASS** |
| `sellers_clean` | `3,095` | `3,095` | `0` | **PASS** |
| `sellers_with_geolocation` | `3,095` | `3,095` | `0` | **PASS** |
| `customer_rfm (derived SQL table)` | `93,358` | `93,358` | `0` | **PASS** |

---

## 2. Live MySQL vs. Validated Python Metric Reconciliation (`22` Key Metrics)

| Metric | Live MySQL Query Result | Validated Python Result | Abs Diff | Status |
| :--- | ---: | ---: | ---: | :---: |
| **Total Orders (All Statuses)** | `99441` | `99441` | `0.0` | **PASS** |
| **Delivered Orders (Full Dataset)** | `96478` | `96478` | `0.0` | **PASS** |
| **Delivery Completion Rate (%)** | `97.02` | `97.02` | `0.0` | **PASS** |
| **Delivered Order Value Proxy (BRL, Full)** | `15422461.77` | `15422461.77` | `0.0` | **PASS** |
| **Delivered Merchandise Revenue (BRL, Full)** | `13221498.11` | `13221498.11` | `0.0` | **PASS** |
| **Delivered Freight Value (BRL, Full)** | `2198275.64` | `2198275.64` | `0.0` | **PASS** |
| **Gross Payment Value (All Statuses, BRL)** | `16008872.12` | `16008872.12` | `0.0` | **PASS** |
| **Mean Order Value Proxy (BRL)** | `159.86` | `159.86` | `0.0` | **PASS** |
| **Unique Customers (All Statuses)** | `96096` | `96096` | `0.0` | **PASS** |
| **Unique Delivered Customers (Full)** | `93358` | `93358` | `0.0` | **PASS** |
| **Window D-2 Delivered Orders (Jan 17–Aug 18)** | `96211` | `96211` | `0.0` | **PASS** |
| **Window D-2 Order Value Proxy (BRL)** | `15375875.44` | `15375875.44` | `0.0` | **PASS** |
| **Window D-2 Item Revenue (BRL)** | `13181027.13` | `13181027.13` | `0.0` | **PASS** |
| **True Repeat Customers (Rule D-5)** | `2015` | `2015` | `0.0` | **PASS** |
| **True Repeat Rate (Rule D-5, %)** | `2.16` | `2.16` | `0.0` | **PASS** |
| **Same-Day Split-Checkout Buyers** | `786` | `786` | `0.0` | **PASS** |
| **Any-Day Repeat Customers (Option A)** | `2801` | `2801` | `0.0` | **PASS** |
| **Repeat Customer Revenue Share (D-5, %)** | `4.19` | `4.19` | `0.0` | **PASS** |
| **Average Delivery Days** | `12.56` | `12.56` | `0.0` | **PASS** |
| **Late Delivery Rate (%)** | `8.11` | `8.11` | `0.0` | **PASS** |
| **Average Review Score (Delivered)** | `4.16` | `4.16` | `0.0` | **PASS** |
| **Top Category Item Revenue (health_beauty, BRL)** | `1233131.72` | `1233131.72` | `0.0` | **PASS** |

---

## 3. Live MySQL RFM Customer Segmentation Census (`customer_rfm`)

| Customer Segment | Customers | Avg Recency (Days) | Avg Purchase Days | Avg Monetary (BRL) | Total Monetary / Order Value Proxy (BRL) |
| :--- | ---: | ---: | ---: | ---: | ---: |
| **Recent Customers** | `37,219` | `89.85` | `1.03` | `R$ 168.44` | `R$ 6,269,299.23` |
| **Lost Customers** | `37,358` | `394.00` | `1.01` | `R$ 165.11` | `R$ 6,167,951.88` |
| **Needs Attention** | `18,272` | `219.17` | `1.00` | `R$ 153.14` | `R$ 2,798,239.09` |
| **Potential Loyalists** | `449` | `197.87` | `2.20` | `R$ 328.03` | `R$ 147,286.12` |
| **Champions** | `23` | `81.30` | `5.13` | `R$ 855.85` | `R$ 19,684.50` |
| **At Risk** | `31` | `335.35` | `3.06` | `R$ 486.06` | `R$ 15,067.94` |
| **Loyal Customers** | `6` | `210.50` | `5.17` | `R$ 822.17` | `R$ 4,933.01` |
