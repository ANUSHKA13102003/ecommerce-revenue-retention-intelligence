
"""
Phase 4: Reproducible data-cleaning pipeline
Project: E-commerce Revenue & Customer Retention Intelligence

Raw CSV files are never modified.
All cleaned datasets and quality logs are written to data/processed
and reports/data_quality.
"""

from pathlib import Path
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone

import numpy as np
import pandas as pd


# ---------------------------------------------------------
# 1. PROJECT PATHS AND SETTINGS
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
REPORTS = ROOT / "reports" / "data_quality"

PROCESSED.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

ANALYSIS_START = pd.Timestamp("2017-01-01")
ANALYSIS_END = pd.Timestamp("2018-09-01")

# Brazil bounding box from the project's DQ-27 documentation.
LAT_MIN, LAT_MAX = -33.75, -5.27
LNG_MIN, LNG_MAX = -73.99, -34.79

TABLES = {
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


# ---------------------------------------------------------
# 2. HELPER FUNCTIONS
# ---------------------------------------------------------

def load_csv(table_name):
    """Load a raw CSV without changing the source file."""
    path = RAW / TABLES[table_name]

    if not path.exists():
        raise FileNotFoundError(f"Missing raw dataset: {path}")

    return pd.read_csv(path)


def sha256_file(path):
    """Calculate SHA256 hash of a file."""
    digest = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def save_csv(df, filename):
    """Save a processed dataset."""
    output_path = PROCESSED / filename
    df.to_csv(output_path, index=False)
    return output_path


def normalize_city(value):
    """Normalize city names for consistent matching."""
    if pd.isna(value):
        return pd.NA

    value = str(value).strip().casefold()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        char for char in value
        if not unicodedata.combining(char)
    )
    value = re.sub(r"\s+", " ", value)

    return value if value else pd.NA


def most_frequent(series):
    """Return the most frequent non-null value."""
    values = series.dropna()

    if values.empty:
        return pd.NA

    modes = values.mode()
    return modes.iloc[0] if not modes.empty else values.iloc[0]


def date_column(df, column):
    if column in df.columns:
        df[column] = pd.to_datetime(
            df[column], errors="coerce"
        )


def write_log(data):
    path = REPORTS / "cleaning_log.json"

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=4, default=str)


# ---------------------------------------------------------
# 3. LOAD RAW DATA
# ---------------------------------------------------------

print("\nPHASE 4: LOADING RAW DATA")

raw = {
    name: load_csv(name)
    for name in TABLES
}

input_hashes = {
    TABLES[name]: sha256_file(RAW / TABLES[name])
    for name in TABLES
}

for name, df in raw.items():
    print(f"{name:15} {len(df):>10,} rows")


# ---------------------------------------------------------
# 4. CLEAN ORDERS
# ---------------------------------------------------------

print("\nCleaning orders...")

orders = raw["orders"].copy()

order_date_columns = [
    "order_purchase_timestamp",
    "order_approved_at",
    "order_delivered_carrier_date",
    "order_delivered_customer_date",
    "order_estimated_delivery_date",
]

for column in order_date_columns:
    date_column(orders, column)

orders["missing_delivery_date"] = (
    orders["order_delivered_customer_date"].isna()
)

orders["missing_stage_date"] = (
    orders[
        [
            "order_approved_at",
            "order_delivered_carrier_date",
            "order_delivered_customer_date",
        ]
    ].isna().any(axis=1)
)

orders["carrier_before_purchase"] = (
    orders["order_delivered_carrier_date"]
    < orders["order_purchase_timestamp"]
).fillna(False)

orders["carrier_before_approval"] = (
    orders["order_delivered_carrier_date"]
    < orders["order_approved_at"]
).fillna(False)

orders["delivered_before_carrier"] = (
    orders["order_delivered_customer_date"]
    < orders["order_delivered_carrier_date"]
).fillna(False)

orders["status_date_conflict"] = (
    orders["order_status"].eq("delivered")
    & orders["order_delivered_customer_date"].isna()
)

orders["has_items"] = orders["order_id"].isin(
    raw["items"]["order_id"]
)

orders["in_analysis_window"] = (
    orders["order_purchase_timestamp"].ge(ANALYSIS_START)
    & orders["order_purchase_timestamp"].lt(ANALYSIS_END)
)

orders["delivery_days"] = (
    orders["order_delivered_customer_date"]
    - orders["order_purchase_timestamp"]
).dt.total_seconds() / 86400

orders["is_late"] = (
    orders["order_status"].eq("delivered")
    & orders["order_delivered_customer_date"].notna()
    & orders["order_estimated_delivery_date"].notna()
    & (
        orders["order_delivered_customer_date"]
        > orders["order_estimated_delivery_date"]
    )
)

