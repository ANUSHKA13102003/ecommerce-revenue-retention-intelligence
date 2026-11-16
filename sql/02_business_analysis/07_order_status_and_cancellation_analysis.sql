-- ============================================================
-- PROJECT: E-COMMERCE REVENUE & CUSTOMER RETENTION INTELLIGENCE
-- ANALYSIS 15: ORDER STATUS AND CANCELLATION ANALYSIS
-- DATABASE: ecommerce_analytics
-- ============================================================
USE ecommerce_analytics;

-- 1. Full Dataset Order Status Breakdown (All 99,441 Orders)
SELECT
    order_status,
    COUNT(*) AS order_count,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS share_of_orders_pct,
    SUM(CASE WHEN has_items = 1 THEN 1 ELSE 0 END) AS orders_with_items,
    SUM(CASE WHEN has_items = 0 THEN 1 ELSE 0 END) AS orders_without_items,
    SUM(CASE WHEN payment_value IS NOT NULL THEN 1 ELSE 0 END) AS orders_with_payment,
    ROUND(COALESCE(SUM(payment_value), 0), 2) AS total_payment_value_brl,
    ROUND(COALESCE(SUM(item_revenue), 0), 2) AS total_item_price_brl,
    ROUND(AVG(payment_value), 2) AS avg_payment_value_brl,
    ROUND(AVG(review_score), 2) AS avg_review_score
FROM order_level
GROUP BY order_status
ORDER BY order_count DESC;

-- 2. Monthly Order Fulfilment vs Cancellation / Unavailability Rate (Jan 2017 - Aug 2018)
SELECT
    DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS order_month,
    COUNT(*) AS total_orders,
    SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END) AS delivered_orders,
    SUM(CASE WHEN order_status = 'canceled' THEN 1 ELSE 0 END) AS canceled_orders,
    SUM(CASE WHEN order_status = 'unavailable' THEN 1 ELSE 0 END) AS unavailable_orders,
    SUM(CASE WHEN order_status NOT IN ('delivered', 'canceled', 'unavailable') THEN 1 ELSE 0 END) AS in_progress_orders,
    ROUND(
        100.0 * SUM(CASE WHEN order_status = 'delivered' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
        2
    ) AS delivery_completion_rate_pct,
    ROUND(
        100.0 * SUM(CASE WHEN order_status IN ('canceled', 'unavailable') THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0),
        2
    ) AS cancellation_or_unavailable_rate_pct
FROM order_level
WHERE in_analysis_window = 1
GROUP BY DATE_FORMAT(order_purchase_timestamp, '%Y-%m')
ORDER BY order_month;

