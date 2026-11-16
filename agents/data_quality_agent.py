"""
Data Quality Agent
===================
Surfaces measured data quality findings, flag counts, grain rules, and
financial reconciliation checks from `phase3_quality_results.json` and
`cleaning_log.json`. Never modifies raw data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class DataQualityAgent:
    """Inspects and reports verified data quality flags and reconciliation checks."""

    def __init__(self) -> None:
        self.phase3_path = ROOT / "reports" / "data_quality" / "phase3_quality_results.json"
        self.clean_log_path = ROOT / "reports" / "data_quality" / "cleaning_log.json"

    def run(self) -> dict[str, Any]:
        p3 = json.loads(self.phase3_path.read_text(encoding="utf-8"))
        clean_log = json.loads(self.clean_log_path.read_text(encoding="utf-8"))

        return {
            "agent": "DataQualityAgent",
            "status": "success",
            "raw_files_unchanged": bool(clean_log["validation_checks"]["raw_files_unchanged"]),
            "all_cleaning_checks_passed": bool(clean_log["all_checks_passed"]),
            "quality_flag_counts": clean_log["quality_flag_counts"],
            "financial_reconciliation_brl": clean_log["reconciliation"],
            "primary_key_checks": p3["primary_keys"],
            "chronology_violations": p3["chronology_violations"],
            "recommendations_applied": [
                "Flagged 8 delivered orders missing customer delivery date (excluded from delivery-time averages only).",
                "Preserved 1 delivered order missing payment record as NULL payment_value rather than 0.",
                "Aggregated order_items, order_payments, and order_reviews to order_id prior to joining.",
                "Deduplicated geolocation_zip_lookup to 17,737 valid within-Brazil ZIP centroids.",
                "Mapped 610 unassigned product categories to 'Unknown' and added 2 documented manual category translations.",
            ],
        }

