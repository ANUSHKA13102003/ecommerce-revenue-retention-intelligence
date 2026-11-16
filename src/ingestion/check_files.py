"""
check_files.py — Quick file existence checker
==============================================
Run this script to verify all required Olist CSV files
are present in data/raw/.

Usage:
    python src/ingestion/check_files.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"

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


def check_files() -> bool:
    """
    Check that all expected CSV files exist in data/raw/.

    Returns
    -------
    bool
        True if all files are present, False otherwise.
    """
    print(f"Checking for {len(EXPECTED_FILES)} files in: {DATA_RAW}\n")

    all_found = True
    missing = []

    for fname in EXPECTED_FILES:
        fpath = DATA_RAW / fname
        if fpath.exists():
            size_mb = fpath.stat().st_size / (1024 ** 2)
            print(f"  ✓  {fname}  ({size_mb:.2f} MB)")
        else:
            all_found = False
            missing.append(fname)
            print(f"  ✗  {fname}  — MISSING")

    print()
    if all_found:
        print("All files present. ✓")
    else:
        print(f"MISSING {len(missing)} file(s):")
        for m in missing:
            print(f"  - {m}")
        print()
        print("Download the dataset from:")
        print("  https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce")
        print()
        print("Extract the ZIP and place all CSV files in:")
        print(f"  {DATA_RAW}")

    return all_found


if __name__ == "__main__":
    ok = check_files()
    sys.exit(0 if ok else 1)

