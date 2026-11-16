# Proposed Cleaning Plan — AWAITING APPROVAL

> **Status: PROPOSED. Nothing in this plan has been executed.**
> Raw files in `data/raw/` stay unchanged. Every step creates **new derived tables** in `data/processed/`.
> Each rule references an issue ID in [data_quality_log.md](data_quality_log.md).

## Principles

1. **Non-destructive.** We add flag columns instead of deleting rows. Every derived table keeps the same row count as its raw source. The only exceptions are explicit aggregations, whose expected counts are listed below.
2. **Reversible.** Every derived table can be regenerated from the raw files with one script.
3. **Traceable.** Every flag column name maps to a DQ-ID.
4. **Validated.** After each step we assert the row count and run a key-uniqueness check.

## Step-by-step plan

| Step | Output (derived) | Rules applied | Expected rows | Validation |
|------|------------------|---------------|--------------:|------------|
| 1 | `orders_clean` | Parse dates. Add flags: `missing_delivery_date` (DQ-07), `missing_stage_date` (DQ-08), `status_date_conflict` (DQ-09), `carrier_before_purchase` (DQ-12), `carrier_before_approval` (DQ-11), `delivered_before_carrier` (DQ-13), `has_items` (DQ-15), `in_analysis_window` (DQ-31). Add derived `delivery_days` and `is_late` (only for delivered orders with a delivery date) | 99,441 | Row count; order_id unique; flag counts match log |
| 2 | `customers_clean` | Keep `customer_id` + `customer_unique_id`. Add `customer_city_normalised` (DQ-29) | 99,441 | Row count; customer_id unique |
| 3 | `order_items_clean` | Parse `shipping_limit_date`. Add flag `shipping_limit_outlier` (> 60 days after purchase, DQ-24) | 112,650 | Row count; composite PK unique; flag = 12 |
| 4 | `payments_clean` | Add flag `installments_invalid` (DQ-19) | 103,886 | Row count; composite PK unique |
| 5 | `reviews_clean` | Parse dates. Add `review_before_purchase` flag (DQ-25) | 99,224 | Row count; (review_id, order_id) unique |
| 6 | `products_clean` | Add `category_name_en`: translation table, then supplementary mapping for 2 categories (DQ-21), then `unknown` for null (DQ-20). Add flags `missing_dimensions` (DQ-22) and `zero_weight` (DQ-23) | 32,951 | Row count; 0 null `category_name_en` |
| 7 | `data/external/category_translation_supplement.csv` | 2 manual rows (see D-4) with source note | 2 | Exactly 2 rows; no overlap with the official translation file |
| 8 | `geolocation_zip_lookup` | Remove exact duplicates (DQ-26). Exclude out-of-bbox rows (DQ-27). One row per zip: median lat/lng, most frequent state and city (DQ-28). Normalised city (DQ-29) | 19,015 or slightly fewer, if a zip has only out-of-bbox rows (count will be reported) | zip unique; all coordinates inside the bbox |
| 9 | `order_item_summary` / `order_payment_summary` / `order_review_summary` | Aggregation rules from §5 of the log (DQ-02) | 98,666 / 99,440 / 98,673 | Key unique; sums equal raw sums (e.g., price total = 13,591,643.70) |
| 10 | `order_level` | `orders_clean` LEFT JOIN the 3 summaries + customer_unique_id | 99,441 | `validate="one_to_one"`; totals reconcile to §6 of the log |
| 11 | `data/processed/cleaning_log.json` | Run metadata: input hashes, output row counts, flag counts | — | Hashes match the Phase 3 hashes |

## Decisions needed from you

| ID | Decision | Options | Recommendation |
|----|----------|---------|----------------|
| **D-1** | **Primary revenue definition** (DQ-15, DQ-16) | (a) **Delivered-order item revenue** = `SUM(price)` for delivered orders. (b) GMV = `SUM(price + freight)` for delivered orders. (c) `SUM(payment_value)` for delivered orders. (d) Same as (a)–(c) but including all non-canceled/unavailable statuses | Primary KPI: **(c) payment value, delivered orders**, labelled "order value (revenue proxy)". Category/product/seller views use **(a) item price**, because payments cannot be split across items. Both definitions are documented. Note: Olist's *actual* revenue (commission) is not in the data |
| **D-2** | **Analysis window** for trends and cohorts (DQ-31) | (a) 2017-01 → 2018-08. (b) Full range | **(a)** for monthly trends and cohorts. Headline totals are reported for the full dataset with clear labels |
| **D-3** | **Order-level review score** when an order has multiple reviews (DQ-02) | (a) Most recent review. (b) Mean. (c) Minimum | **(a) most recent**, with (b) as a sensitivity check |
| **D-4** | **Supplementary translations** (DQ-21) | `pc_gamer` → `pc_gamer`; `portateis_cozinha_e_preparadores_de_alimentos` → `portable_kitchen_and_food_preparers` | Approve as proposed. The translation is manual and will be documented as such |
| **D-5** | **Repeat-customer definition** (DQ-04b) | (a) 2+ distinct **delivered** orders. (b) 2+ orders on **distinct purchase days**. (c) 2+ orders, any status | **(b) combined with delivered status**: excludes same-day split baskets. (a) and (c) are reported as sensitivity checks |
| **D-6** | **Inactivity (at-risk) window**: needed in Phase 5; can be decided later | e.g., 180 / 270 / 365 days since last purchase | Defer to Phase 5. It will be labelled an *analytical risk rule*, not observed churn |

## What will NOT be done

- No raw rows deleted. No raw values overwritten.
- No outliers removed (DQ-32 values are plausible business values).
- No imputation of missing dates, categories or dimensions with invented values.

