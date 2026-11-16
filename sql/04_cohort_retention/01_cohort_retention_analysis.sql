-- ============================================================
-- PROJECT: E-COMMERCE REVENUE & CUSTOMER RETENTION INTELLIGENCE
-- ANALYSIS 08 & 09: MONTHLY COHORT CUSTOMER RETENTION MATRIX
-- DATABASE: ecommerce_analytics
--
-- BUSINESS RULE (D-2 & D-5):
-- Analysis window: January 2017 to August 2018 (in_analysis_window = 1).
-- Cohort month = Month of customer_unique_id's first delivered order.
-- Active in month m = customer placed at least 1 delivered order in month m.
-- For month index 0 (M0), retention is 100.00%.
-- ============================================================
USE ecommerce_analytics;

-- 1. Long-Format Cohort Retention Table (Cohort Month x Period Index)
WITH delivered_window AS (
    SELECT
        customer_unique_id,
        order_id,
        DATE(order_purchase_timestamp) AS purchase_date,
        DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS order_month,
        (YEAR(order_purchase_timestamp) * 12 + MONTH(order_purchase_timestamp)) AS order_month_num,
        COALESCE(payment_value, 0) AS payment_value
    FROM order_level
    WHERE is_delivered = 1
        AND in_analysis_window = 1
        AND customer_unique_id IS NOT NULL
),
customer_cohort AS (
    SELECT
        customer_unique_id,
        MIN(order_month) AS cohort_month,
        MIN(order_month_num) AS cohort_month_num
    FROM delivered_window
    GROUP BY customer_unique_id
),
cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_unique_id) AS cohort_size
    FROM customer_cohort
    GROUP BY cohort_month
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        d.order_month,
        (d.order_month_num - c.cohort_month_num) AS month_index,
        COUNT(DISTINCT d.customer_unique_id) AS active_customers,
        COUNT(DISTINCT d.order_id) AS delivered_orders,
        ROUND(SUM(d.payment_value), 2) AS cohort_order_value_brl
    FROM delivered_window d
    INNER JOIN customer_cohort c
        ON d.customer_unique_id = c.customer_unique_id
    GROUP BY
        c.cohort_month,
        d.order_month,
        (d.order_month_num - c.cohort_month_num)
)
SELECT
    a.cohort_month,
    s.cohort_size,
    a.order_month,
    a.month_index,
    a.active_customers,
    ROUND(100.0 * a.active_customers / NULLIF(s.cohort_size, 0), 3) AS retention_rate_pct,
    a.delivered_orders,
    a.cohort_order_value_brl
FROM cohort_activity a
INNER JOIN cohort_sizes s
    ON a.cohort_month = s.cohort_month
ORDER BY a.cohort_month, a.month_index;

-- 2. Pivoted Monthly Cohort Retention Matrix (M0 to M12 Retention %)
WITH delivered_window AS (
    SELECT
        customer_unique_id,
        DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS order_month,
        (YEAR(order_purchase_timestamp) * 12 + MONTH(order_purchase_timestamp)) AS order_month_num
    FROM order_level
    WHERE is_delivered = 1
        AND in_analysis_window = 1
        AND customer_unique_id IS NOT NULL
),
customer_cohort AS (
    SELECT
        customer_unique_id,
        MIN(order_month) AS cohort_month,
        MIN(order_month_num) AS cohort_month_num
    FROM delivered_window
    GROUP BY customer_unique_id
),
cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_unique_id) AS cohort_size
    FROM customer_cohort
    GROUP BY cohort_month
),
cohort_activity AS (
    SELECT
        c.cohort_month,
        (d.order_month_num - c.cohort_month_num) AS month_index,
        COUNT(DISTINCT d.customer_unique_id) AS active_customers
    FROM delivered_window d
    INNER JOIN customer_cohort c
        ON d.customer_unique_id = c.customer_unique_id
    GROUP BY c.cohort_month, (d.order_month_num - c.cohort_month_num)
)
SELECT
    s.cohort_month,
    s.cohort_size,
    ROUND(100.0 * MAX(CASE WHEN a.month_index = 0 THEN a.active_customers ELSE 0 END) / s.cohort_size, 2) AS m0_pct,
    ROUND(100.0 * MAX(CASE WHEN a.month_index = 1 THEN a.active_customers ELSE 0 END) / s.cohort_size, 3) AS m1_pct,
    ROUND(100.0 * MAX(CASE WHEN a.month_index = 2 THEN a.active_customers ELSE 0 END) / s.cohort_size, 3) AS m2_pct,
    ROUND(100.0 * MAX(CASE WHEN a.month_index = 3 THEN a.active_customers ELSE 0 END) / s.cohort_size, 3) AS m3_pct,
    ROUND(100.0 * MAX(CASE WHEN a.month_index = 4 THEN a.active_customers ELSE 0 END) / s.cohort_size, 3) AS m4_pct,
    ROUND(100.0 * MAX(CASE WHEN a.month_index = 5 THEN a.active_customers ELSE 0 END) / s.cohort_size, 3) AS m5_pct,
    ROUND(100.0 * MAX(CASE WHEN a.month_index = 6 THEN a.active_customers ELSE 0 END) / s.cohort_size, 3) AS m6_pct,
    ROUND(100.0 * MAX(CASE WHEN a.month_index = 7 THEN a.active_customers ELSE 0 END) / s.cohort_size, 3) AS m7_pct,
    ROUND(100.0 * MAX(CASE WHEN a.month_index = 8 THEN a.active_customers ELSE 0 END) / s.cohort_size, 3) AS m8_pct,
    ROUND(100.0 * MAX(CASE WHEN a.month_index = 9 THEN a.active_customers ELSE 0 END) / s.cohort_size, 3) AS m9_pct,
    ROUND(100.0 * MAX(CASE WHEN a.month_index = 10 THEN a.active_customers ELSE 0 END) / s.cohort_size, 3) AS m10_pct,
    ROUND(100.0 * MAX(CASE WHEN a.month_index = 11 THEN a.active_customers ELSE 0 END) / s.cohort_size, 3) AS m11_pct,
    ROUND(100.0 * MAX(CASE WHEN a.month_index = 12 THEN a.active_customers ELSE 0 END) / s.cohort_size, 3) AS m12_pct
FROM cohort_sizes s
LEFT JOIN cohort_activity a
    ON s.cohort_month = a.cohort_month
GROUP BY s.cohort_month, s.cohort_size
ORDER BY s.cohort_month;