orders["is_delivered"] = orders["order_status"].eq("delivered")

save_csv(orders, "orders_clean.csv")


# ---------------------------------------------------------
# 5. CLEAN CUSTOMERS
# ---------------------------------------------------------

print("Cleaning customers...")

customers = raw["customers"].copy()

customers["customer_city_normalized"] = (
    customers["customer_city"].apply(normalize_city)
)

save_csv(customers, "customers_clean.csv")


# ---------------------------------------------------------
# 6. CLEAN ORDER ITEMS
# ---------------------------------------------------------

print("Cleaning order items...")

items = raw["items"].copy()

date_column(items, "shipping_limit_date")

items["shipping_limit_outlier"] = (
    items["shipping_limit_date"]
    > (
        orders.set_index("order_id")["order_purchase_timestamp"]
        .reindex(items["order_id"]).reset_index(drop=True)
        + pd.Timedelta(days=60)
    )
).fillna(False)

items["missing_category"] = (
    items["product_id"].map(
        raw["products"].set_index("product_id")["product_category_name"]
    ).isna()
)

save_csv(items, "order_items_clean.csv")


# ---------------------------------------------------------
# 7. CLEAN PAYMENTS
# ---------------------------------------------------------

print("Cleaning payments...")

payments = raw["payments"].copy()

payments["installments_invalid"] = (
    payments["payment_installments"].isna()
    | payments["payment_installments"].le(0)
    | payments["payment_installments"].gt(24)
)

save_csv(payments, "payments_clean.csv")


# ---------------------------------------------------------
# 8. CLEAN REVIEWS
# ---------------------------------------------------------

print("Cleaning reviews...")

reviews = raw["reviews"].copy()

date_column(reviews, "review_creation_date")
date_column(reviews, "review_answer_timestamp")

purchase_dates = orders.set_index("order_id")[
    "order_purchase_timestamp"
]

reviews["review_before_purchase"] = (
    reviews["review_creation_date"]
    < reviews["order_id"].map(purchase_dates)
).fillna(False)

# Keep every original review row in reviews_clean.
save_csv(reviews, "reviews_clean.csv")

# For order-level reporting, use the most recent review per order.
reviews_order = reviews.sort_values(
    ["review_creation_date", "review_answer_timestamp"],
    na_position="first"
).drop_duplicates("order_id", keep="last")

review_summary = (
    reviews_order.groupby("order_id", as_index=False)
    .agg(
        review_score=("review_score", "first"),
        review_creation_date=("review_creation_date", "first"),
        review_answer_timestamp=("review_answer_timestamp", "first"),
        review_before_purchase=("review_before_purchase", "first"),
    )
)

save_csv(review_summary, "order_review_summary.csv")


# ---------------------------------------------------------
# 9. CLEAN PRODUCTS AND CATEGORY TRANSLATIONS
# ---------------------------------------------------------

print("Cleaning products...")

products = raw["products"].copy()
translation = raw["translation"].copy()

products = products.merge(
    translation,
    on="product_category_name",
    how="left",
    validate="many_to_one"
)

# Apply the two manual mappings approved in the cleaning plan.
manual_translations = {
    "pc_gamer": "pc_gamer",
    "portateis_cozinha_e_preparadores_de_alimentos":
        "portable_kitchen_and_food_preparers",
}

products["category_name_en"] = (
    products["product_category_name_english"]
)

for source, target in manual_translations.items():
    products.loc[
        products["product_category_name"].eq(source),
        "category_name_en"
    ] = target

products["category_name_en"] = (
    products["category_name_en"].fillna("Unknown")
)

dimension_columns = [
    "product_length_cm",
    "product_height_cm",
    "product_width_cm",
]

products["missing_dimensions"] = (
    products[dimension_columns].isna().any(axis=1)
)

products["zero_weight"] = (
    products["product_weight_g"].eq(0)
)

save_csv(products, "products_clean.csv")


# ---------------------------------------------------------
# 10. CLEAN SELLERS
# ---------------------------------------------------------

print("Cleaning sellers...")

sellers = raw["sellers"].copy()

sellers["seller_city_normalized"] = (
    sellers["seller_city"].apply(normalize_city)
)

save_csv(sellers, "sellers_clean.csv")


# ---------------------------------------------------------
# 11. GEOLOCATION ZIP LOOKUP
# ---------------------------------------------------------

print("Building ZIP-code geolocation lookup...")

geo = raw["geolocation"].copy()

geo = geo.drop_duplicates()

in_bounds = (
    geo["geolocation_lat"].between(LAT_MIN, LAT_MAX)
    & geo["geolocation_lng"].between(LNG_MIN, LNG_MAX)
)

