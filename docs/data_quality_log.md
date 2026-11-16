# Data Quality Log — Phase 3 Assessment

**Generated from:** [`src/cleaning/quality_assessment.py`](../src/cleaning/quality_assessment.py)
**Machine-readable results:** [`reports/data_quality/phase3_quality_results.json`](../reports/data_quality/phase3_quality_results.json)
**Independent cross-check:** [`src/cleaning/verify_quality_findings.py`](../src/cleaning/verify_quality_findings.py). **10/10 checks passed.**
**Raw file immutability:** We computed SHA-256 hashes of all 9 raw files before and after the run. They were identical (`raw_files_unchanged: true`).

> Every number in this document is copied from the JSON output above. Nothing has been estimated or invented.
> **No records have been deleted or modified.** The treatments below are *proposals* that need approval (see [proposed_cleaning_plan.md](proposed_cleaning_plan.md)).

---

## 1. Classification Scheme

| Class | Meaning |
|-------|---------|
| **ERROR** | Confirmed data error: the value is impossible or contradicts another field |
| **BUSINESS** | Expected business or system condition: the value looks unusual but is valid |
| **MISSING-OK** | Legitimately missing: the value does not exist yet or is optional |
| **FLAG** | Analytical caveat or statistical outlier: the value is not an error but affects interpretation |

Severity reflects **impact on this project's business questions**: High / Medium / Low / Info.

---

## 2. Primary-Key Uniqueness (measured)

| Table | Key | Rows | Distinct keys | Unique? |
|-------|-----|-----:|--------------:|:-------:|
| orders | order_id | 99,441 | 99,441 | ✅ |
| customers | customer_id | 99,441 | 99,441 | ✅ |
| order_items | (order_id, order_item_id) | 112,650 | 112,650 | ✅ |
| order_payments | (order_id, payment_sequential) | 103,886 | 103,886 | ✅ |
| order_reviews | review_id | 99,224 | 98,410 | ❌ (see DQ-01) |
| order_reviews | (review_id, order_id) | 99,224 | 99,224 | ✅ |
| products | product_id | 32,951 | 32,951 | ✅ |
| sellers | seller_id | 3,095 | 3,095 | ✅ |
| category_translation | product_category_name | 71 | 71 | ✅ |
| geolocation | zip_code_prefix | 1,000,163 | 19,015 | ❌ by design (lookup, see DQ-26) |

No primary-key column contains nulls. `order_item_id` has no gaps within any order (sequence 1..n is complete).

## 3. Foreign-Key Integrity (measured)

| Relationship | Child rows | Orphan rows | Result |
|--------------|-----------:|------------:|:------:|
| orders.customer_id → customers | 99,441 | 0 | ✅ |
| order_items.order_id → orders | 112,650 | 0 | ✅ |
| order_items.product_id → products | 112,650 | 0 | ✅ |
| order_items.seller_id → sellers | 112,650 | 0 | ✅ |
| payments.order_id → orders | 103,886 | 0 | ✅ |
| reviews.order_id → orders | 99,224 | 0 | ✅ |
| products.category → translation | 32,951 (610 null) | 13 (2 categories) | ⚠ DQ-21 |
| customers.zip → geolocation | 99,441 | 278 (157 zips) | ⚠ DQ-30 |
| sellers.zip → geolocation | 3,095 | 7 (7 zips) | ⚠ DQ-30 |

**Coverage (parent rows without child rows):**

| Check | Rows | % |
|-------|-----:|--:|
| Orders without items | 775 | 0.78% |
| Orders without payments | 1 | 0.001% |
| Orders without reviews | 768 | 0.77% |
| Customers without orders | 0 | 0% |
| Products never sold | 0 | 0% |
| Sellers never sold | 0 | 0% |

---

## 4. Issue Register

### 4.1 Confirmed data errors

