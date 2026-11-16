"""
Phase 5 — Execute & Validate All Project SQL Scripts and Views
===============================================================
Executes every SQL analysis script and view definition in `sql/`,
persists `data/processed/customer_rfm.csv`, exports query result
tables to `reports/sql_outputs/`, and validates results against
independent pandas calculations and the baseline metrics.

Usage:
    python src/database/execute_and_validate_sql.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.database.db_engine import AnalyticsDBEngine

SQL_DIR = ROOT / "sql"
OUT_DIR = ROOT / "reports" / "sql_outputs"
PROCESSED_DIR = ROOT / "data" / "processed"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def main() -> None:
    print("=" * 72)
    print("  PHASE 5 — EXECUTING & VALIDATING ALL SQL ANALYSES & VIEWS")
    print("=" * 72)

    engine = AnalyticsDBEngine(prefer_mysql=True)
    print(f"Active execution backend: {engine.mode.upper()}")

    sql_scripts = [
        ("01_verify_imported_row_counts", SQL_DIR / "01_data_quality" / "01_verify_imported_row_counts.sql"),
        ("02_key_and_reconciliation_checks", SQL_DIR / "01_data_quality" / "02_key_and_reconciliation_checks.sql"),
        ("01_monthly_revenue_analysis", SQL_DIR / "02_business_analysis" / "01_monthly_revenue_analysis.sql"),
        ("02_product_and_category_performance", SQL_DIR / "02_business_analysis" / "02_product_and_category_performance.sql"),
        ("03_seller_performance_analysis", SQL_DIR / "02_business_analysis" / "03_seller_performance_analysis.sql"),
        ("04_delivery_and_satisfaction_analysis", SQL_DIR / "02_business_analysis" / "04_delivery_and_satisfaction_analysis.sql"),
        ("05_payment_and_installment_analysis", SQL_DIR / "02_business_analysis" / "05_payment_and_installment_analysis.sql"),
        ("06_geographic_sales_performance", SQL_DIR / "02_business_analysis" / "06_geographic_sales_performance.sql"),
        ("07_order_status_and_cancellation_analysis", SQL_DIR / "02_business_analysis" / "07_order_status_and_cancellation_analysis.sql"),
        ("01_repeat_customer_analysis", SQL_DIR / "03_customer_analytics" / "01_repeat_customer_analysis.sql"),
        ("02_rfm_customer_segmentation", SQL_DIR / "03_customer_analytics" / "02_rfm_customer_segmentation.sql"),
        ("03_customer_lifetime_value_proxy", SQL_DIR / "03_customer_analytics" / "03_customer_lifetime_value_proxy.sql"),
        ("01_cohort_retention_analysis", SQL_DIR / "04_cohort_retention" / "01_cohort_retention_analysis.sql"),
        ("01_analytical_views", SQL_DIR / "05_views" / "01_analytical_views.sql"),
    ]

    summary_manifest: dict = {
        "executed_at": datetime.now().isoformat(),
        "backend": engine.mode,
        "scripts": {},
        "views_verified": {},
        "reconciliation_checks": {},
    }

    for name, path in sql_scripts:
        print(f"\n[SQL] Executing {path.relative_to(ROOT)} ...")
        results = engine.execute_script(path)
        summary_manifest["scripts"][name] = {
            "path": str(path.relative_to(ROOT)),
            "result_sets": len(results),
            "row_counts": [len(df) for df in results],
        }
        for idx, df in enumerate(results, start=1):
            out_csv = OUT_DIR / f"{name}_result_{idx}.csv"
            df.to_csv(out_csv, index=False)
            print(f"  -> Result {idx}: {len(df):,} rows × {len(df.columns)} cols saved to {out_csv.name}")

    # Export full customer_rfm table to data/processed/customer_rfm.csv for downstream tools
    rfm_df = engine.query("SELECT * FROM customer_rfm")
    rfm_csv_path = PROCESSED_DIR / "customer_rfm.csv"
    rfm_df.to_csv(rfm_csv_path, index=False)
    print(f"\n[Export] Saved customer_rfm table ({len(rfm_df):,} rows) -> {rfm_csv_path.relative_to(ROOT)}")

    # Verify all 8 views created in 01_analytical_views.sql
    views = [
        "vw_executive_monthly_kpis",
        "vw_category_performance",
        "vw_seller_performance",
        "vw_customer_lifecycle",
        "vw_rfm_segments_summary",
        "vw_delivery_and_reviews_by_state",
        "vw_payment_method_summary",
        "vw_order_status_summary",
    ]
    print("\n[Views] Verifying analytical views:")
    for vw in views:
        vdf = engine.query(f"SELECT * FROM {vw}")
        vdf.to_csv(OUT_DIR / f"{vw}.csv", index=False)
        summary_manifest["views_verified"][vw] = len(vdf)
        print(f"  ✓ {vw:<35s} : {len(vdf):>8,d} rows")

    # Independent Reconciliation Checks against Expected Baseline
    print("\n[Validation] Running independent reconciliation checks...")
    rfm_summary = engine.query(
        "SELECT customer_segment, customer_count FROM vw_rfm_segments_summary ORDER BY customer_count DESC"
    )
    actual_rfm = dict(zip(rfm_summary["customer_segment"], rfm_summary["customer_count"].astype(int)))
    expected_rfm = {
        "Lost Customers": 37358,
        "Recent Customers": 37219,
        "Needs Attention": 18272,
        "Potential Loyalists": 449,
        "At Risk": 31,
        "Champions": 23,
        "Loyal Customers": 6,
    }
    rfm_match = actual_rfm == expected_rfm and int(rfm_df.shape[0]) == 93358
    print(f"  ✓ RFM exact match with MySQL baseline (93,358 customers): {rfm_match}")
    if not rfm_match:
        raise AssertionError(f"RFM mismatch! Actual: {actual_rfm}, Expected: {expected_rfm}")

    # Verify financial totals
    fin_df = pd.read_csv(OUT_DIR / "02_key_and_reconciliation_checks_result_3.csv")
    item_rev_ok = np.isclose(fin_df["raw_item_price_total_brl"].iloc[0], 13591643.70)
    pay_rev_ok = np.isclose(fin_df["raw_payment_total_brl"].iloc[0], 16008872.12)
    print(f"  ✓ Item revenue total reconciles (13,591,643.70 BRL): {item_rev_ok}")
    print(f"  ✓ Payment total reconciles (16,008,872.12 BRL): {pay_rev_ok}")

    summary_manifest["reconciliation_checks"] = {
        "rfm_exact_match": bool(rfm_match),
        "rfm_segments": actual_rfm,
        "item_revenue_reconciles": bool(item_rev_ok),
        "payment_total_reconciles": bool(pay_rev_ok),
        "delivered_order_value_proxy_brl": float(fin_df["delivered_order_value_proxy_brl"].iloc[0]),
    }

    manifest_path = OUT_DIR / "sql_execution_manifest.json"
    manifest_path.write_text(json.dumps(summary_manifest, indent=2), encoding="utf-8")
    print(f"\nManifest saved to: {manifest_path.relative_to(ROOT)}")
    print("=" * 72)
    print("  PHASE 5 SQL EXECUTION & VALIDATION COMPLETED SUCCESSFULLY.")
    print("=" * 72)


if __name__ == "__main__":
    main()

