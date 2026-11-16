# Analytical Methodology & Governance Rules

## 1. Approved Business Governance Decisions (D-1 to D-6)

| Rule ID | Domain | Approved Methodology | Empirical Impact |
|---|---|---|---|
| **D-1** | **Revenue & Monetary Definitions** | Use `SUM(payment_value)` on delivered orders (`is_delivered = 1`) as **Delivered Order Value (Revenue Proxy)** (`R$ 15,422,461.77`). Use `SUM(price)` (`R$ 13,221,498.11` delivered) for product, category, and seller rankings. Track `freight_value` (`R$ 2,198,235.63` delivered) separately. | Prevents conflating total buyer checkout spend (`price + freight + installment interest`) with merchandise price or Olist's undisclosed marketplace commission. |
| **D-2** | **Time-Series & Cohort Window** | Restrict monthly growth trends and cohort retention matrices to **January 2017 – August 2018** (`in_analysis_window = 1`, `20` complete months, `96,211` delivered orders, `R$ 15,375,875.44`). | Eliminates artificial boundary cliff effects caused by sparse early data (`Sept–Dec 2016`: `267` delivered orders) and right-censored fulfillment (`Sept–Oct 2018`: `0` delivered orders). |
| **D-3** | **Order-Level Review Deduplication** | Deduplicate `reviews_clean` (`99,224` rows across `98,673` orders) to `1` row per `order_id` (`order_review_summary`) by selecting the most recent review (`review_answer_timestamp DESC, review_creation_date DESC, review_id DESC`). Retain `avg_review_score` as a sensitivity check. | Ensures `1:1` order grain when joining satisfaction scores to delivery delay metrics. |
| **D-4** | **Category Translation Governance** | Preserve original Portuguese category names (`product_category_name`). Join `71` official English translations plus `2` documented manual project mappings (`pc_gamer` -> `pc_gamer`, `portateis_cozinha_e_preparadores_de_alimentos` -> `portable_kitchen_and_food_preparers`). Map `610` products with `NULL` categories to `Unknown`. | Achieves `100%` category coverage across `32,951` unique products while maintaining full auditability (`translation_source`). |
| **D-5** | **Repeat Customer Definition** | Group by `customer_unique_id` (true customer identifier). Define a **True Repeat Customer** as having **$\ge 2$ distinct delivered orders placed on $\ge 2$ distinct calendar dates** (`2,015` customers / `2.16%` full dataset; `2,005` / `2.15%` in analysis window). Report Option (a) `2+` delivered orders any day (`2,801` / `3.00%`) and Option (c) `2+` orders all statuses (`2,997` / `3.12%`) as sensitivity checks. | Separates `786` same-day multi-order customers (`0.84%`) whose multiple `order_id`s result from Olist splitting multi-seller shopping carts at checkout rather than true return visits. |
| **D-6** | **Recency Inactivity vs. Churn** | Evaluate customer recency against the dataset's final delivered purchase snapshot (`2018-10-17`) using `90`, `180`, `270`, and `365`-day inactivity bands. Never label inactivity as observed contractual churn. | Respects the non-contractual nature of marketplace retail where customers can remain inactive for months without formally "churning." |

---

## 2. RFM Customer Segmentation Methodology

Implemented identically in SQL (`sql/03_customer_analytics/02_rfm_customer_segmentation.sql`) and Python (`src/database/execute_and_validate_sql.py`), evaluated across all **`93,358` unique delivered customers**:

1. **Base Metrics per `customer_unique_id`:**
   - **Recency (`recency_days`):** `DATEDIFF('2018-10-17', MAX(DATE(order_purchase_timestamp)))`
   - **Frequency (`purchase_days`):** `COUNT(DISTINCT DATE(order_purchase_timestamp))` (distinct delivered purchase dates, aligned with Rule D-5)
   - **Monetary (`monetary_value`):** `ROUND(SUM(payment_value), 2)` across delivered orders
2. **Scoring (`1` to `5`):**
   - **Recency Score (`r_score`):** Cumulative distribution (`CUME_DIST() OVER (ORDER BY recency_days ASC)`) bucketed into quintiles (`<=0.20` -> `5`, `<=0.40` -> `4`, `<=0.60` -> `3`, `<=0.80` -> `2`, `>0.80` -> `1`).
   - **Frequency Score (`f_score`):** Explicit rule-based scoring (`1` purchase day -> `1`; `2` purchase days -> `3`; `3` purchase days -> `4`; `4+` purchase days -> `5`) because `97.84%` of customers have exactly `1` purchase day, which would cause standard `NTILE(5)` to arbitrarily assign scores `1..5` to identical `frequency = 1` customers.
   - **Monetary Score (`m_score`):** Cumulative distribution (`CUME_DIST() OVER (ORDER BY monetary_value ASC)`) bucketed into quintiles (`<=0.20` -> `1` up to `>0.80` -> `5`).
3. **Segment Assignment Rules (`7` Segments):**
   - **Champions (`23` customers):** `r_score >= 4 AND f_score >= 4 AND m_score >= 4`
   - **Loyal Customers (`6` customers):** `r_score >= 3 AND f_score >= 4` (not Champions)
   - **Potential Loyalists (`449` customers):** `r_score >= 3 AND f_score = 3` (`2` distinct purchase days with recent/moderate recency)
   - **At Risk (`31` customers):** `r_score <= 2 AND f_score >= 4` (high-frequency repeat buyers who have not purchased recently)
   - **Recent Customers (`37,219` customers):** `r_score >= 4 AND f_score = 1`
   - **Needs Attention (`18,272` customers):** `r_score = 3 AND f_score = 1`
   - **Lost Customers (`37,358` customers):** `r_score <= 2 AND f_score <= 3`

---

## 3. Statistical Hypothesis Testing Methodology

To evaluate the operational impact of delivery delays on customer review scores (`95,824` delivered orders with both valid delivery timestamps and review scores):

- **Parametric Test:** Two-sample Welch's t-test (`scipy.stats.ttest_ind(..., equal_var=False)`) comparing review scores of On-Time (`Mean = 4.2936`, `n = 87,998`) vs. Late (`Mean = 2.5665`, `n = 7,826`) delivered orders ($t = 96.49, p < 0.0001$).
- **Non-Parametric Test:** Mann-Whitney U test (`scipy.stats.mannwhitneyu`) due to discrete ordinal `1–5` review scores ($U = 500,829,014.5, p < 0.0001$).
- **Correlation Analysis:** Spearman rank correlation ($\rho = -0.3054, p < 0.0001$) and Pearson linear correlation ($r = -0.3692, p < 0.0001$) between `delivery_delay_days` and `primary_review_score`.
