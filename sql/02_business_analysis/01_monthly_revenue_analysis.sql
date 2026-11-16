-- ==========================================================
-- PROJECT: E-commerce Revenue & Customer Retention Intelligence
-- ANALYSIS 01: Monthly Revenue and Sales Trends
-- Database: ecommerce_analytics
-- Analysis period: January 2017 - August 2018
-- ==========================================================
USE ecommerce_analytics;
-- 1. Calculate monthly business performance
WITH monthly_sales AS (
    SELECT DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS sales_month,
        COUNT(DISTINCT order_id) AS delivered_orders,
        ROUND(SUM(payment_value), 2) AS order_value_proxy,
        ROUND(
            SUM(payment_value) / NULLIF(COUNT(DISTINCT order_id), 0),
            2
        ) AS average_order_value
    FROM order_level
    WHERE is_delivered = 1
        AND payment_value IS NOT NULL
        AND in_analysis_window = 1
    GROUP BY DATE_FORMAT(order_purchase_timestamp, '%Y-%m')
),
-- 2. Calculate previous month's revenue
monthly_growth AS (
    SELECT sales_month,
        delivered_orders,
        order_value_proxy,
        average_order_value,
        LAG(order_value_proxy) OVER (
            ORDER BY sales_month
        ) AS previous_month_revenue
    FROM monthly_sales
) -- 3. Final monthly performance report
SELECT sales_month,
    delivered_orders,
    order_value_proxy,
    average_order_value,
    previous_month_revenue,
    ROUND(
        (
            order_value_proxy - previous_month_revenue
        ) / NULLIF(previous_month_revenue, 0) * 100,
        2
    ) AS revenue_growth_percent
FROM monthly_growth
ORDER BY sales_month;