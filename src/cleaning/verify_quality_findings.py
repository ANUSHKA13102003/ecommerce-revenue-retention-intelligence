"""
Independent cross-check of key Phase 3 findings.
Uses different code paths (merge indicators, set arithmetic, SQL-like
groupbys) than quality_assessment.py so that a bug in one script is
unlikely to be reproduced in the other. Read-only.

Usage:
    python src/cleaning/verify_quality_findings.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
RES = json.load(open(ROOT / "reports" / "data_quality" / "phase3_quality_results.json", encoding="utf-8"))

od = pd.read_csv(RAW / "olist_orders_dataset.csv")
cu = pd.read_csv(RAW / "olist_customers_dataset.csv")
it = pd.read_csv(RAW / "olist_order_items_dataset.csv")
pa = pd.read_csv(RAW / "olist_order_payments_dataset.csv")
rv = pd.read_csv(RAW / "olist_order_reviews_dataset.csv")
pr = pd.read_csv(RAW / "olist_products_dataset.csv")

checks = []


def check(name, independent, reported):
    ok = independent == reported
    checks.append(ok)
    print(f"{'PASS' if ok else 'FAIL'}  {name}: independent={independent}  reported={reported}")


# Orders without items (merge indicator)
m = od.merge(it[["order_id"]].drop_duplicates(), on="order_id", how="left", indicator=True)
check("orders without items", int((m["_merge"] == "left_only").sum()),
      next(c["parent_rows_without_child"] for c in RES["coverage"] if c["check"] == "orders without items"))

# Orders without payments
check("orders without payments", len(set(od.order_id) - set(pa.order_id)), RES["orders_without_payment"]["count"])

# Repeated review ids
vc = rv["review_id"].value_counts()
check("review_ids repeated", int((vc > 1).sum()), RES["reviews"]["review_ids_repeated"])
check("rows with repeated review_id", int(vc[vc > 1].sum()), RES["reviews"]["rows_with_repeated_review_id"])

# Item rows for products with missing category (merge path)
im = it.merge(pr[["product_id", "product_category_name"]], on="product_id", how="left")
check("item rows with missing category", int(im["product_category_name"].isna().sum()),
      RES["products"]["missing_category_item_rows"])

# Repeat customers (2+ orders, any status)
oc = od.merge(cu, on="customer_id")
n = oc.groupby("customer_unique_id").size()
check("customer_unique_id with 2+ orders", int((n >= 2).sum()),
      RES["customers"]["unique_ids_with_2plus_orders_all_statuses"])

# Delivered status but missing customer delivery date
check("delivered w/o customer date",
      int(((od.order_status == "delivered") & od.order_delivered_customer_date.isna()).sum()),
      RES["delivery_date_consistency"]["delivered_status_missing_customer_date"])

# Carrier date earlier than approval date (string compare works for ISO format)
both = od.dropna(subset=["order_approved_at", "order_delivered_carrier_date"])
check("carrier before approved",
      int((both.order_delivered_carrier_date < both.order_approved_at).sum()),
      RES["chronology_violations"]["carrier_before_approved"])

# Payment vs items reconciliation (cents arithmetic)
p = (pa.assign(c=(pa.payment_value * 100).round()).groupby("order_id")["c"].sum())
i = (it.assign(c=((it.price + it.freight_value) * 100).round()).groupby("order_id")["c"].sum())
j = pd.concat([p, i], axis=1, join="inner", keys=["p", "i"])
check("orders reconciled within 1 cent", int(((j.p - j.i).abs() <= 1).sum()),
      RES["payment_item_reconciliation"]["abs_diff_le_0_01"])

# Total payment value
check("total payment value", round(float(pa.payment_value.sum()), 2),
      RES["payment_item_reconciliation"]["total_payment_all_orders"])

print(f"\n{sum(checks)}/{len(checks)} cross-checks passed")

