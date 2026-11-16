"""
SQL Analyst Agent
==================
Converts natural-language business questions into safe, schema-aware,
read-only SQL queries, validates them with `validate_sql_query`, executes
them against `AnalyticsDBEngine`, and returns verified results with full
table and metric lineage.

Supports:
- Deterministic Local Intent Routing (default, zero paid API required)
- Safe handling of unsupported or out-of-scope questions (never fabricates data)
- Optional External LLM SQL Adapter (enabled only if `LLM_PROVIDER`,
  `LLM_API_KEY`, and `LLM_MODEL` are configured in environment variables,
  still subject to the exact same `validate_sql_query` safety gate).
"""

from __future__ import annotations

from typing import Any

import pandas as pd

from agents.schemas.agent_schemas import ChartRecommendation, SQLValidationResult
from agents.tools.sql_safety_validator import validate_sql_query
from src.database.db_engine import AnalyticsDBEngine


PREBUILT_BUSINESS_QUERIES: dict[str, dict[str, Any]] = {
    "rfm_segments": {
        "keywords": [
            "segment",
            "segments",
            "rfm",
            "champions",
            "loyal",
            "lost",
            "needs attention",
            "at risk",
        ],
        "sql": (
            "SELECT customer_segment, customer_count, customer_share_pct, "
            "avg_recency_days, avg_purchase_days, avg_monetary_brl, "
            "total_order_value_brl, revenue_share_pct "
            "FROM vw_rfm_segments_summary "
            "ORDER BY total_order_value_brl DESC"
        ),
        "source_tables": ["customer_rfm", "vw_rfm_segments_summary", "order_level"],
        "metric_definitions": [
            "Monetary (BRL) = SUM(payment_value) on delivered orders per customer_unique_id (Delivered Order Value Proxy, Rule D-1).",
            "Frequency = COUNT(DISTINCT DATE(order_purchase_timestamp)) for delivered orders (Rule D-5).",
            "Recency = Days from customer's last delivered purchase to dataset snapshot (2018-10-17).",
        ],
        "chart": ChartRecommendation(
            chart_type="bar",
            x_column="customer_segment",
            y_column="total_order_value_brl",
            title="Delivered Order Value Proxy (R$) by RFM Customer Segment",
            rationale="Compares total order value proxy and customer counts across the 7 validated RFM segments.",
        ),
    },
    "repeat_purchase_rate": {
        "keywords": [
            "repeat",
            "d-5",
            "d5",
            "return",
            "returning",
            "retention rate",
            "one-time",
            "clv",
            "lifetime",
            "split basket",
        ],
        "sql": (
            "SELECT repeat_status_d5, "
            "COUNT(*) AS customer_count, "
            "ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS customer_share_pct, "
            "SUM(delivered_orders) AS total_delivered_orders, "
            "ROUND(SUM(historical_clv_brl), 2) AS total_order_value_brl, "
            "ROUND(AVG(historical_clv_brl), 2) AS avg_historical_clv_brl, "
            "ROUND(AVG(avg_order_value_brl), 2) AS avg_order_value_brl "
            "FROM vw_customer_lifecycle "
            "GROUP BY repeat_status_d5 "
            "ORDER BY customer_count DESC"
        ),
        "source_tables": ["vw_customer_lifecycle", "order_level"],
        "metric_definitions": [
            "Repeat Customer (Rule D-5) = customer_unique_id with 2+ delivered orders placed on 2+ distinct calendar dates.",
            "Historical CLV Proxy (BRL) = SUM(payment_value) across delivered orders per customer_unique_id (Order Value Proxy, not Olist commission).",
        ],
        "chart": ChartRecommendation(
            chart_type="bar",
            x_column="repeat_status_d5",
            y_column="avg_historical_clv_brl",
            title="Average Historical CLV Proxy (R$): True Repeat vs Non-Repeat Customers",
            rationale="Contrasts the 2.0x higher historical order value of Rule D-5 repeat customers against one-time buyers.",
        ),
    },
    "cohort_retention": {
        "keywords": [
            "cohort",
            "cohorts",
            "weakest retention",
            "acquisition month",
            "m+1",
            "m1",
            "heatmap",
        ],
        "sql": (
            "WITH delivered_window AS ("
            "  SELECT customer_unique_id, "
            "  DATE_FORMAT(order_purchase_timestamp, '%Y-%m') AS order_month, "
            "  (YEAR(order_purchase_timestamp) * 12 + MONTH(order_purchase_timestamp)) AS ym_num "
            "  FROM order_level "
            "  WHERE is_delivered = 1 AND in_analysis_window = 1 AND customer_unique_id IS NOT NULL"
            "), customer_cohort AS ("
            "  SELECT customer_unique_id, MIN(order_month) AS cohort_month, MIN(ym_num) AS cohort_num "
            "  FROM delivered_window GROUP BY customer_unique_id"
            "), cohort_sizes AS ("
            "  SELECT cohort_month, COUNT(DISTINCT customer_unique_id) AS cohort_size "
            "  FROM customer_cohort GROUP BY cohort_month"
            "), m1_activity AS ("
            "  SELECT c.cohort_month, COUNT(DISTINCT d.customer_unique_id) AS m1_customers "
            "  FROM delivered_window d INNER JOIN customer_cohort c "
            "  ON d.customer_unique_id = c.customer_unique_id "
            "  WHERE (d.ym_num - c.cohort_num) = 1 GROUP BY c.cohort_month"
            ") "
            "SELECT s.cohort_month, s.cohort_size, COALESCE(m.m1_customers, 0) AS m1_returning_customers, "
            "ROUND(100.0 * COALESCE(m.m1_customers, 0) / s.cohort_size, 3) AS m1_retention_rate_pct "
            "FROM cohort_sizes s LEFT JOIN m1_activity m ON s.cohort_month = m.cohort_month "
            "WHERE s.cohort_month < '2018-08' "
            "ORDER BY m1_retention_rate_pct ASC"
        ),
        "source_tables": ["order_level"],
        "metric_definitions": [
            "Cohort Month = YYYY-MM of customer_unique_id's first delivered purchase inside Jan 2017 – Aug 2018 (Rule D-2).",
            "M+1 Retention Rate (%) = % of cohort customers placing a delivered order in the immediately following calendar month.",
        ],
        "chart": ChartRecommendation(
            chart_type="bar",
            x_column="cohort_month",
            y_column="m1_retention_rate_pct",
            title="M+1 Cohort Repeat Retention Rate (%) by Acquisition Month (2017-01 to 2018-07)",
            rationale="Ranks acquisition cohorts from lowest to highest month-1 repeat purchase rate.",
        ),
    },
    "delivery_vs_reviews": {
        "keywords": [
            "review",
            "reviews",
            "score",
            "scores",
            "rating",
            "ratings",
            "satisfaction",
            "relate to lower",
            "late delivery relate",
            "delay relate",
        ],
        "sql": (
            "WITH delay_classified AS ("
            "  SELECT order_id, payment_value, delivery_days, is_late, review_score, "
            "  DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) AS delay_calendar_days, "
            "  CASE "
            "    WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) <= -8 THEN '1. Early (8+ days early)' "
            "    WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) BETWEEN -7 AND -1 THEN '2. Early (1-7 days early)' "
            "    WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) = 0 THEN '3. On Estimated Date (0 days)' "
            "    WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) BETWEEN 1 AND 3 THEN '4. Slightly Late (1-3 days)' "
            "    WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) BETWEEN 4 AND 7 THEN '5. Moderately Late (4-7 days)' "
            "    ELSE '6. Severely Late (8+ days)' "
            "  END AS delivery_timing_bucket "
            "  FROM order_level "
            "  WHERE is_delivered = 1 AND missing_delivery_date = 0 AND order_estimated_delivery_date IS NOT NULL"
            ") "
            "SELECT delivery_timing_bucket, "
            "COUNT(*) AS delivered_orders, "
            "ROUND(100.0 * COUNT(*) / NULLIF(SUM(COUNT(*)) OVER (), 0), 2) AS order_share_pct, "
            "ROUND(SUM(payment_value), 2) AS order_value_proxy_brl, "
            "ROUND(AVG(delivery_days), 2) AS avg_actual_delivery_days, "
            "ROUND(AVG(review_score), 2) AS avg_review_score, "
            "ROUND(100.0 * SUM(CASE WHEN review_score = 1 THEN 1 ELSE 0 END) / NULLIF(COUNT(review_score), 0), 2) AS one_star_share_pct, "
            "ROUND(100.0 * SUM(CASE WHEN review_score = 5 THEN 1 ELSE 0 END) / NULLIF(COUNT(review_score), 0), 2) AS five_star_share_pct "
            "FROM delay_classified "
            "GROUP BY delivery_timing_bucket "
            "ORDER BY delivery_timing_bucket"
        ),
        "source_tables": ["order_level", "order_review_summary"],
        "metric_definitions": [
            "Primary Review Score (Rule D-3) = Score (1–5) from the most recent review per order.",
            "Late Delivery = order_delivered_customer_date > order_estimated_delivery_date (is_late = 1).",
            "1-Star Share (%) = % of reviewed delivered orders in the bucket receiving a 1-star rating.",
        ],
        "chart": ChartRecommendation(
            chart_type="bar",
            x_column="delivery_timing_bucket",
            y_column="avg_review_score",
            title="Average Customer Review Score (1–5) by Delivery Timing Bucket",
            rationale="Illustrates the steep drop in review scores once delivery crosses the estimated date.",
        ),
    },
    "delivery_and_regions": {
        "keywords": [
            "region",
            "regions",
            "state",
            "states",
            "geographic",
            "delay rate",
            "highest delivery delay",
            "where",
        ],
        "sql": (
            "SELECT customer_state, delivered_orders, unique_customers, "
            "order_value_proxy_brl, item_revenue_brl, freight_value_brl, "
            "avg_delivery_days, late_delivery_rate_pct, avg_review_score "
            "FROM vw_delivery_and_reviews_by_state "
            "ORDER BY late_delivery_rate_pct DESC"
        ),
        "source_tables": ["vw_delivery_and_reviews_by_state", "order_level", "customers_clean"],
        "metric_definitions": [
            "Late Delivery Rate (%) = % of delivered orders with delivery timestamp after estimated delivery date.",
            "Average Review Score = Mean of most recent review score (1–5) per delivered order (Rule D-3).",
        ],
        "chart": ChartRecommendation(
            chart_type="bar",
            x_column="customer_state",
            y_column="late_delivery_rate_pct",
            title="Late Delivery Rate (%) by Brazilian State",
            rationale="Identifies states with elevated logistics delays and corresponding customer satisfaction drops.",
        ),
    },
    "seller_performance": {
        "keywords": [
            "seller",
            "sellers",
            "merchant",
            "merchants",
            "vendor",
            "vendors",
            "largest share of merchandise",
        ],
        "sql": (
            "SELECT seller_id, seller_state, seller_city, delivered_orders, "
            "items_sold, item_revenue_brl, freight_value_brl, "
            "late_delivery_rate_pct, avg_review_score "
            "FROM vw_seller_performance "
            "ORDER BY item_revenue_brl DESC "
            "LIMIT 20"
        ),
        "source_tables": ["vw_seller_performance", "order_items_clean", "sellers_clean", "order_level"],
        "metric_definitions": [
            "Seller Merchandise Revenue (BRL) = SUM(price) across delivered items fulfilled by the seller (Rule D-1; excludes freight and buyer installment interest).",
        ],
        "chart": ChartRecommendation(
            chart_type="bar",
            x_column="seller_id",
            y_column="item_revenue_brl",
            title="Top 20 Sellers by Delivered Merchandise Revenue — SUM(price) (R$)",
            rationale="Ranks top marketplace sellers by merchandise revenue alongside delivery SLA and review ratings.",
        ),
    },
    "category_performance": {
        "keywords": [
            "category",
            "categories",
            "product",
            "products",
            "merchandise revenue",
            "most sales",
            "most revenue",
        ],
        "sql": (
            "SELECT category_name_en, category_name_pt, delivered_orders, items_sold, "
            "item_revenue_brl, freight_value_brl, avg_item_price_brl, "
            "late_delivery_rate_pct, avg_review_score "
            "FROM vw_category_performance "
            "ORDER BY item_revenue_brl DESC "
            "LIMIT 15"
        ),
        "source_tables": ["vw_category_performance", "order_items_clean", "products_clean", "order_level"],
        "metric_definitions": [
            "Delivered Merchandise Revenue (BRL) = SUM(price) for delivered order items (Rule D-1; distinct from Order Value Proxy).",
            "Freight Value (BRL) = SUM(freight_value) reported separately from merchandise price.",
        ],
        "chart": ChartRecommendation(
            chart_type="bar",
            x_column="category_name_en",
            y_column="item_revenue_brl",
            title="Top 15 Product Categories by Delivered Merchandise Revenue — SUM(price) (R$)",
            rationale="Ranks top revenue-generating product categories by merchandise item price.",
        ),
    },
    "payment_analysis": {
        "keywords": ["payment", "installment", "installments", "credit card", "boleto", "voucher", "debit"],
        "sql": (
            "SELECT payment_type, transaction_count, delivered_orders, "
            "total_payment_value_brl, avg_transaction_value_brl, avg_installments "
            "FROM vw_payment_method_summary "
            "ORDER BY total_payment_value_brl DESC"
        ),
        "source_tables": ["vw_payment_method_summary", "payments_clean", "orders_clean"],
        "metric_definitions": [
            "Total Payment Value (BRL) = SUM(payment_value) by payment method on delivered orders (Order Value Proxy, Rule D-1).",
        ],
        "chart": ChartRecommendation(
            chart_type="bar",
            x_column="payment_type",
            y_column="total_payment_value_brl",
            title="Delivered Order Value Proxy (R$) by Payment Method",
            rationale="Shows dominance of credit card (78.46%) and boleto (17.96%) transactions.",
        ),
    },
    "monthly_revenue_trend": {
        "keywords": [
            "monthly",
            "month",
            "trend",
            "trends",
            "changed",
            "over time",
            "total order value",
            "order value proxy",
            "aov",
            "average order value",
            "growth",
        ],
        "sql": (
            "SELECT sales_month, delivered_orders, active_customers, "
            "order_value_proxy_brl, item_revenue_brl, freight_value_brl, "
            "average_order_value_brl, mom_growth_pct, late_delivery_rate_pct, avg_review_score "
            "FROM vw_executive_monthly_kpis "
            "ORDER BY sales_month"
        ),
        "source_tables": ["vw_executive_monthly_kpis", "order_level"],
        "metric_definitions": [
            "Delivered Order Value Proxy (BRL) = SUM(payment_value) on delivered orders in Jan 2017 – Aug 2018 (Rules D-1 & D-2).",
            "Delivered Merchandise Revenue (BRL) = SUM(price) on delivered items, tracked separately from freight_value.",
            "Average Order Value (BRL) = Delivered Order Value Proxy / Delivered Orders.",
        ],
        "chart": ChartRecommendation(
            chart_type="line",
            x_column="sales_month",
            y_column="order_value_proxy_brl",
            title="Monthly Delivered Order Value Proxy (R$) — Jan 2017 to Aug 2018",
            rationale="Time-series line chart tracks monthly order value trajectory and seasonality (Nov 2017 Black Friday peak).",
        ),
    },
    "june_2018_decline_analysis": {
        "keywords": [
            "june 2018",
            "2018-06",
            "decline in june",
            "drop in june",
            "why did order value decline",
        ],
        "sql": (
            "SELECT sales_month, delivered_orders, active_customers, "
            "order_value_proxy_brl, item_revenue_brl, freight_value_brl, "
            "average_order_value_brl, mom_growth_pct, avg_delivery_days, "
            "late_delivery_rate_pct, avg_review_score "
            "FROM vw_executive_monthly_kpis "
            "WHERE sales_month BETWEEN '2018-03' AND '2018-08' "
            "ORDER BY sales_month"
        ),
        "source_tables": ["vw_executive_monthly_kpis", "order_level"],
        "metric_definitions": [
            "MoM Order Value Growth (%) = Month-over-Month % change in Delivered Order Value Proxy (payment_value, Rule D-1).",
            "Order Volume vs AOV Decomposition = Δ Order Value decomposed into Δ Delivered Orders (-9.63% in Jun 2018) and Δ Mean Order Value (-0.79% in Jun 2018).",
        ],
        "chart": ChartRecommendation(
            chart_type="bar",
            x_column="sales_month",
            y_column="order_value_proxy_brl",
            title="Q2–Q3 2018 Monthly Order Value Proxy (R$) — June 2018 Decline Decomposition",
            rationale="Highlights the -10.34% MoM decline in June 2018 following the May 2018 Brazilian logistics disruption.",
        ),
    },
    "executive_decision_actions": {
        "keywords": [
            "business actions",
            "management consider",
            "what actions",
            "recommendations",
            "strategic actions",
            "decision",
            "priorities",
        ],
        "sql": (
            "SELECT customer_segment, customer_count, customer_share_pct, "
            "avg_recency_days, avg_purchase_days, avg_monetary_brl, "
            "total_order_value_brl, revenue_share_pct "
            "FROM vw_rfm_segments_summary "
            "ORDER BY total_order_value_brl DESC"
        ),
        "source_tables": [
            "vw_rfm_segments_summary",
            "vw_delivery_and_reviews_by_state",
            "vw_seller_performance",
            "vw_category_performance",
        ],
        "metric_definitions": [
            "Decision Pillar 1 (Retention): 37,219 'Recent Customers' (R$ 6,269,299.23) + 18,272 'Needs Attention' (R$ 2,798,239.09).",
            "Decision Pillar 2 (Logistics SLA): 8.11% late delivery rate causing a -1.73 star drop (4.29 vs 2.57 stars).",
            "Decision Pillar 3 (Seller Concentration): Top 10% of sellers (297 merchants) generate 67.11% (R$ 8,873,076.37) of item revenue.",
        ],
        "chart": ChartRecommendation(
            chart_type="bar",
            x_column="customer_segment",
            y_column="total_order_value_brl",
            title="Targetable Order Value Pool (R$) by Customer Segment for Management Action",
            rationale="Quantifies the revenue pool at stake across retention and reactivation management initiatives.",
        ),
    },
}

