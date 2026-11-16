"""
Customer Analytics Agent
=========================
Interprets verified RFM customer segmentation, repeat-purchase sensitivity
definitions (Rule D-5 vs options a and c), cohort retention matrices, and
historical Customer Lifetime Value (CLV) proxy results.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


class CustomerAnalyticsAgent:
    """Provides verified customer segmentation, cohort retention, and CLV intelligence."""

    def __init__(self) -> None:
        self.sql_out = ROOT / "reports" / "sql_outputs"
        self.summary_path = ROOT / "reports" / "analytics_summary.json"

    def run(self) -> dict[str, Any]:
        summary = json.loads(self.summary_path.read_text(encoding="utf-8"))
        rfm_df = pd.read_csv(self.sql_out / "vw_rfm_segments_summary.csv").sort_values(
            "customer_count", ascending=False
        )
        clv_df = pd.read_csv(
            self.sql_out / "03_customer_lifetime_value_proxy_result_2.csv"
        )
        cohort_df = pd.read_csv(
            self.sql_out / "01_cohort_retention_analysis_result_2.csv"
        )

        # Find strongest and weakest M+1 retention cohorts (excluding 2018-08 which is right-censored at M+1)
        valid_m1 = cohort_df[cohort_df["cohort_month"] < "2018-08"].sort_values(
            "m1_pct", ascending=False
        )
        best_cohort = valid_m1.iloc[0].to_dict()
        weakest_cohort = valid_m1.iloc[-1].to_dict()

        return {
            "agent": "CustomerAnalyticsAgent",
            "status": "success",
            "total_delivered_customers": 93358,
            "retention_metrics": summary["retention_metrics"],
            "rfm_segments": rfm_df.to_dict(orient="records"),
            "clv_behaviour_groups": clv_df.to_dict(orient="records"),
            "cohort_m1_best": {
                "cohort_month": best_cohort["cohort_month"],
                "cohort_size": int(best_cohort["cohort_size"]),
                "m1_retention_pct": float(best_cohort["m1_pct"]),
            },
            "cohort_m1_weakest": {
                "cohort_month": weakest_cohort["cohort_month"],
                "cohort_size": int(weakest_cohort["cohort_size"]),
                "m1_retention_pct": float(weakest_cohort["m1_pct"]),
            },
            "analytical_inactivity_sensitivity": summary[
                "analytical_inactivity_sensitivity_not_observed_churn"
            ],
        }

