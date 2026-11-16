"""
Phase 2 — Data Acquisition Validation & Profiling
===================================================
Reads all 9 Olist CSV files, validates their existence,
and generates a comprehensive metadata report.

RULES:
- Raw files are NEVER modified.
- All results are measured from actual data.
- No fabricated values.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

import pandas as pd
import numpy as np

# ── Project paths ──────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
REPORTS_DIR = PROJECT_ROOT / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ── Expected files ─────────────────────────────────────────
EXPECTED_FILES = [
    "olist_orders_dataset.csv",
    "olist_customers_dataset.csv",
    "olist_order_items_dataset.csv",
    "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset.csv",
    "olist_products_dataset.csv",
    "olist_sellers_dataset.csv",
    "olist_geolocation_dataset.csv",
    "product_category_name_translation.csv",
]

# Columns likely containing dates (for date-range detection)
DATE_COLUMNS = {
    "olist_orders_dataset.csv": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "olist_order_reviews_dataset.csv": [
        "review_creation_date",
        "review_answer_timestamp",
    ],
    "olist_order_items_dataset.csv": [
        "shipping_limit_date",
    ],
}


def format_bytes(size_bytes: int) -> str:
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 ** 2):.2f} MB"


def check_file_existence() -> dict:
    """Check whether all expected files exist."""
    results = {}
    all_found = True
    for fname in EXPECTED_FILES:
        fpath = DATA_RAW / fname
        exists = fpath.exists()
        if not exists:
            all_found = False
        results[fname] = {
            "exists": exists,
            "path": str(fpath),
            "size_bytes": fpath.stat().st_size if exists else 0,
            "size_human": format_bytes(fpath.stat().st_size) if exists else "N/A",
        }
    return results, all_found


def profile_csv(filepath: Path, fname: str) -> dict:
    """
    Profile a single CSV file. Returns structured metadata.
    Does NOT modify the file.
    """
    report = {"filename": fname, "errors": []}

    # ── Read the CSV ───────────────────────────────────────
    try:
        df = pd.read_csv(filepath, low_memory=False)
        report["read_success"] = True
    except Exception as e:
        report["read_success"] = False
        report["errors"].append(f"PARSE ERROR: {str(e)}")
        return report

    # ── Basic shape ────────────────────────────────────────
    report["rows"] = int(df.shape[0])
    report["columns"] = int(df.shape[1])
    report["column_names"] = list(df.columns)

    # ── Data types ─────────────────────────────────────────
    report["dtypes"] = {col: str(dtype) for col, dtype in df.dtypes.items()}

    # ── Memory usage ───────────────────────────────────────
    report["memory_mb"] = round(df.memory_usage(deep=True).sum() / (1024 ** 2), 2)

    # ── Missing values ─────────────────────────────────────
    missing = df.isnull().sum()
    missing_pct = (df.isnull().sum() / len(df) * 100).round(2)
    report["missing_values"] = {
        col: {"count": int(missing[col]), "pct": float(missing_pct[col])}
        for col in df.columns
    }
    report["total_missing_cells"] = int(missing.sum())
    report["total_cells"] = int(df.shape[0] * df.shape[1])
    report["missing_pct_overall"] = round(
        report["total_missing_cells"] / report["total_cells"] * 100, 2
    ) if report["total_cells"] > 0 else 0.0

    # ── Duplicate rows ─────────────────────────────────────
    dup_count = int(df.duplicated().sum())
    report["duplicate_rows"] = dup_count
    report["duplicate_pct"] = round(dup_count / len(df) * 100, 2) if len(df) > 0 else 0.0

    # ── Date ranges ────────────────────────────────────────
    report["date_ranges"] = {}
    if fname in DATE_COLUMNS:
        for col in DATE_COLUMNS[fname]:
            if col in df.columns:
                try:
                    parsed = pd.to_datetime(df[col], errors="coerce")
                    valid = parsed.dropna()
                    if len(valid) > 0:
                        report["date_ranges"][col] = {
                            "min": str(valid.min()),
                            "max": str(valid.max()),
                            "null_count": int(parsed.isnull().sum()),
                            "parse_failures": int(parsed.isnull().sum() - df[col].isnull().sum()),
                        }
                    else:
                        report["date_ranges"][col] = {"min": None, "max": None, "note": "All null or unparseable"}
                except Exception as e:
                    report["date_ranges"][col] = {"error": str(e)}

    # ── Sample values (first 3 unique per column) ──────────
    report["sample_values"] = {}
    for col in df.columns:
        try:
            uniques = df[col].dropna().unique()[:3]
            report["sample_values"][col] = [str(v) for v in uniques]
        except Exception:
            report["sample_values"][col] = []

    # ── Unique counts ──────────────────────────────────────
    report["unique_counts"] = {col: int(df[col].nunique()) for col in df.columns}

    return report


def main():
    print("=" * 70)
    print("  PHASE 2 — DATA ACQUISITION VALIDATION & PROFILING")
    print(f"  Timestamp: {datetime.now().isoformat()}")
    print("=" * 70)

    # ── Step 1: File existence ─────────────────────────────
    print("\n[1/3] Checking file existence...")
    file_results, all_found = check_file_existence()

    for fname, info in file_results.items():
        status = "✓ FOUND" if info["exists"] else "✗ MISSING"
        print(f"  {status}  {fname:45s}  {info['size_human']:>10s}")

    if not all_found:
        missing = [f for f, i in file_results.items() if not i["exists"]]
        print(f"\n  ERROR: {len(missing)} file(s) missing: {missing}")
        print("  Place the missing files in data/raw/ and re-run.")
        sys.exit(1)

    print(f"\n  All {len(EXPECTED_FILES)} files found. ✓")
    total_size = sum(i["size_bytes"] for i in file_results.values())
    print(f"  Total raw data size: {format_bytes(total_size)}")

    # ── Step 2: Profile each CSV ───────────────────────────
    print("\n[2/3] Profiling each CSV file...\n")
    all_profiles = {}

    for fname in EXPECTED_FILES:
        fpath = DATA_RAW / fname
        print(f"  Reading {fname}...", end=" ", flush=True)
        profile = profile_csv(fpath, fname)
        all_profiles[fname] = profile

        if profile["read_success"]:
            print(
                f"OK  ({profile['rows']:,} rows × {profile['columns']} cols, "
                f"{profile['memory_mb']} MB in memory, "
                f"{profile['duplicate_rows']:,} duplicate rows, "
                f"{profile['total_missing_cells']:,} missing cells)"
            )
        else:
            print(f"FAILED — {profile['errors']}")

    # ── Step 3: Generate summary report ────────────────────
    print("\n[3/3] Generating metadata report...\n")

    # Console summary table
    print(f"{'File':<45s} {'Rows':>10s} {'Cols':>5s} {'Dups':>7s} {'Missing':>10s} {'Miss%':>7s}")
    print("-" * 90)
    for fname, p in all_profiles.items():
        if p["read_success"]:
            print(
                f"{fname:<45s} {p['rows']:>10,d} {p['columns']:>5d} "
                f"{p['duplicate_rows']:>7,d} {p['total_missing_cells']:>10,d} "
                f"{p['missing_pct_overall']:>6.2f}%"
            )

    # Total rows across all files
    total_rows = sum(p["rows"] for p in all_profiles.values() if p["read_success"])
    print("-" * 90)
    print(f"{'TOTAL':<45s} {total_rows:>10,d}")

    # Date ranges
    print("\n  DATE RANGES:")
    for fname, p in all_profiles.items():
        if p.get("date_ranges"):
            for col, dr in p["date_ranges"].items():
                if "min" in dr and dr["min"]:
                    print(f"    {fname} → {col}: {dr['min']} to {dr['max']}  (nulls: {dr['null_count']})")

    # Warnings
    warnings = []
    for fname, p in all_profiles.items():
        if p.get("duplicate_rows", 0) > 0:
            warnings.append(f"  ⚠ {fname}: {p['duplicate_rows']:,} duplicate rows detected")
        if p.get("missing_pct_overall", 0) > 5:
            warnings.append(f"  ⚠ {fname}: {p['missing_pct_overall']:.2f}% missing values")

    if warnings:
        print("\n  WARNINGS:")
        for w in warnings:
            print(w)

    # ── Save JSON metadata ─────────────────────────────────
    metadata = {
        "generated_at": datetime.now().isoformat(),
        "data_source": "Olist Brazilian E-Commerce Public Dataset",
        "kaggle_url": "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce",
        "licence": "CC BY-NC-SA 4.0",
        "total_files": len(EXPECTED_FILES),
        "total_raw_size_bytes": total_size,
        "total_raw_size_human": format_bytes(total_size),
        "total_rows": total_rows,
        "file_checks": file_results,
        "profiles": all_profiles,
    }

    json_path = REPORTS_DIR / "dataset_metadata.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
    print(f"\n  Metadata saved to: {json_path}")

    print("\n" + "=" * 70)
    print("  PHASE 2 COMPLETE — All files validated and profiled.")
    print("  Raw files have NOT been modified.")
    print("=" * 70)

    return metadata


if __name__ == "__main__":
    main()
