-- =====================================================
-- ANALYSIS 02: REPEAT CUSTOMER AND RETENTION ANALYSIS
-- Database: ecommerce_analytics
-- Period: January 2017 - August 2018
-- Definition: 2+ delivered orders on distinct purchase days
-- =====================================================
USE ecommerce_analytics;
-- Step 1: Calculate delivered orders per customer
WITH customer_orders AS (
    SELECT customer_unique_id,
        COUNT(DISTINCT order_id) AS delivered_orders,
        COUNT(DISTINCT DATE(order_purchase_timestamp)) AS distinct_purchase_days
    FROM order_level
    WHERE is_delivered = 1
        AND in_analysis_window = 1
        AND customer_unique_id IS NOT NULL
    GROUP BY customer_unique_id
),
-- Step 2: Classify customers
customer_segments AS (
    SELECT customer_unique_id,
        delivered_orders,
        distinct_purchase_days,
        CASE
            WHEN delivered_orders >= 2
            AND distinct_purchase_days >= 2 THEN 'Repeat Customer'
            ELSE 'One-time Customer'
        END AS customer_type
    FROM customer_orders
) -- Step 3: Calculate retention KPIs
SELECT COUNT(*) AS total_unique_customers,
    SUM(
        CASE
            WHEN customer_type = 'Repeat Customer' THEN 1
            ELSE 0
        END
    ) AS repeat_customers,
    SUM(
        CASE
            WHEN customer_type = 'One-time Customer' THEN 1
            ELSE 0
        END
    ) AS one_time_customers,
    ROUND(
        100.0 * SUM(
            CASE
                WHEN customer_type = 'Repeat Customer' THEN 1
                ELSE 0
            END
        ) / NULLIF(COUNT(*), 0),
        2
    ) AS repeat_customer_rate_percent,
    SUM(delivered_orders) AS total_delivered_orders,
    ROUND(AVG(delivered_orders), 2) AS average_orders_per_customer
FROM customer_segments;