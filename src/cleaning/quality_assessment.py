"""
Phase 3 — Data Understanding & Quality Assessment (READ-ONLY)
==============================================================
Measures data quality issues across all 9 Olist CSV files.

Guarantees:
- Raw files are opened read-only and NEVER modified.
- SHA-256 hashes are computed before and after the run to prove it.
- No records are removed; all checks only COUNT and FLAG.
- All numbers written to the JSON output are measured from the data.

Usage:
    python src/cleaning/quality_assessment.py

Output:
    reports/data_quality/phase3_quality_results.json
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW = PROJECT_ROOT / "data" / "raw"
OUT_DIR = PROJECT_ROOT / "reports" / "data_quality"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FILES = {
    "orders": "olist_orders_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "items": "olist_order_items_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "translation": "product_category_name_translation.csv",
}

ORDER_DATE_COLS = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

# 27 Brazilian federative units (26 states + Federal District)
BRAZIL_UF = {
    "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
    "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
    "SP", "SE", "TO",
}

# Approximate bounding box of Brazil (documented rule, generous margins)
BRAZIL_LAT = (-33.75, 5.27)
BRAZIL_LNG = (-73.99, -34.79)


# ── helpers ────────────────────────────────────────────────
def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def jsonable(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if np.isnan(o) else float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp, datetime)):
        return str(o)
    if isinstance(o, (pd.Timedelta,)):
        return str(o)
    return str(o)


def pk_check(df: pd.DataFrame, cols: list[str]) -> dict:
    dup_mask = df.duplicated(subset=cols, keep=False)
    return {
        "key": cols,
        "rows": len(df),
        "distinct_keys": int(df[cols].drop_duplicates().shape[0]),
        "null_key_rows": int(df[cols].isnull().any(axis=1).sum()),
        "rows_sharing_a_key": int(dup_mask.sum()),
        "is_unique": bool(not dup_mask.any()),
    }


def fk_check(child, ccol, parent, pcol, name) -> dict:
    vals = child[ccol]
    non_null = vals.dropna()
    parent_set = set(parent[pcol].dropna().unique())
    orphan = ~non_null.isin(parent_set)
    return {
        "relationship": name,
        "child_rows": int(len(vals)),
        "child_null_fk_rows": int(vals.isnull().sum()),
        "orphan_rows": int(orphan.sum()),
        "orphan_distinct_values": int(non_null[orphan].nunique()),
        "orphan_examples": [str(v) for v in non_null[orphan].unique()[:5]],
    }


def coverage(parent, pcol, child, ccol, name) -> dict:
    child_set = set(child[ccol].dropna().unique())
    missing = ~parent[pcol].isin(child_set)
    return {
        "check": name,
        "parent_rows": int(len(parent)),
        "parent_rows_without_child": int(missing.sum()),
        "pct": round(float(missing.mean() * 100), 4),
    }


def numeric_profile(s: pd.Series) -> dict:
    s = s.dropna()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    upper = q3 + 1.5 * iqr
    lower = q1 - 1.5 * iqr
    return {
        "count": int(s.size),
        "min": float(s.min()),
        "p01": float(s.quantile(0.01)),
        "p25": float(q1),
        "median": float(s.median()),
        "mean": round(float(s.mean()), 4),
        "p75": float(q3),
        "p99": float(s.quantile(0.99)),
        "p999": float(s.quantile(0.999)),
        "max": float(s.max()),
        "zero_count": int((s == 0).sum()),
        "negative_count": int((s < 0).sum()),
        "iqr_lower_fence": round(float(lower), 4),
        "iqr_upper_fence": round(float(upper), 4),
        "iqr_outliers_above": int((s > upper).sum()),
        "iqr_outliers_below": int((s < lower).sum()),
    }


def norm_text(x: str) -> str:
    x = unicodedata.normalize("NFKD", str(x)).encode("ascii", "ignore").decode()
    return " ".join(x.lower().strip().split())


# ── main ───────────────────────────────────────────────────
def main() -> dict:
    R: dict = {"generated_at": datetime.now().isoformat()}

    # 0. Immutability: hashes BEFORE
    hashes_before = {k: sha256(RAW / f) for k, f in FILES.items()}

    print("Loading raw CSVs (read-only)...")
    d = {k: pd.read_csv(RAW / f, low_memory=False) for k, f in FILES.items()}

    od, cu, it, pa, rv = d["orders"], d["customers"], d["items"], d["payments"], d["reviews"]
    pr, se, ge, tr = d["products"], d["sellers"], d["geolocation"], d["translation"]

    # In-memory typed copies (raw files untouched)
    odt = od.copy()
    for c in ORDER_DATE_COLS:
        odt[c] = pd.to_datetime(odt[c], errors="coerce")
    itt = it.copy()
    itt["shipping_limit_date"] = pd.to_datetime(itt["shipping_limit_date"], errors="coerce")
    rvt = rv.copy()
    rvt["review_creation_date"] = pd.to_datetime(rvt["review_creation_date"], errors="coerce")
    rvt["review_answer_timestamp"] = pd.to_datetime(rvt["review_answer_timestamp"], errors="coerce")

    # 1. PRIMARY KEYS ───────────────────────────────────────
    print("[1] Primary-key checks")
    R["primary_keys"] = {
        "orders.order_id": pk_check(od, ["order_id"]),
        "customers.customer_id": pk_check(cu, ["customer_id"]),
        "items.(order_id, order_item_id)": pk_check(it, ["order_id", "order_item_id"]),
        "payments.(order_id, payment_sequential)": pk_check(pa, ["order_id", "payment_sequential"]),
        "reviews.review_id": pk_check(rv, ["review_id"]),
        "reviews.(review_id, order_id)": pk_check(rv, ["review_id", "order_id"]),
        "products.product_id": pk_check(pr, ["product_id"]),
        "sellers.seller_id": pk_check(se, ["seller_id"]),
        "translation.product_category_name": pk_check(tr, ["product_category_name"]),
        "geolocation.zip_code_prefix": pk_check(ge, ["geolocation_zip_code_prefix"]),
    }

    # 2. FOREIGN KEYS ───────────────────────────────────────
    print("[2] Foreign-key checks")
    ge_zips = ge[["geolocation_zip_code_prefix"]].drop_duplicates()
    R["foreign_keys"] = [
        fk_check(od, "customer_id", cu, "customer_id", "orders.customer_id -> customers"),
        fk_check(it, "order_id", od, "order_id", "items.order_id -> orders"),
        fk_check(it, "product_id", pr, "product_id", "items.product_id -> products"),
        fk_check(it, "seller_id", se, "seller_id", "items.seller_id -> sellers"),
        fk_check(pa, "order_id", od, "order_id", "payments.order_id -> orders"),
        fk_check(rv, "order_id", od, "order_id", "reviews.order_id -> orders"),
        fk_check(pr, "product_category_name", tr, "product_category_name",
                 "products.category -> translation"),
        fk_check(cu, "customer_zip_code_prefix", ge_zips, "geolocation_zip_code_prefix",
                 "customers.zip -> geolocation"),
        fk_check(se, "seller_zip_code_prefix", ge_zips, "geolocation_zip_code_prefix",
                 "sellers.zip -> geolocation"),
    ]
    R["coverage"] = [
        coverage(od, "order_id", it, "order_id", "orders without items"),
        coverage(od, "order_id", pa, "order_id", "orders without payments"),
        coverage(od, "order_id", rv, "order_id", "orders without reviews"),
        coverage(cu, "customer_id", od, "customer_id", "customers without orders"),
        coverage(pr, "product_id", it, "product_id", "products never sold"),
        coverage(se, "seller_id", it, "seller_id", "sellers never sold"),
    ]
    # status of orders without items
    no_items = od[~od["order_id"].isin(set(it["order_id"]))]
    R["orders_without_items_by_status"] = no_items["order_status"].value_counts().to_dict()

    # 3. ORDER STATUS & MISSING DELIVERY DATES ─────────────
    print("[3] Order status vs missing dates")
    R["order_status_distribution"] = od["order_status"].value_counts().to_dict()
    null_tbl = {}
    for status, g in od.groupby("order_status"):
        null_tbl[status] = {
            "orders": int(len(g)),
            "null_approved_at": int(g["order_approved_at"].isnull().sum()),
            "null_delivered_carrier_date": int(g["order_delivered_carrier_date"].isnull().sum()),
            "null_delivered_customer_date": int(g["order_delivered_customer_date"].isnull().sum()),
        }
    R["missing_dates_by_status"] = null_tbl
    delivered = od[od["order_status"] == "delivered"]
    not_delivered = od[od["order_status"] != "delivered"]
    R["delivery_date_consistency"] = {
        "delivered_status_missing_customer_date": int(delivered["order_delivered_customer_date"].isnull().sum()),
        "delivered_status_missing_carrier_date": int(delivered["order_delivered_carrier_date"].isnull().sum()),
        "delivered_status_missing_approved_at": int(delivered["order_approved_at"].isnull().sum()),
        "non_delivered_status_with_customer_date": int(not_delivered["order_delivered_customer_date"].notnull().sum()),
        "non_delivered_with_customer_date_by_status":
            not_delivered[not_delivered["order_delivered_customer_date"].notnull()]["order_status"]
            .value_counts().to_dict(),
    }

    # 4. CHRONOLOGY / INVALID DATES ─────────────────────────
    print("[4] Date validity & chronology")
    R["date_parse_failures"] = {
        c: int(odt[c].isnull().sum() - od[c].isnull().sum()) for c in ORDER_DATE_COLS
    }
    p, a = odt["order_purchase_timestamp"], odt["order_approved_at"]
    ca, cd = odt["order_delivered_carrier_date"], odt["order_delivered_customer_date"]
    est = odt["order_estimated_delivery_date"]
    R["chronology_violations"] = {
        "approved_before_purchase": int((a < p).sum()),
        "carrier_before_purchase": int((ca < p).sum()),
        "carrier_before_approved": int((ca < a).sum()),
        "customer_delivery_before_purchase": int((cd < p).sum()),
        "customer_delivery_before_carrier": int((cd < ca).sum()),
        "estimated_before_purchase": int((est < p).sum()),
    }
    # Magnitudes for the most common violation types
    diff_ca_a = (a - ca).dt.total_seconds() / 3600
    R["carrier_before_approved_hours"] = (
        numeric_profile(diff_ca_a[ca < a]) if (ca < a).any() else None
    )
    diff_cd_ca = (ca - cd).dt.total_seconds() / 3600
    R["customer_before_carrier_hours"] = (
        numeric_profile(diff_cd_ca[cd < ca]) if (cd < ca).any() else None
    )

    # delivery time distribution for delivered orders (outlier rule)
    del_days = (cd - p).dt.total_seconds() / 86400
    R["delivery_days_profile"] = numeric_profile(del_days[od["order_status"] == "delivered"])

    # purchase month distribution (sparse edges of time window)
    pm = p.dt.to_period("M").astype(str).value_counts().sort_index()
    R["orders_per_purchase_month"] = pm.to_dict()

    # 5. CUSTOMERS ──────────────────────────────────────────
    print("[5] customer_id vs customer_unique_id")
    ids_per_u = cu.groupby("customer_unique_id")["customer_id"].nunique()
    oc = od.merge(cu[["customer_id", "customer_unique_id", "customer_state"]],
                  on="customer_id", how="left", validate="one_to_one")
    orders_per_u = oc.groupby("customer_unique_id")["order_id"].nunique()
    deliv_per_u = (oc[oc["order_status"] == "delivered"]
                   .groupby("customer_unique_id")["order_id"].nunique())
    repeat_u = orders_per_u[orders_per_u > 1].index
    days_per_repeat = (oc[oc["customer_unique_id"].isin(repeat_u)]
                       .assign(day=lambda x: pd.to_datetime(x["order_purchase_timestamp"]).dt.date)
                       .groupby("customer_unique_id")["day"].nunique())
    states_per_u = cu.groupby("customer_unique_id")["customer_state"].nunique()
    R["customers"] = {
        "customer_id_rows": int(len(cu)),
        "customer_id_distinct": int(cu["customer_id"].nunique()),
        "customer_unique_id_distinct": int(cu["customer_unique_id"].nunique()),
        "orders_customer_id_duplicated": int(od["customer_id"].duplicated().sum()),
        "customer_ids_per_unique_id_distribution": ids_per_u.value_counts().sort_index().to_dict(),
        "max_customer_ids_for_one_unique_id": int(ids_per_u.max()),
        "unique_ids_with_2plus_orders_all_statuses": int((orders_per_u > 1).sum()),
        "unique_ids_with_2plus_delivered_orders": int((deliv_per_u > 1).sum()),
        "unique_ids_with_at_least_1_delivered_order": int(deliv_per_u.size),
        "repeat_ids_whose_orders_are_all_same_day": int((days_per_repeat == 1).sum()),
        "repeat_ids_with_orders_on_2plus_days": int((days_per_repeat > 1).sum()),
        "unique_ids_with_multiple_states": int((states_per_u > 1).sum()),
        "invalid_customer_state_codes": int((~cu["customer_state"].isin(BRAZIL_UF)).sum()),
    }

    # 6. MISSING PAYMENT ORDER ──────────────────────────────
    print("[6] Orders missing payments")
    no_pay = od[~od["order_id"].isin(set(pa["order_id"]))]
    no_pay_items = it[it["order_id"].isin(set(no_pay["order_id"]))]
    R["orders_without_payment"] = {
        "count": int(len(no_pay)),
        "records": no_pay.to_dict(orient="records"),
        "item_rows": int(len(no_pay_items)),
        "items_price_sum": round(float(no_pay_items["price"].sum()), 2),
        "items_freight_sum": round(float(no_pay_items["freight_value"].sum()), 2),
        "has_review": bool(no_pay["order_id"].isin(set(rv["order_id"])).any()),
    }

    # payment-level anomalies
    R["payments"] = {
        "payment_type_distribution": pa["payment_type"].value_counts().to_dict(),
        "not_defined_rows": int((pa["payment_type"] == "not_defined").sum()),
        "not_defined_order_status": (
            pa[pa["payment_type"] == "not_defined"]
            .merge(od[["order_id", "order_status"]], on="order_id", how="left")["order_status"]
            .value_counts().to_dict()
        ),
        "not_defined_payment_value_sum": round(float(pa.loc[pa["payment_type"] == "not_defined", "payment_value"].sum()), 2),
        "zero_value_rows": int((pa["payment_value"] == 0).sum()),
        "zero_value_by_type": pa[pa["payment_value"] == 0]["payment_type"].value_counts().to_dict(),
        "zero_installments_rows": int((pa["payment_installments"] == 0).sum()),
        "zero_installments_by_type": pa[pa["payment_installments"] == 0]["payment_type"].value_counts().to_dict(),
        "payments_per_order_distribution": pa.groupby("order_id").size().value_counts().sort_index().head(10).to_dict(),
        "payment_value_profile": numeric_profile(pa["payment_value"]),
        "installments_profile": numeric_profile(pa["payment_installments"]),
    }

    # reconciliation: payments vs items, at ORDER level (grain-safe)
    pay_o = pa.groupby("order_id", as_index=False)["payment_value"].sum()
    itm_o = it.groupby("order_id", as_index=False).agg(price=("price", "sum"),
                                                       freight=("freight_value", "sum"))
    itm_o["items_total"] = itm_o["price"] + itm_o["freight"]
    rec = pay_o.merge(itm_o, on="order_id", how="inner", validate="one_to_one")
    rec["diff"] = (rec["payment_value"] - rec["items_total"]).round(2)
    R["payment_item_reconciliation"] = {
        "orders_with_both": int(len(rec)),
        "abs_diff_le_0_01": int((rec["diff"].abs() <= 0.01).sum()),
        "abs_diff_gt_0_01": int((rec["diff"].abs() > 0.01).sum()),
        "abs_diff_gt_1": int((rec["diff"].abs() > 1).sum()),
        "payment_gt_items_by_more_than_1": int((rec["diff"] > 1).sum()),
        "payment_lt_items_by_more_than_1": int((rec["diff"] < -1).sum()),
        "total_payment_value": round(float(rec["payment_value"].sum()), 2),
        "total_items_value": round(float(rec["items_total"].sum()), 2),
        "total_payment_all_orders": round(float(pa["payment_value"].sum()), 2),
        "total_items_price_all": round(float(it["price"].sum()), 2),
        "total_items_freight_all": round(float(it["freight_value"].sum()), 2),
        "diff_profile_nonzero": numeric_profile(rec.loc[rec["diff"].abs() > 0.01, "diff"]),
    }

    # 7. REVIEWS ────────────────────────────────────────────
    print("[7] Review-ID investigation")
    rep = rv[rv.duplicated("review_id", keep=False)]
    o_c = od[["order_id", "customer_id", "order_purchase_timestamp"]].merge(
        cu[["customer_id", "customer_unique_id"]], on="customer_id", how="left")
    repc = rep.merge(o_c, on="order_id", how="left")
    g = repc.groupby("review_id").agg(
        n_rows=("order_id", "size"),
        n_orders=("order_id", "nunique"),
        n_scores=("review_score", "nunique"),
        n_titles=("review_comment_title", lambda s: s.fillna("<NULL>").nunique()),
        n_msgs=("review_comment_message", lambda s: s.fillna("<NULL>").nunique()),
        n_create=("review_creation_date", "nunique"),
        n_answer=("review_answer_timestamp", "nunique"),
        n_customers=("customer_unique_id", "nunique"),
        n_purchase_ts=("order_purchase_timestamp", "nunique"),
    )
    content_same = (g["n_scores"] == 1) & (g["n_titles"] == 1) & (g["n_msgs"] == 1) & \
                   (g["n_create"] == 1) & (g["n_answer"] == 1)
    rpo = rv.groupby("order_id").size()
    multi_rev_orders = rpo[rpo > 1].index
    scores_multi = rv[rv["order_id"].isin(multi_rev_orders)].groupby("order_id")["review_score"].nunique()
    rv_p = rvt.merge(odt[["order_id", "order_purchase_timestamp"]], on="order_id", how="left")
    R["reviews"] = {
        "rows": int(len(rv)),
        "distinct_review_id": int(rv["review_id"].nunique()),
        "distinct_order_id": int(rv["order_id"].nunique()),
        "exact_duplicate_rows": int(rv.duplicated().sum()),
        "review_ids_repeated": int(len(g)),
        "rows_with_repeated_review_id": int(len(rep)),
        "repeated_id_group_size_distribution": g["n_rows"].value_counts().sort_index().to_dict(),
        "repeated_ids_spanning_different_orders": int((g["n_orders"] > 1).sum()),
        "repeated_ids_same_order_twice": int((g["n_orders"] < g["n_rows"]).sum()),
        "repeated_ids_identical_content": int(content_same.sum()),
        "repeated_ids_differing_content": int((~content_same).sum()),
        "repeated_ids_single_customer": int((g["n_customers"] == 1).sum()),
        "repeated_ids_multiple_customers": int((g["n_customers"] > 1).sum()),
        "repeated_ids_same_purchase_timestamp": int((g["n_purchase_ts"] == 1).sum()),
        "orders_with_multiple_reviews": int(len(multi_rev_orders)),
        "orders_with_multiple_reviews_differing_scores": int((scores_multi > 1).sum()),
        "reviews_per_order_distribution": rpo.value_counts().sort_index().to_dict(),
        "review_score_distribution": rv["review_score"].value_counts().sort_index().to_dict(),
        "answer_before_creation": int((rvt["review_answer_timestamp"] < rvt["review_creation_date"]).sum()),
        "creation_before_purchase_date": int(
            (rv_p["review_creation_date"] < rv_p["order_purchase_timestamp"].dt.normalize()).sum()),
        "null_title": int(rv["review_comment_title"].isnull().sum()),
        "null_message": int(rv["review_comment_message"].isnull().sum()),
    }

    # 8. PRODUCTS & CATEGORIES ──────────────────────────────
    print("[8] Products & categories")
    miss_cat = pr[pr["product_category_name"].isnull()]
    miss_cat_items = it[it["product_id"].isin(set(miss_cat["product_id"]))]
    text_cols = ["product_name_lenght", "product_description_lenght", "product_photos_qty"]
    dim_cols = ["product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"]
    untrans = pr[pr["product_category_name"].notnull() &
                 ~pr["product_category_name"].isin(set(tr["product_category_name"]))]
    untrans_summary = {}
    for cat, gcat in untrans.groupby("product_category_name"):
        ids = set(gcat["product_id"])
        ci = it[it["product_id"].isin(ids)]
        untrans_summary[cat] = {
            "products": int(len(gcat)),
            "item_rows": int(len(ci)),
            "price_sum": round(float(ci["price"].sum()), 2),
        }
    missing_dims = pr[pr[dim_cols].isnull().any(axis=1)]
    R["products"] = {
        "missing_category_products": int(len(miss_cat)),
        "missing_category_also_missing_all_text_attrs": int(miss_cat[text_cols].isnull().all(axis=1).sum()),
        "missing_category_products_sold": int(miss_cat["product_id"].isin(set(it["product_id"])).sum()),
        "missing_category_item_rows": int(len(miss_cat_items)),
        "missing_category_price_sum": round(float(miss_cat_items["price"].sum()), 2),
        "missing_category_price_share_pct": round(float(miss_cat_items["price"].sum() / it["price"].sum() * 100), 4),
        "categories_in_products": int(pr["product_category_name"].nunique()),
        "categories_in_translation": int(tr["product_category_name"].nunique()),
        "untranslated_categories": untrans_summary,
        "translation_entries_unused_by_products": sorted(
            set(tr["product_category_name"]) - set(pr["product_category_name"].dropna())),
        "products_missing_dimensions": int(len(missing_dims)),
        "missing_dimension_records": missing_dims[["product_id", "product_category_name"] + dim_cols].to_dict(orient="records"),
        "missing_dimension_products_sold": int(missing_dims["product_id"].isin(set(it["product_id"])).sum()),
        "zero_weight_products": int((pr["product_weight_g"] == 0).sum()),
        "zero_photos_products": int((pr["product_photos_qty"] == 0).sum()),
        "weight_profile": numeric_profile(pr["product_weight_g"]),
    }

    # 9. ORDER ITEMS: prices, freight, shipping_limit_date ──
    print("[9] Items: price/freight/shipping_limit_date")
    ip = itt.merge(odt[["order_id", "order_purchase_timestamp", "order_status",
                        "order_estimated_delivery_date"]], on="order_id", how="left")
    ip["ship_limit_days_after_purchase"] = (
        (ip["shipping_limit_date"] - ip["order_purchase_timestamp"]).dt.total_seconds() / 86400)
    late_year = ip[ip["shipping_limit_date"].dt.year > 2018]
    sl = ip["ship_limit_days_after_purchase"]
    R["items"] = {
        "price_profile": numeric_profile(it["price"]),
        "freight_profile": numeric_profile(it["freight_value"]),
        "zero_price_rows": int((it["price"] == 0).sum()),
        "zero_freight_rows": int((it["freight_value"] == 0).sum()),
        "freight_greater_than_price_rows": int((it["freight_value"] > it["price"]).sum()),
        "items_per_order_distribution": it.groupby("order_id")["order_item_id"].max().value_counts().sort_index().to_dict(),
        "order_item_id_gaps": int(
            (it.groupby("order_id")["order_item_id"].agg(lambda s: s.max() != s.nunique())).sum()),
        "shipping_limit_days_profile": numeric_profile(sl),
        "shipping_limit_before_purchase": int((sl < 0).sum()),
        "shipping_limit_gt_30_days": int((sl > 30).sum()),
        "shipping_limit_gt_60_days": int((sl > 60).sum()),
        "shipping_limit_gt_365_days": int((sl > 365).sum()),
        "shipping_limit_year_gt_2018_rows": int(len(late_year)),
        "shipping_limit_year_gt_2018_records": late_year[[
            "order_id", "order_item_id", "order_purchase_timestamp", "shipping_limit_date",
            "order_status", "price"]].to_dict(orient="records"),
        "shipping_limit_gt_60_days_by_status":
            ip[sl > 60]["order_status"].value_counts().to_dict(),
    }

    # 10. SELLERS & GEOLOCATION ─────────────────────────────
    print("[10] Sellers & geolocation")
    in_box = ge["geolocation_lat"].between(*BRAZIL_LAT) & ge["geolocation_lng"].between(*BRAZIL_LNG)
    states_per_zip = ge.groupby("geolocation_zip_code_prefix")["geolocation_state"].nunique()
    cities_raw = ge["geolocation_city"].nunique()
    cities_norm = ge["geolocation_city"].map(norm_text).nunique()
    R["geolocation"] = {
        "rows": int(len(ge)),
        "exact_duplicate_rows": int(ge.duplicated().sum()),
        "rows_after_exact_dedup": int(len(ge) - ge.duplicated().sum()),
        "distinct_zip_prefixes": int(ge["geolocation_zip_code_prefix"].nunique()),
        "rows_per_zip_profile": numeric_profile(ge.groupby("geolocation_zip_code_prefix").size()),
        "rows_outside_brazil_bbox": int((~in_box).sum()),
        "zips_with_multiple_states": int((states_per_zip > 1).sum()),
        "distinct_city_raw": int(cities_raw),
        "distinct_city_normalised": int(cities_norm),
        "invalid_state_codes": int((~ge["geolocation_state"].isin(BRAZIL_UF)).sum()),
    }
    R["sellers"] = {
        "invalid_state_codes": int((~se["seller_state"].isin(BRAZIL_UF)).sum()),
        "distinct_states": int(se["seller_state"].nunique()),
        "distinct_city_raw": int(se["seller_city"].nunique()),
        "distinct_city_normalised": int(se["seller_city"].map(norm_text).nunique()),
    }
    R["customers"]["distinct_city_raw"] = int(cu["customer_city"].nunique())
    R["customers"]["distinct_city_normalised"] = int(cu["customer_city"].map(norm_text).nunique())

    # 11. Immutability: hashes AFTER
    hashes_after = {k: sha256(RAW / f) for k, f in FILES.items()}
    R["raw_file_sha256"] = hashes_before
    R["raw_files_unchanged"] = hashes_before == hashes_after

    out = OUT_DIR / "phase3_quality_results.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(R, f, indent=2, ensure_ascii=False, default=jsonable)
    print(f"\nSaved: {out}")
    print(f"Raw files unchanged (SHA-256 before == after): {R['raw_files_unchanged']}")
    return R


if __name__ == "__main__":
    main()

