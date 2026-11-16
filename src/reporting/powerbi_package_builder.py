"""
Phase 8 — Power BI Star-Schema Data Export & Date Table Builder
================================================================
Generates clean, star-schema-ready CSV exports in `powerbi/data_exports/`
(including `dim_date.csv`, pre-reconciled summary tables with explicit
`YYYY-MM-01` date keys, and `star_schema_relationships.json`) so Power BI
Desktop can connect either via MySQL (`ecommerce_analytics` tables/views)
or via direct CSV import.

Usage:
    python src/reporting/powerbi_package_builder.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SQL_OUT = ROOT / "reports" / "sql_outputs"
PBI_EXPORTS = ROOT / "powerbi" / "data_exports"
PBI_EXPORTS.mkdir(parents=True, exist_ok=True)


def build_dim_date(start_date: str = "2016-01-01", end_date: str = "2018-12-31") -> pd.DataFrame:
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    df = pd.DataFrame({"date_key": dates.strftime("%Y-%m-%d")})
    df["year"] = dates.year
    df["quarter_num"] = dates.quarter
    df["quarter_label"] = "Q" + dates.quarter.astype(str) + " " + dates.year.astype(str)
    df["month_num"] = dates.month
    df["year_month"] = dates.strftime("%Y-%m")
    df["month_start_date"] = dates.strftime("%Y-%m-01")
    df["month_name"] = dates.strftime("%B")
    df["month_short"] = dates.strftime("%b %Y")
    df["day_of_month"] = dates.day
    df["day_of_week_num"] = dates.day_of_week + 1
    df["day_name"] = dates.strftime("%A")
    df["is_weekend"] = dates.day_of_week.isin([5, 6])
    df["in_analysis_window"] = (dates >= pd.Timestamp("2017-01-01")) & (
        dates < pd.Timestamp("2018-09-01")
    )
    return df


def build_powerbi_exports() -> list[Path]:
    saved: list[Path] = []

    # 1. Date Dimension Table (PK: date_key, 1,096 rows)
    dim_date = build_dim_date()
    p_date = PBI_EXPORTS / "dim_date.csv"
    dim_date.to_csv(p_date, index=False)
    saved.append(p_date)

    # 2. Export all validated analytical views & cohort/delivery tables with date keys
    view_files = {
        "vw_executive_monthly_kpis.csv": "pbi_monthly_kpis.csv",
        "vw_category_performance.csv": "pbi_category_performance.csv",
        "vw_seller_performance.csv": "pbi_seller_performance.csv",
        "vw_rfm_segments_summary.csv": "pbi_rfm_segments_summary.csv",
        "vw_delivery_and_reviews_by_state.csv": "pbi_state_performance.csv",
        "vw_payment_method_summary.csv": "pbi_payment_methods.csv",
        "vw_order_status_summary.csv": "pbi_order_status_summary.csv",
        "01_cohort_retention_analysis_result_1.csv": "pbi_cohort_retention_long.csv",
        "01_cohort_retention_analysis_result_2.csv": "pbi_cohort_retention_matrix.csv",
        "04_delivery_and_satisfaction_analysis_result_2.csv": "pbi_delivery_delay_buckets.csv",
        "03_customer_lifetime_value_proxy_result_2.csv": "pbi_customer_clv_groups.csv",
    }

    for src_name, dst_name in view_files.items():
        src = SQL_OUT / src_name
        dst = PBI_EXPORTS / dst_name
        if src.exists():
            df_v = pd.read_csv(src)
            if "sales_month" in df_v.columns and "month_start_date" not in df_v.columns:
                df_v.insert(1, "month_start_date", df_v["sales_month"].astype(str) + "-01")
            if "cohort_month" in df_v.columns and "cohort_start_date" not in df_v.columns:
                df_v.insert(1, "cohort_start_date", df_v["cohort_month"].astype(str) + "-01")
            df_v.to_csv(dst, index=False)
            saved.append(dst)

    # 3. Export Star-Schema Metadata & Relationship Specification
    rel_manifest = {
        "currency": "BRL (R$ #,##0.00)",
        "primary_analysis_window": "2017-01-01 to 2018-08-31",
        "granular_star_schema_relationships": [
            {
                "from_table": "order_level",
                "from_column": "PurchaseDate (Date.From([order_purchase_timestamp]))",
                "to_table": "dim_date",
                "to_column": "date_key",
                "cardinality": "Many-to-One (*:1)",
                "cross_filter_direction": "Single (dim_date filters order_level)",
            },
            {
                "from_table": "order_items_clean",
                "from_column": "order_id",
                "to_table": "order_level",
                "to_column": "order_id",
                "cardinality": "Many-to-One (*:1)",
                "cross_filter_direction": "Single (order_level filters order_items_clean)",
            },
            {
                "from_table": "order_items_clean",
                "from_column": "product_id",
                "to_table": "products_clean",
                "to_column": "product_id",
                "cardinality": "Many-to-One (*:1)",
                "cross_filter_direction": "Single (products_clean filters order_items_clean)",
            },
            {
                "from_table": "order_items_clean",
                "from_column": "seller_id",
                "to_table": "sellers_clean",
                "to_column": "seller_id",
                "cardinality": "Many-to-One (*:1)",
                "cross_filter_direction": "Single (sellers_clean filters order_items_clean)",
            },
            {
                "from_table": "order_level",
                "from_column": "customer_id",
                "to_table": "customers_clean",
                "to_column": "customer_id",
                "cardinality": "One-to-One (1:1)",
                "cross_filter_direction": "Single (customers_clean filters order_level)",
            },
            {
                "from_table": "order_level",
                "from_column": "customer_unique_id",
                "to_table": "customer_rfm",
                "to_column": "customer_unique_id",
                "cardinality": "Many-to-One (*:1)",
                "cross_filter_direction": "Single (customer_rfm filters order_level on delivered orders)",
            },
            {
                "from_table": "payments_clean",
                "from_column": "order_id",
                "to_table": "order_level",
                "to_column": "order_id",
                "cardinality": "Many-to-One (*:1)",
                "cross_filter_direction": "Single (order_level filters payments_clean)",
            },
        ],
        "summary_mart_relationships": [
            {
                "from_table": "pbi_monthly_kpis",
                "from_column": "month_start_date",
                "to_table": "dim_date",
                "to_column": "date_key",
                "cardinality": "Many-to-One (*:1)",
                "cross_filter_direction": "Single",
            },
            {
                "from_table": "pbi_cohort_retention_long",
                "from_column": "cohort_start_date",
                "to_table": "dim_date",
                "to_column": "date_key",
                "cardinality": "Many-to-One (*:1)",
                "cross_filter_direction": "Single",
            },
            {
                "from_table": "pbi_cohort_retention_matrix",
                "from_column": "cohort_start_date",
                "to_table": "dim_date",
                "to_column": "date_key",
                "cardinality": "Many-to-One (*:1)",
                "cross_filter_direction": "Single",
            },
        ],
    }
    rel_path = PBI_EXPORTS / "star_schema_relationships.json"
    rel_path.write_text(json.dumps(rel_manifest, indent=2), encoding="utf-8")
    saved.append(rel_path)

    return saved


if __name__ == "__main__":
    paths = build_powerbi_exports()
    print(f"Prepared {len(paths)} Power BI exports in {PBI_EXPORTS.relative_to(ROOT)}:")
    for p in paths:
        print(f"  ✓ {p.name} ({p.stat().st_size / 1024:.1f} KB)")