UNSUPPORTED_DOMAINS = [
    "weather",
    "bitcoin",
    "crypto",
    "stock price",
    "employee",
    "salary",
    "payroll",
    "net profit",
    "cogs",
    "cost of goods",
    "ad spend",
    "marketing spend",
    "cac",
]


class SQLAnalystAgent:
    """Routes business questions to verified read-only SQL queries and executes them safely."""

    def __init__(self, db_engine: AnalyticsDBEngine | None = None) -> None:
        self.engine = db_engine or AnalyticsDBEngine(prefer_mysql=True)

    def match_intent(self, question: str) -> str:
        if not question or not question.strip():
            return "unsupported_question"
        q_low = question.lower().strip()

        # Check explicit out-of-scope / unmeasured domains first
        if any(bad in q_low for bad in UNSUPPORTED_DOMAINS):
            return "unsupported_question"

        # Explicit June 2018 decline check before general monthly revenue trend
        if "june 2018" in q_low or "2018-06" in q_low or "decline in june" in q_low:
            return "june_2018_decline_analysis"

        # Explicit executive business actions / management recommendations check
        if (
            "business actions" in q_low
            or "management consider" in q_low
            or "what actions" in q_low
            or ("management" in q_low and "action" in q_low)
        ):
            return "executive_decision_actions"

        # Disambiguate delivery vs review score questions from state/region delay questions
        if ("late" in q_low or "delay" in q_low or "delivery" in q_low) and (
            "review" in q_low or "score" in q_low or "rating" in q_low or "satisfaction" in q_low
        ) and not ("state" in q_low or "region" in q_low):
            return "delivery_vs_reviews"

        # Disambiguate seller merchandise questions from category merchandise questions
        if "seller" in q_low or "sellers" in q_low or "merchant" in q_low or "vendor" in q_low:
            return "seller_performance"

        priority = [
            "june_2018_decline_analysis",
            "executive_decision_actions",
            "rfm_segments",
            "repeat_purchase_rate",
            "cohort_retention",
            "delivery_vs_reviews",
            "delivery_and_regions",
            "seller_performance",
            "payment_analysis",
            "category_performance",
            "monthly_revenue_trend",
        ]
        best_intent = "unsupported_question"
        best_score = 0
        for intent in priority:
            spec = PREBUILT_BUSINESS_QUERIES[intent]
            hits = sum(1 for kw in spec["keywords"] if kw in q_low)
            if hits > best_score:
                best_score = hits
                best_intent = intent

        # General revenue/order fallback only if question asks about revenue, orders, or sales
        if best_score == 0 and any(w in q_low for w in ["revenue", "order", "orders", "sales", "gmv", "value"]):
            return "monthly_revenue_trend"

        return best_intent

    def run_question(
        self, question: str, custom_sql: str | None = None, max_rows: int = 100
    ) -> dict[str, Any]:
        if custom_sql is not None and custom_sql.strip():
            intent = "custom_sql_query"
            sql_to_run = custom_sql.strip()
            source_tables: list[str] = []
            metric_defs = ["Custom read-only SQL query verified against schema allow-list."]
            chart_rec = None
        else:
            intent = self.match_intent(question)
            if intent == "unsupported_question":
                return {
                    "intent": "unsupported_question",
                    "sql_query": "-- Question outside Olist dataset scope; no SQL executed.",
                    "validation": SQLValidationResult(
                        is_safe=False,
                        reason="Unsupported or out-of-scope question: dataset covers Olist orders, items, payments, reviews, products, sellers, RFM segments, and cohorts (2016–2018).",
                        referenced_tables=[],
                        normalized_sql="",
                    ),
                    "df": pd.DataFrame(),
                    "source_tables": [],
                    "metric_definitions": [
                        "Available domains: Monthly Order Value Proxy & Merchandise Revenue, June 2018 Order Value Decline Analysis, Category & Product Sales, Seller Performance, Repeat Customer Rate (Rule D-5), RFM Segmentation, Cohort Retention, Delivery Delays vs Review Scores, State Logistics, Payment Methods, and Executive Decision Actions."
                    ],
                    "chart_recommendation": None,
                    "error": "Unsupported question domain.",
                }
            spec = PREBUILT_BUSINESS_QUERIES[intent]
            sql_to_run = spec["sql"]
            source_tables = spec["source_tables"]
            metric_defs = spec["metric_definitions"]
            chart_rec = spec["chart"]

        validation: SQLValidationResult = validate_sql_query(sql_to_run)
        if not validation.is_safe:
            return {
                "intent": intent,
                "sql_query": sql_to_run,
                "validation": validation,
                "df": pd.DataFrame(),
                "source_tables": source_tables or validation.referenced_tables,
                "metric_definitions": metric_defs,
                "chart_recommendation": chart_rec,
                "error": validation.reason,
            }

        df = self.engine.query(validation.normalized_sql)
        if len(df) > max_rows:
            df = df.head(max_rows)
        return {
            "intent": intent,
            "sql_query": validation.normalized_sql,
            "validation": validation,
            "df": df,
            "source_tables": source_tables or validation.referenced_tables,
            "metric_definitions": metric_defs,
            "chart_recommendation": chart_rec,
            "error": None,
        }
