-- ============================================================
-- PROJECT: E-COMMERCE REVENUE & CUSTOMER RETENTION INTELLIGENCE
-- ANALYSIS 14: GEOGRAPHIC SALES & LOGISTICS PERFORMANCE
-- DATABASE: ecommerce_analytics
--
-- GRAIN SAFETY:
-- Uses order_level joined to customers_clean (1:1 on customer_id).
-- Geolocation raw table is NEVER joined directly to orders.
-- ============================================================
USE ecommerce_analytics;

-- 1. Customer State Performance (Delivered Orders)
SELECT
    c.customer_state,
    COUNT(DISTINCT o.order_id) AS delivered_orders,
    COUNT(DISTINCT o.customer_unique_id) AS unique_customers,
    ROUND(SUM(o.payment_value), 2) AS order_value_proxy_brl,
    ROUND(
        100.0 * SUM(o.payment_value) / NULLIF(SUM(SUM(o.payment_value)) OVER (), 0),
        2
    ) AS share_of_order_value_pct,
    ROUND(SUM(o.item_revenue), 2) AS item_revenue_brl,
    ROUND(SUM(o.freight_value), 2) AS freight_value_brl,
    ROUND(
        100.0 * SUM(o.freight_value) / NULLIF(SUM(o.item_revenue), 0),
        2
    ) AS freight_to_item_price_pct,
    ROUND(AVG(o.payment_value), 2) AS avg_order_value_brl,
    ROUND(AVG(o.delivery_days), 2) AS avg_delivery_days,
    ROUND(
        100.0 * SUM(CASE WHEN o.is_late = 1 THEN 1 ELSE 0 END)
        / NULLIF(SUM(CASE WHEN o.missing_delivery_date = 0 THEN 1 ELSE 0 END), 0),
        2
    ) AS late_delivery_rate_pct,
    ROUND(AVG(o.review_score), 2) AS avg_review_score
FROM order_level o
INNER JOIN customers_clean c
    ON o.customer_id = c.customer_id
WHERE o.is_delivered = 1
GROUP BY c.customer_state
ORDER BY order_value_proxy_brl DESC;

-- 2. Intra-State vs Inter-State Fulfilment Performance (Item Grain)
WITH item_routes AS (
    SELECT
        i.order_id,
        i.price,
        i.freight_value,
        c.customer_state,
        s.seller_state,
        o.delivery_days,
        o.is_late,
        o.review_score,
        CASE
            WHEN c.customer_state = s.seller_state THEN 'Intra-State (Same State)'
            ELSE 'Inter-State (Cross-State)'
        END AS route_type
    FROM order_items_clean i
    INNER JOIN order_level o
        ON i.order_id = o.order_id
    INNER JOIN customers_clean c
        ON o.customer_id = c.customer_id
    INNER JOIN sellers_clean s
        ON i.seller_id = s.seller_id
    WHERE o.is_delivered = 1
)
SELECT
    route_type,
    COUNT(*) AS items_shipped,
    COUNT(DISTINCT order_id) AS distinct_orders,
    ROUND(SUM(price), 2) AS item_revenue_brl,
    ROUND(SUM(freight_value), 2) AS freight_value_brl,
    ROUND(AVG(freight_value), 2) AS avg_item_freight_brl,
    ROUND(AVG(delivery_days), 2) AS avg_delivery_days,
    ROUND(100.0 * AVG(CASE WHEN is_late = 1 THEN 1.0 ELSE 0.0 END), 2) AS late_delivery_rate_pct,
    ROUND(AVG(review_score), 2) AS avg_review_score
FROM item_routes
GROUP BY route_type
ORDER BY items_shipped DESC;