| ID | Table | Issue | Affected | Severity | Business impact | Proposed treatment | Validation |
|----|-------|-------|---------:|:--------:|-----------------|--------------------|------------|
| DQ-07 | orders | Status `delivered` but `order_delivered_customer_date` is null | 8 orders | Low | These 8 cannot be included in delivery-time or delay metrics | Keep. Flag `missing_delivery_date`. Exclude only from delivery-time metrics; keep in revenue | Flag count = 8 |
| DQ-08 | orders | Status `delivered` but carrier date null (2) or `order_approved_at` null (14) | 2 / 14 orders | Low | Affects the matching stage-duration metrics only | Keep. Flag. Exclude from the affected stage metric only | Flag counts = 2 / 14 |
| DQ-09 | orders | Status `canceled` but a customer delivery date exists | 6 orders | Low | Status and dates conflict | Keep status as recorded. Flag `status_date_conflict`. Status-based metrics treat them as canceled | Flag count = 6 |
| DQ-12 | orders | Carrier handoff timestamp is **before** purchase timestamp | 166 orders | Low | This is impossible, so carrier-stage durations for these orders are invalid | Flag `chronology_issue`. Exclude from purchase→carrier metrics | Flag count = 166 |
| DQ-13 | orders | Customer delivery is **before** carrier handoff | 23 orders (median gap 39.9 h) | Low | carrier→customer duration is invalid | Flag. Exclude from carrier→customer metric | Flag count = 23 |
| DQ-14 | payments | One order has no payment record: `bfbd0f9bdef84302105ad712db648a6c` (status delivered, purchased 2016-09-15, 3 items, price 134.97, freight 8.49, has a review) | 1 order | Low | Payment-based revenue understates this order's value by 143.46 BRL | Keep the order. Leave payment value **NULL, not 0**. Item-based metrics still include it | Order present in order-level table with null payment |
| DQ-19 | payments | `payment_installments = 0` on credit_card rows (the minimum should be 1) | 2 rows | Low | Negligible | Keep raw value. Treat as unknown in installment analysis | Count = 2 |
| DQ-21 | products / translation | 2 categories have no English translation: `pc_gamer` (3 products, 9 item rows, 1,545.95 BRL) and `portateis_cozinha_e_preparadores_de_alimentos` (10 products, 15 item rows, 3,968.53 BRL) | 13 products | Low | These categories would show as blank in English reports | Add a **documented supplementary mapping** in `data/external/` (the original file is not edited) | 0 untranslated categories after mapping |
| DQ-23 | products | `product_weight_g = 0` | 4 products | Low | Weight-based freight analysis only | Flag. Exclude from weight analyses | Count = 4 |
| DQ-24 | order_items | `shipping_limit_date` is implausibly far after purchase. The 4 rows dated 2020 come from 3 orders purchased in 2017 (about 1,056 days later). 12 rows are > 60 days after purchase. | 4 rows (2020); 12 rows (> 60 d) | Low | Would distort any seller shipping-deadline (SLA) metric. Not used in core revenue KPIs | Keep. Flag `shipping_limit_outlier` when > 60 days after purchase | Flag count = 12 |
| DQ-25 | reviews | Review creation date is earlier than the order purchase date | 64 reviews | Low | This is impossible timing. Review-timing analysis would be wrong | Keep the score. Flag. Exclude from review-timing analysis only | Count = 64 |
| DQ-27 | geolocation | Coordinates outside Brazil's bounding box (lat −33.75..5.27, lng −73.99..−34.79) | 42 rows | Low | Would distort map positions | Exclude these rows when computing zip-code centroids. Raw file unchanged | Derived lookup contains no out-of-box coordinates |
| DQ-28 | geolocation | One zip prefix maps to more than one state | 8 zips | Low | Ambiguous state assignment | Use the most frequent state per zip | Derived lookup has 1 state per zip |
| DQ-29 | geolocation / sellers | City names are spelled inconsistently (case and accents). Geolocation has 8,011 distinct raw names but 5,965 after lowercasing and removing accents. Sellers drop from 611 to 606. Customers stay at 4,119. | — | Low | City-level grouping would split the same city into several rows | Add a derived `city_normalised` column. Prefer **state-level** geography for reporting | Distinct counts match the normalised figures |

### 4.2 Expected business or system conditions

