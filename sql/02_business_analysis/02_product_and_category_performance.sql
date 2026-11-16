-- ============================================================
-- PROJECT: E-COMMERCE REVENUE & CUSTOMER RETENTION INTELLIGENCE
-- ANALYSIS 04: PRODUCT AND CATEGORY PERFORMANCE
-- DATABASE: ecommerce_analytics
--
-- BUSINESS RULE (D-1 & D-4):
-- Product and category performance uses SUM(price) on delivered
-- order items (BRL), with freight_value reported separately.
-- Category translations include official Olist English names plus
-- two documented manual project mappings, and 'Unknown' for nulls.
-- ============================================================
USE ecommerce_analytics;

-- 1. Category Performance Summary (Delivered Orders, All Dates)
WITH delivered_items AS (
    SELECT
        i.order_id,
        i.order_item_id,
        i.product_id,
        i.seller_id,
        i.price,
        i.freight_value,
        p.product_category_name AS category_name_pt,
        COALESCE(p.category_name_en, 'Unknown') AS category_name_en,
        o.in_analysis_window
    FROM order_items_clean i
    INNER JOIN orders_clean o
        ON i.order_id = o.order_id
    LEFT JOIN products_clean p
        ON i.product_id = p.product_id
    WHERE o.is_delivered = 1
),
category_agg AS (
    SELECT
        category_name_en,
        COALESCE(MAX(category_name_pt), 'unassigned') AS category_name_pt,
        COUNT(DISTINCT order_id) AS delivered_orders,
        COUNT(*) AS items_sold,
        COUNT(DISTINCT product_id) AS distinct_products,
        COUNT(DISTINCT seller_id) AS distinct_sellers,
        ROUND(SUM(price), 2) AS item_revenue_brl,
        ROUND(SUM(freight_value), 2) AS freight_value_brl,
        ROUND(SUM(price + freight_value), 2) AS total_item_gmv_brl,
        ROUND(AVG(price), 2) AS avg_item_price_brl,
        ROUND(AVG(freight_value), 2) AS avg_freight_brl
    FROM delivered_items
    GROUP BY category_name_en
),
category_ranked AS (
    SELECT
        *,
        DENSE_RANK() OVER (ORDER BY item_revenue_brl DESC) AS revenue_rank,
        ROUND(
            100.0 * item_revenue_brl / NULLIF(SUM(item_revenue_brl) OVER (), 0),
            2
        ) AS revenue_share_pct,
        ROUND(
            100.0 * SUM(item_revenue_brl) OVER (
                ORDER BY item_revenue_brl DESC
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) / NULLIF(SUM(item_revenue_brl) OVER (), 0),
            2
        ) AS cumulative_revenue_share_pct
    FROM category_agg
)
SELECT
    revenue_rank,
    category_name_en,
    category_name_pt,
    delivered_orders,
    items_sold,
    distinct_products,
    distinct_sellers,
    item_revenue_brl,
    freight_value_brl,
    total_item_gmv_brl,
    avg_item_price_brl,
    avg_freight_brl,
    revenue_share_pct,
    cumulative_revenue_share_pct
FROM category_ranked
ORDER BY revenue_rank;

-- 2. Top 25 Individual Products by Delivered Item Revenue (BRL)
SELECT
    i.product_id,
    COALESCE(p.category_name_en, 'Unknown') AS category_name_en,
    COUNT(DISTINCT i.order_id) AS delivered_orders,
    COUNT(*) AS units_sold,
    ROUND(SUM(i.price), 2) AS item_revenue_brl,
    ROUND(SUM(i.freight_value), 2) AS freight_value_brl,
    ROUND(AVG(i.price), 2) AS avg_unit_price_brl,
    ROUND(AVG(r.review_score), 2) AS avg_order_review_score
FROM order_items_clean i
INNER JOIN orders_clean o
    ON i.order_id = o.order_id
LEFT JOIN products_clean p
    ON i.product_id = p.product_id
LEFT JOIN order_review_summary r
    ON i.order_id = r.order_id
WHERE o.is_delivered = 1
GROUP BY i.product_id, COALESCE(p.category_name_en, 'Unknown')
ORDER BY item_revenue_brl DESC
LIMIT 25;

