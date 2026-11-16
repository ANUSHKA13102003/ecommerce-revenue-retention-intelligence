-- ============================================================
-- PROJECT: E-COMMERCE REVENUE & CUSTOMER RETENTION INTELLIGENCE
-- ANALYSIS 11 & 12: DELIVERY PERFORMANCE & REVIEW SATISFACTION
-- DATABASE: ecommerce_analytics
--
-- BUSINESS RULE (D-3):
-- Primary order-level review score uses the most recent review per
-- order (stored in order_level / order_review_summary).
-- Delivery metrics are evaluated on delivered orders with non-null
-- customer delivery dates (96,470 orders; 8 delivered orders lack a
-- delivery date per DQ-07).
-- ============================================================
USE ecommerce_analytics;

-- 1. Overall Delivery & Review KPIs (Delivered Orders)
SELECT
    COUNT(*) AS total_delivered_orders,
    SUM(CASE WHEN missing_delivery_date = 0 THEN 1 ELSE 0 END) AS orders_with_delivery_date,
    SUM(CASE WHEN missing_delivery_date = 1 THEN 1 ELSE 0 END) AS orders_missing_delivery_date,
    SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END) AS late_delivered_orders,
    SUM(CASE WHEN missing_delivery_date = 0 AND is_late = 0 THEN 1 ELSE 0 END) AS on_time_delivered_orders,
    ROUND(
        100.0 * SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN missing_delivery_date = 0 THEN 1 ELSE 0 END), 0),
        2
    ) AS late_delivery_rate_pct,
    ROUND(
        100.0 * SUM(CASE WHEN missing_delivery_date = 0 AND is_late = 0 THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN missing_delivery_date = 0 THEN 1 ELSE 0 END), 0),
        2
    ) AS on_time_delivery_rate_pct,
    ROUND(AVG(delivery_days), 2) AS avg_delivery_days,
    ROUND(AVG(CASE WHEN is_late = 0 THEN delivery_days END), 2) AS avg_on_time_delivery_days,
    ROUND(AVG(CASE WHEN is_late = 1 THEN delivery_days END), 2) AS avg_late_delivery_days,
    ROUND(AVG(review_score), 2) AS overall_avg_review_score,
    ROUND(AVG(CASE WHEN is_late = 0 AND missing_delivery_date = 0 THEN review_score END), 2) AS on_time_avg_review_score,
    ROUND(AVG(CASE WHEN is_late = 1 THEN review_score END), 2) AS late_avg_review_score
FROM order_level
WHERE is_delivered = 1;

-- 2. Delivery Delay Buckets vs Review Scores & Satisfaction Breakdown
WITH delivery_classified AS (
    SELECT
        order_id,
        payment_value,
        delivery_days,
        DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) AS delay_days,
        is_late,
        review_score,
        CASE
            WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) <= -8 THEN '1. Early (8+ days early)'
            WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) BETWEEN -7 AND -1 THEN '2. Early (1-7 days early)'
            WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) = 0 THEN '3. On Estimated Date (0 days)'
            WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) BETWEEN 1 AND 3 THEN '4. Slightly Late (1-3 days)'
            WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) BETWEEN 4 AND 7 THEN '5. Moderately Late (4-7 days)'
            ELSE '6. Severely Late (8+ days)'
        END AS delivery_timing_bucket
    FROM order_level
    WHERE is_delivered = 1
        AND missing_delivery_date = 0
        AND order_estimated_delivery_date IS NOT NULL
)
SELECT
    delivery_timing_bucket,
    COUNT(*) AS delivered_orders,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS order_share_pct,
    ROUND(AVG(delivery_days), 2) AS avg_actual_delivery_days,
    ROUND(AVG(delay_days), 2) AS avg_days_vs_estimate,
    ROUND(AVG(review_score), 2) AS avg_review_score,
    ROUND(
        100.0 * SUM(CASE WHEN review_score = 1 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(review_score), 0),
        2
    ) AS one_star_share_pct,
    ROUND(
        100.0 * SUM(CASE WHEN review_score = 5 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(review_score), 0),
        2
    ) AS five_star_share_pct,
    ROUND(SUM(payment_value), 2) AS order_value_proxy_brl
FROM delivery_classified
GROUP BY delivery_timing_bucket
ORDER BY delivery_timing_bucket;

-- 3. Review Score Distribution (1 to 5 Stars) with Delivery & Order Metrics
SELECT
    review_score,
    COUNT(*) AS delivered_orders,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS share_of_reviewed_orders_pct,
    ROUND(AVG(delivery_days), 2) AS avg_delivery_days,
    ROUND(100.0 * AVG(CASE WHEN is_late = 1 THEN 1.0 ELSE 0.0 END), 2) AS late_delivery_rate_pct,
    ROUND(AVG(payment_value), 2) AS avg_order_value_brl,
    ROUND(SUM(payment_value), 2) AS total_order_value_proxy_brl
FROM order_level
WHERE is_delivered = 1
    AND review_score IS NOT NULL
GROUP BY review_score
ORDER BY review_score DESC;

