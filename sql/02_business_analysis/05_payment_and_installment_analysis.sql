-- ============================================================
-- PROJECT: E-COMMERCE REVENUE & CUSTOMER RETENTION INTELLIGENCE
-- ANALYSIS 13: PAYMENT METHODS AND INSTALLMENT ANALYSIS
-- DATABASE: ecommerce_analytics
-- ============================================================
USE ecommerce_analytics;

-- 1. Payment Method Breakdown (Delivered Orders)
SELECT
    pa.payment_type,
    COUNT(*) AS payment_transactions,
    COUNT(DISTINCT pa.order_id) AS distinct_delivered_orders,
    ROUND(SUM(pa.payment_value), 2) AS total_payment_value_brl,
    ROUND(
        100.0 * SUM(pa.payment_value) / NULLIF(SUM(SUM(pa.payment_value)) OVER (), 0),
        2
    ) AS share_of_payment_value_pct,
    ROUND(AVG(pa.payment_value), 2) AS avg_transaction_value_brl,
    ROUND(AVG(pa.payment_installments), 2) AS avg_installments,
    MAX(pa.payment_installments) AS max_installments
FROM payments_clean pa
INNER JOIN orders_clean o
    ON pa.order_id = o.order_id
WHERE o.is_delivered = 1
GROUP BY pa.payment_type
ORDER BY total_payment_value_brl DESC;

-- 2. Credit Card Installment Tiers vs Order Value (Delivered Orders)
WITH credit_card_payments AS (
    SELECT
        pa.order_id,
        pa.payment_installments,
        pa.payment_value,
        CASE
            WHEN pa.payment_installments <= 1 THEN '1. Single Payment (0-1x)'
            WHEN pa.payment_installments BETWEEN 2 AND 3 THEN '2. Short Installments (2-3x)'
            WHEN pa.payment_installments BETWEEN 4 AND 6 THEN '3. Medium Installments (4-6x)'
            WHEN pa.payment_installments BETWEEN 7 AND 10 THEN '4. Long Installments (7-10x)'
            ELSE '5. Extended Installments (11x+)'
        END AS installment_tier
    FROM payments_clean pa
    INNER JOIN orders_clean o
        ON pa.order_id = o.order_id
    WHERE o.is_delivered = 1
        AND pa.payment_type = 'credit_card'
)
SELECT
    installment_tier,
    COUNT(*) AS transactions,
    COUNT(DISTINCT order_id) AS delivered_orders,
    ROUND(SUM(payment_value), 2) AS total_payment_value_brl,
    ROUND(
        100.0 * SUM(payment_value) / NULLIF(SUM(SUM(payment_value)) OVER (), 0),
        2
    ) AS share_of_cc_value_pct,
    ROUND(AVG(payment_value), 2) AS avg_payment_value_brl
FROM credit_card_payments
GROUP BY installment_tier
ORDER BY installment_tier;

