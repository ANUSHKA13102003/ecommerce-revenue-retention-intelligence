"""
Data Profiler Agent
====================
Inspects validated table schemas, row counts, missing value distributions,
and date ranges from `reports/dataset_metadata.json` and `cleaning_log.json`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class DataProfilerAgent:
    """Returns structured schema and profiling metadata for raw and cleaned datasets."""

    def __init__(self) -> None:
        self.meta_path = ROOT / "reports" / "dataset_metadata.json"
        self.clean_log_path = ROOT / "reports" / "data_quality" / "cleaning_log.json"

    def run(self) -> dict[str, Any]:
        meta = json.loads(self.meta_path.read_text(encoding="utf-8"))
        clean_log = json.loads(self.clean_log_path.read_text(encoding="utf-8"))

        table_summaries = []
        for fname, prof in meta.get("profiles", {}).items():
            table_summaries.append(
                {
                    "filename": fname,
                    "rows": prof["rows"],
                    "columns": prof["columns"],
                    "column_names": prof["column_names"],
                    "duplicate_rows": prof["duplicate_rows"],
                    "missing_pct_overall": prof["missing_pct_overall"],
                    "date_ranges": prof.get("date_ranges", {}),
                }
            )

        return {
            "agent": "DataProfilerAgent",
            "status": "success",
            "raw_total_files": meta["total_files"],
            "raw_total_rows": meta["total_rows"],
            "raw_total_size_human": meta["total_raw_size_human"],
            "cleaned_table_row_counts": clean_log["output_row_counts"],
            "raw_table_profiles": table_summaries,
        }

