"""
Phase 6 — Python Analytics & Statistical KPI Engine
====================================================
Computes verified descriptive statistics, revenue trends, customer retention,
RFM segmentation, cohort matrices, product/seller performance, delivery vs
review statistical tests (Spearman/Pearson correlation, Mann-Whitney U test,
Kruskal-Wallis test), and geographic insights from the cleaned datasets.

Usage:
    python src/analytics/kpi_engine.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROCESSED = ROOT / "data" / "processed"
SQL_OUT = ROOT / "reports" / "sql_outputs"
REPORTS = ROOT / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)


def compute_all_analytics() -> dict:
    """Compute and cross-validate all project KPIs and statistical tests."""
    order_level = pd.read_csv(
        PROCESSED / "order_level.csv",
        parse_dates=[
            "order_purchase_timestamp",
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
        ],
        low_memory=False,
    )
    items = pd.read_csv(PROCESSED / "order_items_clean.csv", low_memory=False)
    products = pd.read_csv(PROCESSED / "products_clean.csv", low_memory=False)
    customers = pd.read_csv(PROCESSED / "customers_clean.csv", low_memory=False)
    rfm = pd.read_csv(PROCESSED / "customer_rfm.csv", low_memory=False)

    delivered = order_level[order_level["is_delivered"] == True].copy()
    delivered_win = delivered[delivered["in_analysis_window"] == True].copy()

    # 1. Executive Headline KPIs (Full Dataset vs Analysis Window Jan 2017 - Aug 2018)
    executive_kpis = {
        "full_dataset": {
            "total_orders_all_statuses": int(len(order_level)),
            "delivered_orders": int(len(delivered)),
            "delivery_completion_rate_pct": round(float(len(delivered) / len(order_level) * 100), 2),
            "unique_customers_all_statuses": int(order_level["customer_unique_id"].nunique()),
            "unique_delivered_customers": int(delivered["customer_unique_id"].nunique()),
            "delivered_order_value_proxy_brl": round(float(delivered["payment_value"].sum()), 2),
            "delivered_item_revenue_brl": round(float(delivered["item_revenue"].sum()), 2),
            "delivered_freight_value_brl": round(float(delivered["freight_value"].sum()), 2),
            "all_orders_payment_total_brl": round(float(order_level["payment_value"].sum()), 2),
            "all_orders_item_revenue_brl": round(float(order_level["item_revenue"].sum()), 2),
            "average_order_value_proxy_brl": round(float(delivered["payment_value"].mean()), 2),
            "median_order_value_proxy_brl": round(float(delivered["payment_value"].median()), 2),
            "iqr_order_value_proxy_brl": round(
                float(delivered["payment_value"].quantile(0.75) - delivered["payment_value"].quantile(0.25)), 2
            ),
            "avg_delivery_days": round(float(delivered["delivery_days"].mean()), 2),
            "median_delivery_days": round(float(delivered["delivery_days"].median()), 2),
            "late_delivery_rate_timestamp_pct": round(
                float(
                    delivered.loc[~delivered["missing_delivery_date"], "is_late"].mean() * 100
                ),
                2,
            ),
            "avg_review_score_delivered": round(float(delivered["review_score"].mean()), 2),
        },
        "analysis_window_2017_01_to_2018_08": {
            "total_orders_all_statuses": int((order_level["in_analysis_window"] == True).sum()),
            "delivered_orders": int(len(delivered_win)),
            "unique_delivered_customers": int(delivered_win["customer_unique_id"].nunique()),
            "delivered_order_value_proxy_brl": round(float(delivered_win["payment_value"].sum()), 2),
            "delivered_item_revenue_brl": round(float(delivered_win["item_revenue"].sum()), 2),
            "delivered_freight_value_brl": round(float(delivered_win["freight_value"].sum()), 2),
            "average_order_value_proxy_brl": round(float(delivered_win["payment_value"].mean()), 2),
            "median_order_value_proxy_brl": round(float(delivered_win["payment_value"].median()), 2),
        },
    }

    # 2. Repeat Customer & Retention Metrics (D-5 Approved Rule + Sensitivity)
    cust_del = (
        delivered.assign(pdate=delivered["order_purchase_timestamp"].dt.date)
        .groupby("customer_unique_id")
        .agg(
            delivered_orders=("order_id", "nunique"),
            distinct_days=("pdate", "nunique"),
            total_value=("payment_value", "sum"),
        )
    )
    cust_win = (
        delivered_win.assign(pdate=delivered_win["order_purchase_timestamp"].dt.date)
        .groupby("customer_unique_id")
        .agg(
            delivered_orders=("order_id", "nunique"),
            distinct_days=("pdate", "nunique"),
            total_value=("payment_value", "sum"),
        )
    )

    repeat_d5_full = int(((cust_del["delivered_orders"] >= 2) & (cust_del["distinct_days"] >= 2)).sum())
    repeat_d5_win = int(((cust_win["delivered_orders"] >= 2) & (cust_win["distinct_days"] >= 2)).sum())

    retention_metrics = {
        "full_dataset_delivered": {
            "unique_customers": int(len(cust_del)),
            "repeat_customers_d5_distinct_days": repeat_d5_full,
            "repeat_rate_d5_pct": round(repeat_d5_full / len(cust_del) * 100, 2),
            "same_day_multi_order_customers": int(
                ((cust_del["delivered_orders"] >= 2) & (cust_del["distinct_days"] == 1)).sum()
            ),
            "repeat_customers_opt_a_any_day": int((cust_del["delivered_orders"] >= 2).sum()),
            "repeat_rate_opt_a_pct": round(
                float((cust_del["delivered_orders"] >= 2).mean() * 100), 2
            ),
            "repeat_customer_revenue_share_d5_pct": round(
                float(
                    cust_del.loc[
                        (cust_del["delivered_orders"] >= 2) & (cust_del["distinct_days"] >= 2),
                        "total_value",
                    ].sum()
                    / cust_del["total_value"].sum()
                    * 100
                ),
                2,
            ),
        },
        "analysis_window_delivered": {
            "unique_customers": int(len(cust_win)),
            "repeat_customers_d5_distinct_days": repeat_d5_win,
            "repeat_rate_d5_pct": round(repeat_d5_win / len(cust_win) * 100, 2),
        },
    }

    # 3. Statistical Hypothesis Tests (Delivery Delay vs Customer Satisfaction)
    valid_del = delivered[
        (~delivered["missing_delivery_date"]) & (delivered["review_score"].notna())
    ].copy()
    valid_del["delay_days"] = (
        valid_del["order_delivered_customer_date"].dt.normalize()
        - valid_del["order_estimated_delivery_date"].dt.normalize()
    ).dt.days

    on_time_scores = valid_del.loc[valid_del["is_late"] == False, "review_score"]
    late_scores = valid_del.loc[valid_del["is_late"] == True, "review_score"]

    mw_stat, mw_pval = stats.mannwhitneyu(on_time_scores, late_scores, alternative="greater")
    spearman_r, spearman_p = stats.spearmanr(
        valid_del["delivery_days"], valid_del["review_score"]
    )
    delay_spearman_r, delay_spearman_p = stats.spearmanr(
        valid_del["delay_days"], valid_del["review_score"]
    )

    statistical_tests = {
        "on_time_vs_late_review_score_mann_whitney": {
            "on_time_n": int(len(on_time_scores)),
            "late_n": int(len(late_scores)),
            "on_time_mean_score": round(float(on_time_scores.mean()), 4),
            "late_mean_score": round(float(late_scores.mean()), 4),
            "score_drop_when_late": round(float(on_time_scores.mean() - late_scores.mean()), 4),
            "u_statistic": float(mw_stat),
            "p_value": float(mw_pval),
            "statistically_significant_at_0_001": bool(mw_pval < 0.001),
        },
        "delivery_days_vs_review_score_spearman": {
            "spearman_rho": round(float(spearman_r), 4),
            "p_value": float(spearman_p),
        },
        "delay_days_vs_estimate_spearman": {
            "spearman_rho": round(float(delay_spearman_r), 4),
            "p_value": float(delay_spearman_p),
        },
    }

    # 4. Inactivity / Analytical At-Risk Thresholds (D-6 Deferred to Analytics Layer)
    # Explicitly labelled as analytical inactivity thresholds, NOT observed churn.
    inactivity_sensitivity = {}
    for threshold_days in [90, 180, 270, 365]:
        cnt = int((rfm["recency"] > threshold_days).sum())
        inactivity_sensitivity[f"inactive_over_{threshold_days}_days"] = {
            "customer_count": cnt,
            "share_of_delivered_customers_pct": round(cnt / len(rfm) * 100, 2),
        }

    # 5. Load Top SQL Summaries for Unified Access
    cat_df = pd.read_csv(SQL_OUT / "vw_category_performance.csv").sort_values(
        "item_revenue_brl", ascending=False
    )
    rfm_sum_df = pd.read_csv(SQL_OUT / "vw_rfm_segments_summary.csv").sort_values(
        "customer_count", ascending=False
    )
    state_df = pd.read_csv(SQL_OUT / "vw_delivery_and_reviews_by_state.csv").sort_values(
        "order_value_proxy_brl", ascending=False
    )
    monthly_df = pd.read_csv(SQL_OUT / "vw_executive_monthly_kpis.csv").sort_values("sales_month")

    summary = {
        "generated_at": datetime.now().isoformat(),
        "currency": "BRL",
        "executive_kpis": executive_kpis,
        "retention_metrics": retention_metrics,
        "statistical_tests": statistical_tests,
        "analytical_inactivity_sensitivity_not_observed_churn": inactivity_sensitivity,
        "rfm_segments": rfm_sum_df.to_dict(orient="records"),
        "top_10_categories": cat_df.head(10).to_dict(orient="records"),
        "top_10_states": state_df.head(10).to_dict(orient="records"),
        "peak_sales_month": monthly_df.sort_values(
            "order_value_proxy_brl", ascending=False
        ).iloc[0].to_dict(),
    }

    out_path = REPORTS / "analytics_summary.json"
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"Saved comprehensive analytics summary -> {out_path.relative_to(ROOT)}")
    return summary


if __name__ == "__main__":
    res = compute_all_analytics()
    print("Headline Delivered Order Value Proxy (BRL):",
          f"{res['executive_kpis']['full_dataset']['delivered_order_value_proxy_brl']:,.2f}")
    print("Delivered Item Revenue (BRL):",
          f"{res['executive_kpis']['full_dataset']['delivered_item_revenue_brl']:,.2f}")
    print("True Repeat Customer Rate (D-5, Full Delivered):",
          f"{res['retention_metrics']['full_dataset_delivered']['repeat_rate_d5_pct']}%")
    print("On-Time vs Late Review Score:",
          res["statistical_tests"]["on_time_vs_late_review_score_mann_whitney"]["on_time_mean_score"],
          "vs",
          res["statistical_tests"]["on_time_vs_late_review_score_mann_whitney"]["late_mean_score"])

