-- ============================================================
-- PROJECT: E-COMMERCE REVENUE & CUSTOMER RETENTION INTELLIGENCE
-- ANALYSIS 10: CUSTOMER LIFETIME VALUE (CLV) PROXY & REPEAT BEHAVIOUR
-- DATABASE: ecommerce_analytics
--
-- BUSINESS RULE (D-1 & D-5):
-- Historical CLV proxy = SUM(payment_value) across delivered orders
-- per customer_unique_id (BRL). Explicitly distinguished from
-- predictive CLV.
-- Repeat Customer (D-5) = 2+ delivered orders on 2+ distinct
-- purchase dates. Options (a) 2+ delivered orders (any day) and
-- (c) 2+ orders (any status) are also reported as sensitivity checks.
-- ============================================================
USE ecommerce_analytics;

-- 1. Repeat Customer Definition Sensitivity Comparison (Full Dataset & Analysis Window)
WITH customer_all_orders AS (
    SELECT
        customer_unique_id,
        COUNT(DISTINCT order_id) AS all_status_orders,
        COUNT(DISTINCT CASE WHEN is_delivered = 1 THEN order_id END) AS delivered_orders,
        COUNT(DISTINCT CASE WHEN is_delivered = 1 THEN DATE(order_purchase_timestamp) END) AS delivered_purchase_days,
        ROUND(SUM(CASE WHEN is_delivered = 1 THEN COALESCE(payment_value, 0) ELSE 0 END), 2) AS historical_clv_brl
    FROM order_level
    WHERE customer_unique_id IS NOT NULL
    GROUP BY customer_unique_id
)
SELECT
    COUNT(*) AS total_unique_customers_all_statuses,
    SUM(CASE WHEN delivered_orders >= 1 THEN 1 ELSE 0 END) AS total_delivered_customers,
    -- Approved Primary Rule D-5 (Option b): 2+ delivered orders on 2+ distinct dates
    SUM(CASE WHEN delivered_orders >= 2 AND delivered_purchase_days >= 2 THEN 1 ELSE 0 END) AS repeat_customers_d5_distinct_days,
    ROUND(
        100.0 * SUM(CASE WHEN delivered_orders >= 2 AND delivered_purchase_days >= 2 THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN delivered_orders >= 1 THEN 1 ELSE 0 END), 0),
        2
    ) AS repeat_rate_d5_pct,
    -- Sensitivity Check Option (a): 2+ delivered orders (including same-day split baskets)
    SUM(CASE WHEN delivered_orders >= 2 THEN 1 ELSE 0 END) AS repeat_customers_opt_a_delivered,
    ROUND(
        100.0 * SUM(CASE WHEN delivered_orders >= 2 THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN delivered_orders >= 1 THEN 1 ELSE 0 END), 0),
        2
    ) AS repeat_rate_opt_a_pct,
    -- Sensitivity Check Option (c): 2+ orders across all order statuses
    SUM(CASE WHEN all_status_orders >= 2 THEN 1 ELSE 0 END) AS repeat_customers_opt_c_all_statuses,
    ROUND(
        100.0 * SUM(CASE WHEN all_status_orders >= 2 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        2
    ) AS repeat_rate_opt_c_pct
FROM customer_all_orders;

-- 2. Historical CLV Proxy by Customer Behaviour Group (Delivered Customers)
WITH customer_clv AS (
    SELECT
        customer_unique_id,
        COUNT(DISTINCT order_id) AS delivered_orders,
        COUNT(DISTINCT DATE(order_purchase_timestamp)) AS distinct_purchase_days,
        MIN(DATE(order_purchase_timestamp)) AS first_purchase_date,
        MAX(DATE(order_purchase_timestamp)) AS last_purchase_date,
        DATEDIFF(MAX(DATE(order_purchase_timestamp)), MIN(DATE(order_purchase_timestamp))) AS lifespan_days,
        ROUND(SUM(COALESCE(payment_value, 0)), 2) AS historical_clv_brl,
        ROUND(AVG(payment_value), 2) AS avg_order_value_brl
    FROM order_level
    WHERE is_delivered = 1
        AND customer_unique_id IS NOT NULL
    GROUP BY customer_unique_id
),
classified_clv AS (
    SELECT
        *,
        CASE
            WHEN delivered_orders >= 2 AND distinct_purchase_days >= 2 THEN '1. True Repeat Customer (2+ Delivered Orders, 2+ Days)'
            WHEN delivered_orders >= 2 AND distinct_purchase_days = 1 THEN '2. Same-Day Multi-Order Customer (Split Basket)'
            ELSE '3. Single-Order Customer (1 Delivered Order)'
        END AS customer_behaviour_group
    FROM customer_clv
)
SELECT
    customer_behaviour_group,
    COUNT(*) AS customer_count,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS customer_share_pct,
    SUM(delivered_orders) AS total_delivered_orders,
    ROUND(AVG(delivered_orders), 2) AS avg_delivered_orders,
    ROUND(AVG(lifespan_days), 2) AS avg_lifespan_days,
    ROUND(SUM(historical_clv_brl), 2) AS total_historical_clv_brl,
    ROUND(100.0 * SUM(historical_clv_brl) / NULLIF(SUM(SUM(historical_clv_brl)) OVER (), 0), 2) AS clv_share_pct,
    ROUND(AVG(historical_clv_brl), 2) AS avg_historical_clv_brl,
    ROUND(AVG(avg_order_value_brl), 2) AS avg_order_value_brl
FROM classified_clv
GROUP BY customer_behaviour_group
ORDER BY customer_behaviour_group;

