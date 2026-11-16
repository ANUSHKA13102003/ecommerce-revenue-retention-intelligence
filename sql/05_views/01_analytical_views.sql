-- ============================================================
-- PROJECT: E-COMMERCE REVENUE & CUSTOMER RETENTION INTELLIGENCE
-- MODULE: REUSABLE ANALYTICAL VIEWS FOR BI, REPORTING & AI AGENT
-- DATABASE: ecommerce_analytics
-- ============================================================
USE ecommerce_analytics;

-- 1. Executive Monthly KPIs View (Jan 2017 - Aug 2018 Analysis Window)
CREATE OR REPLACE VIEW vw_executive_monthly_kpis AS
WITH monthly_base AS (
    SELECT
        DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS sales_month,
        COUNT(DISTINCT order_id) AS delivered_orders,
        COUNT(DISTINCT customer_unique_id) AS active_customers,
        ROUND(SUM(payment_value), 2) AS order_value_proxy_brl,
        ROUND(SUM(item_revenue), 2) AS item_revenue_brl,
        ROUND(SUM(freight_value), 2) AS freight_value_brl,
        ROUND(SUM(payment_value) / NULLIF(COUNT(DISTINCT order_id), 0), 2) AS average_order_value_brl,
        ROUND(AVG(delivery_days), 2) AS avg_delivery_days,
        ROUND(
            100.0 * SUM(CASE WHEN is_late = 1 THEN 1 ELSE 0 END)
            / NULLIF(SUM(CASE WHEN missing_delivery_date = 0 THEN 1 ELSE 0 END), 0),
            2
        ) AS late_delivery_rate_pct,
        ROUND(AVG(review_score), 2) AS avg_review_score
    FROM order_level
    WHERE is_delivered = 1
        AND payment_value IS NOT NULL
        AND in_analysis_window = 1
    GROUP BY DATE_FORMAT(order_purchase_timestamp, '%Y-%m')
)
SELECT
    sales_month,
    delivered_orders,
    active_customers,
    order_value_proxy_brl,
    item_revenue_brl,
    freight_value_brl,
    average_order_value_brl,
    LAG(order_value_proxy_brl) OVER (ORDER BY sales_month) AS prev_month_order_value_brl,
    ROUND(
        100.0 * (order_value_proxy_brl - LAG(order_value_proxy_brl) OVER (ORDER BY sales_month))
        / NULLIF(LAG(order_value_proxy_brl) OVER (ORDER BY sales_month), 0),
        2
    ) AS mom_growth_pct,
    avg_delivery_days,
    late_delivery_rate_pct,
    avg_review_score
FROM monthly_base;

-- 2. Category Performance View (Delivered Orders)
CREATE OR REPLACE VIEW vw_category_performance AS
SELECT
    COALESCE(p.category_name_en, 'Unknown') AS category_name_en,
    COALESCE(MAX(p.product_category_name), 'unassigned') AS category_name_pt,
    COUNT(DISTINCT i.order_id) AS delivered_orders,
    COUNT(*) AS items_sold,
    COUNT(DISTINCT i.product_id) AS distinct_products,
    COUNT(DISTINCT i.seller_id) AS distinct_sellers,
    ROUND(SUM(i.price), 2) AS item_revenue_brl,
    ROUND(SUM(i.freight_value), 2) AS freight_value_brl,
    ROUND(AVG(i.price), 2) AS avg_item_price_brl,
    ROUND(AVG(o.delivery_days), 2) AS avg_delivery_days,
    ROUND(100.0 * AVG(CASE WHEN o.is_late = 1 THEN 1.0 ELSE 0.0 END), 2) AS late_delivery_rate_pct,
    ROUND(AVG(o.review_score), 2) AS avg_review_score
FROM order_items_clean i
INNER JOIN order_level o
    ON i.order_id = o.order_id
LEFT JOIN products_clean p
    ON i.product_id = p.product_id
WHERE o.is_delivered = 1
GROUP BY COALESCE(p.category_name_en, 'Unknown');

-- 3. Seller Performance View (Delivered Orders)
CREATE OR REPLACE VIEW vw_seller_performance AS
SELECT
    i.seller_id,
    MAX(s.seller_state) AS seller_state,
    MAX(s.seller_city_normalized) AS seller_city,
    COUNT(DISTINCT i.order_id) AS delivered_orders,
    COUNT(*) AS items_sold,
    COUNT(DISTINCT i.product_id) AS distinct_products,
    ROUND(SUM(i.price), 2) AS item_revenue_brl,
    ROUND(SUM(i.freight_value), 2) AS freight_value_brl,
    ROUND(AVG(i.price), 2) AS avg_item_price_brl,
    ROUND(AVG(o.delivery_days), 2) AS avg_delivery_days,
    ROUND(100.0 * AVG(CASE WHEN o.is_late = 1 THEN 1.0 ELSE 0.0 END), 2) AS late_delivery_rate_pct,
    ROUND(AVG(o.review_score), 2) AS avg_review_score