geo_out_of_bounds_count = int((~in_bounds).sum())

geo = geo.loc[in_bounds].copy()

geo["city_normalized"] = (
    geo["geolocation_city"].apply(normalize_city)
)

geo_lookup = (
    geo.groupby("geolocation_zip_code_prefix")
    .agg(
        geolocation_lat=("geolocation_lat", "median"),
        geolocation_lng=("geolocation_lng", "median"),
        geolocation_state=("geolocation_state", most_frequent),
        geolocation_city=("city_normalized", most_frequent),
    )
    .reset_index()
)

geo_lookup = geo_lookup.rename(
    columns={
        "geolocation_zip_code_prefix": "zip_code_prefix"
    }
)

save_csv(geo_lookup, "geolocation_zip_lookup.csv")


# ---------------------------------------------------------
# 12. ORDER-LEVEL AGGREGATIONS
# ---------------------------------------------------------

print("Creating order-level summaries...")

item_summary = (
    items.groupby("order_id", as_index=False)
    .agg(
        item_count=("order_item_id", "count"),
        item_revenue=("price", "sum"),
        freight_value=("freight_value", "sum"),
        distinct_products=("product_id", "nunique"),
        distinct_sellers=("seller_id", "nunique"),
    )
)

payment_summary = (
    payments.groupby("order_id", as_index=False)
    .agg(
        payment_value=("payment_value", "sum"),
        payment_count=("payment_sequential", "count"),
        max_installments=("payment_installments", "max"),
    )
)

save_csv(item_summary, "order_item_summary.csv")
save_csv(payment_summary, "order_payment_summary.csv")


# ---------------------------------------------------------
# 13. BUILD ORDER-LEVEL ANALYTICS TABLE
# ---------------------------------------------------------

print("Building order-level analytics table...")

order_level = orders.merge(
    customers[
        ["customer_id", "customer_unique_id"]
    ],
    on="customer_id",
    how="left",
    validate="many_to_one"
)

order_level = order_level.merge(
    item_summary,
    on="order_id",
    how="left",
    validate="one_to_one"
)

order_level = order_level.merge(
    payment_summary,
    on="order_id",
    how="left",
    validate="one_to_one"
)

order_level = order_level.merge(
    review_summary,
    on="order_id",
    how="left",
    validate="one_to_one",
    suffixes=("", "_review")
)

order_level["item_count"] = (
    order_level["item_count"].fillna(0).astype(int)
)

order_level["payment_count"] = (
    order_level["payment_count"].fillna(0).astype(int)
)

order_level["has_items"] = order_level["item_count"].gt(0)

save_csv(order_level, "order_level.csv")


# ---------------------------------------------------------
# 14. CUSTOMER AND SELLER GEO LOOKUPS
# ---------------------------------------------------------

print("Creating customer and seller location tables...")

customer_geo = customers.merge(
    geo_lookup,
    left_on="customer_zip_code_prefix",
    right_on="zip_code_prefix",
    how="left",
    validate="many_to_one"
)

seller_geo = sellers.merge(
    geo_lookup,
    left_on="seller_zip_code_prefix",
    right_on="zip_code_prefix",
    how="left",
    validate="many_to_one"
)

save_csv(customer_geo, "customers_with_geolocation.csv")
save_csv(seller_geo, "sellers_with_geolocation.csv")


# ---------------------------------------------------------
# 15. RECONCILIATION AND QUALITY LOG
# ---------------------------------------------------------

print("Validating output datasets...")

row_counts = {
    "orders_clean": len(orders),
    "customers_clean": len(customers),
    "order_items_clean": len(items),
    "payments_clean": len(payments),
    "reviews_clean": len(reviews),
    "products_clean": len(products),
    "sellers_clean": len(sellers),
    "geolocation_zip_lookup": len(geo_lookup),
    "order_item_summary": len(item_summary),
    "order_payment_summary": len(payment_summary),
    "order_review_summary": len(review_summary),
    "order_level": len(order_level),
}

flag_counts = {
    "missing_delivery_date": int(
        orders["missing_delivery_date"].sum()
    ),
    "missing_stage_date": int(
        orders["missing_stage_date"].sum()
    ),
    "carrier_before_purchase": int(
        orders["carrier_before_purchase"].sum()
    ),
    "carrier_before_approval": int(
        orders["carrier_before_approval"].sum()
    ),
    "delivered_before_carrier": int(
        orders["delivered_before_carrier"].sum()
    ),
    "status_date_conflict": int(
        orders["status_date_conflict"].sum()
    ),
    "orders_without_items": int(
        (~orders["has_items"]).sum()
    ),
    "shipping_limit_outliers": int(
        items["shipping_limit_outlier"].sum()
    ),
    "invalid_installments": int(
        payments["installments_invalid"].sum()
    ),
    "reviews_before_purchase": int(
        reviews["review_before_purchase"].sum()
    ),
    "products_missing_dimensions": int(
        products["missing_dimensions"].sum()
    ),
    "products_zero_weight": int(
        products["zero_weight"].sum()
    ),
    "geolocation_out_of_bounds": geo_out_of_bounds_count,
    "customers_without_geolocation": int(
        customer_geo["geolocation_lat"].isna().sum()
    ),
    "sellers_without_geolocation": int(
        seller_geo["geolocation_lat"].isna().sum()
    ),
    "orders_without_payments": int(
        order_level["payment_value"].isna().sum()
    ),
}

