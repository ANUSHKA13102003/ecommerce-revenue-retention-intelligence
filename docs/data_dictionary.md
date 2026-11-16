# Data Dictionary

## Overview

This document describes every table and column in the Olist Brazilian E-Commerce dataset, as measured from the actual downloaded CSV files.

**Source:** [Olist Brazilian E-Commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
**Licence:** CC BY-NC-SA 4.0
**Date range:** 2016-09-04 to 2018-10-17 (based on order_purchase_timestamp)
**Total records across all files:** 1,550,922

---

## Source Tables

### 1. olist_orders_dataset.csv

**Grain:** One row per order.
**Rows:** 99,441 | **Columns:** 8 | **Duplicates:** 0 | **File size:** 16.84 MB

| Column | Pandas Dtype | Unique | Missing | Missing % | Description |
|--------|-------------|--------|---------|-----------|-------------|
| order_id | object (str) | 99,441 | 0 | 0.00% | Unique order identifier |
| customer_id | object (str) | 99,441 | 0 | 0.00% | FK to customers table (one per order) |
| order_status | object (str) | 8 | 0 | 0.00% | Order status (delivered, shipped, etc.) |
| order_purchase_timestamp | object (str) | 98,875 | 0 | 0.00% | Purchase timestamp |
| order_approved_at | object (str) | 90,733 | 160 | 0.16% | Payment approval timestamp |
| order_delivered_carrier_date | object (str) | 81,018 | 1,783 | 1.79% | Carrier handoff timestamp |
| order_delivered_customer_date | object (str) | 95,664 | 2,965 | 2.98% | Customer delivery timestamp |
| order_estimated_delivery_date | object (str) | 459 | 0 | 0.00% | Estimated delivery date |

**Date ranges:**
- order_purchase_timestamp: 2016-09-04 21:15:19 → 2018-10-17 17:30:18
- order_approved_at: 2016-09-15 12:16:38 → 2018-09-03 17:40:06
- order_delivered_carrier_date: 2016-10-08 10:34:01 → 2018-09-11 19:48:28
- order_delivered_customer_date: 2016-10-11 13:46:32 → 2018-10-17 13:22:46
- order_estimated_delivery_date: 2016-09-30 00:00:00 → 2018-11-12 00:00:00

---

### 2. olist_customers_dataset.csv

**Grain:** One row per customer_id (order-level; use customer_unique_id for true customer identity).
**Rows:** 99,441 | **Columns:** 5 | **Duplicates:** 0 | **File size:** 8.62 MB

| Column | Pandas Dtype | Unique | Missing | Missing % | Description |
|--------|-------------|--------|---------|-----------|-------------|
| customer_id | object (str) | 99,441 | 0 | 0.00% | Unique per order — FK to orders |
| customer_unique_id | object (str) | 96,096 | 0 | 0.00% | True unique customer identifier |
| customer_zip_code_prefix | int64 | 14,994 | 0 | 0.00% | Customer ZIP code (first 5 digits) |
| customer_city | object (str) | 4,119 | 0 | 0.00% | Customer city |
| customer_state | object (str) | 27 | 0 | 0.00% | Customer state (2-letter code) |

> **Important (corrected in Phase 3):** `customer_id` is generated **per order**: 99,441 unique values, and none is repeated in the orders table. `customer_unique_id` (96,096 unique) identifies the actual customer and **must be used for retention analysis**. Measured in Phase 3: 2,997 unique customers have 2+ orders (any status); 2,801 have 2+ delivered orders; 848 of the 2,997 placed all orders on the same day. See DQ-04 in [data_quality_log.md](data_quality_log.md).

---

### 3. olist_order_items_dataset.csv

**Grain:** One row per order-item (an order can have multiple items).
**Rows:** 112,650 | **Columns:** 7 | **Duplicates:** 0 | **File size:** 14.72 MB

| Column | Pandas Dtype | Unique | Missing | Missing % | Description |
|--------|-------------|--------|---------|-----------|-------------|
| order_id | object (str) | 98,666 | 0 | 0.00% | FK to orders |
| order_item_id | int64 | 21 | 0 | 0.00% | Sequential item number within order |
| product_id | object (str) | 32,951 | 0 | 0.00% | FK to products |
| seller_id | object (str) | 3,095 | 0 | 0.00% | FK to sellers |
| shipping_limit_date | object (str) | 93,318 | 0 | 0.00% | Seller shipping deadline |
| price | float64 | 5,968 | 0 | 0.00% | Item price (BRL) |
| freight_value | float64 | 6,999 | 0 | 0.00% | Item freight value (BRL) |

**Date range:** shipping_limit_date: 2016-09-19 → 2020-04-09 (note: extends beyond order dates)

> **Important:** 112,650 item rows vs. 99,441 orders → ~1.13 items per order on average. Some orders have up to 21 items.

---

### 4. olist_order_payments_dataset.csv

**Grain:** One row per payment transaction (an order can have multiple payment methods/installments).
**Rows:** 103,886 | **Columns:** 5 | **Duplicates:** 0 | **File size:** 5.51 MB

| Column | Pandas Dtype | Unique | Missing | Missing % | Description |
|--------|-------------|--------|---------|-----------|-------------|
| order_id | object (str) | 99,440 | 0 | 0.00% | FK to orders |
| payment_sequential | int64 | 29 | 0 | 0.00% | Sequential payment number |
| payment_type | object (str) | 5 | 0 | 0.00% | Payment method |
| payment_installments | int64 | 24 | 0 | 0.00% | Number of installments |
| payment_value | float64 | 29,077 | 0 | 0.00% | Payment amount (BRL) |

> **Important:** 103,886 payment rows vs. 99,441 orders → some orders have multiple payment records. 99,440 unique order_ids here (1 less than orders table — to investigate in Phase 3).

---

### 5. olist_order_reviews_dataset.csv

**Grain:** One row per review (an order can have multiple reviews).
**Rows:** 99,224 | **Columns:** 7 | **Duplicates:** 0 | **File size:** 13.78 MB

| Column | Pandas Dtype | Unique | Missing | Missing % | Description |
|--------|-------------|--------|---------|-----------|-------------|
| review_id | object (str) | 98,410 | 0 | 0.00% | Review identifier |
| order_id | object (str) | 98,673 | 0 | 0.00% | FK to orders |
| review_score | int64 | 5 | 0 | 0.00% | Score (1–5) |
| review_comment_title | object (str) | 4,527 | 87,656 | 88.34% | Optional title |
| review_comment_message | object (str) | 36,159 | 58,247 | 58.70% | Optional comment text |
| review_creation_date | object (str) | 636 | 0 | 0.00% | Review creation date |
| review_answer_timestamp | object (str) | 98,248 | 0 | 0.00% | Response timestamp |

**Date range:**
- review_creation_date: 2016-10-02 → 2018-08-31
- review_answer_timestamp: 2016-10-07 → 2018-10-29

> **Note:** High missing rates for review_comment_title (88.34%) and review_comment_message (58.70%) are expected — most reviewers leave only a star rating.

---

### 6. olist_products_dataset.csv

**Grain:** One row per product.
**Rows:** 32,951 | **Columns:** 9 | **Duplicates:** 0 | **File size:** 2.27 MB

| Column | Pandas Dtype | Unique | Missing | Missing % | Description |
|--------|-------------|--------|---------|-----------|-------------|
| product_id | object (str) | 32,951 | 0 | 0.00% | Unique product identifier |
| product_category_name | object (str) | 73 | 610 | 1.85% | Category (Portuguese) |
| product_name_lenght | float64 | 66 | 610 | 1.85% | Name character length |
| product_description_lenght | float64 | 2,960 | 610 | 1.85% | Description character length |
| product_photos_qty | float64 | 19 | 610 | 1.85% | Number of photos |
| product_weight_g | float64 | 2,204 | 2 | 0.01% | Weight in grams |
| product_length_cm | float64 | 99 | 2 | 0.01% | Length in centimetres |
| product_height_cm | float64 | 102 | 2 | 0.01% | Height in centimetres |
| product_width_cm | float64 | 95 | 2 | 0.01% | Width in centimetres |

> **Note:** 610 products missing category and text-metadata (1.85%). 2 products missing physical dimensions.

---

### 7. olist_sellers_dataset.csv

**Grain:** One row per seller.
**Rows:** 3,095 | **Columns:** 4 | **Duplicates:** 0 | **File size:** 0.17 MB

| Column | Pandas Dtype | Unique | Missing | Missing % | Description |
|--------|-------------|--------|---------|-----------|-------------|
| seller_id | object (str) | 3,095 | 0 | 0.00% | Unique seller identifier |
| seller_zip_code_prefix | int64 | 2,246 | 0 | 0.00% | Seller ZIP (first 5 digits) |
| seller_city | object (str) | 611 | 0 | 0.00% | Seller city |
| seller_state | object (str) | 23 | 0 | 0.00% | Seller state |

---

### 8. olist_geolocation_dataset.csv

**Grain:** Multiple rows per ZIP code (different lat/lng points within ZIP area).
**Rows:** 1,000,163 | **Columns:** 5 | **Duplicates:** 261,831 (26.18%) | **File size:** 58.44 MB

| Column | Pandas Dtype | Unique | Missing | Missing % | Description |
|--------|-------------|--------|---------|-----------|-------------|
| geolocation_zip_code_prefix | int64 | 19,015 | 0 | 0.00% | ZIP code prefix |
| geolocation_lat | float64 | 717,372 | 0 | 0.00% | Latitude |
| geolocation_lng | float64 | 717,615 | 0 | 0.00% | Longitude |
| geolocation_city | object (str) | 8,011 | 0 | 0.00% | City name |
| geolocation_state | object (str) | 27 | 0 | 0.00% | State code |

> **Warning:** 261,831 fully duplicate rows (26.18%). This table has many-to-one relationship with ZIP codes. Quality issues to be investigated in Phase 3.

---

### 9. product_category_name_translation.csv

**Grain:** One row per product category.
**Rows:** 71 | **Columns:** 2 | **Duplicates:** 0 | **File size:** 2.6 KB

| Column | Pandas Dtype | Unique | Missing | Missing % | Description |
|--------|-------------|--------|---------|-----------|-------------|
| product_category_name | object (str) | 71 | 0 | 0.00% | Category name (Portuguese) |
| product_category_name_english | object (str) | 71 | 0 | 0.00% | Category name (English) |

> **Note:** Products table has 73 unique categories, translation table has 71 → 2 categories may be untranslated (to verify in Phase 3).

---

## Grain Summary (Critical for Joins)

| Table | Grain | PK Candidate | Rows |
|-------|-------|-------------|------|
| orders | 1 row per order | order_id | 99,441 |
| customers | 1 row per customer_id | customer_id | 99,441 |
| order_items | 1 row per order-item | (order_id, order_item_id) | 112,650 |
| order_payments | 1 row per payment | (order_id, payment_sequential) | 103,886 |
| order_reviews | 1 row per (review_id, order_id); 1 review can link to several orders of the same customer | (review_id, order_id) | 99,224 |
| products | 1 row per product | product_id | 32,951 |
| sellers | 1 row per seller | seller_id | 3,095 |
| geolocation | Multiple rows per ZIP | (none — lookup table) | 1,000,163 |
| category_translation | 1 row per category | product_category_name | 71 |

> **⚠ Aggregation Warning:** Orders, items, and payments have DIFFERENT grains. Joining items × payments without pre-aggregation will multiply values incorrectly. Always aggregate to order level before cross-table joins.

---

## Star Schema Tables (Phase 4)

*To be created in Phase 4.*
