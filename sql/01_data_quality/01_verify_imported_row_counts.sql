USE ecommerce_analytics;

SELECT 'customers_clean' AS table_name, COUNT(*) AS exact_rows FROM customers_clean
UNION ALL
SELECT 'customers_with_geolocation', COUNT(*) FROM customers_with_geolocation
UNION ALL
SELECT 'geolocation_zip_lookup', COUNT(*) FROM geolocation_zip_lookup
UNION ALL
SELECT 'order_item_summary', COUNT(*) FROM order_item_summary
UNION ALL
SELECT 'order_items_clean', COUNT(*) FROM order_items_clean
UNION ALL
SELECT 'order_level', COUNT(*) FROM order_level
UNION ALL
SELECT 'order_payment_summary', COUNT(*) FROM order_payment_summary
UNION ALL
SELECT 'order_review_summary', COUNT(*) FROM order_review_summary
UNION ALL
SELECT 'orders_clean', COUNT(*) FROM orders_clean
UNION ALL
SELECT 'payments_clean', COUNT(*) FROM payments_clean
UNION ALL
SELECT 'products_clean', COUNT(*) FROM products_clean
UNION ALL
SELECT 'reviews_clean', COUNT(*) FROM reviews_clean
UNION ALL
SELECT 'sellers_clean', COUNT(*) FROM sellers_clean
UNION ALL
SELECT 'sellers_with_geolocation', COUNT(*) FROM sellers_with_geolocation;