reconciliation = {
    "item_price_total": round(float(items["price"].sum()), 2),
    "item_freight_total": round(float(items["freight_value"].sum()), 2),
    "payment_value_total": round(float(payments["payment_value"].sum()), 2),
    "order_level_item_price_total": round(
        float(order_level["item_revenue"].sum()), 2
    ),
    "order_level_payment_total": round(
        float(order_level["payment_value"].sum()), 2
    ),
}

checks = {
    "orders_row_count_preserved": (
        len(orders) == len(raw["orders"])
    ),
    "customers_row_count_preserved": (
        len(customers) == len(raw["customers"])
    ),
    "items_row_count_preserved": (
        len(items) == len(raw["items"])
    ),
    "payments_row_count_preserved": (
        len(payments) == len(raw["payments"])
    ),
    "reviews_row_count_preserved": (
        len(reviews) == len(raw["reviews"])
    ),
    "products_row_count_preserved": (
        len(products) == len(raw["products"])
    ),
    "sellers_row_count_preserved": (
        len(sellers) == len(raw["sellers"])
    ),
    "orders_unique": orders["order_id"].is_unique,
    "customers_unique": customers["customer_id"].is_unique,
    "order_level_unique": order_level["order_id"].is_unique,
    "item_summary_unique": item_summary["order_id"].is_unique,
    "payment_summary_unique": payment_summary["order_id"].is_unique,
    "review_summary_unique": review_summary["order_id"].is_unique,
    "geo_zip_unique": geo_lookup["zip_code_prefix"].is_unique,
    "item_revenue_reconciles": np.isclose(
        reconciliation["item_price_total"],
        reconciliation["order_level_item_price_total"]
    ),
    "payment_reconciles": np.isclose(
        reconciliation["payment_value_total"],
        reconciliation["order_level_payment_total"]
    ),
}

# Confirm raw input files have not changed during the run.
final_hashes = {
    TABLES[name]: sha256_file(RAW / TABLES[name])
    for name in TABLES
}

checks["raw_files_unchanged"] = input_hashes == final_hashes

log = {
    "project": "E-commerce Revenue & Customer Retention Intelligence",
    "phase": "Phase 4 - Data Cleaning",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "analysis_window": {
        "start": str(ANALYSIS_START.date()),
        "end_exclusive": str(ANALYSIS_END.date()),
    },
    "geolocation_boundary": {
        "latitude_min": LAT_MIN,
        "latitude_max": LAT_MAX,
        "longitude_min": LNG_MIN,
        "longitude_max": LNG_MAX,
    },
    "input_sha256": input_hashes,
    "output_row_counts": row_counts,
    "quality_flag_counts": flag_counts,
    "reconciliation": reconciliation,
    "validation_checks": {
        key: bool(value) for key, value in checks.items()
    },
    "all_checks_passed": bool(all(checks.values())),
}

write_log(log)


# ---------------------------------------------------------
# 16. FINAL SUMMARY
# ---------------------------------------------------------

print("\n" + "=" * 60)
print("PHASE 4 CLEANING SUMMARY")
print("=" * 60)

print("\nOUTPUT ROW COUNTS")
for name, count in row_counts.items():
    print(f"{name:30} {count:>10,}")

print("\nQUALITY FLAGS")
for name, count in flag_counts.items():
    print(f"{name:35} {count:>10,}")

print("\nVALIDATION CHECKS")
for name, passed in checks.items():
    status = "PASS" if passed else "FAIL"
    print(f"{name:35} {status}")

print("\nRECONCILIATION")
for name, value in reconciliation.items():
    print(f"{name:35} {value:,.2f}")

print("\nOverall result:", "PASS" if all(checks.values()) else "FAIL")
print(f"Processed files: {PROCESSED}")
print(f"Cleaning log: {REPORTS / 'cleaning_log.json'}")

if not all(checks.values()):
    raise RuntimeError(
        "One or more validation checks failed. Review the cleaning log."
    )

print("\nPHASE 4 CLEANING COMPLETED SUCCESSFULLY.")