FROM order_items_clean i
INNER JOIN order_level o
    ON i.order_id = o.order_id
LEFT JOIN sellers_clean s
    ON i.seller_id = s.seller_id
WHERE o.is_delivered = 1
GROUP BY i.seller_id;

-- 4. Customer Lifecycle & Historical CLV Proxy View
CREATE OR REPLACE VIEW vw_customer_lifecycle AS
SELECT
    o.customer_unique_id,
    MAX(c.customer_state) AS customer_state,
    COUNT(DISTINCT o.order_id) AS delivered_orders,
    COUNT(DISTINCT DATE(o.order_purchase_timestamp)) AS distinct_purchase_days,
    MIN(DATE(o.order_purchase_timestamp)) AS first_purchase_date,
    MAX(DATE(o.order_purchase_timestamp)) AS last_purchase_date,
    DATEDIFF(MAX(DATE(o.order_purchase_timestamp)), MIN(DATE(o.order_purchase_timestamp))) AS lifespan_days,
    ROUND(SUM(COALESCE(o.payment_value, 0)), 2) AS historical_clv_brl,
    ROUND(AVG(o.payment_value), 2) AS avg_order_value_brl,
    ROUND(AVG(o.review_score), 2) AS avg_review_score,
    CASE
        WHEN COUNT(DISTINCT o.order_id) >= 2
             AND COUNT(DISTINCT DATE(o.order_purchase_timestamp)) >= 2
        THEN 'Repeat Customer'
        ELSE 'One-Time Customer'
    END AS repeat_status_d5
FROM order_level o
LEFT JOIN customers_clean c
    ON o.customer_id = c.customer_id
WHERE o.is_delivered = 1
    AND o.customer_unique_id IS NOT NULL
GROUP BY o.customer_unique_id;

-- 5. RFM Segment Summary View
CREATE OR REPLACE VIEW vw_rfm_segments_summary AS
SELECT
    customer_segment,
    COUNT(*) AS customer_count,
    ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS customer_share_pct,
    ROUND(AVG(recency), 2) AS avg_recency_days,
    ROUND(AVG(frequency), 2) AS avg_purchase_days,
    ROUND(AVG(monetary), 2) AS avg_monetary_brl,
    ROUND(SUM(monetary), 2) AS total_order_value_brl,
    ROUND(100.0 * SUM(monetary) / NULLIF(SUM(SUM(monetary)) OVER (), 0), 2) AS revenue_share_pct
FROM customer_rfm
GROUP BY customer_segment;

-- 6. Delivery & Review Performance by Customer State View
CREATE OR REPLACE VIEW vw_delivery_and_reviews_by_state AS
SELECT
    c.customer_state,
    COUNT(DISTINCT o.order_id) AS delivered_orders,
    COUNT(DISTINCT o.customer_unique_id) AS unique_customers,
    ROUND(SUM(o.payment_value), 2) AS order_value_proxy_brl,
    ROUND(SUM(o.item_revenue), 2) AS item_revenue_brl,
    ROUND(SUM(o.freight_value), 2) AS freight_value_brl,
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
GROUP BY c.customer_state;

-- 7. Payment Method Summary View
CREATE OR REPLACE VIEW vw_payment_method_summary AS
SELECT
    pa.payment_type,
    COUNT(*) AS transaction_count,
    COUNT(DISTINCT pa.order_id) AS delivered_orders,
    ROUND(SUM(pa.payment_value), 2) AS total_payment_value_brl,
    ROUND(AVG(pa.payment_value), 2) AS avg_transaction_value_brl,
    ROUND(AVG(pa.payment_installments), 2) AS avg_installments
FROM payments_clean pa
INNER JOIN orders_clean o
    ON pa.order_id = o.order_id
WHERE o.is_delivered = 1
GROUP BY pa.payment_type;

-- 8. Order Status Summary View
CREATE OR REPLACE VIEW vw_order_status_summary AS
SELECT
    order_status,
    COUNT(*) AS order_count,
    SUM(CASE WHEN has_items = 1 THEN 1 ELSE 0 END) AS orders_with_items,
    ROUND(COALESCE(SUM(payment_value), 0), 2) AS total_payment_value_brl,
    ROUND(COALESCE(SUM(item_revenue), 0), 2) AS total_item_price_brl,
    ROUND(AVG(review_score), 2) AS avg_review_score
FROM order_level
GROUP BY order_status;

