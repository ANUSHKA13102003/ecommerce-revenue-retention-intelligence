-- ============================================================
-- PROJECT: E-COMMERCE REVENUE & CUSTOMER RETENTION INTELLIGENCE
-- MODULE: DATA QUALITY, KEY UNIQUENESS & RECONCILIATION CHECKS
-- DATABASE: ecommerce_analytics
-- ============================================================
USE ecommerce_analytics;

-- 1. Primary Key Uniqueness Checks (Expected duplicate_keys = 0)
SELECT 'orders_clean.order_id' AS key_check,
    COUNT(*) AS total_rows,
    COUNT(DISTINCT order_id) AS distinct_keys,
    COUNT(*) - COUNT(DISTINCT order_id) AS duplicate_keys
FROM orders_clean
UNION ALL
SELECT 'customers_clean.customer_id',
    COUNT(*),
    COUNT(DISTINCT customer_id),
    COUNT(*) - COUNT(DISTINCT customer_id)
FROM customers_clean
UNION ALL
SELECT 'order_level.order_id',
    COUNT(*),
    COUNT(DISTINCT order_id),
    COUNT(*) - COUNT(DISTINCT order_id)
FROM order_level
UNION ALL
SELECT 'products_clean.product_id',
    COUNT(*),
    COUNT(DISTINCT product_id),
    COUNT(*) - COUNT(DISTINCT product_id)
FROM products_clean
UNION ALL
SELECT 'sellers_clean.seller_id',
    COUNT(*),
    COUNT(DISTINCT seller_id),
    COUNT(*) - COUNT(DISTINCT seller_id)
FROM sellers_clean
UNION ALL
SELECT 'geolocation_zip_lookup.zip_code_prefix',
    COUNT(*),
    COUNT(DISTINCT zip_code_prefix),
    COUNT(*) - COUNT(DISTINCT zip_code_prefix)
FROM geolocation_zip_lookup;

-- 2. Foreign Key Orphan Checks (Expected orphan_rows = 0)
SELECT 'orders_clean.customer_id -> customers_clean' AS fk_relationship,
    COUNT(*) AS orphan_rows
FROM orders_clean o
LEFT JOIN customers_clean c ON o.customer_id = c.customer_id
WHERE c.customer_id IS NULL
UNION ALL
SELECT 'order_items_clean.order_id -> orders_clean',
    COUNT(*)
FROM order_items_clean i
LEFT JOIN orders_clean o ON i.order_id = o.order_id
WHERE o.order_id IS NULL
UNION ALL
SELECT 'order_items_clean.product_id -> products_clean',
    COUNT(*)
FROM order_items_clean i
LEFT JOIN products_clean p ON i.product_id = p.product_id
WHERE p.product_id IS NULL
UNION ALL
SELECT 'order_items_clean.seller_id -> sellers_clean',
    COUNT(*)
FROM order_items_clean i
LEFT JOIN sellers_clean s ON i.seller_id = s.seller_id
WHERE s.seller_id IS NULL
UNION ALL
SELECT 'payments_clean.order_id -> orders_clean',
    COUNT(*)
FROM payments_clean pa
LEFT JOIN orders_clean o ON pa.order_id = o.order_id
WHERE o.order_id IS NULL;

-- 3. Financial Reconciliation: Raw Clean Tables vs Order-Level Table
SELECT
    (SELECT ROUND(SUM(price), 2) FROM order_items_clean) AS raw_item_price_total_brl,
    (SELECT ROUND(SUM(item_revenue), 2) FROM order_level) AS order_level_item_revenue_total_brl,
    (SELECT ROUND(SUM(freight_value), 2) FROM order_items_clean) AS raw_freight_total_brl,
    (SELECT ROUND(SUM(freight_value), 2) FROM order_level) AS order_level_freight_total_brl,
    (SELECT ROUND(SUM(payment_value), 2) FROM payments_clean) AS raw_payment_total_brl,
    (SELECT ROUND(SUM(payment_value), 2) FROM order_level) AS order_level_payment_total_brl,
    (SELECT ROUND(SUM(payment_value), 2) FROM order_level WHERE is_delivered = 1) AS delivered_order_value_proxy_brl;

