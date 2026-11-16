-- ============================================================
-- PROJECT: E-COMMERCE REVENUE & CUSTOMER RETENTION INTELLIGENCE
-- ANALYSIS 05: SELLER PERFORMANCE & CONCENTRATION ANALYSIS
-- DATABASE: ecommerce_analytics
--
-- BUSINESS RULE (D-1):
-- Seller performance uses SUM(price) on delivered order items (BRL),
-- with freight_value documented separately.
-- ============================================================
USE ecommerce_analytics;

-- 1. Top 50 Sellers by Delivered Item Revenue (BRL)
WITH seller_orders AS (
    SELECT
        i.seller_id,
        s.seller_state,
        s.seller_city_normalized AS seller_city,
        i.order_id,
        i.product_id,
        i.price,
        i.freight_value,
        o.is_late,
        o.delivery_days,
        r.review_score
    FROM order_items_clean i
    INNER JOIN orders_clean o
        ON i.order_id = o.order_id
    LEFT JOIN sellers_clean s
        ON i.seller_id = s.seller_id
    LEFT JOIN order_review_summary r
        ON i.order_id = r.order_id
    WHERE o.is_delivered = 1
),
seller_agg AS (
    SELECT
        seller_id,
        MAX(seller_state) AS seller_state,
        MAX(seller_city) AS seller_city,
        COUNT(DISTINCT order_id) AS delivered_orders,
        COUNT(*) AS items_sold,
        COUNT(DISTINCT product_id) AS distinct_products,
        ROUND(SUM(price), 2) AS item_revenue_brl,
        ROUND(SUM(freight_value), 2) AS freight_value_brl,
        ROUND(AVG(price), 2) AS avg_item_price_brl,
        ROUND(AVG(delivery_days), 2) AS avg_delivery_days,
        ROUND(100.0 * AVG(CASE WHEN is_late = 1 THEN 1.0 ELSE 0.0 END), 2) AS late_delivery_rate_pct,
        ROUND(AVG(review_score), 2) AS avg_review_score
    FROM seller_orders
    GROUP BY seller_id
)
SELECT
    DENSE_RANK() OVER (ORDER BY item_revenue_brl DESC) AS seller_rank,
    seller_id,
    seller_state,
    seller_city,
    delivered_orders,
    items_sold,
    distinct_products,
    item_revenue_brl,
    freight_value_brl,
    avg_item_price_brl,
    avg_delivery_days,
    late_delivery_rate_pct,
    avg_review_score,
    ROUND(
        100.0 * item_revenue_brl / NULLIF(SUM(item_revenue_brl) OVER (), 0),
        3
    ) AS revenue_share_pct
FROM seller_agg
ORDER BY item_revenue_brl DESC
LIMIT 50;

-- 2. Seller Concentration by Revenue Decile / Pareto Tier
WITH seller_totals AS (
    SELECT
        i.seller_id,
        COUNT(DISTINCT i.order_id) AS delivered_orders,
        ROUND(SUM(i.price), 2) AS item_revenue_brl
    FROM order_items_clean i
    INNER JOIN orders_clean o
        ON i.order_id = o.order_id
    WHERE o.is_delivered = 1
    GROUP BY i.seller_id
),
seller_ranked AS (
    SELECT
        *,
        NTILE(10) OVER (ORDER BY item_revenue_brl DESC) AS revenue_decile
    FROM seller_totals
)
SELECT
    revenue_decile,
    COUNT(*) AS seller_count,
    SUM(delivered_orders) AS total_delivered_orders,
    ROUND(SUM(item_revenue_brl), 2) AS decile_item_revenue_brl,
    ROUND(AVG(item_revenue_brl), 2) AS avg_seller_revenue_brl,
    ROUND(
        100.0 * SUM(item_revenue_brl) / NULLIF(SUM(SUM(item_revenue_brl)) OVER (), 0),
        2
    ) AS share_of_total_item_revenue_pct
FROM seller_ranked
GROUP BY revenue_decile
ORDER BY revenue_decile;