| ID | Table | Finding | Affected | Severity | Business impact | Proposed treatment | Validation |
|----|-------|---------|---------:|:--------:|-----------------|--------------------|------------|
| DQ-01 | reviews | **Repeated `review_id` values are NOT invalid duplicates.** 789 review_ids cover 1,603 rows (764 appear twice, 25 three times). For **all 789**: each row has a *different* order_id, identical score, title, message and timestamps, and the *same* customer_unique_id. 254 of them share the same purchase timestamp. This pattern shows one customer review linked to several of that customer's orders. There are 0 exact duplicate rows. | 789 ids / 1,603 rows | Low | Counting rows would over-count *reviews* by 814 (99,224 − 98,410). Order-level analysis is unaffected | Keep all rows. Use composite key **(review_id, order_id)**. Count distinct review_id for review-level metrics | Composite key unique: 99,224 = 99,224 |
| DQ-02 | reviews | Orders with more than one review: 547 (543 with 2, 4 with 3). **202 of them have different scores.** | 547 orders | Medium | Joining reviews to orders without aggregating first would duplicate order rows and revenue | Aggregate to one row per order **before** joining (rule in §5). Flag `has_multiple_reviews` | Review aggregate has 98,673 rows = distinct reviewed orders |
| DQ-04 | customers | `customer_id` is **one per order**: 99,441 distinct, never repeated in orders. `customer_unique_id` is the real person: 96,096 distinct. 93,099 unique_ids have 1 customer_id; the maximum is 17. | 96,096 customers | **High** | Using `customer_id` would make repeat-purchase rate **0%** by construction | Use **`customer_unique_id`** for all customer, retention, RFM and cohort analysis | orders↔customers join is 1:1 (validated). Unique-id count = 96,096 |
| DQ-04b | customers | 2,997 unique customers have 2+ orders (any status). 2,801 have 2+ **delivered** orders. **848 of the 2,997 placed all their orders on the same calendar day.** | 2,997 | **High** | Same-day multiple orders may be a split basket, not a returning customer. The definition chosen changes the repeat rate | Decision required (see cleaning plan D-5) | Counts reproduced by the cross-check |
| DQ-05 | customers | 39 unique customers appear in more than one state | 39 | Low | Customer geography is ambiguous for these people | Order geography: use that order's address. Customer geography: use the most recent order's state | Count = 39 |
| DQ-15 | orders | 775 orders have no item rows: unavailable 603, canceled 164, created 5, invoiced 2, shipped 1 | 775 | Medium | Payments of **162,591.95 BRL** belong to orders with no items. This is total payments 16,008,872.12 minus payments on orders that have items, 15,846,280.17. | Keep. Flag `has_items`. Product metrics exclude them naturally. Revenue definition must exclude canceled/unavailable orders (decision D-1) | Arithmetic reconciles exactly (§6) |
| DQ-16 | payments vs items | For orders with both, `SUM(payment_value)` ≠ `SUM(price + freight)` in 303 of 98,665 orders (> 0.01 BRL). 249 differ by > 1 BRL: 232 paid more, 17 paid less. Net difference: +2,870.39 BRL. 98,362 orders (99.69%) reconcile to the cent. | 303 orders | Medium | Payment value and item value are **different revenue measures**. The cause of the differences (e.g., installment interest, vouchers) is **not verifiable** from this data | Do not adjust any values. Define the revenue measures explicitly (decision D-1) | Cross-check passed (cents arithmetic) |
| DQ-17 | payments | `payment_type = not_defined`: 3 rows, all on canceled orders, total value 0.00 | 3 | Info | None once canceled orders are excluded | Keep | Count = 3 |
| DQ-18 | payments | `payment_value = 0`: 9 rows (6 voucher, 3 not_defined) | 9 | Info | A zero-value voucher is plausible | Keep | Count = 9 |
| DQ-26 | geolocation | 261,831 exact duplicate rows (26.18%). 738,332 rows remain after de-duplication, covering 19,015 zips. Each zip has many coordinates (median 29, max 1,146). | 1,000,163 | Medium | **Joining raw geolocation to orders would multiply rows.** | Never join the raw table. Build a derived **one-row-per-zip** lookup (median lat/lng, most frequent city/state) in `data/processed/` | Lookup rows = distinct zips. Order count unchanged after join |
| DQ-33 | order_items | Freight is higher than item price | 4,124 rows | Info | Typical for cheap or heavy items | Keep | — |

### 4.3 Legitimately missing values

| ID | Table | Finding | Affected | Severity | Treatment |
|----|-------|---------|---------:|:--------:|-----------|
| DQ-06 | orders | **2,965 null customer delivery dates are fully explained by status.** 2,957 belong to orders that are not delivered: shipped 1,107, canceled 619, unavailable 609, invoiced 314, processing 301, created 5, approved 2. Only 8 belong to delivered orders (DQ-07). | 2,957 | Info | Keep null. Delivery metrics use `status = delivered` only |
| DQ-10 | orders | Null `order_approved_at`: 141 canceled + 5 created (never approved) + 14 delivered (DQ-08) = 160 | 146 legitimate | Info | Keep null |
| DQ-03 | reviews | Orders with no review | 768 | Low | Keep. Review score is null. Excluded from review analyses only |
| DQ-34 | reviews | Comment title null 87,656 (88.34%). Comment message null 58,247 (58.70%). Both fields are optional. | — | Info | Keep. Text analysis is out of scope |
| DQ-20 | products | 610 products have no category. **All 610 also lack name, description and photo attributes**, which suggests the source omitted the whole record rather than random gaps. All 610 were sold: 1,603 item rows, 179,535.28 BRL, **1.32% of item price**. | 610 | Medium | Keep raw null. Derived category label = `unknown`. These products appear in category charts as "Unknown" |
| DQ-22 | products | 2 products have no physical dimensions (1 `bebes`, 1 with no category). Both were sold. | 2 | Low | Keep null. Exclude from size/weight analysis |
| DQ-30 | customers / sellers | Zip prefix not found in geolocation: 278 customer rows (157 zips) and 7 seller rows | 285 | Low | Keep. Lat/lng null. **State is still available** from the customer/seller table |

