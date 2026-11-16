-- ============================================================
-- PROJECT: E-COMMERCE REVENUE & CUSTOMER RETENTION INTELLIGENCE
-- MODULE: RFM CUSTOMER SEGMENTATION
-- DATABASE: ecommerce_analytics
-- SOURCE TABLE: order_level
--
-- RFM DEFINITIONS:
-- Recency  = Days since the customer's latest delivered order
-- Frequency = Distinct delivered purchase days
-- Monetary = Total payment value of delivered orders (BRL)
--
-- IMPORTANT:
-- Payment value is used as an order-value proxy.
-- It is not Olist's actual commission revenue.
-- ============================================================
USE ecommerce_analytics;
-- Remove the previous output table before rebuilding
DROP TABLE IF EXISTS customer_rfm;
-- ============================================================
-- STEP 1: BUILD CUSTOMER RFM TABLE
-- ============================================================
CREATE TABLE customer_rfm AS WITH delivered_orders AS (
    SELECT customer_unique_id,
        order_id,
        DATE(order_purchase_timestamp) AS purchase_date,
        payment_value
    FROM order_level
    WHERE order_status = 'delivered'
        AND customer_unique_id IS NOT NULL
        AND order_purchase_timestamp IS NOT NULL
),
snapshot AS (
    SELECT MAX(purchase_date) AS snapshot_date
    FROM delivered_orders
),
customer_metrics AS (
    SELECT customer_unique_id,
        MAX(purchase_date) AS last_purchase_date,
        COUNT(DISTINCT purchase_date) AS frequency,
        ROUND(SUM(payment_value), 2) AS monetary
    FROM delivered_orders
    GROUP BY customer_unique_id
),
rfm_base AS (
    SELECT c.customer_unique_id,
        DATEDIFF(
            s.snapshot_date,
            c.last_purchase_date
        ) AS recency,
        c.frequency,
        c.monetary
    FROM customer_metrics c
        CROSS JOIN snapshot s
),
-- ============================================================
-- STEP 2: CALCULATE PERCENTILES
-- CUME_DIST keeps identical values together.
-- ============================================================
rfm_percentiles AS (
    SELECT *,
        CUME_DIST() OVER (
            ORDER BY recency ASC
        ) AS recency_pct,
        CUME_DIST() OVER (
            ORDER BY monetary ASC
        ) AS monetary_pct
    FROM rfm_base
),
-- ============================================================
-- STEP 3: ASSIGN RFM SCORES
-- ============================================================
rfm_scored AS (
    SELECT customer_unique_id,
        recency,
        frequency,
        monetary,
        -- Lower recency means a more recent purchase.
        CASE
            WHEN recency_pct <= 0.20 THEN 5
            WHEN recency_pct <= 0.40 THEN 4
            WHEN recency_pct <= 0.60 THEN 3
            WHEN recency_pct <= 0.80 THEN 2
            ELSE 1
        END AS r_score,
        -- Frequency uses fixed thresholds.
        -- Identical purchase-day counts receive identical scores.
        CASE
            WHEN frequency = 1 THEN 1
            WHEN frequency = 2 THEN 2
            WHEN frequency = 3 THEN 3
            WHEN frequency BETWEEN 4 AND 5 THEN 4
            ELSE 5
        END AS f_score,
        -- Higher monetary value means a higher score.
        CASE
            WHEN monetary_pct <= 0.20 THEN 1
            WHEN monetary_pct <= 0.40 THEN 2
            WHEN monetary_pct <= 0.60 THEN 3
            WHEN monetary_pct <= 0.80 THEN 4
            ELSE 5
        END AS m_score
    FROM rfm_percentiles
) -- ============================================================
-- STEP 4: CREATE FINAL CUSTOMER SEGMENTS
-- ============================================================
SELECT customer_unique_id,
    recency,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    CONCAT(
        r_score,
        f_score,
        m_score
    ) AS rfm_score,
    CASE
        WHEN r_score >= 4
        AND f_score >= 4
        AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3
        AND f_score >= 4 THEN 'Loyal Customers'
        WHEN r_score >= 4
        AND f_score <= 2 THEN 'Recent Customers'
        WHEN r_score >= 3
        AND f_score >= 2 THEN 'Potential Loyalists'
        WHEN r_score <= 2
        AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2
        AND f_score <= 2 THEN 'Lost Customers'
        ELSE 'Needs Attention'
    END AS customer_segment
FROM rfm_scored;
-- ============================================================
-- STEP 5: VALIDATE TOTAL CUSTOMER RECORDS
-- ============================================================
SELECT COUNT(*) AS total_customers
FROM customer_rfm;
-- ============================================================
-- STEP 6: CUSTOMER SEGMENT SUMMARY
-- ============================================================
SELECT customer_segment,
    COUNT(*) AS customer_count,
    ROUND(AVG(recency), 2) AS avg_recency_days,
    ROUND(AVG(frequency), 2) AS avg_purchase_days,
    ROUND(SUM(monetary), 2) AS total_order_value_brl
FROM customer_rfm
GROUP BY customer_segment
ORDER BY customer_count DESC;
-- ============================================================
-- STEP 7: VALIDATE FREQUENCY SCORE CONSISTENCY
-- Expected: zero inconsistent frequency values.
-- ============================================================
SELECT frequency,
    COUNT(*) AS customer_count,
    MIN(f_score) AS lowest_score,
    MAX(f_score) AS highest_score
FROM customer_rfm
GROUP BY frequency
ORDER BY frequency;
-- ============================================================
-- STEP 8: VALIDATE RECENCY SCORE CONSISTENCY
-- Expected: zero rows.
-- ============================================================
SELECT recency,
    COUNT(*) AS customer_count,
    MIN(r_score) AS lowest_score,
    MAX(r_score) AS highest_score
FROM customer_rfm
GROUP BY recency
HAVING MIN(r_score) <> MAX(r_score);
-- ============================================================
-- STEP 9: VALIDATE MONETARY SCORE CONSISTENCY
-- Expected: zero rows.
-- ============================================================
SELECT monetary,
    COUNT(*) AS customer_count,
    MIN(m_score) AS lowest_score,
    MAX(m_score) AS highest_score
FROM customer_rfm
GROUP BY monetary
HAVING MIN(m_score) <> MAX(m_score);
-- ============================================================
-- END OF RFM CUSTOMER SEGMENTATION
-- ============================================================