### 4.4 Analytical caveats and outliers (flag only, never removed)

| ID | Finding | Severity | Treatment |
|----|---------|:--------:|-----------|
| DQ-11 | Carrier handoff is recorded **before** payment approval in 1,359 orders (median 17.2 h earlier, max 4,109 h). The cause cannot be confirmed from this data. Purchase→customer-delivery has **0** violations. | Medium | Flag. Don't report approval→carrier duration for flagged orders. Headline delivery time uses purchase→customer delivery, which is unaffected |
| DQ-31 | **Sparse months at both ends of the period:** 2016-09 (4 orders), 2016-10 (324), **2016-11 (0, absent)**, 2016-12 (1), 2018-09 (16), 2018-10 (4). Months 2017-01 to 2018-08 have 800 to 7,544 orders each. | **High** | Trend and cohort charts would show artificial drops. Proposed analysis window: **2017-01 to 2018-08** for trends and cohorts (decision D-2). Later cohorts are also **right-censored**: they have less time to repeat. |
| DQ-32 | IQR outlier flags (1.5×IQR rule): item price 8,427 above the 277.40 fence (max 6,735.00). Freight 11,613 above the fence and 383 at zero. Payment value 7,981 above the fence (max 13,664.08). Delivery days 4,896 above the 29.15-day fence (median 10.2, max 209.6). Installments up to 24. Product weight up to 40,425 g. | Info | **No removal.** These are plausible business values (expensive goods, long-distance delivery). Report medians alongside means. Use robust quantile bins for RFM |

---

## 5. Grain & Aggregation Strategy (approved design rule for later phases)

```
order_items (112,650)   ──agg by order_id──►  order_item_summary (98,666)  ─┐
order_payments (103,886)──agg by order_id──►  order_payment_summary (99,440)├─ 1:1 LEFT JOIN ─► order-level table (99,441)
order_reviews (99,224)  ──agg by order_id──►  order_review_summary (98,673) ─┘          │
orders (99,441) ── 1:1 ── customers (99,441) ──► customer_unique_id ──agg──► customer-level table (96,096)
```

| Source | Aggregation to order level |
|--------|----------------------------|
| order_items | `item_count`, `SUM(price)`, `SUM(freight_value)`, distinct sellers, distinct products |
| order_payments | `SUM(payment_value)`, payment row count, `MAX(payment_installments)`, primary payment type = type with the largest value |
| order_reviews | Order score = **most recent review** (latest `review_answer_timestamp`), `review_count`, `has_multiple_reviews` flag. The mean score is kept as a sensitivity check |

**Rules:**
1. Never join items × payments × reviews directly. Aggregate each to `order_id` first.
2. Every join to `orders` must keep 99,441 rows (asserted with `validate="one_to_one"`).
3. Category, product and seller revenue are computed at **item grain using `price`**. Payments are never prorated to items.
4. Customer metrics group by `customer_unique_id`.
5. Geolocation is joined only through the derived one-row-per-zip lookup.

## 6. Revenue Reconciliation (measured)

| Measure | BRL |
|---------|----:|
| Total `payment_value`, all payment rows | 16,008,872.12 |
| Payments on orders that have items | 15,846,280.17 |
| → Payments on orders **without** items (canceled/unavailable etc.) | 162,591.95 |
| Total item `price` | 13,591,643.70 |
| Total item `freight_value` | 2,251,909.54 |
| Item price + freight, all items | 15,843,553.24 |
| Item price + freight on orders with payments | 15,843,409.78 |
| → Difference = order with no payment (DQ-14: 134.97 + 8.49) | 143.46 ✅ |

Both differences reconcile exactly to the issues identified above.

---

## 7. Corrections to Earlier Documentation

- **Phase 2 data dictionary** said the gap of 3,345 between `customer_id` and `customer_unique_id` "indicates the repeat-purchase population". That was imprecise. The measured number of unique customers with 2+ orders is **2,997** (2,801 with 2+ delivered orders). The dictionary has been corrected.
- **Phase 2** described the review grain as "~1 per order". The correct grain is **one row per (review_id, order_id)** pair.
